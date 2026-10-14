"""Vaciar chapas (`docs/historico/A6-reparto-por-chapa/`), sin Sparrow: quien
dice si un conjunto entra en una chapa es una cuenta de una dimensión."""
from __future__ import annotations

from app.services.nesting.sparrow_reparto import vaciar_chapas

_CAPACIDAD = 100.0


def _pieza(id_: str) -> dict:
    return {"id": id_, "rotation": 0, "tx": 0.0, "ty": 0.0}


def _chapas(*grupos: str) -> list[list[dict]]:
    """`_chapas("a", "bc")` son dos chapas: una con la pieza a y otra con
    b y c."""
    return [[_pieza(id_) for id_ in grupo] for grupo in grupos]


class _Barras:
    """Piezas de una sola dimensión: un conjunto entra en una chapa si sus
    largos suman a lo sumo `_CAPACIDAD`. Anota cada consulta que recibe."""

    def __init__(self, **largos: float):
        self.largos = largos
        self.consultas: list[frozenset[str]] = []

    def area(self, id_: str) -> float:
        return self.largos[id_]

    def entra(self, ids: list[str]) -> list[dict] | None:
        self.consultas.append(frozenset(ids))
        if sum(self.largos[id_] for id_ in ids) > _CAPACIDAD:
            return None
        return [_pieza(id_) for id_ in ids]


def _repartos(chapas, barras, hay_tiempo=lambda: True) -> list[list[str]]:
    """Cada reparto que entrega `vaciar_chapas`, como chapas ordenadas:
    `["ab", "c"]` es una chapa con a y b y otra con c."""
    return [
        sorted("".join(sorted(q["id"] for q in chapa)) for chapa in reparto)
        for reparto in vaciar_chapas(chapas, barras.area, _CAPACIDAD, barras.entra, hay_tiempo)
    ]


def test_vacia_la_chapa_menos_ocupada_repartiendo_sus_piezas():
    barras = _Barras(a=60, b=30, c=30)

    assert _repartos(_chapas("a", "b", "c"), barras) == [["a", "bc"]]


def test_no_consulta_por_un_conjunto_que_no_entra_ni_por_area():
    barras = _Barras(a=60, b=30, c=30)

    _repartos(_chapas("a", "b", "c"), barras)

    # b va con c; después a no entra con b y c (120), y eso se sabe sin
    # preguntar. La única otra consulta es c con a, al intentar vaciar "bc".
    assert barras.consultas == [frozenset("bc"), frozenset("ac")]


def test_sigue_vaciando_mientras_haya_una_chapa_que_se_pueda():
    barras = _Barras(a=25, b=25, c=25, d=25)

    assert _repartos(_chapas("a", "b", "c", "d"), barras) == [["ab", "c", "d"], ["ab", "cd"], ["abcd"]]


def test_una_chapa_que_no_se_vacia_entera_queda_como_estaba():
    """b entra con a (90), pero c ya no (110): la chapa "bc" no se vacía,
    y b no puede quedar mudada."""
    barras = _Barras(a=70, b=20, c=20)
    chapas = _chapas("a", "bc")

    assert _repartos(chapas, barras) == []
    assert chapas == _chapas("a", "bc")


def test_sin_tiempo_deja_de_consultar_y_descarta_lo_que_estaba_a_medias():
    """Alcanza para tres consultas. La tercera muda b a la chapa "cd"; a se
    queda sin consulta, así que ese reparto a medias no se entrega."""
    barras = _Barras(a=25, b=25, c=25, d=25)

    repartos = _repartos(_chapas("a", "b", "c", "d"), barras, hay_tiempo=lambda: len(barras.consultas) < 3)

    assert repartos == [["ab", "c", "d"], ["ab", "cd"]]
    assert len(barras.consultas) == 3


def test_con_una_sola_chapa_no_consulta_nada():
    barras = _Barras(a=40, b=40)

    assert _repartos(_chapas("ab"), barras) == []
    assert barras.consultas == []


def test_cada_unidad_de_una_pieza_se_reparte_por_separado():
    largos = {"7#0": 50.0, "7#1": 50.0}
    consultas: list[list[str]] = []

    def entra(ids: list[str]) -> list[dict] | None:
        consultas.append(ids)
        return [_pieza(id_) for id_ in ids]

    repartos = list(vaciar_chapas([[_pieza("7#0")], [_pieza("7#1")]], largos.__getitem__, _CAPACIDAD, entra, lambda: True))

    assert [[sorted(q["id"] for q in chapa) for chapa in reparto] for reparto in repartos] == [[["7#0", "7#1"]]]


def test_consulta_por_piezas_que_llenan_la_chapa_justa_aunque_la_suma_redondee_de_mas():
    """0,2 + 83,9 + 15,9 es 100, pero con decimales de máquina da
    100,00000000000001: el filtro por área lo salteaba sin preguntar."""
    largos = {"a": 0.2, "b": 83.9, "c": 15.9}
    consultas: list[list[str]] = []

    def entra(ids: list[str]) -> list[dict] | None:
        consultas.append(sorted(ids))
        return [_pieza(id_) for id_ in ids]

    repartos = list(vaciar_chapas(_chapas("ab", "c"), largos.__getitem__, _CAPACIDAD, entra, lambda: True))

    assert consultas == [["a", "b", "c"]]
    assert len(repartos) == 1
