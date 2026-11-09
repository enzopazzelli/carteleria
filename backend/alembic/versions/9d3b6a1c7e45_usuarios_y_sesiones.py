"""usuarios y sesiones

Revision ID: 9d3b6a1c7e45
Revises: f2c8a4d6e913
Create Date: 2026-11-09 22:00:00.000000

1.1: las personas que usan el sistema y sus sesiones, y quién creó cada trabajo y
presupuesto y quién hizo cada cambio de estado. Las tres columnas nuevas quedan vacías en lo
que ya estaba (de antes de tener usuarios) y se vacían si la persona se borra. La contraseña no
se guarda: se guarda una huella. El token de una sesión tampoco: solo su huella.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9d3b6a1c7e45'
down_revision: Union[str, Sequence[str], None] = 'f2c8a4d6e913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tabla, columna y nombre de la clave foránea (con nombre: SQLite, en modo batch, lo necesita).
_QUIEN_LO_HIZO = (
    ('trabajos', 'creado_por_id', 'fk_trabajos_creado_por_id'),
    ('presupuestos', 'creado_por_id', 'fk_presupuestos_creado_por_id'),
    ('cambios_de_estado', 'usuario_id', 'fk_cambios_de_estado_usuario_id'),
)


def upgrade() -> None:
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario', sa.String(length=40), nullable=False),
        sa.Column('nombre', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('contrasena_hash', sa.String(length=255), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.Column('puede_aprobar', sa.Boolean(), nullable=False),
        sa.Column('administra_usuarios', sa.Boolean(), nullable=False),
        sa.Column('debe_cambiar_contrasena', sa.Boolean(), nullable=False),
        sa.Column('intentos_fallidos', sa.Integer(), nullable=False),
        sa.Column('bloqueado_hasta', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ultimo_ingreso_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('usuario', name='uq_usuarios_usuario'),
    )
    op.create_table(
        'sesiones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('mantener', sa.Boolean(), nullable=False),
        sa.Column('expira_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ultimo_uso_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_sesiones_token_hash'),
    )
    for tabla, columna, nombre in _QUIEN_LO_HIZO:
        with op.batch_alter_table(tabla) as lote:
            lote.add_column(sa.Column(columna, sa.Integer(), nullable=True))
            lote.create_foreign_key(nombre, 'usuarios', [columna], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    for tabla, columna, nombre in reversed(_QUIEN_LO_HIZO):
        with op.batch_alter_table(tabla) as lote:
            lote.drop_constraint(nombre, type_='foreignkey')
            lote.drop_column(columna)
    op.drop_table('sesiones')
    op.drop_table('usuarios')
