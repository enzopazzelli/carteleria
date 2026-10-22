"""La forma de un mensaje (A9, diseño §5.2)."""
from __future__ import annotations

from app.api.esquemas_mensajes import AvisoLeer, ErrorLeer, avisos_leer
from app.mensajes import (
    MENSAJE_INESPERADO,
    Aviso,
    ChapaNombrada,
    ErrorParaElUsuario,
    ErrorPrevisto,
    aviso_desde,
    error_para_guardar,
    lista_de_nombres,
)


def test_un_aviso_guardado_antes_de_a9_es_un_texto_suelto():
    assert aviso_desde("aviso viejo") == Aviso("aviso viejo")


def test_un_aviso_guardado_como_dict_vuelve_con_lo_que_nombra():
    guardado = {"mensaje": "m", "piezas": [3, 4], "chapas": [{"ejecucion_id": 7, "plancha": 1}]}

    aviso = aviso_desde(guardado)

    assert aviso == Aviso("m", (3, 4), (ChapaNombrada(7, 1),))
    assert aviso.como_dict() == guardado


def test_el_error_para_el_usuario_lleva_detalle_piezas_y_chapas():
    error = ErrorParaElUsuario("Texto claro", detalle="técnico", piezas=["3"], chapas=[ChapaNombrada(7, 0)], estado=409)

    assert error.estado == 409
    assert error.como_dict() == {
        "mensaje": "Texto claro",
        "detalle": "técnico",
        "piezas": [3],
        "chapas": [{"ejecucion_id": 7, "plancha": 0}],
    }


def test_las_piezas_invalidas_viajan_solo_si_hay():
    assert "piezas_invalidas" not in ErrorParaElUsuario("m").como_dict()
    assert ErrorParaElUsuario("m", piezas_invalidas=["5"]).como_dict()["piezas_invalidas"] == [5]


def test_la_lista_de_nombres_sigue_el_orden_y_no_repite():
    nombres = {"3": "aro", "4": "B-3"}

    assert lista_de_nombres(["4", "3", "4"], nombres) == "«B-3», «aro»"
    assert lista_de_nombres([9], nombres) == "«sin nombre»"


def test_un_error_previsto_lleva_su_texto_sin_traza():
    falla = error_para_guardar(ErrorPrevisto("El grupo no tiene piezas."))

    assert falla.mensaje == "El grupo no tiene piezas."
    assert falla.detalle is None
    assert isinstance(ErrorPrevisto("m"), ValueError), "lo que hoy ataja un ValueError lo sigue atajando"


def test_el_error_de_una_biblioteca_no_se_muestra_como_mensaje():
    """Revisión de A9: un `UnicodeDecodeError` es un `ValueError`, y su texto
    en inglés llegaba a la pantalla (el error del 14/10)."""
    try:
        b"\xed".decode("utf-8")
    except UnicodeDecodeError as error:
        falla = error_para_guardar(error)

    assert falla.mensaje == MENSAJE_INESPERADO
    assert "UnicodeDecodeError" in falla.detalle


def test_cualquier_otra_excepcion_es_inesperada_con_la_traza_en_el_detalle():
    try:
        raise RuntimeError("bum")
    except RuntimeError as error:
        falla = error_para_guardar(error)

    assert falla.mensaje == MENSAJE_INESPERADO
    assert falla.estado == 500
    assert "RuntimeError: bum" in falla.detalle


def test_un_error_para_el_usuario_queda_como_esta():
    error = ErrorParaElUsuario("m")

    assert error_para_guardar(error) is error


def test_los_esquemas_leen_avisos_viejos_y_nuevos():
    leidos = [AvisoLeer(**a) for a in avisos_leer(["viejo", Aviso("nuevo", (2,))])]

    assert [a.mensaje for a in leidos] == ["viejo", "nuevo"]
    assert leidos[1].piezas == [2]
    assert ErrorLeer(mensaje="m").detalle is None
