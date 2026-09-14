"""Cliente del motor de nesting irregular (Deepnest headless).

Spike de la Fase 0 de [`docs/PLAN-MOTOR-NESTING-DEEPNEST.md`]. **No es
código de producción todavía**: habla con el motor por `subprocess`, un
proceso por corrida. El servicio HTTP en Docker es la Fase 1, y solo se
justifica si el spike rinde.

Lo que este módulo garantiza, y es lo que lo hace útil aunque el
transporte cambie:

1. **La frontera `Decimal` ↔ float queda contenida acá.** El resto del
   backend trabaja en `Decimal` sobre milímetros (`CONVENCIONES §6`);
   JSON y JavaScript solo tienen `double`. Al recibir, se re-cuantiza a
   milímetros con la precisión de `PAR-29` y se valida — el JSON es
   transporte, no fuente de verdad.

2. **Devuelve un `ResultadoAnidado` normal**, el mismo tipo que produce
   `MotorNestingRectangular`. Así `aprovechamiento.py`, `comparador.py`
   y el visor (`visualizacion.py`) lo consumen sin enterarse de que
   atrás hubo otro motor. Es la condición para poder comparar los dos
   sobre las mismas piezas.

3. **Nunca se confía en el aprovechamiento que reporta el motor.** Viene
   en `diagnostico` como dato informativo; el número que el sistema
   publica lo calcula Python con `shapely` sobre la geometría real
   (`ADR-08`, corrección de `DECISIONES §1.1`).
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path

from .models import ParametrosCorte, Pieza, Plancha, PosicionPieza, ResultadoAnidado, RotacionPermitida
from .validacion_manual import GeometriaPieza

# PAR-29: precisión de posición exigida (±0,5 mm). Se cuantiza bastante
# más fino que eso — el objetivo es cortar la cola de decimales del
# float, no degradar la precisión del motor.
_DECIMALES_MM = Decimal("0.0001")

_RUTA_MOTOR_DEFAULT = Path(__file__).resolve().parents[4] / "nesting-engine"


@dataclass(frozen=True)
class OpcionesMotorDeepnest:
    """Perillas del motor. Ninguna tiene equivalente en `rectpack`, así
    que no viven en `ParametrosCorte` (que es de negocio, `PAR-01` a
    `PAR-04`) sino acá, separadas."""

    # Semilla del PRNG: lo que hace reproducible al algoritmo genético.
    # Ver docs/PLAN-MOTOR-NESTING-DEEPNEST.md §5.
    semilla: str = "cartelería"
    # Presupuesto de búsqueda. Cortar por generaciones y no por reloj es
    # lo que mantiene el resultado reproducible entre corridas.
    generaciones: int = 3
    poblacion: int = 10
    tiempo_maximo_ms: int = 0  # 0 = sin tope de reloj; ver PAR-09
    # 'box' | 'gravity' | 'convexhull'
    estrategia: str = "box"
    corte_compartido: bool = True
    # Cuánto vale el ahorro de corte compartido contra el de material:
    # 0 = optimizar solo material, 1 = solo tiempo de corte.
    peso_corte_compartido: float = 0.5
    # 'libre' | 'apilar_en_ancho'. Ver `_transponer_para_apilar_en_ancho`.
    orientacion: str = "libre"


@dataclass(frozen=True)
class ResultadoDeepnest:
    """El `ResultadoAnidado` de siempre, más lo que solo este motor sabe."""

    resultado: ResultadoAnidado
    # Las geometrías ORIGINALES de las piezas, indexadas por el id de
    # instancia (`pieza#n`) además de por el id base. Deepnest no rota la
    # geometría: la rotación viaja en `PosicionPieza.angulo_libre_grados`
    # — ver `_posicion_desde_colocacion`.
    geometrias: dict[str, GeometriaPieza]
    largo_corte_compartido_mm: Decimal
    diagnostico: dict = field(default_factory=dict)


class ErrorMotorDeepnest(RuntimeError):
    """El motor no pudo correr o devolvió algo inutilizable."""


def _a_float(valor: Decimal) -> float:
    return float(valor)


def _a_mm(valor: float) -> Decimal:
    """float del JSON → Decimal en milímetros, con la cola de decimales
    del punto flotante recortada."""
    return Decimal(str(valor)).quantize(_DECIMALES_MM)


def _rotar(punto: tuple[float, float], grados: float) -> tuple[float, float]:
    radianes = math.radians(grados)
    cos, sin = math.cos(radianes), math.sin(radianes)
    x, y = punto
    return x * cos - y * sin, x * sin + y * cos


def _armar_payload(
    piezas: list[Pieza],
    geometrias: dict[str, GeometriaPieza],
    plancha,
    params: ParametrosCorte,
    opciones: OpcionesMotorDeepnest,
    piezas_rectas: set[str] | None,
) -> dict:
    payload_piezas = []
    for pieza in piezas:
        geometria = geometrias.get(pieza.id)
        if geometria is None or not geometria.contorno_local_mm:
            raise ErrorMotorDeepnest(
                f"La pieza {pieza.id} no tiene contorno real. Deepnest anida por forma, no por "
                "bounding box: sin contorno no hay nada que anidar. Las piezas cargadas a mano "
                "(CART-201) todavía no sirven para este motor."
            )
        entrada = {
            "id": pieza.id,
            "cantidad": pieza.cantidad,
            "contorno_mm": [[_a_float(x), _a_float(y)] for x, y in geometria.contorno_local_mm],
            "agujeros_mm": [
                [[_a_float(x), _a_float(y)] for x, y in agujero] for agujero in geometria.agujeros_local_mm
            ],
        }
        # Declarar qué piezas son de tramos rectos reales es lo que
        # habilita el corte de líneas compartidas — el motor ignora toda
        # arista que no venga marcada. Ver src/geometria.js del motor.
        if piezas_rectas is not None and pieza.id in piezas_rectas:
            entrada["contorno_recto"] = True
        payload_piezas.append(entrada)

    return {
        "plancha": {"ancho_mm": _a_float(plancha.ancho_mm), "alto_mm": _a_float(plancha.alto_mm)},
        "piezas": payload_piezas,
        "parametros": {
            "kerf_mm": _a_float(params.kerf_mm),
            "margen_borde_mm": _a_float(params.margen_borde_mm),
            "separacion_piezas_mm": _a_float(params.separacion_piezas_mm),
            "rotaciones_permitidas": params.rotaciones_permitidas.value,
        },
        "motor": {
            "semilla": opciones.semilla,
            "generaciones": opciones.generaciones,
            "poblacion": opciones.poblacion,
            "tiempo_maximo_ms": opciones.tiempo_maximo_ms,
            "estrategia": opciones.estrategia,
            "corte_compartido": opciones.corte_compartido,
            "peso_corte_compartido": opciones.peso_corte_compartido,
        },
    }


def _transponer_para_apilar_en_ancho(plancha, params):
    """Hace que el motor amontone contra el ANCHO de la plancha primero,
    dejando el sobrante como una franja limpia al final del largo.

    **Por qué hace falta.** La estrategia `gravity` de Deepnest comprime
    contra su propio eje X (pesa el ancho ×5). Sobre una plancha parada
    —1220 × 2440, típica— eso produce una columna alta y angosta, y el
    sobrante queda como una tira fina al costado: inservible para volver
    a stockear como retazo. Lo que sirve en el taller es lo contrario:
    llenar a lo ancho e ir avanzando por el largo, para que lo que sobre
    sea un pedazo entero al final.

    **Cómo se resuelve, sin tocar el motor.** Se le manda la plancha
    TRANSPUESTA (el largo real como su ancho) y se usa `gravity`: así el
    eje que el motor comprime es el largo real. Después se rota el
    resultado +90° para volver a la plancha real. La rotación es propia
    (determinante +1), no un espejo: una pieza espejada no se puede
    cortar, sería un defecto grave y silencioso.

    **Por qué no sirve con materiales con veta.** La vuelta de 90° gira
    TODAS las piezas. El conjunto {0, 90, 180, 270} es cerrado bajo esa
    rotación, así que un material sin veta (`PAR-04` = `LIBRE_0_90`)
    queda igual de legal. Pero con veta las rotaciones legales son
    {0, 180}, y al girarlas quedarían en {90, 270}: todas las piezas
    cortadas contra la veta. Por eso se rechaza en vez de entregar un
    layout que el taller no puede cortar.

    Devuelve `(plancha_para_el_motor, ancho_real_mm)`.
    """
    if params.rotaciones_permitidas is not RotacionPermitida.LIBRE_0_90:
        raise ErrorMotorDeepnest(
            "`orientacion='apilar_en_ancho'` no se puede usar con un material con veta "
            f"(PAR-04 = {params.rotaciones_permitidas.value}): la maniobra gira el layout 90° y "
            "dejaría todas las piezas cortadas contra la veta. Usar 'libre' para este material."
        )
    return Plancha(ancho_mm=plancha.alto_mm, alto_mm=plancha.ancho_mm), plancha.ancho_mm


def _desde_coordenadas_transpuestas(colocacion: dict, ancho_real_mm: Decimal) -> dict:
    """Lleva una colocación del marco transpuesto al marco real.

    El motor colocó sobre `[0, L] × [0, W]`; la plancha real es
    `[0, W] × [0, L]`. Se usa la rotación de **+90°** —`(x, y) → (-y, x)`,
    más una traslación de `+W` en X para volver al primer cuadrante—, no
    la de -90°. Las dos son rotaciones propias y dan el mismo layout,
    pero difieren en a qué borde queda pegado el conjunto: `gravity`
    amontona contra el origen del eje que comprime, y con +90° ese eje
    sigue siendo el origen del largo real. Con -90° las piezas terminaban
    contra el borde LEJANO y el sobrante del lado del origen — el mismo
    ahorro de material, pero al revés de como se corta: el operario mide
    desde la esquina de la chapa, no desde el fondo.

    Aplicado a la transformación de la pieza (`R(a)·p + t`), da
    `R(a + 90)·p + (W - ty, tx)`."""
    tx, ty = float(colocacion["tx_mm"]), float(colocacion["ty_mm"])
    return {
        **colocacion,
        "angulo_grados": (float(colocacion["angulo_grados"]) + 90) % 360,
        "tx_mm": float(ancho_real_mm) - ty,
        "ty_mm": tx,
    }


def _posicion_desde_colocacion(colocacion: dict, geometria: GeometriaPieza) -> PosicionPieza:
    """Traduce una colocación de Deepnest a `PosicionPieza`.

    El contrato del motor dice: la posición final es rotar el contorno
    original `angulo_grados` alrededor del origen y trasladarlo
    (`tx_mm`, `ty_mm`).

    `rotada_90` no alcanza para representar eso: es un booleano heredado
    de `ADR-01`, y Deepnest rota a 0/90/180/270. Se usa entonces la
    representación de **ángulo libre** que `PosicionPieza` ya admite
    (`angulo_libre_grados` + `centro_libre_*`), la misma que introdujo
    `anidado_huecos.py` y que `posicion_manual_desde_pieza` y el visor
    saben leer. Así la geometría que se dibuja sigue siendo la ORIGINAL
    de la pieza — no hay una copia rotada por instancia dando vueltas.

    El ancla de esa representación es el CENTRO del bounding box de la
    pieza en su marco local, no la esquina: rotar sobre el centro no
    mueve la pieza de lugar. Como el motor rota alrededor del origen y
    después traslada, el centro final es `R(ángulo)·centro_local + t`.

    `x_mm`/`y_mm`/`ancho`/`alto`/`rotada_90` se completan igual con el
    bounding box axis-aligned de la forma ya rotada — la aproximación
    conservadora que `PosicionPieza` documenta para el código que todavía
    no sabe de ángulo libre (`aprovechamiento.py`, `comparador.py`).
    """
    angulo = float(colocacion["angulo_grados"])
    tx, ty = float(colocacion["tx_mm"]), float(colocacion["ty_mm"])

    def transformar(punto: tuple[Decimal, Decimal]) -> tuple[float, float]:
        rx, ry = _rotar((float(punto[0]), float(punto[1])), angulo)
        return rx + tx, ry + ty

    contorno = [transformar(p) for p in geometria.contorno_local_mm]
    min_x = min(x for x, _ in contorno)
    min_y = min(y for _, y in contorno)
    max_x = max(x for x, _ in contorno)
    max_y = max(y for _, y in contorno)

    centro_x, centro_y = transformar((geometria.ancho_mm / 2, geometria.alto_mm / 2))

    return PosicionPieza(
        pieza_id=f"{colocacion['pieza_id']}#{colocacion['instancia']}",
        plancha_indice=int(colocacion["plancha_indice"]),
        x_mm=_a_mm(min_x),
        y_mm=_a_mm(min_y),
        ancho_colocado_mm=_a_mm(max_x - min_x),
        alto_colocado_mm=_a_mm(max_y - min_y),
        rotada_90=round(angulo) % 180 == 90,
        angulo_libre_grados=Decimal(str(angulo)),
        centro_libre_x_mm=_a_mm(centro_x),
        centro_libre_y_mm=_a_mm(centro_y),
    )


def _resolver_node() -> str:
    node = shutil.which("node")
    if node is None:
        raise ErrorMotorDeepnest(
            "No se encontró `node` en el PATH. El motor de Deepnest corre en Node (>= 20). "
            "En producción esto es un contenedor; para probar local hace falta Node instalado."
        )
    return node


def anidar_con_deepnest(
    piezas: list[Pieza],
    geometrias: dict[str, GeometriaPieza],
    plancha,
    params: ParametrosCorte,
    opciones: OpcionesMotorDeepnest | None = None,
    piezas_rectas: set[str] | None = None,
    ruta_motor: Path | None = None,
    registrar_proceso: Callable[[subprocess.Popen], None] | None = None,
) -> ResultadoDeepnest:
    """Corre el motor de Deepnest sobre las piezas dadas.

    `registrar_proceso`: se llama con el `Popen` del motor apenas arranca,
    para que quien orquesta pueda matarlo si el usuario cancela. Sin esto,
    cancelar solo descartaría el resultado y el proceso seguiría comiendo
    CPU varios minutos.

    `piezas_rectas`: ids de las piezas cuyo contorno son tramos rectos
    reales (no la discretización de una curva). Solo esas cuentan para el
    corte de líneas compartidas. `dxf.py` es quien puede saberlo de
    verdad — mientras no lo exponga, el que llama decide, y si no declara
    ninguna el motor devuelve una advertencia en vez de simular que la
    feature funcionó.
    """
    opciones = opciones or OpcionesMotorDeepnest()
    motor = ruta_motor or _RUTA_MOTOR_DEFAULT
    cli = motor / "src" / "cli.js"
    if not cli.exists():
        raise ErrorMotorDeepnest(f"No existe el motor en {cli}. ¿Falta correr `npm install` en {motor}?")

    apilar_en_ancho = opciones.orientacion == "apilar_en_ancho"
    if apilar_en_ancho:
        plancha_motor, ancho_real_mm = _transponer_para_apilar_en_ancho(plancha, params)
        # `gravity` es la única estrategia que comprime contra un eje; las
        # otras dos no tienen preferencia direccional y la transposición
        # no haría nada.
        opciones = replace(opciones, estrategia="gravity")
    else:
        plancha_motor, ancho_real_mm = plancha, plancha.ancho_mm

    payload = _armar_payload(piezas, geometrias, plancha_motor, params, opciones, piezas_rectas)

    # `Popen` y no `subprocess.run` para poder ENTREGAR el proceso a quien
    # llama: con corridas de varios minutos, cancelar tiene que matar el
    # proceso de verdad. Un "cancelar" que solo descarta el resultado deja
    # un núcleo al 100% hasta que el motor termine solo.
    proceso = subprocess.Popen(  # noqa: S603 — el ejecutable y los argumentos son nuestros
        [_resolver_node(), str(cli), "--silencioso"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        cwd=str(motor),
    )
    if registrar_proceso is not None:
        registrar_proceso(proceso)

    salida_texto, error_texto = proceso.communicate(json.dumps(payload))

    if proceso.returncode != 0:
        raise ErrorMotorDeepnest(
            f"El motor falló (código {proceso.returncode}):\n{(error_texto or '').strip()}"
        )

    try:
        salida = json.loads(salida_texto)
    except json.JSONDecodeError as error:
        raise ErrorMotorDeepnest(
            f"El motor no devolvió JSON válido: {error}.\nSalida: {(salida_texto or '')[:400]}"
        ) from error

    posiciones: list[PosicionPieza] = []
    geometrias_colocadas: dict[str, GeometriaPieza] = {}
    for colocacion in salida["posiciones"]:
        if apilar_en_ancho:
            colocacion = _desde_coordenadas_transpuestas(colocacion, ancho_real_mm)
        geometria = geometrias[colocacion["pieza_id"]]
        posicion = _posicion_desde_colocacion(colocacion, geometria)
        posiciones.append(posicion)
        # Por id de instancia Y por id base: quien dibuje puede indexar
        # de cualquiera de las dos formas (`render_svg_plancha` prueba
        # primero la instancia y después la base).
        geometrias_colocadas[posicion.pieza_id] = geometria
        geometrias_colocadas[colocacion["pieza_id"]] = geometria

    resultado = ResultadoAnidado(
        posiciones=posiciones,
        planchas_usadas=int(salida["planchas_usadas"]),
        advertencias=list(salida.get("advertencias", [])),
    )

    return ResultadoDeepnest(
        resultado=resultado,
        geometrias=geometrias_colocadas,
        largo_corte_compartido_mm=_a_mm(float(salida.get("largo_corte_compartido_mm", 0))),
        diagnostico=salida.get("diagnostico", {}),
    )


__all__ = [
    "ErrorMotorDeepnest",
    "OpcionesMotorDeepnest",
    "ResultadoDeepnest",
    "anidar_con_deepnest",
]
