"""el origen del retazo

Revision ID: c8e4f1a7b925
Revises: b5d7a9c3e142
Create Date: 2026-11-08 18:00:00.000000

A21: de dónde salió un retazo que se guardó desde el sobrante de una chapa: la
corrida, el número de chapa y un texto legible. Los formatos que ya había (las
chapas de catálogo y los retazos a mano) quedan sin origen. La pareja
corrida + chapa es única, para no guardar dos veces el mismo sobrante.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8e4f1a7b925'
down_revision: Union[str, Sequence[str], None] = 'b5d7a9c3e142'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # El modo batch de SQLite recrea la tabla y necesita el nombre explícito
    # de cada restricción.
    with op.batch_alter_table('formatos') as tabla:
        tabla.add_column(sa.Column('origen_ejecucion_id', sa.Integer(), nullable=True))
        tabla.add_column(sa.Column('origen_plancha', sa.Integer(), nullable=True))
        tabla.add_column(sa.Column('origen_texto', sa.String(length=200), nullable=True))
        tabla.create_foreign_key(
            'fk_formatos_origen_ejecucion_id', 'ejecuciones_nesting', ['origen_ejecucion_id'], ['id'],
            ondelete='SET NULL',
        )
        tabla.create_unique_constraint('uq_formato_origen', ['origen_ejecucion_id', 'origen_plancha'])


def downgrade() -> None:
    with op.batch_alter_table('formatos') as tabla:
        tabla.drop_constraint('uq_formato_origen', type_='unique')
        tabla.drop_constraint('fk_formatos_origen_ejecucion_id', type_='foreignkey')
        tabla.drop_column('origen_texto')
        tabla.drop_column('origen_plancha')
        tabla.drop_column('origen_ejecucion_id')
