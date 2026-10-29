"""Ayudas comunes de las pruebas de la API."""
from __future__ import annotations

import threading
import time


def mensaje_de(respuesta) -> str:
    """El texto del error de una respuesta (A9: `detail` es `{mensaje, detalle, ...}`)."""
    return respuesta.json()["detail"]["mensaje"]


def segundos_que_tarda_otro_pedido(cliente, pedir_el_lento, modulo, nombre: str, monkeypatch) -> float:
    """Cuánto tarda `GET /trabajos` en contestar mientras `pedir_el_lento`
    está adentro de `modulo.nombre` (la lectura del DXF), que espera hasta
    que se la suelte. Un DXF que tardaba en leerse trababa toda la app, no
    solo su pedido (revisión de la tanda 6 de A17)."""
    empezo, soltar = threading.Event(), threading.Event()
    original = getattr(modulo, nombre)

    def lento(*args, **kwargs):
        empezo.set()
        soltar.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(modulo, nombre, lento)
    respuestas = []
    hilo = threading.Thread(target=lambda: respuestas.append(pedir_el_lento()))
    hilo.start()
    try:
        assert empezo.wait(5), "la lectura no arrancó"
        inicio = time.perf_counter()
        assert cliente.get("/trabajos").status_code == 200
        return time.perf_counter() - inicio
    finally:
        soltar.set()
        hilo.join(10)
        assert respuestas and respuestas[0].status_code == 200, respuestas
