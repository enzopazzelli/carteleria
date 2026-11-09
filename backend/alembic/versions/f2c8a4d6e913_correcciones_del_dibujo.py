"""las correcciones del dibujo

Revision ID: f2c8a4d6e913
Revises: e1b7c4a9d256
Create Date: 2026-11-09 12:00:00.000000

A24: lo que alguien marcó sobre un dibujo (esta forma se corta, esta no va) se
guarda por la huella del contenido del archivo, para aplicarlo solo cuando
vuelve a cargarse el mismo archivo. Las formas se guardan sin el prefijo del
trabajo. La huella es única: hay una sola fila por archivo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2c8a4d6e913'
down_revision: Union[str, Sequence[str], None] = 'e1b7c4a9d256'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'correcciones_del_dibujo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('huella', sa.String(length=64), nullable=False),
        sa.Column('correcciones', sa.JSON(), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('huella', name='uq_correcciones_del_dibujo_huella'),
    )


def downgrade() -> None:
    op.drop_table('correcciones_del_dibujo')
