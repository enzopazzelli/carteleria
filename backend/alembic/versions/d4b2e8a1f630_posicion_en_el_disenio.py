"""dónde estaba cada pieza en el dibujo

Revision ID: d4b2e8a1f630
Revises: c3a91f4e7b20
Create Date: 2026-10-24 12:00:00.000000

A14: cada pieza guarda el giro y el corrimiento que la llevan de su marco
local al dibujo. Las piezas que ya estaban quedan en `NULL` y se
recuperan del DXF guardado la primera vez que se pide el diseño.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.modelos.tipos  # noqa: F401 - la plantilla lo pide para todas las migraciones


revision: str = 'd4b2e8a1f630'
down_revision: Union[str, Sequence[str], None] = 'c3a91f4e7b20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('piezas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('disenio_x_mm', app.modelos.tipos.Milimetros(length=40), nullable=True))
        batch_op.add_column(sa.Column('disenio_y_mm', app.modelos.tipos.Milimetros(length=40), nullable=True))
        batch_op.add_column(sa.Column('disenio_angulo_grados', app.modelos.tipos.Milimetros(length=40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('piezas', schema=None) as batch_op:
        batch_op.drop_column('disenio_angulo_grados')
        batch_op.drop_column('disenio_y_mm')
        batch_op.drop_column('disenio_x_mm')
