"""el multiplicador de la línea de costo

Revision ID: a3c9f1e2b7d4
Revises: e7a1c5d9b318
Create Date: 2026-11-07 21:00:00.000000

A19: cada línea de material guarda el margen de la planilla de su material
(`PAR-61`), como multiplicador del costo, al recalcular los materiales. Las
líneas que ya había quedan sin él y usan el margen general del presupuesto
hasta que se recalculen.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.modelos.tipos


revision: str = 'a3c9f1e2b7d4'
down_revision: Union[str, Sequence[str], None] = 'e7a1c5d9b318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('lineas_costo') as tabla:
        tabla.add_column(sa.Column('multiplicador', app.modelos.tipos.Milimetros(length=40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('lineas_costo') as tabla:
        tabla.drop_column('multiplicador')
