"""familia del material

Revision ID: a8f2c61b9d04
Revises: 7f91bcd3ef15
Create Date: 2026-10-14 18:00:00.000000

La completa para los materiales que ya había, con una copia de la regla de
`app.modelos.catalogo.familia_desde_nombre` (A8): una migración no cambia
si después cambia el código.
"""
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Los tipos propios (Milimetros) aparecen por nombre completo en las
# migraciones autogeneradas; sin este import, `upgrade` falla con
# NameError. Va en la plantilla para que valga para todas.
import app.modelos.tipos


# revision identifiers, used by Alembic.
revision: str = 'a8f2c61b9d04'
down_revision: Union[str, Sequence[str], None] = '7f91bcd3ef15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FAMILIAS_POR_PREFIJO = (
    ("CHAPA", "Chapas"),
    ("ACRILICO", "Acrílicos"),
    ("ALTO IMPACTO", "Alto impacto"),
    ("CORRUGADO", "Corrugado"),
    ("POLICARBONATO", "Policarbonato"),
)


def _familia(nombre):
    plano = unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode().upper().strip()
    for prefijo, familia in _FAMILIAS_POR_PREFIJO:
        if plano.startswith(prefijo):
            return familia
    return "Otros"


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('materiales', schema=None) as batch_op:
        batch_op.add_column(sa.Column('familia', sa.String(length=40), nullable=True))

    conexion = op.get_bind()
    materiales = sa.table('materiales', sa.column('id', sa.Integer), sa.column('nombre', sa.String), sa.column('familia', sa.String))
    for id_, nombre in conexion.execute(sa.select(materiales.c.id, materiales.c.nombre)).all():
        conexion.execute(materiales.update().where(materiales.c.id == id_).values(familia=_familia(nombre)))

    with op.batch_alter_table('materiales', schema=None) as batch_op:
        batch_op.alter_column('familia', existing_type=sa.String(length=40), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('materiales', schema=None) as batch_op:
        batch_op.drop_column('familia')
