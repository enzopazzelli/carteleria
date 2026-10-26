"""Los pasos de la tarjeta de un trabajo (`docs/plan/A16-pagina-de-inicio/diseno.md §5.4`)."""
from __future__ import annotations

import pytest

from app.pasos import GrupoParaPasos, Pasos, TrabajoParaPasos, pasos_del_trabajo


def _grupo(nombre="Calibre 18", *, con_piezas=True, terminado=False, ultimo=None):
    return GrupoParaPasos(nombre, con_piezas, terminado, ultimo)


def _trabajo(*, piezas=2, sin_grupo=0, grupos=(), presupuesto=None):
    return TrabajoParaPasos(piezas, sin_grupo, list(grupos), presupuesto)


def test_sin_piezas_falta_el_dibujo():
    assert pasos_del_trabajo(_trabajo(piezas=0)) == Pasos(
        "pendiente", "pendiente", "pendiente", "pendiente", "Falta cargar el dibujo", "piezas")


def test_sin_grupos_faltan_los_grupos():
    p = pasos_del_trabajo(_trabajo(sin_grupo=2))
    assert (p.piezas, p.grupos, p.frase, p.destino) == ("hecho", "pendiente", "Falta armar los grupos", "grupos")


def test_con_piezas_sin_grupo_las_cuenta():
    p = pasos_del_trabajo(_trabajo(piezas=5, sin_grupo=3, grupos=[_grupo(terminado=True, ultimo="lista")]))
    assert (p.grupos, p.anidado, p.frase) == ("a_medias", "hecho", "Faltan 3 piezas sin grupo")


def test_una_sola_pieza_sin_grupo_va_en_singular():
    assert pasos_del_trabajo(_trabajo(sin_grupo=1, grupos=[_grupo()])).frase == "Falta 1 pieza sin grupo"


def test_sin_anidar():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo()]))
    assert (p.anidado, p.frase, p.destino) == ("pendiente", "Falta anidar Calibre 18", "anidado")


@pytest.mark.parametrize("estado", ["encolada", "corriendo"])
def test_un_anidado_corriendo(estado):
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(ultimo=estado)]))
    assert (p.anidado, p.frase) == ("a_medias", "Anidando Calibre 18…")


def test_anidando_otra_vez_aunque_haya_uno_terminado():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(terminado=True, ultimo="corriendo")]))
    assert (p.anidado, p.frase) == ("a_medias", "Anidando Calibre 18…")


def test_un_anidado_con_error():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo("Chapa20", ultimo="error")]))
    assert (p.anidado, p.frase) == ("error", "El anidado de Chapa20 terminó con error")


def test_un_error_despues_de_uno_terminado_no_cuenta():
    assert pasos_del_trabajo(_trabajo(grupos=[_grupo(terminado=True, ultimo="error")])).anidado == "hecho"


def test_dos_grupos_con_uno_solo_anidado_nombra_el_que_falta():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo("A", terminado=True, ultimo="lista"), _grupo("B")]))
    assert (p.anidado, p.frase) == ("a_medias", "Falta anidar B")


def test_un_anidado_cancelado_cuenta_como_sin_anidar():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(ultimo="cancelada")]))
    assert (p.anidado, p.frase) == ("pendiente", "Falta anidar Calibre 18")


def test_un_grupo_vacio_no_cuenta():
    grupos = [_grupo("A", terminado=True, ultimo="lista"), _grupo("Vacío", con_piezas=False)]
    assert pasos_del_trabajo(_trabajo(grupos=grupos)).anidado == "hecho"


def test_anidado_sin_presupuesto_lleva_a_chapas():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(terminado=True, ultimo="lista")]))
    assert (p.presupuesto, p.frase, p.destino) == ("pendiente", "Falta el presupuesto", "chapas")


def test_con_presupuesto_dice_su_estado_y_lleva_al_costeo():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(terminado=True, ultimo="lista")], presupuesto="BORRADOR"))
    assert p == Pasos("hecho", "hecho", "hecho", "hecho", "Presupuesto en borrador", "costeo")
