"""el artículo de origen de una línea de costo

Revision ID: e1b7c4a9d256
Revises: c8e4f1a7b925
Create Date: 2026-11-08 20:00:00.000000

A23: de qué artículo de la planilla salió una línea que se agregó del catálogo: su
`id` y, aparte, su código y su proveedor, para que la línea siga diciendo de dónde
vino aunque el artículo desaparezca. Las líneas que ya había quedan sin artículo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1b7c4a9d256'
down_revision: Union[str, Sequence[str], None] = 'c8e4f1a7b925'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # El modo batch de SQLite recrea la tabla y necesita el nombre explícito
    # de cada restricción.
    with op.batch_alter_table('lineas_costo') as tabla:
        tabla.add_column(sa.Column('articulo_id', sa.Integer(), nullable=True))
        tabla.add_column(sa.Column('articulo_codigo', sa.String(length=40), nullable=True))
        tabla.add_column(sa.Column('articulo_proveedor', sa.String(length=120), nullable=True))
        tabla.create_foreign_key(
            'fk_lineas_costo_articulo_id', 'articulos', ['articulo_id'], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('lineas_costo') as tabla:
        tabla.drop_constraint('fk_lineas_costo_articulo_id', type_='foreignkey')
        tabla.drop_column('articulo_proveedor')
        tabla.drop_column('articulo_codigo')
        tabla.drop_column('articulo_id')
