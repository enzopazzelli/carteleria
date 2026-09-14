"""Base declarativa y sesión."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from ..config import url_de_base


class Base(DeclarativeBase):
    """Base de todas las tablas.

    `creado_en` y `actualizado_en` en todas: sin fecha no se puede
    reconstruir qué pasó cuando un número no cierra, y agregarlas después
    es una migración por tabla."""

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def crear_motor(url: str | None = None):
    """Motor de SQLAlchemy, con SQLite configurado para no morder.

    Dos ajustes que solo aplican a SQLite y que se activan solos:

    - **WAL**: permite que alguien lea mientras el anidado escribe. Sin
      esto, un `GET` durante un guardado devuelve "database is locked".
    - **`check_same_thread=False`**: el anidado corre en otro hilo y
      necesita su propia sesión sobre la misma base.

    Con PostgreSQL nada de esto se ejecuta y no hay que tocar el código.
    """
    url = url or url_de_base()
    es_sqlite = url.startswith("sqlite")
    motor = create_engine(
        url,
        connect_args={"check_same_thread": False} if es_sqlite else {},
        future=True,
    )
    if es_sqlite:

        @event.listens_for(motor, "connect")
        def _configurar_sqlite(conexion, _registro):
            cursor = conexion.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            # Antes de fallar con "database is locked", esperar. El
            # anidado escribe de a ráfagas cortas; 5 segundos alcanza.
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return motor


Sesion = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False)


def inicializar(url: str | None = None):
    motor = crear_motor(url)
    Sesion.configure(bind=motor)
    return motor
