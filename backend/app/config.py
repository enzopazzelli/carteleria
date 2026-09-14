"""Configuración del backend.

Todo sale de variables de entorno, con defaults que funcionan sin
instalar nada — ver `docs/PLAN-SLICE-VERTICAL.md`. Los defaults son de
**desarrollo local**: no cambian lo que decide `ADR-05` para producción
(PostgreSQL + Celery/Redis), lo dejan como un cambio de configuración.
"""
from __future__ import annotations

import os
from pathlib import Path

#: Raíz del backend. Todo lo que se guarda en disco cuelga de acá.
RAIZ = Path(__file__).resolve().parent.parent

#: Carpeta de datos locales. Está en `.gitignore` (`backend/local/`)
#: porque acá adentro terminan geometrías reales del cliente.
DIRECTORIO_DATOS = Path(os.getenv("CARTELERIA_DATOS", RAIZ / "local"))

#: SQLite por default: viene con Python, no hay nada que instalar.
#: En producción, `DATABASE_URL=postgresql+psycopg://...` y no cambia
#: ninguna otra línea de código — para eso están las cinco reglas del
#: plan (nada específico de PostgreSQL en el schema, Alembic desde el
#: día uno, nada de SQL crudo).
def url_de_base() -> str:
    definida = os.getenv("DATABASE_URL")
    if definida:
        return definida
    DIRECTORIO_DATOS.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DIRECTORIO_DATOS / 'carteleria.db'}"


#: 'proceso' (hilos, sin instalar nada) o 'celery' cuando exista.
COLA = os.getenv("CARTELERIA_COLA", "proceso")

#: Dónde se guardan los DXF subidos. Se conservan porque un trabajo
#: tiene que poder re-parsearse con otra escala sin volver a subirlo.
DIRECTORIO_ARCHIVOS = DIRECTORIO_DATOS / "archivos"

#: Ruta al motor de nesting irregular (`nesting-engine/`).
RUTA_MOTOR_DEEPNEST = Path(os.getenv("CARTELERIA_MOTOR", RAIZ.parent / "nesting-engine"))
