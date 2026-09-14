"""Trabajos, grupos de corte, piezas, ejecuciones de nesting y colocaciones.

La regla que sostiene todo el slice: **nada cuelga de un estado global,
todo cuelga de un `Trabajo`.** Es lo que hoy hace mal `servidor_visor.py`
—un único `_estado` compartido por todos— y lo que permite diferir la
autenticación sin que se cuele lógica de un solo usuario.

**Un trabajo puede cortarse en varios materiales.** `GrupoDeCorte` es la
generalización de lo que el visor local llamaba "Tanda 1 / Tanda 2": en
vez de dos tandas fijas del mismo material, un trabajo tiene N grupos,
cada uno con su propio material y su propio anidado. Es lo que hace
falta para "seleccionar piezas del layout, pasarlas a otro material,
identificar qué materiales se van a usar y cotizarlos" — ver
`docs/PLAN-GRUPOS-DE-CORTE.md`.
"""
from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .tipos import Milimetros


class EstadoEjecucion(str, enum.Enum):
    ENCOLADA = "encolada"
    CORRIENDO = "corriendo"
    LISTA = "lista"
    CANCELADA = "cancelada"
    ERROR = "error"


class Trabajo(Base):
    """Un proyecto: de dónde salieron las piezas.

    Ya NO tiene `formato_id` ni `parametros_usados` — un trabajo puede
    repartirse en varios materiales, así que esos dos campos viven en
    cada `GrupoDeCorte`, no acá.
    """

    __tablename__ = "trabajos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    #: Nombre original del DXF, para que el operario reconozca el trabajo.
    archivo_origen: Mapped[str | None] = mapped_column(String(260), default=None)
    #: Ruta del archivo guardado, para poder re-parsear con otra escala
    #: sin pedirle al usuario que lo suba de nuevo.
    archivo_guardado: Mapped[str | None] = mapped_column(String(400), default=None)
    #: Sin default a propósito, igual que en `parsear_dxf`: adivinar la
    #: escala da un resultado catastróficamente equivocado y nada avisa.
    escala_a_mm: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)

    piezas: Mapped[list[Pieza]] = relationship(
        back_populates="trabajo", cascade="all, delete-orphan"
    )
    grupos: Mapped[list[GrupoDeCorte]] = relationship(
        back_populates="trabajo", cascade="all, delete-orphan", order_by="GrupoDeCorte.orden"
    )


class GrupoDeCorte(Base):
    """Un subconjunto de piezas de un trabajo, destinado a UN material.

    Es el punto de la generalización: antes había "Tanda 1" y "Tanda 2"
    codificadas a mano, siempre del mismo material que el resto del
    trabajo. Acá cada grupo elige su propio `formato_id` — uno puede ser
    chapa negra cal. 22 y otro acrílico, dentro del mismo trabajo.

    `formato_id` es nullable: un grupo puede existir ("piezas que van a
    ir en acrílico") antes de que alguien confirme QUÉ formato de
    acrílico. Sin formato asignado no se puede anidar — eso lo valida el
    servicio, no el modelo.
    """

    __tablename__ = "grupos_de_corte"

    id: Mapped[int] = mapped_column(primary_key=True)
    trabajo_id: Mapped[int] = mapped_column(ForeignKey("trabajos.id", ondelete="CASCADE"))
    #: Editable por el usuario — "Chapa negra", "Acrílico frente". Si no
    #: se pone nombre, la UI puede mostrar el nombre del material.
    nombre: Mapped[str] = mapped_column(String(120))
    formato_id: Mapped[int | None] = mapped_column(
        ForeignKey("formatos.id", ondelete="SET NULL"), default=None
    )
    #: COPIA de los parámetros con los que se calculó, no una referencia
    #: (`CART-210`). Un grupo viejo tiene que reproducirse tal cual,
    #: aunque después alguien cambie el material — mismo criterio que el
    #: snapshot inmutable de `ADR-04`. Es por GRUPO y no por trabajo
    #: porque PAR-01..04 son por material (`CART-105`): dos grupos del
    #: mismo trabajo pueden tener kerf distinto si el material es distinto.
    parametros_usados: Mapped[dict | None] = mapped_column(JSON, default=None)
    #: Orden de aparición en la UI. No es el id: el usuario puede
    #: reordenar los grupos sin que eso implique borrar y recrear.
    orden: Mapped[int] = mapped_column(Integer, default=0)

    trabajo: Mapped[Trabajo] = relationship(back_populates="grupos")
    piezas: Mapped[list[Pieza]] = relationship(back_populates="grupo")
    ejecuciones: Mapped[list[EjecucionNesting]] = relationship(
        back_populates="grupo", cascade="all, delete-orphan"
    )


class Pieza(Base):
    """Una pieza a cortar, con su geometría real.

    Cuelga del `Trabajo` (es el origen: todas las piezas de un DXF
    parseado), no del `GrupoDeCorte`. `grupo_id` es nullable a propósito:
    una pieza recién importada no tiene material asignado todavía, y
    "sin asignar" es un estado normal del flujo, no un caso de error.
    Moverla de un grupo a otro es actualizar este campo.

    El contorno y los agujeros van como JSON (lista de `[x, y]` en mm) en
    vez de tablas de puntos: son cientos de puntos por pieza, nunca se
    consultan por punto, y se leen siempre enteros. Una tabla de vértices
    sería más "normalizada" y peor en todo lo que importa acá.
    """

    __tablename__ = "piezas"

    id: Mapped[int] = mapped_column(primary_key=True)
    trabajo_id: Mapped[int] = mapped_column(ForeignKey("trabajos.id", ondelete="CASCADE"))
    #: NULL = todavía no se decidió en qué material va esta pieza.
    grupo_id: Mapped[int | None] = mapped_column(
        ForeignKey("grupos_de_corte.id", ondelete="SET NULL"), default=None
    )
    #: El id que trajo el archivo (`carrusel-131`), no el de la base:
    #: es el que el diseñador reconoce.
    id_origen: Mapped[str] = mapped_column(String(120))
    cantidad: Mapped[int] = mapped_column(Integer, default=1)
    ancho_mm: Mapped[Decimal] = mapped_column(Milimetros())
    alto_mm: Mapped[Decimal] = mapped_column(Milimetros())
    #: Contorno y agujeros en el marco local de la pieza ([0,ancho]×[0,alto]).
    contorno_mm: Mapped[list] = mapped_column(JSON)
    agujeros_mm: Mapped[list] = mapped_column(JSON, default=list)
    #: El diseñador la sacó del trabajo entero: no se corta en NINGÚN
    #: grupo. Distinto de `grupo_id is None` (todavía sin decidir).
    descartada: Mapped[bool] = mapped_column(Boolean, default=False)
    #: Si sus tramos rectos son rectas reales. Habilita el corte de
    #: líneas compartidas — el motor ignora toda arista sin esta marca.
    contorno_recto: Mapped[bool] = mapped_column(Boolean, default=False)

    trabajo: Mapped[Trabajo] = relationship(back_populates="piezas")
    grupo: Mapped[GrupoDeCorte | None] = relationship(back_populates="piezas")
    colocaciones: Mapped[list[Colocacion]] = relationship(
        back_populates="pieza", cascade="all, delete-orphan"
    )


class EjecucionNesting(Base):
    """Una corrida del motor sobre las piezas de UN grupo de corte.

    Es una tabla y no un campo del grupo porque **un grupo se anida
    muchas veces**: con un motor y con otro, con una plancha y con otra.
    Guardar solo la última haría imposible comparar, que es justamente
    para lo que se construyó todo esto.
    """

    __tablename__ = "ejecuciones_nesting"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupos_de_corte.id", ondelete="CASCADE"))
    motor: Mapped[str] = mapped_column(String(20))  # rectpack | deepnest
    estado: Mapped[str] = mapped_column(String(20), default=EstadoEjecucion.ENCOLADA.value)
    #: Semilla del PRNG: es lo que hace reproducible al motor irregular.
    semilla: Mapped[str | None] = mapped_column(String(80), default=None)
    #: Opciones del motor (generaciones, población, orientación...).
    opciones: Mapped[dict | None] = mapped_column(JSON, default=None)
    #: Snapshot de los parámetros de corte de ESTA corrida.
    parametros: Mapped[dict | None] = mapped_column(JSON, default=None)

    planchas_usadas: Mapped[int | None] = mapped_column(Integer, default=None)
    #: Calculado por Python con shapely sobre área real (`ADR-08`), nunca
    #: tomado de lo que el motor diga de sí mismo.
    aprovechamiento_pct: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    largo_corte_compartido_mm: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    milisegundos: Mapped[int | None] = mapped_column(Integer, default=None)
    #: Advertencias y errores, para que no se pierdan al recargar.
    mensajes: Mapped[list | None] = mapped_column(JSON, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    #: Un grupo puede tener varias ejecuciones (probar rectpack y
    #: deepnest, o recalcular con otros parámetros). El costeo necesita
    #: saber CUÁL usar — esta marca lo dice, en vez de asumir "la última"
    #: (que podría ser una prueba descartada).
    es_definitiva: Mapped[bool] = mapped_column(Boolean, default=False)

    grupo: Mapped[GrupoDeCorte] = relationship(back_populates="ejecuciones")
    colocaciones: Mapped[list[Colocacion]] = relationship(
        back_populates="ejecucion", cascade="all, delete-orphan"
    )


class Colocacion(Base):
    """Dónde quedó una instancia de pieza.

    Se guarda **centro + ángulo libre**, no esquina + booleano de 90°.
    Es la representación que ya usan `anidado_huecos.py` y el motor
    irregular (que rota a 0/90/180/270), y la única que sobrevive a que
    el operario gire una pieza a mano a un ángulo cualquiera. Guardar
    `rotada_90` perdería la posición real.
    """

    __tablename__ = "colocaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    ejecucion_id: Mapped[int] = mapped_column(
        ForeignKey("ejecuciones_nesting.id", ondelete="CASCADE")
    )
    pieza_id: Mapped[int] = mapped_column(ForeignKey("piezas.id", ondelete="CASCADE"))
    #: Cuál de las copias, cuando la pieza tiene cantidad > 1.
    instancia: Mapped[int] = mapped_column(Integer, default=0)
    plancha_indice: Mapped[int] = mapped_column(Integer, default=0)
    centro_x_mm: Mapped[Decimal] = mapped_column(Milimetros())
    centro_y_mm: Mapped[Decimal] = mapped_column(Milimetros())
    angulo_grados: Mapped[Decimal] = mapped_column(Milimetros())
    #: El operario la corrigió después de anidar. Sirve para avisarle
    #: que un recálculo va a descartar ese ajuste.
    movida_a_mano: Mapped[bool] = mapped_column(Boolean, default=False)

    ejecucion: Mapped[EjecucionNesting] = relationship(back_populates="colocaciones")
    pieza: Mapped[Pieza] = relationship(back_populates="colocaciones")
