"""El registro del servidor (A9, `docs/historico/A9-mensajes-entendibles/diseno.md §5.3`).

Guarda, con fecha y hora, cada error inesperado y cada corrida o
comparación que falla, con su traza: lo que la pantalla muestra en «Ver
detalle técnico» y no se pierde al cerrar la página. Rota por tamaño
(`PAR-54`, `PAR-55`)."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

NOMBRE = "carteleria"


def registro() -> logging.Logger:
    return logging.getLogger(NOMBRE)


def configurar_registro(carpeta: Path, tamano_bytes: int, archivos: int) -> Path:
    """Deja el registro escribiendo en `carpeta/servidor.log`. Se puede
    llamar varias veces (cada arranque de la app, cada prueba): si ya
    escribe ahí no agrega otro archivo, y si escribía en otra carpeta la
    cambia."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "servidor.log"
    logger = registro()
    logger.setLevel(logging.INFO)
    for manejador in list(logger.handlers):
        if not isinstance(manejador, RotatingFileHandler):
            continue
        if Path(manejador.baseFilename) == ruta.resolve():
            return ruta
        logger.removeHandler(manejador)
        manejador.close()
    manejador = RotatingFileHandler(ruta, maxBytes=tamano_bytes, backupCount=archivos, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(manejador)
    return ruta
