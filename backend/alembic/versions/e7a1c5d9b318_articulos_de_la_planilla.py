"""los artículos de la planilla

Revision ID: e7a1c5d9b318
Revises: d4b2e8a1f630
Create Date: 2026-11-01 12:00:00.000000

A18: los renglones de la hoja `COTIZADOR` se guardan tal cual en
`articulos`, uno por código y proveedor; cada planilla aplicada queda en
`cargas_de_planilla`, con los precios que cambiaron en `cambios_de_precio`.
Las medidas suman lo que se cambia a mano en Materiales: el proveedor
marcado y si la medida se escribió a mano. Las que ya estaban quedan en
automático y con la medida leída.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.modelos.tipos


revision: str = 'e7a1c5d9b318'
down_revision: Union[str, Sequence[str], None] = 'd4b2e8a1f630'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _numero(nombre: str) -> sa.Column:
    return sa.Column(nombre, app.modelos.tipos.Milimetros(length=40), nullable=True)


def _fechas() -> list[sa.Column]:
    return [
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        'articulos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=40), nullable=False),
        sa.Column('proveedor', sa.String(length=120), nullable=False),
        sa.Column('descripcion', sa.String(length=300), nullable=False),
        sa.Column('categoria', sa.String(length=120), nullable=False),
        sa.Column('unidad_compra', sa.String(length=20), nullable=True),
        _numero('factor_conversion'),
        sa.Column('unidad_venta', sa.String(length=20), nullable=True),
        _numero('precio_bruto_compra'),
        sa.Column('moneda', sa.String(length=10), nullable=True),
        _numero('precio_bruto_ars'),
        _numero('iva'),
        _numero('precio_neto_compra'),
        _numero('porcentaje_costo_1'),
        _numero('porcentaje_costo_2'),
        _numero('costo_unidad_venta'),
        _numero('margen_venta_1'),
        _numero('margen_venta_2'),
        _numero('margen_venta_3'),
        _numero('margen_venta_4'),
        sa.Column('fila', sa.Integer(), nullable=False),
        sa.Column('en_ultima_planilla', sa.Boolean(), nullable=False),
        sa.Column('precio_cambiado_en', sa.DateTime(timezone=True), nullable=False),
        *_fechas(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo', 'proveedor', name='uq_articulo_codigo_proveedor'),
    )
    op.create_table(
        'cargas_de_planilla',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('archivo', sa.String(length=255), nullable=False),
        _numero('dolar_compra'),
        _numero('dolar_venta'),
        sa.Column('articulos', sa.Integer(), nullable=False),
        sa.Column('cambios', sa.Integer(), nullable=False),
        *_fechas(),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'cambios_de_precio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('carga_id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=40), nullable=False),
        sa.Column('proveedor', sa.String(length=120), nullable=False),
        _numero('antes'),
        _numero('despues'),
        *_fechas(),
        sa.ForeignKeyConstraint(['carga_id'], ['cargas_de_planilla.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('formatos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('proveedor_a_mano', sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column('medida_a_mano', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table('formatos', schema=None) as batch_op:
        batch_op.drop_column('medida_a_mano')
        batch_op.drop_column('proveedor_a_mano')
    op.drop_table('cambios_de_precio')
    op.drop_table('cargas_de_planilla')
    op.drop_table('articulos')
