"""Segunda etapa del anidado con Sparrow: vaciar chapas.

Sparrow acomoda las piezas en una franja larga, y `sparrow_worker` la
corta en chapas: recorta una ventana del ancho de una chapa, se queda con
las piezas que cayeron enteras y recalcula el resto. Las últimas chapas
quedan a medio llenar. Esta etapa parte de ese resultado y trata de
vaciar una chapa repartiendo sus piezas en las demás, de a una,
preguntando cada vez si «las piezas de esa chapa, más esta» entran en una
sola chapa.

Es lógica pura: no conoce a Sparrow. La pregunta la responde
`entra_en_una_chapa`, que el worker arma con Sparrow y los tests con una
cuenta simple. Mediciones y diseño: `docs/historico/A6-reparto-por-chapa/`.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator

#: Las colocaciones de una chapa: `{"id", "rotation", "tx", "ty"}`, sin `sheet`.
Chapa = list[dict]


def vaciar_chapas(
    chapas: list[Chapa],
    area: Callable[[str], float],
    area_util: float,
    entra_en_una_chapa: Callable[[list[str]], Chapa | None],
    hay_tiempo: Callable[[], bool],
) -> Iterator[list[Chapa]]:
    """Entrega cada reparto que usa una chapa menos que el anterior, a
    medida que aparece. No modifica `chapas`. Termina cuando ninguna chapa
    se puede vaciar o cuando `hay_tiempo()` dice que no.

    Se intenta primero con la chapa que menos área de piezas tiene, que es
    la más barata de vaciar. Sus piezas van de mayor a menor, cada una a
    la chapa menos ocupada que la acepte. Si una pieza no entra en
    ninguna, esa chapa queda como estaba y no se vuelve a intentar: las
    demás solo pueden llenarse más.

    Un `None` de `entra_en_una_chapa` no prueba que el conjunto no entre
    (Sparrow corta por tiempo). El costo de un «no» equivocado es una
    chapa que no se vació."""
    actuales = [list(chapa) for chapa in chapas]
    sin_salida: set[frozenset[str]] = set()

    def ocupado(chapa: Chapa) -> float:
        return sum(area(q["id"]) for q in chapa)

    def ids(chapa: Chapa) -> frozenset[str]:
        return frozenset(q["id"] for q in chapa)

    while len(actuales) > 1:
        donantes = [chapa for chapa in sorted(actuales, key=ocupado) if ids(chapa) not in sin_salida]
        if not donantes:
            return
        donante = donantes[0]
        # Copia de la lista, no de las chapas: una chapa que recibe se
        # reemplaza en `resto`, y `actuales` no cambia hasta que la
        # donante se vació entera.
        resto = [chapa for chapa in actuales if chapa is not donante]
        for pieza in sorted((q["id"] for q in donante), key=area, reverse=True):
            recibida = False
            for indice in sorted(range(len(resto)), key=lambda i: ocupado(resto[i])):
                if ocupado(resto[indice]) + area(pieza) > area_util:
                    continue
                if not hay_tiempo():
                    return
                nueva = entra_en_una_chapa([*(q["id"] for q in resto[indice]), pieza])
                if nueva is not None:
                    resto[indice] = nueva
                    recibida = True
                    break
            if not recibida:
                sin_salida.add(ids(donante))
                break
        else:
            actuales = resto
            yield [list(chapa) for chapa in actuales]
