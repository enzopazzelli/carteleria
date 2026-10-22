"""Los errores de los cálculos, dichos para el usuario (A9, diseño §5.4)."""
from __future__ import annotations

from decimal import Decimal as D

from app.api.traducir_errores import medida, para_el_usuario
from app.mensajes import MENSAJE_INESPERADO, ErrorParaElUsuario, ErrorPrevisto
from app.services.nesting.engine import PiezasSinUbicar
from app.services.nesting.models import Plancha
from app.services.nesting.sparrow import (
    CalculoInterrumpido,
    ErrorGeometriaSparrow,
    PiezaSinContorno,
    PiezasQueNoEntran,
    ResultadoQueNoPasaElControl,
    SinLugarUtil,
    TiempoAgotado,
)

NOMBRES = {"3": "aro", "4": "B-3"}
CHAPA = Plancha(D("1000.00"), D("2000.00"))


def test_la_medida_va_sin_ceros_de_mas():
    assert medida(CHAPA) == "1000 × 2000"
    assert medida(Plancha(D("1000.5"), D("1000"))) == "1000,5 × 1000"


def test_piezas_que_no_entran_con_sus_nombres_y_la_chapa():
    error = para_el_usuario(PiezasQueNoEntran(["3", "4"]), NOMBRES, plancha=CHAPA)

    assert error.mensaje == (
        "Estas piezas no entran en la chapa de 1000 × 2000 con el margen y el kerf actuales: "
        "«aro», «B-3». Elegí una chapa más grande o seccionalas."
    )
    assert error.piezas == (3, 4)


def test_contorno_mal_dibujado_marca_las_piezas():
    error = para_el_usuario(ErrorGeometriaSparrow(["4"]), NOMBRES)

    assert error.mensaje == "Estas piezas tienen el contorno o los huecos mal dibujados: «B-3». Corregí el dibujo y volvé a cargarlo."
    assert error.piezas == (4,) and error.piezas_invalidas == (4,)


def test_pieza_sin_contorno():
    assert para_el_usuario(PiezaSinContorno("3"), NOMBRES).mensaje == "«aro» no tiene contorno: volvé a cargar el dibujo."


def test_chapa_sin_lugar_util_nombra_el_material():
    error = para_el_usuario(SinLugarUtil(), NOMBRES, plancha=CHAPA, material="CHAPA NEGRA")

    assert error.mensaje == (
        "Con el margen, el kerf y la separación de «CHAPA NEGRA», a la chapa de 1000 × 2000 no le queda "
        "lugar útil. Revisá esos valores o elegí otra chapa."
    )


def test_sin_tiempo():
    assert para_el_usuario(TiempoAgotado(30), NOMBRES).mensaje == "No llegó a un resultado en 30 s. Probá con más tiempo."


def test_un_resultado_que_no_pasa_el_control_deja_el_motivo_en_el_detalle():
    error = para_el_usuario(ResultadoQueNoPasaElControl("Índices de chapa inconsistentes."), NOMBRES)

    assert error.mensaje == (
        "El cálculo dio un resultado que no pasó el control (piezas que se pisan, que salen de la chapa "
        "o que faltan) y no se guardó. Probá de nuevo; si se repite, avisá."
    )
    assert error.detalle == "Índices de chapa inconsistentes."


def test_un_calculo_interrumpido_deja_el_registro_en_el_detalle():
    error = para_el_usuario(CalculoInterrumpido("Traceback… PanicException"), NOMBRES)

    assert error.mensaje == "El cálculo se interrumpió por un error interno. Probá de nuevo; si se repite, avisá."
    assert error.detalle == "Traceback… PanicException"


def test_el_motor_rectangular_nombra_las_piezas():
    error = para_el_usuario(PiezasSinUbicar(["3"]), NOMBRES)

    assert error.mensaje == "No se pudieron ubicar estas piezas en la chapa: «aro»."
    assert error.piezas == (3,)


def test_lo_que_ya_es_para_el_usuario_queda_y_lo_demas_va_como_siempre():
    propio = ErrorParaElUsuario("m")

    assert para_el_usuario(propio, NOMBRES) is propio
    assert para_el_usuario(ErrorPrevisto("El grupo no tiene piezas."), NOMBRES).mensaje == "El grupo no tiene piezas."
    assert para_el_usuario(RuntimeError("bum"), NOMBRES).mensaje == MENSAJE_INESPERADO
    assert para_el_usuario(ValueError("invalid literal for int()"), NOMBRES).mensaje == MENSAJE_INESPERADO


from app.api.traducir_errores import con_nombres
from app.mensajes import Aviso


def test_un_aviso_que_nombra_piezas_suma_los_nombres():
    aviso = Aviso("Estas piezas tenían huecos que se pisaban y se calcularon con los huecos unidos (el dibujo guardado no cambia):", (3, 4))

    assert con_nombres(aviso, NOMBRES).mensaje.endswith("no cambia): «aro», «B-3».")


def test_un_aviso_sin_piezas_queda_igual():
    assert con_nombres(Aviso("Se usó todo el tiempo de búsqueda."), NOMBRES) == Aviso("Se usó todo el tiempo de búsqueda.")
