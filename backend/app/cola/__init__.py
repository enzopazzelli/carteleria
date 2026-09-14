"""Cola de trabajos — paso 4 de `docs/PLAN-SLICE-VERTICAL.md`.

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
    concurrencia — alcanza para un usuario local corriendo un anidado
    por vez.

    Sin persistencia entre reinicios: si el proceso muere a mitad de
    una corrida, la ejecución queda en `corriendo` para siempre. Es un
    límite conocido del modo local; lo resuelve pasar a Celery/Redis
    (`ADR-05`), no esta clase.
    """

    def encolar(self, tarea: Callable[[], None]) -> None:
        threading.Thread(target=tarea, daemon=True).start()


_cola = ColaDeTrabajosEnProceso()


def cola_de_trabajos() -> ColaDeTrabajosEnProceso:
    return _cola
