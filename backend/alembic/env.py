"""Entorno de Alembic.

Toma la URL de `app.config`, no de `alembic.ini`: así hay **un solo lugar**
donde se decide contra qué base se trabaja, y pasar de SQLite a
PostgreSQL es cambiar `DATABASE_URL` y nada más.

`render_as_batch` está prendido porque SQLite no sabe hacer `ALTER
COLUMN` ni `DROP CONSTRAINT`: Alembic tiene que recrear la tabla y copiar
los datos. Sin esto, la primera migración que cambie una columna falla.
Con PostgreSQL el modo batch no molesta.
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import url_de_base  # noqa: E402
from app.modelos import Base  # noqa: E402

config = context.config
config.set_main_option("sqlalchemy.url", url_de_base())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectable.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
