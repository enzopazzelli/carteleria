"""Las herramientas de `scripts/` que se abren con doble clic tienen que
poder arrancar: un import roto las deja caídas sin que la suite lo note."""
import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _visor():
    spec = importlib.util.spec_from_file_location("servidor_visor", SCRIPTS / "servidor_visor.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_visor_se_puede_importar():
    """`Visor de anidado.cmd` levanta este script. Se cayó cuando se borró
    `anidado_huecos.py` (revisión de A10)."""
    assert hasattr(_visor(), "PUERTO_DEFAULT")


def test_el_visor_anida_con_sparrow_y_mete_la_chica_en_el_hueco():
    """Con Sparrow, el visor usa el mismo cálculo que la app, con
    «Aprovechar huecos» (A10): un aro de 90 con un hueco de 60 y un
    cuadrado de 50 entran en una chapa de 100 solo con el cuadrado adentro."""
    from decimal import Decimal as D

    from app.services.nesting.comparador import OpcionFormato
    from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida
    from app.services.nesting.validacion_manual import GeometriaPieza

    def cuadrado(lado, desde=0):
        return [(D(desde), D(desde)), (D(desde + lado), D(desde)), (D(desde + lado), D(desde + lado)), (D(desde), D(desde + lado))]

    piezas = [Pieza("aro", D(90), D(90)), Pieza("chico", D(50), D(50))]
    geometrias = {"aro": GeometriaPieza(D(90), D(90), cuadrado(90), [cuadrado(60, 15)]),
                  "chico": GeometriaPieza(D(50), D(50), cuadrado(50))}
    opcion = OpcionFormato(plancha=Plancha(D(100), D(100)),
                           params=ParametrosCorte(D(2), D(0), D(0), RotacionPermitida.LIBRE_0_90),
                           precio_por_plancha=D(1))

    tanda = _visor()._Tanda("Tanda 1", piezas, opcion, geometrias, motor="sparrow")

    assert len(tanda.posiciones) == 2
    assert {p.plancha_indice for p in tanda.posiciones} == {0}
    assert any("adentro del hueco" in a for a in tanda.advertencias)


def test_el_visor_lee_el_catalogo_que_arma_hoy_el_extractor(tmp_path):
    """Desde el 2026-09-22 `extraer_catalogo_chapa_xlsx.py` escribe el
    precio como `costo_unidad_venta` con su `unidad_venta`, y el visor
    seguía buscando `precio_referencia_m2`: no arrancaba (A10, al ponerlo
    al día). Un catálogo de antes se sigue leyendo."""
    import json
    from decimal import Decimal as D

    spec = importlib.util.spec_from_file_location("_datos_reales", SCRIPTS / "_datos_reales.py")
    datos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(datos)
    base = {"material": "CHAPA NEGRA", "calibre": 22, "espesor_mm": None, "moneda": "ARS"}
    catalogo = {"formatos": [
        {**base, "codigo": "CHA1", "ancho_mm": "1000.00", "alto_mm": "2000.00", "costo_unidad_venta": 10000, "unidad_venta": "M2"},
        {**base, "codigo": "CHA2", "ancho_mm": "1220.00", "alto_mm": "2440.00", "costo_unidad_venta": None, "unidad_venta": "M2"},
        {**base, "codigo": "CHA3", "ancho_mm": "1000.00", "alto_mm": "1000.00", "costo_unidad_venta": 500, "unidad_venta": "UN"},
        {**base, "codigo": "VIEJO", "ancho_mm": "500.00", "alto_mm": "500.00", "precio_referencia_m2": 4000},
    ], "sin_parsear": [], "advertencias": []}
    ruta = tmp_path / "catalogo.json"
    ruta.write_text(json.dumps(catalogo), encoding="utf-8")

    opciones, _ = datos.opciones_desde_catalogo(ruta)
    assert [o.precio_por_plancha for o in opciones] == [D(20000), D(1000)]
    precios = {f["codigo"]: f["precio_referencia_m2"] for f in datos.formatos_del_catalogo(ruta)}
    assert precios == {"CHA1": 10000, "CHA2": None, "CHA3": None, "VIEJO": 4000}
