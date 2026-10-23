"""Esquemas Pydantic de ejecuciones de nesting, colocaciones y el
resumen de materiales — paso 4 de `docs/historico/PLAN-SLICE-VERTICAL.md`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from .esquemas_mensajes import AvisoLeer, ErrorLeer, avisos_leer


class AnidarCrear(BaseModel):
    #: Rectpack conserva el comportamiento actual; Sparrow es experimental.
    motor: Literal["rectpack", "sparrow"] = "rectpack"
    semilla: int = Field(default=42, ge=0, le=2147483647)
    segundos_por_busqueda: int = Field(default=2, ge=1, le=30)
    tiempo_maximo_s: int = Field(default=240, ge=5, le=300)
    workers: int = Field(default=2, ge=1, le=2)
    simplificacion_mm: float = Field(default=0.3, ge=0, le=2)
    intentos: int = Field(default=3, ge=1, le=8)
    #: Segunda etapa de Sparrow (`sparrow_reparto.py`): vaciar chapas
    #: repartiendo sus piezas en las demás. Prendida por defecto; se apaga
    #: para comparar contra el reparto de antes o para que ese tiempo se
    #: use en probar otras semillas.
    vaciar_chapas: bool = True
    #: Sparrow gira las piezas a cualquier ángulo, no solo de a cuartos de
    #: vuelta. Marcada por defecto (Enzo, 2026-10-14); con veta no se aplica.
    giro_libre: bool = True
    #: Meter las piezas chicas en los huecos de las grandes antes de
    #: acomodar (A10, `huecos_primero.py`). Solo con Sparrow: con el motor
    #: rectangular se rechaza. Apagada si no se manda: quien llama dice lo
    #: que quiere; la pantalla la manda marcada.
    usar_anidado_en_huecos: bool = False
    #: Hacia qué lado queda el sobrante de cada chapa (A12). Al costado si
    #: no se manda, como antes; la pantalla manda arriba. La comparación de
    #: chapas no la mira: compara siempre con el sobrante arriba.
    sobrante: Literal["arriba", "costado"] = "costado"


class ProgresoLeer(BaseModel):
    """Cómo va un anidado o una comparación en curso (A7). Lo que el motor
    todavía no informó viene vacío."""

    segundos: float
    maximo: int
    fase: Literal["huecos", "pasada", "vaciar"] | None = None
    pasada: int | None = None
    pasadas: int | None = None
    mejor_chapas: int | None = None
    #: En la fase de huecos (A10): cuántos huecos lleva y cuántos hay.
    huecos: int | None = None
    huecos_total: int | None = None
    #: Solo en una comparación: qué formato corre, cuántos hay y cuál es.
    formato: int | None = None
    formatos: int | None = None
    descripcion: str | None = None


class EjecucionLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grupo_id: int
    motor: str
    estado: str
    semilla: str | None
    opciones: dict | None
    parametros: dict | None
    planchas_usadas: int | None
    aprovechamiento_pct: Decimal | None
    largo_corte_compartido_mm: Decimal | None
    milisegundos: int | None
    mensajes: list[AvisoLeer] | None
    #: La corrida guarda el mensaje en `error` y el resto en `error_datos`;
    #: `error_completo` los junta (A9).
    error: ErrorLeer | None = Field(default=None, validation_alias=AliasChoices("error_completo", "error"))
    es_definitiva: bool
    creado_en: datetime
    actualizado_en: datetime
    #: Mientras corre (A7): lo que anotó la corrida en la memoria del
    #: servidor. No sale de la base: `obtener_ejecucion` lo agrega.
    progreso: ProgresoLeer | None = None

    @field_validator("mensajes", mode="before")
    @classmethod
    def _avisos_de_antes_y_de_ahora(cls, valor):
        return None if valor is None else avisos_leer(valor)

    @field_validator("error", mode="before")
    @classmethod
    def _error_de_texto(cls, valor):
        return {"mensaje": valor} if isinstance(valor, str) else valor


class ColocacionLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pieza_id: int
    instancia: int
    plancha_indice: int
    centro_x_mm: Decimal
    centro_y_mm: Decimal
    angulo_grados: Decimal
    movida_a_mano: bool


class ColocacionActualizar(BaseModel):
    """Mover y/o rotar (`CART-207`) — lo que no se manda queda como
    estaba. Al menos un campo tiene que venir; si no cambia nada no
    tiene sentido marcar `movida_a_mano`."""

    centro_x_mm: Decimal | None = None
    centro_y_mm: Decimal | None = None
    angulo_grados: Decimal | None = None


class ColocacionAjusteLeer(ColocacionLeer):
    """La colocación resultante, más si la posición pedida es válida.

    Se aplica SIEMPRE, sea válida o no — es la misma decisión que ya
    tomó el visor interactivo (`GUIA-PRUEBAS-LOCALES.md`): bloquear
    frustra el ajuste fino cerca de una posición válida y es
    incompatible con el corte de línea compartida. El cliente decide
    cómo mostrar el conflicto (ej. resaltarlo), no esta API."""

    valida: bool
    motivo: AvisoLeer | None
    #: Las que se movieron con esta porque estaban enteras adentro de alguno
    #: de sus huecos (A10), cada una con su control.
    tambien_movidas: list[ColocacionAjusteLeer] = Field(default_factory=list)


# --- Costeo (envuelve `app/costeo.py`, no lo reemplaza) -------------------


class LineaMaterialLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grupo_id: int
    grupo_nombre: str
    material_nombre: str | None
    formato_id: int | None
    formato_descripcion: str | None
    planchas_usadas: int | None
    area_total_m2: Decimal | None
    moneda: str | None
    precio_unitario: Decimal | None
    unidad_venta: str | None
    ejecucion_id: int | None
    costo_estimado: Decimal | None
    advertencias: list[str]


class ResumenMaterialesLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trabajo_id: int
    lineas: list[LineaMaterialLeer]
    costo_total_por_moneda: dict[str, Decimal]
    advertencias_generales: list[str]


# --- Material usado en ancho × alto (A12) ----------------------------------


class MedidaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ancho_mm: int
    alto_mm: int


class MaterialDeChapaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plancha: int
    usado: MedidaLeer
    sobrante: MedidaLeer
    es_retazo: bool


class MaterialUsadoLeer(BaseModel):
    chapa: MedidaLeer
    chapas: list[MaterialDeChapaLeer]
    #: Como lo diría el dueño: «6 chapas enteras + 1220 × 1650 + 1220 × 900».
    linea: str
    #: `PAR-56`: con qué medida se decidió qué es retazo.
    retazo_minimo_mm: int


# --- Comparar formatos, sin comprometer el grupo (`CART-205`) -------------


class ComparacionFormatosCrear(AnidarCrear):
    formato_ids: list[int]
    criterio: Literal["costo", "material"] = "costo"


class PiezaASeccionarLeer(BaseModel):
    id: int
    id_origen: str
    ancho_mm: Decimal
    alto_mm: Decimal


class OpcionFormatoLeer(BaseModel):
    motor: str = "rectpack"
    advertencias: list[AvisoLeer] = Field(default_factory=list)
    #: Vacíos (`None`) cuando hay `piezas_a_seccionar`: ese formato no se
    #: anidó, así que no tiene planchas, consumo, aprovechamiento ni costo.
    area_total_m2: Decimal | None = Decimal(0)
    formato_id: int
    formato_descripcion: str
    material_nombre: str
    planchas_usadas: int | None
    aprovechamiento_pct: Decimal | None
    costo_total: Decimal | None
    moneda: str
    recomendado: bool
    #: `Formato.precio_simulado` — si esto es `True`, `costo_total` no
    #: es un número real, es de prueba (ver docstring del modelo).
    precio_simulado: bool
    #: Piezas que no entran en este formato con ninguna rotación permitida.
    #: No es un error de la comparación: un diseño más grande que la chapa
    #: se secciona en tramos que se sueldan después (A5, desde la pestaña
    #: Piezas). Hasta que se seccionen, el formato queda sin anidar.
    piezas_a_seccionar: list[PiezaASeccionarLeer] = Field(default_factory=list)
    #: El formato no se pudo anidar (A9): no llegó a tiempo o falló el
    #: cálculo. Como con `piezas_a_seccionar`, sin planchas ni costo.
    error: ErrorLeer | None = None

    @field_validator("advertencias", mode="before")
    @classmethod
    def _avisos(cls, valor):
        return avisos_leer(valor)


class ComparacionLeer(BaseModel):
    """Una comparación de formatos en segundo plano (A7)."""

    id: int
    grupo_id: int
    estado: Literal["corriendo", "lista", "cancelada", "error"]
    progreso: ProgresoLeer | None = None
    #: La tabla de la comparación, cuando terminó bien: la misma que
    #: devuelve `POST /grupos/{id}/comparar-formatos`.
    opciones: list[OpcionFormatoLeer] | None = None
    error: ErrorLeer | None = None
