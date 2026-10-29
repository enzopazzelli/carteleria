"""El resumen de materiales: el puente entre F2 y F3.

Cada test verifica que un caso concreto NO inventa un número: si falta
un dato, el costo tiene que quedar en `None` con una advertencia, nunca
en cero (que se confundiría con "sale gratis").
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.costeo import resumen_materiales
from app.modelos import (
    Base,
    Colocacion,
    EjecucionNesting,
    Formato,
    GrupoDeCorte,
    Material,
    ParametrosCorteMaterial,
    Pieza,
    Trabajo,
)
from app.modelos.base import crear_motor


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion


def _material_con_formato(
    sesion, nombre="Chapa negra", espesor="cal. 22", *, precio=Decimal("120540.20"),
    unidad_venta="M2", factor=Decimal("2.97"), costo_unidad_venta=Decimal("50732.41"),
    moneda="ARS",
):
    material = Material(nombre=nombre, espesor=espesor)
    sesion.add(material)
    sesion.flush()
    formato = Formato(
        material_id=material.id,
        ancho_mm=Decimal("1220"),
        alto_mm=Decimal("2440"),
        moneda=moneda,
        precio_compra=precio,
        unidad_compra="PLANCHA",
        unidad_venta=unidad_venta,
        factor_conversion=factor,
        costo_unidad_venta=costo_unidad_venta,
    )
    sesion.add(formato)
    sesion.add(
        ParametrosCorteMaterial(
            material_id=material.id,
            kerf_mm=Decimal("2"),
            margen_borde_mm=Decimal("10"),
            separacion_piezas_mm=Decimal("5"),
        )
    )
    sesion.flush()
    return material, formato


_CONTORNO = [["0", "0"], ["100", "0"], ["100", "50"], ["0", "50"]]


def _pieza(sesion, trabajo, grupo, nombre, *, cantidad=1, **campos) -> Pieza:
    pieza = Pieza(
        trabajo_id=trabajo.id,
        grupo_id=grupo.id if grupo is not None else None,
        id_origen=nombre,
        ancho_mm=Decimal("100"),
        alto_mm=Decimal("50"),
        contorno_mm=_CONTORNO,
        cantidad=cantidad,
        **campos,
    )
    sesion.add(pieza)
    sesion.flush()
    return pieza


def _anidar(sesion, grupo, *, planchas=3, definitiva=True, estado="lista", motor="rectpack") -> EjecucionNesting:
    """Un anidado de lo que hoy se corta del grupo: una colocación por cada
    copia de cada pieza, como guarda una corrida terminada."""
    ejecucion = EjecucionNesting(
        grupo_id=grupo.id, motor=motor, estado=estado, planchas_usadas=planchas, es_definitiva=definitiva
    )
    sesion.add(ejecucion)
    sesion.flush()
    if estado == "lista":
        for pieza in sesion.scalars(select(Pieza).where(Pieza.grupo_id == grupo.id, Pieza.descartada.is_(False))):
            for instancia in range(pieza.cantidad):
                sesion.add(Colocacion(
                    ejecucion_id=ejecucion.id, pieza_id=pieza.id, instancia=instancia, plancha_indice=0,
                    centro_x_mm=Decimal("100"), centro_y_mm=Decimal("100"), angulo_grados=Decimal("0"),
                ))
    sesion.flush()
    return ejecucion


def _trabajo_con_grupo(sesion, formato, *, planchas=3, definitiva=True, estado="lista", piezas=1):
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    grupo = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Grupo 1", formato_id=formato.id, orden=0)
    sesion.add(grupo)
    sesion.flush()
    for numero in range(1, piezas + 1):
        _pieza(sesion, trabajo, grupo, f"pieza-{numero}")
    _anidar(sesion, grupo, planchas=planchas, definitiva=definitiva, estado=estado)
    sesion.commit()
    return trabajo, grupo


def test_calcula_el_costo_por_area_de_plancha_y_precio_de_m2(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, _ = _trabajo_con_grupo(sesion, formato, planchas=3)

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    area_una_plancha = Decimal("1.220") * Decimal("2.440")
    esperado = area_una_plancha * 3 * Decimal("50732.41")
    assert linea.area_total_m2 == area_una_plancha * 3
    assert linea.costo_estimado == esperado
    assert linea.moneda == "ARS"
    assert linea.precio_unitario == Decimal("50732.41")
    assert linea.unidad_venta == "M2"
    assert linea.ejecucion_id is not None
    assert resumen.costo_total_por_moneda["ARS"] == esperado
    assert linea.advertencias == []


def test_no_costea_con_plano_de_otro_formato(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato)
    grupo.ejecuciones[0].parametros = {"formato": {
        "id": formato.id, "ancho_mm": "1000", "alto_mm": "2000",
    }}
    sesion.commit()
    linea = resumen_materiales(sesion, trabajo.id).lineas[0]
    assert linea.costo_estimado is None
    assert linea.area_total_m2 is None
    assert linea.ejecucion_id is None
    assert any("cambió después" in aviso for aviso in linea.advertencias)


def test_definitiva_fallida_no_desplaza_una_corrida_valida(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato, definitiva=False)
    valida_id = grupo.ejecuciones[0].id
    sesion.add(EjecucionNesting(grupo_id=grupo.id, motor="sparrow", estado="error", es_definitiva=True))
    sesion.commit()
    sesion.expire_all()
    linea = resumen_materiales(sesion, trabajo.id).lineas[0]
    assert linea.ejecucion_id == valida_id
    assert linea.costo_estimado is not None


def test_un_grupo_sin_material_no_tiene_costo_pero_avisa(sesion):
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    sesion.add(GrupoDeCorte(trabajo_id=trabajo.id, nombre="Sin decidir", formato_id=None, orden=0))
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.costo_estimado is None
    assert linea.material_nombre is None
    assert any("sin material asignado" in a for a in linea.advertencias)
    assert resumen.costo_total_por_moneda == {}


def test_un_grupo_con_material_pero_sin_anidar_no_inventa_costo(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    sesion.add(GrupoDeCorte(trabajo_id=trabajo.id, nombre="Grupo 1", formato_id=formato.id, orden=0))
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.costo_estimado is None
    assert linea.material_nombre == "Chapa negra"
    assert any("no tiene un anidado terminado" in a for a in linea.advertencias)


def test_un_formato_sin_precio_no_calcula_costo_cero(sesion):
    _, formato = _material_con_formato(sesion, costo_unidad_venta=None)
    trabajo, _ = _trabajo_con_grupo(sesion, formato, planchas=2)

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.area_total_m2 is not None, "el área se calcula igual, con o sin precio"
    assert linea.costo_estimado is None
    assert linea.precio_unitario is None
    assert any("no tiene precio cargado" in a for a in linea.advertencias)


def test_una_unidad_de_venta_distinta_de_m2_no_se_multiplica_a_ciegas(sesion):
    _, formato = _material_con_formato(sesion, unidad_venta="METRO_LINEAL", factor=Decimal("1"))
    trabajo, _ = _trabajo_con_grupo(sesion, formato, planchas=1)

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.costo_estimado is None
    assert any("no se calcula solo" in a for a in linea.advertencias)


def test_dos_grupos_de_distinto_material_dan_dos_lineas_separadas(sesion):
    """El caso que motiva todo esto: CART-302 pide una línea por
    material, no un total mezclado."""
    _, chapa = _material_con_formato(sesion, nombre="Chapa negra")
    _, acrilico = _material_con_formato(
        sesion, nombre="Acrílico", espesor=None, costo_unidad_venta=Decimal("10000")
    )
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    g1 = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Chapa negra", formato_id=chapa.id, orden=0)
    g2 = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Acrílico frente", formato_id=acrilico.id, orden=1)
    sesion.add_all([g1, g2])
    sesion.flush()
    _pieza(sesion, trabajo, g1, "chapa-1")
    _pieza(sesion, trabajo, g2, "acrilico-1")
    _anidar(sesion, g1, planchas=2)
    _anidar(sesion, g2, planchas=1, motor="deepnest")
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    assert len(resumen.lineas) == 2
    assert {l.material_nombre for l in resumen.lineas} == {"Chapa negra", "Acrílico"}
    assert resumen.costo_total_por_moneda["ARS"] > 0


def test_sin_ejecucion_definitiva_usa_la_mas_reciente_lista_y_avisa(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato, planchas=5, definitiva=False)
    # Una segunda ejecución, más reciente, tampoco marcada definitiva.
    _anidar(sesion, grupo, planchas=4, definitiva=False, motor="deepnest")
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.planchas_usadas == 4, "tiene que usar la más reciente, no la primera"
    assert any("ningún anidado está elegido para cotizar" in a for a in linea.advertencias)


def test_piezas_sin_asignar_se_reportan_en_advertencias_generales(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato)
    sesion.add(
        Pieza(
            trabajo_id=trabajo.id,
            grupo_id=None,
            id_origen="pieza-suelta",
            ancho_mm=Decimal("100"),
            alto_mm=Decimal("50"),
            contorno_mm=[["0", "0"], ["100", "0"], ["100", "50"], ["0", "50"]],
        )
    )
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    assert any("1 pieza(s) todavía sin asignar" in a for a in resumen.advertencias_generales)


def test_una_pieza_descartada_no_cuenta_como_sin_asignar(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato)
    sesion.add(
        Pieza(
            trabajo_id=trabajo.id,
            grupo_id=None,
            id_origen="pieza-descartada",
            ancho_mm=Decimal("100"),
            alto_mm=Decimal("50"),
            contorno_mm=[["0", "0"], ["100", "0"], ["100", "50"], ["0", "50"]],
            descartada=True,
        )
    )
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    assert resumen.advertencias_generales == []


def test_moverse_de_grupo_es_solo_actualizar_grupo_id(sesion):
    """Es el flujo que pidió el usuario: sacar una pieza de un layout y
    pasarla a otro. Acá se prueba que el modelo lo soporta sin ceremonia."""
    _, chapa = _material_con_formato(sesion, nombre="Chapa negra")
    _, acrilico = _material_con_formato(sesion, nombre="Acrílico", espesor=None)
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    g1 = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Chapa", formato_id=chapa.id, orden=0)
    g2 = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Acrílico", formato_id=acrilico.id, orden=1)
    sesion.add_all([g1, g2])
    sesion.flush()
    pieza = Pieza(
        trabajo_id=trabajo.id,
        grupo_id=g1.id,
        id_origen="pieza-1",
        ancho_mm=Decimal("100"),
        alto_mm=Decimal("50"),
        contorno_mm=[["0", "0"], ["100", "0"], ["100", "50"], ["0", "50"]],
    )
    sesion.add(pieza)
    sesion.commit()

    pieza.grupo_id = g2.id
    sesion.commit()
    # Leer los ids ANTES de expunge: después, cualquier objeto queda
    # expirado y desprendido, y hasta `.id` dispara un refresh que falla.
    pieza_id, g2_id, trabajo_id = pieza.id, g2.id, trabajo.id
    sesion.expunge_all()

    releida = sesion.get(Pieza, pieza_id)
    assert releida.grupo_id == g2_id
    assert releida.trabajo_id == trabajo_id, "sigue perteneciendo al mismo trabajo"


# --- El anidado vencido (A17, tarea 35) ---------------------------------------
# Si lo que se corta del grupo no es lo que se anidó, el anidado no se cobra.

_CAMBIARON = "Grupo «Grupo 1»: las piezas cambiaron después del anidado. Anidá de nuevo antes de presupuestar."


def _de(sesion, nombre: str) -> Pieza:
    return sesion.scalars(select(Pieza).where(Pieza.id_origen == nombre)).one()


def _sin_costo_por(linea, aviso: str) -> None:
    assert linea.costo_estimado is None
    assert linea.ejecucion_id is None
    assert aviso in linea.advertencias
    assert not any("todavía no tiene un anidado terminado" in a for a in linea.advertencias)


def test_sacar_una_pieza_despues_de_anidar_vence_el_anidado(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, _ = _trabajo_con_grupo(sesion, formato, piezas=2)
    _de(sesion, "pieza-2").grupo_id = None
    sesion.commit()

    _sin_costo_por(resumen_materiales(sesion, trabajo.id).lineas[0], _CAMBIARON)


def test_sumar_una_pieza_despues_de_anidar_vence_el_anidado(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato)
    _pieza(sesion, trabajo, grupo, "pieza-nueva")
    sesion.commit()

    _sin_costo_por(resumen_materiales(sesion, trabajo.id).lineas[0], _CAMBIARON)


def test_cambiar_una_cantidad_despues_de_anidar_vence_el_anidado(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, _ = _trabajo_con_grupo(sesion, formato)
    _de(sesion, "pieza-1").cantidad = 2
    sesion.commit()

    _sin_costo_por(resumen_materiales(sesion, trabajo.id).lineas[0], _CAMBIARON)


def test_descartar_una_pieza_despues_de_anidar_vence_el_anidado(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, _ = _trabajo_con_grupo(sesion, formato, piezas=2)
    _de(sesion, "pieza-2").descartada = True
    sesion.commit()

    _sin_costo_por(resumen_materiales(sesion, trabajo.id).lineas[0], _CAMBIARON)


def test_seccionar_una_pieza_despues_de_anidar_vence_el_anidado(sesion):
    """Seccionar descarta la original y suma sus tramos al grupo."""
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato)
    original = _de(sesion, "pieza-1")
    original.descartada = True
    _pieza(sesion, trabajo, grupo, "pieza-1 tramo 1", seccionada_de_id=original.id)
    _pieza(sesion, trabajo, grupo, "pieza-1 tramo 2", seccionada_de_id=original.id)
    sesion.commit()

    _sin_costo_por(resumen_materiales(sesion, trabajo.id).lineas[0], _CAMBIARON)


def test_un_grupo_que_se_quedo_sin_piezas_no_cobra_su_anidado_viejo(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, _ = _trabajo_con_grupo(sesion, formato)
    _de(sesion, "pieza-1").grupo_id = None
    sesion.commit()

    _sin_costo_por(
        resumen_materiales(sesion, trabajo.id).lineas[0],
        "Grupo «Grupo 1»: se quedó sin piezas, así que no se cobra su anidado viejo.",
    )


def test_una_pieza_con_cantidad_2_anidada_sigue_vigente(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    grupo = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Grupo 1", formato_id=formato.id, orden=0)
    sesion.add(grupo)
    sesion.flush()
    _pieza(sesion, trabajo, grupo, "doble", cantidad=2)
    _anidar(sesion, grupo)
    sesion.commit()

    linea = resumen_materiales(sesion, trabajo.id).lineas[0]

    assert linea.costo_estimado is not None
    assert linea.advertencias == []


def test_una_pieza_descartada_antes_de_anidar_no_lo_vence(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    grupo = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Grupo 1", formato_id=formato.id, orden=0)
    sesion.add(grupo)
    sesion.flush()
    _pieza(sesion, trabajo, grupo, "se-corta")
    _pieza(sesion, trabajo, grupo, "hueco", descartada=True)
    _anidar(sesion, grupo)
    sesion.commit()

    linea = resumen_materiales(sesion, trabajo.id).lineas[0]

    assert linea.costo_estimado is not None
    assert linea.advertencias == []


def test_con_el_elegido_vencido_cuenta_el_mas_reciente_al_dia(sesion):
    """Se sumó una pieza y se volvió a anidar, pero el elegido sigue siendo
    el de antes (Enzo, 2026-10-29: opción a)."""
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato, planchas=3)
    elegido = grupo.ejecuciones[0]
    _pieza(sesion, trabajo, grupo, "pieza-nueva")
    al_dia = _anidar(sesion, grupo, planchas=4, definitiva=False)
    sesion.commit()

    linea = resumen_materiales(sesion, trabajo.id).lineas[0]

    assert linea.ejecucion_id == al_dia.id
    assert linea.planchas_usadas == 4
    assert linea.advertencias == [
        f"Grupo «Grupo 1»: el anidado elegido (#{elegido.id}) es de antes de que cambiaran las piezas; "
        f"se usó el #{al_dia.id}, el más reciente al día. Confirmá cuál vale antes de cotizar en serio."
    ]


def test_el_anidado_dice_si_esta_vencido(sesion):
    from app.api.esquemas_nesting import EjecucionLeer

    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato, piezas=2)
    ejecucion = grupo.ejecuciones[0]
    assert EjecucionLeer.model_validate(ejecucion).vencido is False

    _de(sesion, "pieza-2").grupo_id = None
    sesion.commit()

    assert EjecucionLeer.model_validate(ejecucion).vencido is True


def test_un_anidado_sin_terminar_no_esta_vencido(sesion):
    """Todavía no tiene colocaciones: vencido es solo un anidado terminado."""
    from app.api.esquemas_nesting import EjecucionLeer

    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato, estado="corriendo", definitiva=False)

    assert EjecucionLeer.model_validate(grupo.ejecuciones[0]).vencido is False


def test_sin_elegido_y_el_mas_reciente_vencido_el_aviso_dice_cual_se_uso(sesion):
    """Se usa uno más viejo que está al día: el aviso decía «se usó el más
    reciente» (revisión de la tanda 7)."""
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato, definitiva=False)
    al_dia = grupo.ejecuciones[0]
    nueva = _pieza(sesion, trabajo, grupo, "pieza-nueva")
    _anidar(sesion, grupo, definitiva=False)
    nueva.grupo_id = None  # el más reciente queda con una de más
    sesion.commit()

    linea = resumen_materiales(sesion, trabajo.id).lineas[0]

    assert linea.ejecucion_id == al_dia.id
    assert linea.advertencias == [
        f"Grupo «Grupo 1»: ningún anidado está elegido para cotizar; se usó el #{al_dia.id}, "
        "el más reciente al día. Confirmá cuál vale antes de cotizar en serio."
    ]


def test_con_el_elegido_al_dia_no_se_revisan_los_otros(sesion, monkeypatch):
    """Con meses de pruebas sobre un trabajo, revisar cada anidado del
    historial cuesta unos 3 ms por anidado (revisión de la tanda 7)."""
    from app import costeo

    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato)
    for _ in range(5):
        _anidar(sesion, grupo, definitiva=False)
    sesion.commit()
    revisados = []
    original = costeo.anidado_vigente
    monkeypatch.setattr(costeo, "anidado_vigente", lambda g, e: revisados.append(e.id) or original(g, e))

    costeo._ejecucion_para_costear(grupo)

    assert len(revisados) == 1
