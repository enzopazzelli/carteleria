"""pieza: seccionado (A5)

Revision ID: 5ecc10ad0a5a
Revises: ff9dc9b0dcdf
Create Date: 2026-10-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Ver la plantilla: los tipos propios aparecen por nombre en las
# migraciones autogeneradas.
import app.modelos.tipos  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "5ecc10ad0a5a"
down_revision: Union[str, Sequence[str], None] = "ff9dc9b0dcdf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("piezas", schema=None) as batch_op:
        batch_op.add_column(sa.Column("seccionada_de_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("seccionado", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_piezas_seccionada_de_id", "piezas", ["seccionada_de_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("piezas", schema=None) as batch_op:
        batch_op.drop_constraint("fk_piezas_seccionada_de_id", type_="foreignkey")
        batch_op.drop_column("seccionado")
        batch_op.drop_column("seccionada_de_id")
