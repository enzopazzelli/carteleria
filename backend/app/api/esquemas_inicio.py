"""Esquemas de la página de inicio (A16, `docs/plan/A16-pagina-de-inicio/diseno.md §5.7`)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from ..pasos import Destino, EstadoPaso


class PresupuestoResumidoLeer(BaseModel):
    """Un renglón de presupuesto, como se ve en una tarjeta o en el inicio."""

    id: int
    codigo: str
    cliente: str
    #: `None` si su trabajo se borró: el presupuesto queda.
    trabajo_id: int | None
    trabajo: str | None
    #: El total de la cuenta (`services/presupuesto/totales.py`); `None`
    #: mientras falte con qué calcularlo, nunca un número inventado.
    total: Decimal | None
    moneda: str
    estado: str


class PasosLeer(BaseModel):
    piezas: EstadoPaso
    grupos: EstadoPaso
    anidado: EstadoPaso
    presupuesto: EstadoPaso


class TarjetaLeer(BaseModel):
    id: int
    nombre: str
    #: Lo último que se hizo en el trabajo, con zona (UTC).
    tocado_en: datetime
    pasos: PasosLeer
    frase: str
    destino: Destino
    #: Un renglón por grupo con un anidado que cuenta: «7 chapas · CHAPA NEGRA cal. 22».
    chapas: list[str]
    #: El más reciente del trabajo.
    presupuesto: PresupuestoResumidoLeer | None
