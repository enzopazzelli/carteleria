"""Configuración del backend.

Todo sale de variables de entorno, con defaults que funcionan sin
instalar nada — ver `docs/historico/PLAN-SLICE-VERTICAL.md`. Los defaults son de
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

#: Los archivos de trabajo de cada anidado y de cada lectura del DXF, que
#: se borran al terminar (A17). Al lado de los datos y no en la carpeta
#: temporal del sistema, que está en C: y suele estar lleno.
DIRECTORIO_TEMPORAL = DIRECTORIO_DATOS / "tmp"


def carpeta_temporal() -> Path:
    DIRECTORIO_TEMPORAL.mkdir(parents=True, exist_ok=True)
    return DIRECTORIO_TEMPORAL


#: Ruta al motor de nesting irregular (`nesting-engine/`).
RUTA_MOTOR_DEEPNEST = Path(os.getenv("CARTELERIA_MOTOR", RAIZ.parent / "nesting-engine"))

#: El registro del servidor (A9): las fallas con su traza, para quien
#: mantiene el sistema. Al lado de los datos, fuera de git.
DIRECTORIO_REGISTRO = DIRECTORIO_DATOS / "registro"

#: `PAR-54` y `PAR-55` (`docs/REGISTRO.md`): tamaño de cada archivo del
#: registro y cuántos viejos se guardan.
TAMANO_REGISTRO_BYTES = int(os.getenv("CARTELERIA_REGISTRO_BYTES", "1000000"))
ARCHIVOS_DE_REGISTRO = int(os.getenv("CARTELERIA_REGISTRO_ARCHIVOS", "5"))

#: `PAR-56` (`docs/REGISTRO.md`): el retazo más chico que se guarda, en mm
#: por lado. Una chapa cuyo sobrante no llega cuenta como entera (A12).
RETAZO_MINIMO_MM = int(os.getenv("CARTELERIA_RETAZO_MINIMO_MM", "250"))

#: `PAR-57` (`docs/REGISTRO.md`): cuánto puede tardar Sparrow en reacomodar
#: la chapa de destino al pasarle una pieza (A17). La pantalla espera.
TIEMPO_PARA_REACOMODAR_S = int(os.getenv("CARTELERIA_TIEMPO_REACOMODAR_S", "30"))

#: `PAR-58` (`docs/REGISTRO.md`): en cuántos tramos, como mucho, se puede
#: seccionar una pieza con una chapa (A17). Es el caso de un retazo de
#: 300 × 300 con una pieza de 10 m: con más, se pide una chapa más grande.
TOPE_DE_TRAMOS = int(os.getenv("CARTELERIA_TOPE_TRAMOS", "50"))
