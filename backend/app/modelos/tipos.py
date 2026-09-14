"""Tipos de columna propios.

Existe uno solo, y es el que evita el bug más caro que podría tener este
proyecto: perder precisión decimal sin que nada avise.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import String, TypeDecorator


class Milimetros(TypeDecorator):
    """Un `Decimal` guardado como texto.

    **Por qué no `Numeric`.** SQLite no tiene tipo decimal: SQLAlchemy
    guardaría `float` y emite un warning avisando que se pierde
    precisión. Para este proyecto eso no es un detalle — la convención
    central es "milímetros en `Decimal`, dinero en `Decimal`"
    (`CONVENCIONES §6`), y `PAR-29` exige ±0,5 mm. Un float que redondea
    mal no se nota en la pantalla: se nota cuando el taller mide la chapa
    cortada.

    **Por qué texto y no enteros escalados.** Guardar micrones (o
    centavos) obliga a elegir una escala fija de antemano, y a que todo
    el que lea la columna sepa cuál es. El texto conserva exactamente el
    `Decimal` que se guardó, incluida su cantidad de decimales.

    **Qué se resigna.** No se puede ordenar ni comparar numéricamente en
    SQL: `'9.5' < '10.2'` es falso como texto. Ninguna de las columnas
    que usan este tipo se ordena ni se filtra por rango en la base — se
    leen, se calculan en Python y se vuelven a guardar. Si alguna vez
    hace falta ordenar por una de estas columnas, la respuesta correcta
    es pasar a PostgreSQL y cambiar este tipo por `NUMERIC` nativo, no
    ordenar el texto.
    """

    impl = String
    cache_ok = True

    # El parámetro se llama `length` y no `longitud` a propósito: Alembic
    # regenera el tipo en las migraciones como `Milimetros(length=40)`, y
    # con un nombre en castellano el `upgrade` falla con un choque de
    # argumentos. Es la única concesión de idioma del módulo.
    def __init__(self, length: int = 40, **kwargs):
        super().__init__(length=length, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, Decimal):
            # Se convierte desde str, nunca desde float: `Decimal(0.1)`
            # arrastra el error binario del float, `Decimal("0.1")` no.
            value = Decimal(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)

    @property
    def python_type(self):
        return Decimal

    def process_literal_param(self, value, dialect):
        # Solo se usa cuando Alembic corre en modo offline (genera SQL
        # como texto en vez de ejecutarlo).
        return "NULL" if value is None else f"'{value}'"
