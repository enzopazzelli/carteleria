"""Seccionado (A5): partir una pieza más grande que la chapa en tramos.

Diseño: `docs/historico/A5-seccionado/diseno.md`."""
from __future__ import annotations

from .grilla import Grilla, Seccionado, celda_util, mejor_grilla, seccionar_con_grilla, tramo_orientado

__all__ = ["Grilla", "Seccionado", "celda_util", "mejor_grilla", "seccionar_con_grilla", "tramo_orientado"]
