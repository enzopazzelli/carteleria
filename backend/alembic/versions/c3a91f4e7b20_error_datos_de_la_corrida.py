"""error entero de la corrida

Revision ID: c3a91f4e7b20
Revises: a8f2c61b9d04
Create Date: 2026-10-15 18:00:00.000000

A9: `error` sigue siendo el mensaje; el resto del error (detalle, piezas,
chapas) va en `error_datos`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.modelos.tipos  # noqa: F401 - la plantilla lo pide para todas las migraciones


revision: str = 'c3a91f4e7b20'
down_revision: Union[str, Sequence[str], None] = 'a8f2c61b9d04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('ejecuciones_nesting', schema=None) as batch_op:
        batch_op.add_column(sa.Column('error_datos', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ejecuciones_nesting', schema=None) as batch_op:
        batch_op.drop_column('error_datos')
