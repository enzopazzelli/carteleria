"""Cola de trabajos — paso 4 de `docs/historico/PLAN-SLICE-VERTICAL.md`.

Interfaz mínima: encolar una tarea sin bloquear a quien la pide. El
código de negocio conoce "encolar", no si atrás hay un hilo (este
adaptador, modo local) o Celery (producción, `ADR-05`) — cambiar de uno
a otro es reemplazar esta clase, no tocar a quien la usa.
"""
from __future__ import annotations

import threading
from collections.abc import Callable


class ColaDeTrabajosEnProceso:
    """Un hilo por tarea encolada, sin cola de espera ni límite de
    concurrencia. Con tres anidados de Sparrow a la vez, en una máquina
    de 4 núcleos, todos terminan bien y cada uno dentro de su tiempo
    máximo (medido el 2026-10-23): lo que pierde cada uno es búsqueda.

    Sin persistencia entre reinicios: una corrida que el proceso deja a
    medias no sigue. Al arrancar, el servidor la pasa a error
    (`cortar_corridas_colgadas`, A10). Que sobreviva a un reinicio lo
    resuelve pasar a Celery/Redis (`ADR-05`), no esta clase.
    """

    def encolar(self, tarea: Callable[[], None]) -> None:
        threading.Thread(target=tarea, daemon=True).start()


_cola = ColaDeTrabajosEnProceso()


def cola_de_trabajos() -> ColaDeTrabajosEnProceso:
    return _cola
