# A9 · Mensajes entendibles — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado:** escrito y aprobado por Enzo el 2026-10-15, con ejecución nativa y una pausa por tramo. **La implementación quedó para más adelante, a pedido de Enzo:** ninguna tarea empezada. No se ensayó sobre una copia: los bloques salen de leer el código de `feat/mensajes-entendibles` en `0457cac` (que incluye el arreglo del «utf-8», `aef764f`, [PR #25](https://github.com/enzopazzelli/carteleria/pull/25)). Lo que se aparte va al final, en «Desvíos».

**Goal:** Que todo error y aviso que ve una persona diga qué pasó y qué hacer, en palabras del taller, con la miniatura de las piezas y chapas que nombra y el detalle técnico aparte, en un desplegable y en un registro del servidor.

**Architecture:** El servidor tiene una forma única para errores y avisos (`app/mensajes.py`: `ErrorParaElUsuario`, `Aviso`) y un solo lugar que convierte cualquier falla en esa forma (`app/api/manejadores.py`). Los cálculos tiran errores con nombre propio que llevan los datos (los `id` de las piezas, los segundos); las rutas, que conocen los nombres del dibujo, los traducen (`app/api/traducir_errores.py`). En la pantalla, `ApiError` trae el error entero y un componente `Mensaje` lo muestra con miniaturas y el desplegable.

**Tech Stack:** Python 3.13, FastAPI, Starlette, SQLAlchemy, Alembic, Pydantic 2, `logging`, pytest; React 18 con TypeScript, TanStack Query, Vitest.

**Spec:** [`diseno.md`](diseno.md), en esta misma carpeta.

## Aclaraciones al diseño

Salen de leer el código al escribir este plan. Ninguna cambia una decisión de Enzo.

1. **Qué avisos pasan a la forma nueva.** Los que nombran piezas o chapas: los de una corrida de anidado, los de cada fila de la comparación y el motivo de Ajuste. Los avisos del costeo, de los totales del presupuesto y de la lectura del DXF siguen siendo texto (no nombran piezas guardadas); en el tramo 4 se revisan sus textos.
2. **Ajuste no rechaza un movimiento:** lo aplica y devuelve `valida: false` con un `motivo`. Ese `motivo` pasa a ser un aviso con las dos piezas y la chapa. **Hoy la pantalla no lo muestra:** dice «pasá el cursor para ver el motivo», pero no hay nada que lo muestre. La Tarea 12 lo muestra debajo del plano.
3. **Los avisos de una corrida tampoco se muestran hoy** en la pestaña Anidado (se guardan, pero ninguna pantalla los lee). La Tarea 12 los muestra.
4. **33 comprobaciones de las pruebas leen `detail` como texto.** Pasan a una ayuda, `mensaje_de(respuesta)`, en la misma tarea que cambia la forma (Tarea 3).
5. **Un `ValueError` sin nombre propio sigue mostrándose con su texto:** son los errores previstos de las rutas («El grupo no tiene piezas…»). La prueba guardiana (Tarea 14) revisa esos textos; cualquier otra excepción es inesperada.

## Global Constraints

- Todo texto que ve una persona va en castellano rioplatense y cumple la regla del §5.1 del diseño.
- Los commits no llevan línea de atribución (`Co-Authored-By`).
- `MENSAJE_INESPERADO` = «Algo falló en el servidor. Si se repite, avisale a quien mantiene el sistema y mandale el detalle.»
- Registro del servidor: `CARTELERIA_DATOS/registro/servidor.log`, rotando por tamaño con `PAR-54` y `PAR-55` (`REGISTRO.md`).
- Pruebas del backend sin tocar la base real: desde `backend/`, `mkdir -p local/tmp-a9/datos && CARTELERIA_DATOS="$PWD/local/tmp-a9/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a9/base"`, y después `rm -rf local/tmp-a9`. En lo que sigue, «correr la suite» quiere decir esto; para una sola prueba, el mismo comando con la ruta y `-k`.
- Pruebas de la pantalla: desde `frontend/`, `npm test` y `npx tsc -b`.
- Editar con la herramienta de edición (conserva los finales de línea); nunca `sed -i`.

## Review Focus

- **Una corrida o una comparación de antes de A9** (error como texto, avisos como textos sueltos): se tiene que leer igual, como mensaje sin detalle ni piezas. Lo prueba la Tarea 4.
- **Cancelar una comparación mientras una chapa calcula:** se cancela entera; la chapa a medio calcular no queda como «fila con error». Lo prueba la Tarea 7.
- **Un dato mal escrito en un campo que no está en la tabla de etiquetas:** mensaje genérico en castellano, nunca «Error 422». Lo prueba la Tarea 3.
- **El servidor se apaga en medio de una acción:** «No se pudo conectar con el servidor…», nunca «Failed to fetch». Lo prueba la Tarea 10.
- **Una pieza nombrada en un mensaje que ya no está en el trabajo** (se volvió a cargar el dibujo): el texto se ve igual y su miniatura no aparece, sin romper la pantalla. Lo prueba la Tarea 11.

---

## Tramo 1 — La base en el servidor

### Task 1: La forma de un mensaje

**Files:**
- Create: `backend/app/mensajes.py`
- Create: `backend/app/api/esquemas_mensajes.py`
- Test: `backend/tests/test_mensajes.py` (nuevo)

**Interfaces:**
- Produces: `MENSAJE_INESPERADO: str`; `ChapaNombrada(ejecucion_id: int, plancha: int)`; `Aviso(mensaje: str, piezas: tuple[int, ...] = (), chapas: tuple[ChapaNombrada, ...] = ())` con `.como_dict() -> dict`; `ErrorParaElUsuario(mensaje, *, detalle=None, piezas=(), chapas=(), piezas_invalidas=(), estado=400)` con `.mensaje`, `.detalle`, `.piezas`, `.chapas`, `.piezas_invalidas`, `.estado`, `.como_dict() -> dict`; `aviso_desde(valor: str | dict | Aviso) -> Aviso`; `lista_de_nombres(ids, nombres: dict[str, str]) -> str`; `error_para_guardar(error: BaseException) -> ErrorParaElUsuario`. En `esquemas_mensajes`: `ChapaNombradaLeer`, `AvisoLeer`, `ErrorLeer`, `avisos_leer(valores) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_mensajes.py`:

```python
"""La forma de un mensaje (A9, diseño §5.2)."""
from __future__ import annotations

from app.api.esquemas_mensajes import AvisoLeer, ErrorLeer, avisos_leer
from app.mensajes import (
    MENSAJE_INESPERADO,
    Aviso,
    ChapaNombrada,
    ErrorParaElUsuario,
    aviso_desde,
    error_para_guardar,
    lista_de_nombres,
)


def test_un_aviso_guardado_antes_de_a9_es_un_texto_suelto():
    assert aviso_desde("aviso viejo") == Aviso("aviso viejo")


def test_un_aviso_guardado_como_dict_vuelve_con_lo_que_nombra():
    guardado = {"mensaje": "m", "piezas": [3, 4], "chapas": [{"ejecucion_id": 7, "plancha": 1}]}

    aviso = aviso_desde(guardado)

    assert aviso == Aviso("m", (3, 4), (ChapaNombrada(7, 1),))
    assert aviso.como_dict() == guardado


def test_el_error_para_el_usuario_lleva_detalle_piezas_y_chapas():
    error = ErrorParaElUsuario("Texto claro", detalle="técnico", piezas=["3"], chapas=[ChapaNombrada(7, 0)], estado=409)

    assert error.estado == 409
    assert error.como_dict() == {
        "mensaje": "Texto claro",
        "detalle": "técnico",
        "piezas": [3],
        "chapas": [{"ejecucion_id": 7, "plancha": 0}],
    }


def test_las_piezas_invalidas_viajan_solo_si_hay():
    assert "piezas_invalidas" not in ErrorParaElUsuario("m").como_dict()
    assert ErrorParaElUsuario("m", piezas_invalidas=["5"]).como_dict()["piezas_invalidas"] == [5]


def test_la_lista_de_nombres_sigue_el_orden_y_no_repite():
    nombres = {"3": "aro", "4": "B-3"}

    assert lista_de_nombres(["4", "3", "4"], nombres) == "«B-3», «aro»"
    assert lista_de_nombres([9], nombres) == "«sin nombre»"


def test_un_value_error_es_un_error_previsto_con_su_texto():
    falla = error_para_guardar(ValueError("El grupo no tiene piezas."))

    assert falla.mensaje == "El grupo no tiene piezas."
    assert "ValueError" in falla.detalle


def test_cualquier_otra_excepcion_es_inesperada_con_la_traza_en_el_detalle():
    try:
        raise RuntimeError("bum")
    except RuntimeError as error:
        falla = error_para_guardar(error)

    assert falla.mensaje == MENSAJE_INESPERADO
    assert falla.estado == 500
    assert "RuntimeError: bum" in falla.detalle


def test_un_error_para_el_usuario_queda_como_esta():
    error = ErrorParaElUsuario("m")

    assert error_para_guardar(error) is error


def test_los_esquemas_leen_avisos_viejos_y_nuevos():
    leidos = [AvisoLeer(**a) for a in avisos_leer(["viejo", Aviso("nuevo", (2,))])]

    assert [a.mensaje for a in leidos] == ["viejo", "nuevo"]
    assert leidos[1].piezas == [2]
    assert ErrorLeer(mensaje="m").detalle is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: la suite con `tests/test_mensajes.py`.
Expected: FAIL con `ModuleNotFoundError: No module named 'app.mensajes'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/mensajes.py`:

```python
"""Mensajes para quien usa el sistema: errores y avisos, con las piezas y
chapas que nombran (A9, `docs/plan/A9-mensajes-entendibles/diseno.md §5.2`).

El texto es para una persona del taller (la regla está en
`CONVENCIONES.md`); lo técnico va en `detalle`, nunca en el mensaje."""
from __future__ import annotations

import traceback
from dataclasses import dataclass

#: Lo que ve quien usa el sistema cuando falla algo que nadie previó.
MENSAJE_INESPERADO = (
    "Algo falló en el servidor. Si se repite, avisale a quien mantiene el sistema y mandale el detalle."
)


@dataclass(frozen=True)
class ChapaNombrada:
    """Una chapa de un resultado de anidado: la `plancha` (desde 0) de la
    corrida `ejecucion_id`."""

    ejecucion_id: int
    plancha: int


@dataclass(frozen=True)
class Aviso:
    """Algo que conviene saber de un resultado que salió bien. El texto ya
    trae los nombres; `piezas` y `chapas` dicen qué dibujar al lado."""

    mensaje: str
    piezas: tuple[int, ...] = ()
    chapas: tuple[ChapaNombrada, ...] = ()

    def como_dict(self) -> dict:
        return {
            "mensaje": self.mensaje,
            "piezas": list(self.piezas),
            "chapas": [{"ejecucion_id": c.ejecucion_id, "plancha": c.plancha} for c in self.chapas],
        }


class ErrorParaElUsuario(Exception):
    """Un error con su mensaje para el usuario. El manejador del servidor
    (`app/api/manejadores.py`) lo convierte en la respuesta."""

    def __init__(
        self,
        mensaje: str,
        *,
        detalle: str | None = None,
        piezas=(),
        chapas=(),
        piezas_invalidas=(),
        estado: int = 400,
    ) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle = detalle
        self.piezas = tuple(int(i) for i in piezas)
        self.chapas = tuple(chapas)
        self.piezas_invalidas = tuple(int(i) for i in piezas_invalidas)
        self.estado = estado

    def como_dict(self) -> dict:
        datos = {**Aviso(self.mensaje, self.piezas, self.chapas).como_dict(), "detalle": self.detalle}
        if self.piezas_invalidas:
            datos["piezas_invalidas"] = list(self.piezas_invalidas)
        return datos


def aviso_desde(valor: str | dict | Aviso) -> Aviso:
    """Un aviso como venga: texto suelto (los guardados antes de A9), el
    dict guardado o el aviso mismo."""
    if isinstance(valor, Aviso):
        return valor
    if isinstance(valor, str):
        return Aviso(valor)
    return Aviso(
        valor["mensaje"],
        tuple(int(i) for i in valor.get("piezas") or ()),
        tuple(ChapaNombrada(int(c["ejecucion_id"]), int(c["plancha"])) for c in valor.get("chapas") or ()),
    )


def lista_de_nombres(ids, nombres: dict[str, str]) -> str:
    """«aro», «B-3»: los nombres del dibujo, en el orden de `ids` y sin repetir."""
    vistos = dict.fromkeys(str(i) for i in ids)
    return ", ".join(f"«{nombres.get(i, 'sin nombre')}»" for i in vistos)


def error_para_guardar(error: BaseException) -> ErrorParaElUsuario:
    """Lo que se muestra de una falla que no pasó por una traducción.

    Un `ErrorParaElUsuario` queda como está. Un `ValueError` es un error
    previsto que ya trae su texto (los de las rutas, y los de los cálculos
    hasta que tengan nombre propio). Cualquier otra cosa no la previó
    nadie: el mensaje es `MENSAJE_INESPERADO` y la traza va al detalle."""
    if isinstance(error, ErrorParaElUsuario):
        return error
    traza = "".join(traceback.format_exception(error))
    if isinstance(error, ValueError):
        return ErrorParaElUsuario(str(error), detalle=traza)
    return ErrorParaElUsuario(MENSAJE_INESPERADO, detalle=traza, estado=500)
```

`backend/app/api/esquemas_mensajes.py`:

```python
"""Cómo publica la API los errores y avisos (A9, diseño §5.2)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..mensajes import aviso_desde


class ChapaNombradaLeer(BaseModel):
    ejecucion_id: int
    plancha: int


class AvisoLeer(BaseModel):
    mensaje: str
    piezas: list[int] = Field(default_factory=list)
    chapas: list[ChapaNombradaLeer] = Field(default_factory=list)


class ErrorLeer(AvisoLeer):
    detalle: str | None = None
    piezas_invalidas: list[int] = Field(default_factory=list)


def avisos_leer(valores) -> list[dict]:
    """Para los `field_validator(mode="before")` de las listas de avisos:
    textos sueltos, dicts o `Aviso`, todos como dict."""
    return [aviso_desde(v).como_dict() for v in valores or []]
```

- [ ] **Step 4: Run test to verify it passes**

Run: la suite con `tests/test_mensajes.py`.
Expected: PASS (9 pruebas).

- [ ] **Step 5: Commit**

```bash
git add backend/app/mensajes.py backend/app/api/esquemas_mensajes.py backend/tests/test_mensajes.py
git commit -m "feat(mensajes): la forma de un error y de un aviso, con lo que nombran (A9)"
```

### Task 2: El registro del servidor

**Files:**
- Create: `backend/app/registro.py`
- Modify: `backend/app/config.py` (al final: `DIRECTORIO_REGISTRO`, `TAMANO_REGISTRO_BYTES`, `ARCHIVOS_DE_REGISTRO`)
- Modify: `backend/app/api/app.py` (`_ciclo_de_vida`)
- Test: `backend/tests/test_registro.py` (nuevo)

**Interfaces:**
- Produces: `registro() -> logging.Logger` (el logger `"carteleria"`); `configurar_registro(carpeta: Path, tamano_bytes: int, archivos: int) -> Path`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_registro.py`:

```python
"""El registro del servidor (A9, diseño §5.3)."""
from __future__ import annotations

from logging.handlers import RotatingFileHandler

import pytest

from app.registro import configurar_registro, registro


@pytest.fixture(autouse=True)
def _sin_archivos_abiertos_al_terminar():
    yield
    for manejador in list(registro().handlers):
        registro().removeHandler(manejador)
        manejador.close()


def _vaciar():
    for manejador in registro().handlers:
        manejador.flush()


def test_escribe_en_la_carpeta_con_fecha_y_nivel(tmp_path):
    ruta = configurar_registro(tmp_path / "registro", 10_000, 2)

    registro().error("una falla de prueba")
    _vaciar()

    assert ruta == tmp_path / "registro" / "servidor.log"
    assert "ERROR una falla de prueba" in ruta.read_text(encoding="utf-8")


def test_rota_por_tamano_y_guarda_los_archivos_pedidos(tmp_path):
    configurar_registro(tmp_path, 200, 2)

    for numero in range(30):
        registro().warning("línea %s %s", numero, "x" * 50)
    _vaciar()

    assert sorted(p.name for p in tmp_path.iterdir()) == ["servidor.log", "servidor.log.1", "servidor.log.2"]


def test_configurar_dos_veces_no_duplica_las_lineas(tmp_path):
    ruta = configurar_registro(tmp_path, 10_000, 2)
    configurar_registro(tmp_path, 10_000, 2)

    registro().error("una sola vez")
    _vaciar()

    assert ruta.read_text(encoding="utf-8").count("una sola vez") == 1


def test_otra_carpeta_reemplaza_el_archivo(tmp_path):
    configurar_registro(tmp_path / "a", 10_000, 2)
    ruta = configurar_registro(tmp_path / "b", 10_000, 2)

    archivos = [m for m in registro().handlers if isinstance(m, RotatingFileHandler)]
    assert [m.baseFilename for m in archivos] == [str(ruta.resolve())]
```

- [ ] **Step 2: Run test to verify it fails**

Run: la suite con `tests/test_registro.py`.
Expected: FAIL con `ModuleNotFoundError: No module named 'app.registro'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/registro.py`:

```python
"""El registro del servidor (A9, `docs/plan/A9-mensajes-entendibles/diseno.md §5.3`).

Guarda, con fecha y hora, cada error inesperado y cada corrida o
comparación que falla, con su traza: lo que la pantalla muestra en «Ver
detalle técnico» y no se pierde al cerrar la página. Rota por tamaño
(`PAR-54`, `PAR-55`)."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

NOMBRE = "carteleria"


def registro() -> logging.Logger:
    return logging.getLogger(NOMBRE)


def configurar_registro(carpeta: Path, tamano_bytes: int, archivos: int) -> Path:
    """Deja el registro escribiendo en `carpeta/servidor.log`. Se puede
    llamar varias veces (cada arranque de la app, cada prueba): si ya
    escribe ahí no agrega otro archivo, y si escribía en otra carpeta la
    cambia."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "servidor.log"
    logger = registro()
    logger.setLevel(logging.INFO)
    for manejador in list(logger.handlers):
        if not isinstance(manejador, RotatingFileHandler):
            continue
        if Path(manejador.baseFilename) == ruta.resolve():
            return ruta
        logger.removeHandler(manejador)
        manejador.close()
    manejador = RotatingFileHandler(ruta, maxBytes=tamano_bytes, backupCount=archivos, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(manejador)
    return ruta
```

Al final de `backend/app/config.py`:

```python
#: El registro del servidor (A9): las fallas con su traza, para quien
#: mantiene el sistema. Al lado de los datos, fuera de git.
DIRECTORIO_REGISTRO = DIRECTORIO_DATOS / "registro"

#: `PAR-54` y `PAR-55` (`docs/REGISTRO.md`): tamaño de cada archivo del
#: registro y cuántos viejos se guardan.
TAMANO_REGISTRO_BYTES = int(os.getenv("CARTELERIA_REGISTRO_BYTES", "1000000"))
ARCHIVOS_DE_REGISTRO = int(os.getenv("CARTELERIA_REGISTRO_ARCHIVOS", "5"))
```

En `backend/app/api/app.py`, sumar los imports y llamar al configurar en el ciclo de vida:

```python
from .. import config
from ..modelos.base import inicializar
from ..registro import configurar_registro
```

```python
@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    # Bindea `Sesion` al motor real. Las tablas las crea Alembic
    # (`alembic upgrade head`) — esta app nunca llama `create_all`.
    inicializar()
    configurar_registro(config.DIRECTORIO_REGISTRO, config.TAMANO_REGISTRO_BYTES, config.ARCHIVOS_DE_REGISTRO)
    yield
```

- [ ] **Step 4: Run test to verify it passes**

Run: la suite con `tests/test_registro.py`, y después la suite entera (el arranque de la app ahora configura el registro: tiene que seguir todo en verde).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/registro.py backend/app/config.py backend/app/api/app.py backend/tests/test_registro.py
git commit -m "feat(servidor): un registro con las fallas y su traza, en la carpeta de datos (A9)"
```

### Task 3: Un solo lugar que ataja los errores

**Files:**
- Create: `backend/app/api/etiquetas.py`
- Create: `backend/app/api/manejadores.py`
- Modify: `backend/app/api/app.py` (registrar los manejadores)
- Create: `backend/tests/api/ayudas.py`
- Modify: las 33 comprobaciones de `detail` en `backend/tests/api/test_rutas_{catalogo,comparaciones,nesting,presupuesto,seccionado,trabajos}.py`
- Test: `backend/tests/api/test_manejadores.py` (nuevo)

**Interfaces:**
- Consumes: `ErrorParaElUsuario`, `MENSAJE_INESPERADO` (Task 1); `registro()` (Task 2).
- Produces: `ETIQUETAS_DE_CAMPOS: dict[str, str]`; `mensaje_de_validacion(errores: list[dict]) -> str`; `registrar_manejadores(app: FastAPI) -> None`; en las pruebas, `mensaje_de(respuesta) -> str`. Toda respuesta de error trae `detail` como `{mensaje, detalle, piezas, chapas[, piezas_invalidas]}`.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_manejadores.py`:

```python
"""Un solo lugar que ataja los errores (A9, diseño §5.3)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.manejadores import registrar_manejadores
from app.mensajes import MENSAJE_INESPERADO, ErrorParaElUsuario

from .test_rutas_nesting import cliente  # noqa: F401
from .test_rutas_presupuesto import _crear_presupuesto


def _app_de_prueba() -> TestClient:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/claro")
    def _claro():
        raise ErrorParaElUsuario("Texto claro.", detalle="técnico", piezas=["3"], estado=409)

    @app.get("/texto")
    def _texto():
        raise HTTPException(404, "No existe el trabajo 9.")

    @app.get("/con-datos")
    def _con_datos():
        raise HTTPException(409, {"mensaje": "Faltan cosas.", "faltantes": ["margen"]})

    @app.get("/inesperado")
    def _inesperado():
        raise RuntimeError("bum")

    return TestClient(app, raise_server_exceptions=False)


def test_un_error_para_el_usuario_responde_con_su_estado_y_su_forma():
    respuesta = _app_de_prueba().get("/claro")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"mensaje": "Texto claro.", "detalle": "técnico", "piezas": [3], "chapas": []}


def test_un_error_de_texto_pasa_a_la_forma_nueva():
    respuesta = _app_de_prueba().get("/texto")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["mensaje"] == "No existe el trabajo 9."


def test_un_error_con_datos_conserva_los_datos():
    assert _app_de_prueba().get("/con-datos").json()["detail"] == {"mensaje": "Faltan cosas.", "faltantes": ["margen"]}


def test_una_direccion_que_no_existe_responde_en_castellano():
    assert _app_de_prueba().get("/no-existe").json()["detail"]["mensaje"] == "No existe esa dirección en el servidor."


def test_un_error_inesperado_da_el_mensaje_general_y_la_traza_queda_en_el_detalle_y_el_registro(caplog):
    with caplog.at_level(logging.ERROR, logger="carteleria"):
        respuesta = _app_de_prueba().get("/inesperado")

    cuerpo = respuesta.json()["detail"]
    assert respuesta.status_code == 500
    assert cuerpo["mensaje"] == MENSAJE_INESPERADO
    assert "RuntimeError: bum" in cuerpo["detalle"]
    assert "RuntimeError: bum" in caplog.text


def test_un_numero_mal_escrito_nombra_el_campo_como_en_pantalla(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "diez"})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["mensaje"] == "«Margen %»: escribí un número."
    assert "margen_pct" in respuesta.json()["detail"]["detalle"]


def test_un_campo_sin_etiqueta_da_un_mensaje_general(cliente):
    respuesta = cliente.post("/grupos/1/comparaciones", json={"formato_ids": [1], "criterio": "otro"})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["mensaje"] == "Uno de los datos no tiene la forma esperada."
```

- [ ] **Step 2: Run test to verify it fails**

Run: la suite con `tests/api/test_manejadores.py`.
Expected: FAIL con `ModuleNotFoundError: No module named 'app.api.manejadores'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/api/etiquetas.py`:

```python
"""Cómo se llama cada campo en la pantalla, para decir cuál está mal
escrito (A9, diseño §5.3). Solo los campos que escribe una persona; uno
que no está acá da un mensaje general."""
from __future__ import annotations

ETIQUETAS_DE_CAMPOS = {
    # Presupuesto (pestaña Costeo)
    "margen_pct": "Margen %",
    "iva_pct": "IVA %",
    "validez_dias": "Validez (días)",
    "total_fijado": "Total fijado",
    "cliente_id": "Cliente",
    "moneda": "Moneda",
    "descripcion": "Descripción",
    "cantidad": "Cantidad",
    "unidad": "Unidad",
    "precio_unitario": "Precio unitario",
    "valor_override": "Valor a mano",
    "texto_cliente": "Texto para el cliente",
    "precio_cliente": "Precio para el cliente",
    "nombre": "Nombre",
    "contacto": "Contacto",
    # Catálogo
    "ancho_mm": "Ancho (mm)",
    "alto_mm": "Alto (mm)",
    "costo_unidad_venta": "Precio por unidad de venta",
    # Anidado
    "kerf_mm": "Kerf (mm)",
    "margen_borde_mm": "Margen de borde (mm)",
    "separacion_piezas_mm": "Separación (mm)",
    "tiempo_maximo_s": "Tiempo máximo (s)",
    "segundos_por_busqueda": "Búsqueda por chapa (s)",
    "semilla": "Semilla",
    "simplificacion_mm": "Simplificación (mm)",
    # Seccionado y Ajuste
    "angulo_grados": "Ángulo",
    "desplazamiento_x_mm": "Corrimiento horizontal (mm)",
    "desplazamiento_y_mm": "Corrimiento vertical (mm)",
}

GENERICO = "Uno de los datos no tiene la forma esperada."

_QUE_PASA = {
    "decimal_parsing": "escribí un número",
    "decimal_type": "escribí un número",
    "float_parsing": "escribí un número",
    "float_type": "escribí un número",
    "finite_number": "escribí un número",
    "int_parsing": "escribí un número entero",
    "int_type": "escribí un número entero",
    "int_from_float": "escribí un número entero",
    "missing": "falta completarlo",
    "string_too_short": "no puede quedar vacío",
    "string_too_long": "es demasiado largo",
    "literal_error": "no es una de las opciones",
    "enum": "no es una de las opciones",
    "bool_parsing": "tiene que ser sí o no",
    "bool_type": "tiene que ser sí o no",
}

_LIMITES = {
    "greater_than": "tiene que ser mayor que {gt}",
    "greater_than_equal": "tiene que ser {ge} o más",
    "less_than": "tiene que ser menor que {lt}",
    "less_than_equal": "tiene que ser {le} o menos",
}


def _numero(valor) -> str:
    return str(valor).replace(".", ",")


def mensaje_de_validacion(errores: list[dict]) -> str:
    """El primer error de Pydantic, dicho con la etiqueta de la pantalla."""
    if not errores:
        return GENERICO
    error = errores[0]
    campo = next((p for p in reversed(error.get("loc", ())) if isinstance(p, str) and p != "body"), None)
    etiqueta = ETIQUETAS_DE_CAMPOS.get(campo)
    tipo = error.get("type", "")
    contexto = error.get("ctx") or {}
    if tipo == "value_error":
        # Los validadores propios ya escriben su texto según la regla.
        texto = str(contexto.get("error", "")).strip()
        if not texto:
            return GENERICO
        return f"«{etiqueta}»: {texto}" if etiqueta else texto
    if etiqueta is None:
        return GENERICO
    if tipo in _LIMITES:
        return f"«{etiqueta}»: " + _LIMITES[tipo].format(**{k: _numero(v) for k, v in contexto.items()}) + "."
    return f"«{etiqueta}»: {_QUE_PASA.get(tipo, 'no tiene la forma esperada')}."
```

`backend/app/api/manejadores.py`:

```python
"""Un solo lugar que convierte cualquier falla en la respuesta que lee la
pantalla: `{"detail": {mensaje, detalle, piezas, chapas}}` (A9, diseño §5.3)."""
from __future__ import annotations

import traceback
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..mensajes import MENSAJE_INESPERADO, ErrorParaElUsuario
from ..registro import registro
from .etiquetas import mensaje_de_validacion

#: Los textos que pone Starlette solo, en inglés.
_POR_DEFECTO = {
    404: "No existe esa dirección en el servidor.",
    405: "El servidor no acepta esa operación en esta dirección.",
}


def _detalle_de_http(error: StarletteHTTPException) -> dict:
    detalle = error.detail
    if isinstance(detalle, dict) and "mensaje" in detalle:
        return detalle
    if isinstance(detalle, str):
        if detalle == HTTPStatus(error.status_code).phrase:
            return {"mensaje": _POR_DEFECTO.get(error.status_code, "El servidor no pudo atender el pedido.")}
        return {"mensaje": detalle}
    return {"mensaje": "El servidor no pudo atender el pedido.", "detalle": repr(detalle)}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorParaElUsuario)
    async def _para_el_usuario(_: Request, error: ErrorParaElUsuario) -> JSONResponse:
        return JSONResponse(status_code=error.estado, content={"detail": error.como_dict()})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, error: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": _detalle_de_http(error)},
            headers=getattr(error, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, error: RequestValidationError) -> JSONResponse:
        errores = error.errors()
        detalle = "\n".join(f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('msg', '')}" for e in errores)
        return JSONResponse(status_code=422, content={"detail": {"mensaje": mensaje_de_validacion(errores), "detalle": detalle}})

    @app.exception_handler(Exception)
    async def _inesperado(peticion: Request, error: Exception) -> JSONResponse:
        traza = "".join(traceback.format_exception(error))
        registro().error("Error inesperado en %s %s\n%s", peticion.method, peticion.url.path, traza)
        return JSONResponse(status_code=500, content={"detail": {"mensaje": MENSAJE_INESPERADO, "detalle": traza}})
```

En `backend/app/api/app.py`, después de `app = FastAPI(...)`:

```python
from .manejadores import registrar_manejadores
```

```python
registrar_manejadores(app)
```

`backend/tests/api/ayudas.py`:

```python
"""Ayudas comunes de las pruebas de la API."""
from __future__ import annotations


def mensaje_de(respuesta) -> str:
    """El texto del error de una respuesta (A9: `detail` es `{mensaje, detalle, ...}`)."""
    return respuesta.json()["detail"]["mensaje"]
```

Las 33 comprobaciones que leen `detail` como texto pasan a `mensaje_de(...)`. Con un guion de un solo uso, fuera de git, que conserva los finales de línea:

```python
# backend/local/tmp-a9/mensaje_de.py — correr desde backend/ y borrar después
import re
from pathlib import Path

for nombre in ("catalogo", "comparaciones", "nesting", "presupuesto", "seccionado", "trabajos"):
    ruta = Path(f"tests/api/test_rutas_{nombre}.py")
    with ruta.open(encoding="utf-8", newline="") as archivo:
        texto = archivo.read()
    lineas = texto.splitlines(keepends=True)
    for i, linea in enumerate(lineas):
        # El PDF del presupuesto usa `detail` como dict (`faltantes`): queda.
        if 'detalle = respuesta.json()["detail"]' in linea and "faltantes" in "".join(lineas[i : i + 3]):
            continue
        lineas[i] = re.sub(r'(\w+)\.json\(\)\["detail"\](?!\[)', r"mensaje_de(\1)", linea)
    nuevo = "".join(lineas)
    if nuevo != texto:
        if "from .ayudas import mensaje_de" not in nuevo:
            nuevo = nuevo.replace("\nimport pytest", "\nimport pytest\n\nfrom .ayudas import mensaje_de", 1)
        with ruta.open("w", encoding="utf-8", newline="") as archivo:
            archivo.write(nuevo)
```

Después, `grep -n 'json()\["detail"\]' backend/tests/api/*.py` tiene que mostrar solo `["detail"]["piezas_invalidas"]` (seccionado) y el `detalle` del PDF (presupuesto); `grep -n "from .ayudas import" backend/tests/api/*.py` tiene que dar los seis archivos (si alguno no empieza con `import pytest`, sumar el import a mano con la herramienta de edición).

- [ ] **Step 4: Run test to verify it passes**

Run: la suite entera.
Expected: PASS. Si alguna prueba vieja falla por leer `detail` como texto por otro camino, pasarla a `mensaje_de`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/etiquetas.py backend/app/api/manejadores.py backend/app/api/app.py backend/tests/api/
git commit -m "feat(servidor): un solo lugar que ataja los errores, con el campo como se llama en pantalla (A9)"
```

### Task 4: La corrida y la comparación guardan el error entero

**Files:**
- Create: `backend/alembic/versions/c3a91f4e7b20_error_datos_de_la_corrida.py`
- Modify: `backend/app/modelos/trabajo.py` (`EjecucionNesting.error_datos`, `error_completo`)
- Modify: `backend/app/api/esquemas_nesting.py` (`EjecucionLeer.error`, `.mensajes`; `OpcionFormatoLeer.advertencias`; `ComparacionLeer.error`)
- Modify: `backend/app/api/rutas_nesting.py` (`_correr_anidado`: el `except` y `ejecucion.mensajes`)
- Modify: `backend/app/api/rutas_comparaciones.py` (`_Comparacion.error`, `_correr`)
- Create: `frontend/src/api/mensajes.ts`
- Modify: `frontend/src/api/nesting.ts` (`Ejecucion.mensajes`, `.error`), `frontend/src/api/piezasYgrupos.ts` (`OpcionFormato.advertencias`, `Comparacion.error`), `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`, `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`
- Test: `backend/tests/modelos/test_migracion_error_datos.py` (nuevo), `backend/tests/api/test_rutas_nesting.py`, `backend/tests/api/test_rutas_comparaciones.py`

**Interfaces:**
- Consumes: `error_para_guardar`, `avisos_leer`, `ErrorLeer`, `AvisoLeer` (Task 1); `registro()` (Task 2).
- Produces: `EjecucionNesting.error_datos: dict | None` y `.error_completo -> dict | None`; `EjecucionLeer.error: ErrorLeer | None`, `.mensajes: list[AvisoLeer] | None`; `OpcionFormatoLeer.advertencias: list[AvisoLeer]`; `ComparacionLeer.error: ErrorLeer | None`. En la pantalla: los tipos `ChapaNombrada`, `Aviso`, `ErrorDelServidor` de `api/mensajes.ts`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/modelos/test_migracion_error_datos.py`:

```python
"""La columna del error entero de una corrida (A9): sube y vuelve."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

_ANTES = "a8f2c61b9d04"


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    return config


def _columnas(base: Path) -> list[str]:
    conexion = sqlite3.connect(base)
    try:
        return [fila[1] for fila in conexion.execute("pragma table_info(ejecuciones_nesting)")]
    finally:
        conexion.close()


def test_la_migracion_agrega_error_datos_y_vuelve(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()

    command.upgrade(config, "head")
    despues = _columnas(base)
    command.downgrade(config, _ANTES)

    assert "error_datos" in despues
    assert "error_datos" not in _columnas(base)
```

Al final de `backend/tests/api/test_rutas_nesting.py`:

```python
def test_un_anidado_que_falla_sin_que_nadie_lo_prevea_guarda_el_mensaje_general_y_la_traza(
    cliente, tmp_path, monkeypatch, caplog
):
    from app.api import rutas_nesting
    from app.mensajes import MENSAJE_INESPERADO

    def bum(self, piezas, tope_planchas_advertencia):
        raise RuntimeError("bum")

    monkeypatch.setattr(rutas_nesting.MotorNestingRectangular, "anidar", bum)
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)

    with caplog.at_level("WARNING", logger="carteleria"):
        ejecucion_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
        final = _esperar_estado(cliente, ejecucion_id)

    assert final["estado"] == "error"
    assert final["error"]["mensaje"] == MENSAJE_INESPERADO
    assert "RuntimeError: bum" in final["error"]["detalle"]
    assert "RuntimeError: bum" in caplog.text


def test_una_corrida_de_antes_de_a9_se_lee_igual(cliente, tmp_path):
    from sqlalchemy.orm import Session

    from app.modelos.trabajo import EjecucionNesting

    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    with Session(cliente.motor) as sesion:
        vieja = EjecucionNesting(grupo_id=grupo["id"], motor="rectpack", estado="error", error="texto viejo", mensajes=["aviso viejo"])
        sesion.add(vieja)
        sesion.commit()
        vieja_id = vieja.id

    leida = cliente.get(f"/ejecuciones/{vieja_id}").json()

    assert leida["error"] == {"mensaje": "texto viejo", "detalle": None, "piezas": [], "chapas": [], "piezas_invalidas": []}
    assert leida["mensajes"] == [{"mensaje": "aviso viejo", "piezas": [], "chapas": []}]
```

En `backend/tests/api/test_rutas_comparaciones.py`, `test_una_falla_a_mitad_de_camino_queda_en_la_comparacion` pasa a leer el mensaje (la Tarea 7 la reemplaza):

```python
    assert final["estado"] == "error"
    assert "falla de prueba" in final["error"]["mensaje"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: la suite con `tests/modelos/test_migracion_error_datos.py`, `tests/api/test_rutas_nesting.py -k "antes_de_a9 or nadie_lo_prevea"` y `tests/api/test_rutas_comparaciones.py -k mitad_de_camino`.
Expected: FAIL (no existe la columna; `error` es texto).

- [ ] **Step 3: Write minimal implementation**

`backend/alembic/versions/c3a91f4e7b20_error_datos_de_la_corrida.py`:

```python
"""error entero de la corrida

Revision ID: c3a91f4e7b20
Revises: a8f2c61b9d04
Create Date: 2026-10-15 18:00:00.000000

A9: `error` sigue siendo el mensaje; el resto del error (detalle, piezas,
chapas) va en `error_datos`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.modelos.tipos  # noqa: F401 - la plantilla lo pide para todas las migraciones


revision: str = 'c3a91f4e7b20'
down_revision: Union[str, Sequence[str], None] = 'a8f2c61b9d04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('ejecuciones_nesting', schema=None) as batch_op:
        batch_op.add_column(sa.Column('error_datos', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ejecuciones_nesting', schema=None) as batch_op:
        batch_op.drop_column('error_datos')
```

En `backend/app/modelos/trabajo.py`, debajo de `error` en `EjecucionNesting`:

```python
    #: Lo que no entra en `error` (A9): `detalle`, `piezas`, `chapas` y, si
    #: hay, `piezas_invalidas`. `error` sigue siendo el mensaje.
    error_datos: Mapped[dict | None] = mapped_column(JSON, default=None)
```

y, como método de la clase:

```python
    @property
    def error_completo(self) -> dict | None:
        """El error como lo publica la API (`ErrorLeer`). Una corrida de
        antes de A9 tiene solo el mensaje."""
        if self.error is None:
            return None
        return {**(self.error_datos or {}), "mensaje": self.error}
```

En `backend/app/api/esquemas_nesting.py`, sumar a los imports `AliasChoices` y `field_validator` de `pydantic`, y:

```python
from .esquemas_mensajes import AvisoLeer, ErrorLeer, avisos_leer
```

En `EjecucionLeer`, reemplazar `mensajes: list | None` y `error: str | None` por:

```python
    mensajes: list[AvisoLeer] | None
    #: La corrida guarda el mensaje en `error` y el resto en `error_datos`;
    #: `error_completo` los junta (A9).
    error: ErrorLeer | None = Field(default=None, validation_alias=AliasChoices("error_completo", "error"))
```

y sumarle:

```python
    @field_validator("mensajes", mode="before")
    @classmethod
    def _avisos_de_antes_y_de_ahora(cls, valor):
        return None if valor is None else avisos_leer(valor)

    @field_validator("error", mode="before")
    @classmethod
    def _error_de_texto(cls, valor):
        return {"mensaje": valor} if isinstance(valor, str) else valor
```

En `OpcionFormatoLeer`, `advertencias: list[str]` pasa a `advertencias: list[AvisoLeer] = Field(default_factory=list)`, con:

```python
    @field_validator("advertencias", mode="before")
    @classmethod
    def _avisos(cls, valor):
        return avisos_leer(valor)
```

En `ComparacionLeer`, `error: str | None = None` pasa a `error: ErrorLeer | None = None`.

En `backend/app/api/rutas_nesting.py`, imports:

```python
from ..mensajes import error_para_guardar
from ..registro import registro
from .esquemas_mensajes import avisos_leer
```

El `except` de `_correr_anidado` queda:

```python
        except Exception as error:  # noqa: BLE001 - cualquier falla del motor se reporta, no se pierde
            sesion.refresh(ejecucion)
            if ejecucion.estado == EstadoEjecucion.CANCELADA.value:
                return  # se canceló mientras corría: no pisar esa decisión con un error
            falla = error_para_guardar(error)
            registro().warning("El anidado #%s terminó en error: %s\n%s", ejecucion_id, falla.mensaje, falla.detalle or "")
            ejecucion.estado = EstadoEjecucion.ERROR.value
            ejecucion.error = falla.mensaje
            ejecucion.error_datos = {k: v for k, v in falla.como_dict().items() if k != "mensaje"}
            sesion.commit()
            return
```

y `ejecucion.mensajes = resultado.advertencias` pasa a `ejecucion.mensajes = avisos_leer(resultado.advertencias)`.

En `backend/app/api/rutas_comparaciones.py`, imports:

```python
from ..mensajes import error_para_guardar
from ..registro import registro
from .esquemas_mensajes import ErrorLeer
```

`_Comparacion.error: str | None = None` pasa a `error: ErrorLeer | None = None`, y el `except` de `_correr`:

```python
    except Exception as error:  # noqa: BLE001 - cualquier falla queda en la comparación, no se pierde
        if not comparacion.cancelar.is_set():
            falla = error_para_guardar(error)
            registro().warning("La comparación #%s terminó en error: %s\n%s", comparacion.id, falla.mensaje, falla.detalle or "")
            comparacion.error = ErrorLeer(**falla.como_dict())
            comparacion.estado = "error"
```

`frontend/src/api/mensajes.ts`:

```ts
/** Errores y avisos del servidor (A9, docs/plan/A9-mensajes-entendibles/diseno.md §5.2). */

/** Una chapa de un resultado: la `plancha` (desde 0) del anidado `ejecucion_id`. */
export interface ChapaNombrada {
  ejecucion_id: number;
  plancha: number;
}

/** El texto ya trae los nombres; `piezas` y `chapas` dicen qué dibujar al lado. */
export interface Aviso {
  mensaje: string;
  piezas: number[];
  chapas: ChapaNombrada[];
}

export interface ErrorDelServidor extends Aviso {
  detalle: string | null;
  piezas_invalidas?: number[];
}
```

Tipos: en `api/nesting.ts`, `Ejecucion.mensajes: Aviso[] | null` y `Ejecucion.error: ErrorDelServidor | null`; en `api/piezasYgrupos.ts`, `OpcionFormato.advertencias: Aviso[]` y `Comparacion.error: ErrorDelServidor | null` (con `import type { Aviso, ErrorDelServidor } from "./mensajes";`).

Usos, para que la pantalla no se rompa hasta el tramo 3:
- `AnidadoTab.tsx`: `{enCurso.error && <span className="ml-2 text-conflict">{enCurso.error.mensaje}</span>}`.
- `GruposTab.tsx`: `setError(comparacion.error?.mensaje ?? "No se pudo comparar.")`, y los avisos de la comparación: `resultado.flatMap((opcion) => (opcion.advertencias ?? []).map((aviso) => aviso.mensaje))`.

`npx tsc -b` dice si queda otro uso.

- [ ] **Step 4: Run tests to verify they pass**

Run: la suite entera; en `frontend/`, `npm test` y `npx tsc -b`.
Expected: PASS y sin errores de tipos. Si alguna prueba vieja lee `["error"]` como texto (`grep -n '\["error"\]' backend/tests/api/*.py`), pasarla a `["error"]["mensaje"]`.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/c3a91f4e7b20_error_datos_de_la_corrida.py backend/app/modelos/trabajo.py backend/app/api/ backend/tests/ frontend/src/api/ frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx frontend/src/routes/TrabajoWorkspace/GruposTab.tsx
git commit -m "feat(anidado): la corrida y la comparacion guardan el error entero, y los avisos con lo que nombran (A9)"
```

**Pausa del tramo 1:** suite del servidor, `npm test`, `npx tsc -b`, y el ok de Enzo.

---

## Tramo 2 — Anidado y comparación

### Task 5: Los errores de los cálculos con nombre propio

**Files:**
- Modify: `backend/app/services/nesting/sparrow.py` (clases nuevas; `preparar_entrada`, `convertir_y_validar`, `anidar_sparrow`)
- Modify: `backend/app/services/nesting/engine.py` (`_validar_todas_colocadas`)
- Test: `backend/tests/services/nesting/test_sparrow.py`, `backend/tests/services/nesting/test_engine.py`

**Interfaces:**
- Produces, en `sparrow.py`, subclases de `ValueError` (lo que hoy los ataja sigue andando): `PiezasQueNoEntran(ids)` con `.ids: list[str]`; `PiezaSinContorno(pieza_id)` con `.pieza_id: str`; `SinLugarUtil()`; `TiempoAgotado(segundos)` con `.segundos`; `ResultadoQueNoPasaElControl(motivo)` con `.motivo: str`; `CalculoInterrumpido(registro)` con `.registro: str`. En `engine.py`: `PiezasSinUbicar(ids)` con `.ids: list[str]`. Su `str()` es técnico: va al detalle.

- [ ] **Step 1: Write the failing test**

Al final de `backend/tests/services/nesting/test_sparrow.py`:

```python
from app.services.nesting.sparrow import (
    CalculoInterrumpido,
    PiezaSinContorno,
    PiezasQueNoEntran,
    ResultadoQueNoPasaElControl,
    SinLugarUtil,
    TiempoAgotado,
)


def test_una_pieza_que_no_entra_dice_cual_es():
    piezas, geometrias, _, params = datos()

    with pytest.raises(PiezasQueNoEntran) as error:
        preparar_entrada(piezas, geometrias, Plancha(D(15), D(15)), params, OpcionesSparrow())

    assert error.value.ids == ["1"]


def test_una_pieza_sin_contorno_dice_cual_es():
    piezas, _, plancha, params = datos()

    with pytest.raises(PiezaSinContorno) as error:
        preparar_entrada(piezas, {}, plancha, params, OpcionesSparrow())

    assert error.value.pieza_id == "1"


def test_una_chapa_sin_lugar_util_tiene_nombre():
    piezas, geometrias, _, _ = datos()
    params = ParametrosCorte(D(0), D(10), D(0), RotacionPermitida.LIBRE_0_90)

    with pytest.raises(SinLugarUtil):
        preparar_entrada(piezas, geometrias, Plancha(D(20), D(20)), params, OpcionesSparrow())


def test_sin_tiempo_dice_cuantos_segundos_tenia():
    with pytest.raises(TiempoAgotado) as error:
        anidar_sparrow(*datos(), OpcionesSparrow(segundos_por_busqueda=10, tiempo_maximo_s=0.01))

    assert error.value.segundos == 0.01


def test_un_resultado_que_no_pasa_el_control_lleva_el_motivo():
    entrada = preparar_entrada(*datos(), OpcionesSparrow())
    q = {'id': '1#0', 'sheet': 0, 'rotation': 0, 'tx': 0, 'ty': 0}

    with pytest.raises(ResultadoQueNoPasaElControl) as error:
        convertir_y_validar(entrada, [q, q])

    assert "duplicadas" in error.value.motivo


def test_un_worker_que_se_corta_lleva_su_registro(monkeypatch, tmp_path):
    con_worker(monkeypatch, worker_que_falla(tmp_path, "print('ValueError: causa de prueba', file=sys.stderr)"))

    with pytest.raises(CalculoInterrumpido) as error:
        anidar_sparrow(*datos(3), OpcionesSparrow(tiempo_maximo_s=20))

    assert "causa de prueba" in error.value.registro
```

Al final de `backend/tests/services/nesting/test_engine.py` (ya importa `Decimal`, `pytest`, `MotorNestingRectangular`, `ParametrosCorte`, `Pieza`, `Plancha` y `RotacionPermitida`; el import de `PiezasSinUbicar` va arriba, junto al de `MotorNestingRectangular`):

```python
from app.services.nesting.engine import PiezasSinUbicar


def test_las_piezas_que_el_motor_rectangular_no_ubica_tienen_nombre():
    motor = MotorNestingRectangular(
        Plancha(Decimal(100), Decimal(100)),
        ParametrosCorte(Decimal(0), Decimal(0), Decimal(0), RotacionPermitida.LIBRE_0_90),
    )

    with pytest.raises(PiezasSinUbicar) as error:
        motor._validar_todas_colocadas([], [Pieza("7", Decimal(10), Decimal(10))])

    assert error.value.ids == ["7"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: la suite con `tests/services/nesting/`.
Expected: FAIL con `ImportError: cannot import name 'CalculoInterrumpido'`.

- [ ] **Step 3: Write minimal implementation**

En `backend/app/services/nesting/sparrow.py`, debajo de `ErrorGeometriaSparrow`:

```python
# Las fallas del cálculo, con nombre propio y los datos que hacen falta
# para decirlas (A9). Su texto es técnico: va al detalle. La ruta, que
# conoce los nombres del dibujo, arma el mensaje para el usuario
# (`app/api/traducir_errores.py`).

class PiezasQueNoEntran(ValueError):
    def __init__(self, ids):
        self.ids = [str(i) for i in ids]
        super().__init__('Piezas que no entran con el kerf y margen actuales: ' + ', '.join(self.ids) + '.')


class PiezaSinContorno(ValueError):
    def __init__(self, pieza_id):
        self.pieza_id = str(pieza_id)
        super().__init__(f'La pieza {pieza_id} no tiene contorno.')


class SinLugarUtil(ValueError):
    def __init__(self):
        super().__init__('Los parámetros no dejan un formato útil válido.')


class TiempoAgotado(ValueError):
    def __init__(self, segundos):
        self.segundos = segundos
        super().__init__(f'Sparrow excedió el tiempo máximo ({segundos} s) sin un anidado completo.')


class ResultadoQueNoPasaElControl(ValueError):
    def __init__(self, motivo):
        self.motivo = motivo
        super().__init__(motivo)


class CalculoInterrumpido(ValueError):
    def __init__(self, registro):
        self.registro = registro
        super().__init__('Sparrow no pudo calcular: ' + registro)
```

Reemplazos en el mismo archivo:

| Hoy | Queda |
|---|---|
| `raise ValueError('Los parámetros no dejan un formato útil válido.')` | `raise SinLugarUtil()` |
| `raise ValueError(f'La pieza {p.id} necesita un contorno real para Sparrow.')` | `raise PiezaSinContorno(p.id)` |
| `raise ValueError('Piezas que no entran con el kerf y margen actuales: '+', '.join(blocked)+'. Revisar formato o seccionado; no se omiten piezas.')` | `raise PiezasQueNoEntran(blocked)` |
| En `convertir_y_validar`, cada `raise ValueError('<motivo>')` (piezas faltantes o duplicadas, colocación inválida, rotación no permitida, sale del formato útil, invade el margen/kerf, viola la separación, índices de chapa inconsistentes) | `raise ResultadoQueNoPasaElControl('<el mismo motivo>')` |
| `raise ValueError('Sparrow excedió el tiempo máximo; no se guardó un plano parcial.')` | `raise TiempoAgotado(opciones.tiempo_maximo_s)` |
| `raise ValueError('Sparrow no pudo calcular: '+registro[-2000:])` | `raise CalculoInterrumpido(registro[-2000:])` |

`raise ValueError('Anidado cancelado.')` y `raise ValueError('No hay piezas para anidar.')` quedan.

En `backend/app/services/nesting/engine.py`, arriba de la clase del motor:

```python
class PiezasSinUbicar(ValueError):
    """El motor rectangular no ubicó todas las piezas (A9). Fallar acá, en
    vez de descartarlas en silencio, es la corrección de
    `DECISIONES-Y-BLOQUEANTES.md §1.2`."""

    def __init__(self, ids):
        self.ids = sorted(str(i) for i in ids)
        super().__init__(f"El motor no pudo ubicar todas las piezas (no colocadas: {self.ids}).")
```

y en `_validar_todas_colocadas`, el `raise ValueError(...)` entero pasa a `raise PiezasSinUbicar(faltantes)`.

- [ ] **Step 4: Run test to verify it passes**

Run: la suite entera.
Expected: PASS. Las pruebas viejas con `match='no entran'`, `'tiempo máximo'`, `'duplicadas'`, `'separación'`, `'Rotación'`, `'ninguna pieza entró'` y `'causa de prueba'` siguen pasando: los textos técnicos conservan esas palabras.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nesting/sparrow.py backend/app/services/nesting/engine.py backend/tests/services/nesting/
git commit -m "feat(anidado): las fallas del calculo con nombre propio y sus datos (A9)"
```

### Task 6: La ruta traduce: nombres del dibujo en lugar de números

**Files:**
- Create: `backend/app/api/traducir_errores.py`
- Modify: `backend/app/api/rutas_nesting.py` (`anidar`, `_correr_anidado`, `_ComparacionPreparada`, `_preparar_comparacion`, `comparar_formatos_de_grupo`; se borra `_error_de_comparacion`)
- Test: `backend/tests/api/test_traducir_errores.py` (nuevo), `backend/tests/api/test_rutas_nesting.py`

**Interfaces:**
- Consumes: las clases de la Task 5; `ErrorGeometriaSparrow` (`.piezas_invalidas`); `ErrorParaElUsuario`, `lista_de_nombres`, `error_para_guardar` (Task 1).
- Produces: `nombres_de_piezas(piezas) -> dict[str, str]` (de `str(Pieza.id)` a `Pieza.id_origen`); `para_el_usuario(error, nombres, *, plancha=None, material=None) -> ErrorParaElUsuario`; `medida(plancha) -> str` («1220 × 2440»); `_ComparacionPreparada.nombres: dict[str, str]`.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_traducir_errores.py`:

```python
"""Los errores de los cálculos, dichos para el usuario (A9, diseño §5.4)."""
from __future__ import annotations

from decimal import Decimal as D

from app.api.traducir_errores import medida, para_el_usuario
from app.mensajes import MENSAJE_INESPERADO, ErrorParaElUsuario
from app.services.nesting.engine import PiezasSinUbicar
from app.services.nesting.models import Plancha
from app.services.nesting.sparrow import (
    CalculoInterrumpido,
    ErrorGeometriaSparrow,
    PiezaSinContorno,
    PiezasQueNoEntran,
    ResultadoQueNoPasaElControl,
    SinLugarUtil,
    TiempoAgotado,
)

NOMBRES = {"3": "aro", "4": "B-3"}
CHAPA = Plancha(D("1000.00"), D("2000.00"))


def test_la_medida_va_sin_ceros_de_mas():
    assert medida(CHAPA) == "1000 × 2000"
    assert medida(Plancha(D("1000.5"), D("1000"))) == "1000,5 × 1000"


def test_piezas_que_no_entran_con_sus_nombres_y_la_chapa():
    error = para_el_usuario(PiezasQueNoEntran(["3", "4"]), NOMBRES, plancha=CHAPA)

    assert error.mensaje == (
        "Estas piezas no entran en la chapa de 1000 × 2000 con el margen y el kerf actuales: "
        "«aro», «B-3». Elegí una chapa más grande o seccionalas."
    )
    assert error.piezas == (3, 4)


def test_contorno_mal_dibujado_marca_las_piezas():
    error = para_el_usuario(ErrorGeometriaSparrow(["4"]), NOMBRES)

    assert error.mensaje == "Estas piezas tienen el contorno o los huecos mal dibujados: «B-3». Corregí el dibujo y volvé a cargarlo."
    assert error.piezas == (4,) and error.piezas_invalidas == (4,)


def test_pieza_sin_contorno():
    assert para_el_usuario(PiezaSinContorno("3"), NOMBRES).mensaje == "«aro» no tiene contorno: volvé a cargar el dibujo."


def test_chapa_sin_lugar_util_nombra_el_material():
    error = para_el_usuario(SinLugarUtil(), NOMBRES, plancha=CHAPA, material="CHAPA NEGRA")

    assert error.mensaje == (
        "Con el margen, el kerf y la separación de «CHAPA NEGRA», a la chapa de 1000 × 2000 no le queda "
        "lugar útil. Revisá esos valores o elegí otra chapa."
    )


def test_sin_tiempo():
    assert para_el_usuario(TiempoAgotado(30), NOMBRES).mensaje == "No llegó a un resultado en 30 s. Probá con más tiempo."


def test_un_resultado_que_no_pasa_el_control_deja_el_motivo_en_el_detalle():
    error = para_el_usuario(ResultadoQueNoPasaElControl("Índices de chapa inconsistentes."), NOMBRES)

    assert error.mensaje == (
        "El cálculo dio un resultado que no pasó el control (piezas que se pisan, que salen de la chapa "
        "o que faltan) y no se guardó. Probá de nuevo; si se repite, avisá."
    )
    assert error.detalle == "Índices de chapa inconsistentes."


def test_un_calculo_interrumpido_deja_el_registro_en_el_detalle():
    error = para_el_usuario(CalculoInterrumpido("Traceback… PanicException"), NOMBRES)

    assert error.mensaje == "El cálculo se interrumpió por un error interno. Probá de nuevo; si se repite, avisá."
    assert error.detalle == "Traceback… PanicException"


def test_el_motor_rectangular_nombra_las_piezas():
    error = para_el_usuario(PiezasSinUbicar(["3"]), NOMBRES)

    assert error.mensaje == "No se pudieron ubicar estas piezas en la chapa: «aro»."
    assert error.piezas == (3,)


def test_lo_que_ya_es_para_el_usuario_queda_y_lo_demas_va_como_siempre():
    propio = ErrorParaElUsuario("m")

    assert para_el_usuario(propio, NOMBRES) is propio
    assert para_el_usuario(ValueError("El grupo no tiene piezas."), NOMBRES).mensaje == "El grupo no tiene piezas."
    assert para_el_usuario(RuntimeError("bum"), NOMBRES).mensaje == MENSAJE_INESPERADO
```

Al final de `backend/tests/api/test_rutas_nesting.py`:

```python
def test_anidar_una_pieza_mas_grande_que_la_chapa_la_nombra(cliente, tmp_path):
    trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path, ancho=2000, alto=100)
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]

    respuesta = cliente.post(f"/grupos/{grupo['id']}/anidar", json={"motor": "sparrow"})

    detalle = respuesta.json()["detail"]
    assert respuesta.status_code == 400
    assert detalle["mensaje"].startswith("Estas piezas no entran en la chapa de 1000 × 1000")
    assert f"«{pieza['id_origen']}»" in detalle["mensaje"]
    assert detalle["piezas"] == [pieza["id"]]
```

(Si `_trabajo_con_grupo_listo` arma una chapa de otra medida, ajustar «1000 × 1000» a la que arma: mirar `_material_con_formato_y_parametros`.)

- [ ] **Step 2: Run test to verify it fails**

Run: la suite con `tests/api/test_traducir_errores.py` y `tests/api/test_rutas_nesting.py -k la_nombra`.
Expected: FAIL con `ModuleNotFoundError: No module named 'app.api.traducir_errores'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/api/traducir_errores.py`:

```python
"""Los errores de los cálculos, dichos para el usuario (A9, diseño §5.4).

Los cálculos conocen las piezas por su `id`; la ruta, que tiene las piezas
del grupo, las nombra como en el dibujo."""
from __future__ import annotations

from decimal import Decimal

from ..mensajes import ErrorParaElUsuario, error_para_guardar, lista_de_nombres
from ..services.nesting.engine import PiezasSinUbicar
from ..services.nesting.sparrow import (
    CalculoInterrumpido,
    ErrorGeometriaSparrow,
    PiezaSinContorno,
    PiezasQueNoEntran,
    ResultadoQueNoPasaElControl,
    SinLugarUtil,
    TiempoAgotado,
)

_PROBA_DE_NUEVO = "Probá de nuevo; si se repite, avisá."


def nombres_de_piezas(piezas) -> dict[str, str]:
    """De `str(Pieza.id)` al nombre del dibujo (`Pieza.id_origen`)."""
    return {str(p.id): p.id_origen for p in piezas}


def _mm(valor) -> str:
    return format(Decimal(str(valor)).normalize(), "f").replace(".", ",")


def medida(plancha) -> str:
    return f"{_mm(plancha.ancho_mm)} × {_mm(plancha.alto_mm)}"


def para_el_usuario(error: BaseException, nombres: dict[str, str], *, plancha=None, material: str | None = None) -> ErrorParaElUsuario:
    if isinstance(error, ErrorParaElUsuario):
        return error
    tecnico = str(error)
    if isinstance(error, PiezasQueNoEntran):
        chapa = f"la chapa de {medida(plancha)}" if plancha is not None else "la chapa"
        return ErrorParaElUsuario(
            f"Estas piezas no entran en {chapa} con el margen y el kerf actuales: "
            f"{lista_de_nombres(error.ids, nombres)}. Elegí una chapa más grande o seccionalas.",
            detalle=tecnico, piezas=error.ids,
        )
    if isinstance(error, ErrorGeometriaSparrow):
        return ErrorParaElUsuario(
            f"Estas piezas tienen el contorno o los huecos mal dibujados: "
            f"{lista_de_nombres(error.piezas_invalidas, nombres)}. Corregí el dibujo y volvé a cargarlo.",
            detalle=tecnico, piezas=error.piezas_invalidas, piezas_invalidas=error.piezas_invalidas,
        )
    if isinstance(error, PiezaSinContorno):
        return ErrorParaElUsuario(
            f"{lista_de_nombres([error.pieza_id], nombres)} no tiene contorno: volvé a cargar el dibujo.",
            detalle=tecnico, piezas=[error.pieza_id],
        )
    if isinstance(error, SinLugarUtil):
        de_material = f"de «{material}»" if material else "de este material"
        chapa = f"a la chapa de {medida(plancha)}" if plancha is not None else "a la chapa"
        return ErrorParaElUsuario(
            f"Con el margen, el kerf y la separación {de_material}, {chapa} no le queda lugar útil. "
            "Revisá esos valores o elegí otra chapa.",
            detalle=tecnico,
        )
    if isinstance(error, TiempoAgotado):
        return ErrorParaElUsuario(f"No llegó a un resultado en {_mm(error.segundos)} s. Probá con más tiempo.", detalle=tecnico)
    if isinstance(error, ResultadoQueNoPasaElControl):
        return ErrorParaElUsuario(
            "El cálculo dio un resultado que no pasó el control (piezas que se pisan, que salen de la chapa "
            f"o que faltan) y no se guardó. {_PROBA_DE_NUEVO}",
            detalle=error.motivo,
        )
    if isinstance(error, CalculoInterrumpido):
        return ErrorParaElUsuario(f"El cálculo se interrumpió por un error interno. {_PROBA_DE_NUEVO}", detalle=error.registro)
    if isinstance(error, PiezasSinUbicar):
        return ErrorParaElUsuario(
            f"No se pudieron ubicar estas piezas en la chapa: {lista_de_nombres(error.ids, nombres)}.",
            detalle=tecnico, piezas=error.ids,
        )
    return error_para_guardar(error)
```

En `backend/app/api/rutas_nesting.py`, import:

```python
from .traducir_errores import nombres_de_piezas, para_el_usuario
```

En `anidar`, el `try` queda:

```python
    grupo = _grupo_o_404(sesion, grupo_id)
    plancha = None
    try:
        plancha, params, piezas = _datos_para_anidar(sesion, grupo)
        if datos.motor == "sparrow":
            preparar_entrada(piezas, _geometrias_del_grupo(grupo), plancha, params, OpcionesSparrow())
    except ValueError as error:
        formato = sesion.get(Formato, grupo.formato_id) if grupo.formato_id else None
        raise para_el_usuario(
            error, nombres_de_piezas(grupo.piezas), plancha=plancha,
            material=formato.material.nombre if formato else None,
        ) from error
```

En `_correr_anidado`, antes del `try` (al lado de `geometrias = {}`):

```python
        nombres = nombres_de_piezas(ejecucion.grupo.piezas)
        plancha = None
        material = ((ejecucion.parametros or {}).get("formato") or {}).get("material_nombre")
```

y en el `except`, `falla = error_para_guardar(error)` pasa a:

```python
            falla = para_el_usuario(error, nombres, plancha=plancha, material=material)
```

En `_ComparacionPreparada`, sumar el campo:

```python
    #: De `str(Pieza.id)` al nombre del dibujo, para decir los errores (A9).
    nombres: dict[str, str]
```

En `_preparar_comparacion`, el bloque que valida antes de buscar queda:

```python
    opciones_sparrow = None
    nombres = nombres_de_piezas(piezas)
    if datos.motor == "sparrow":
        opciones_sparrow = OpcionesSparrow(**datos.model_dump(exclude={"motor", "formato_ids", "usar_anidado_en_huecos", "criterio"}))
        # Validar todos antes de iniciar búsquedas costosas.
        for opcion, formato, ids in zip(opciones, formatos, no_entran):
            if ids:
                continue
            try:
                preparar_entrada(piezas_dominio, geometrias, opcion.plancha, opcion.params, opciones_sparrow)
            except ValueError as error:
                raise para_el_usuario(error, nombres, plancha=opcion.plancha, material=formato.material.nombre) from error
```

y al armar `_ComparacionPreparada(...)`, sumar `nombres=nombres,`.

En `comparar_formatos_de_grupo`:

```python
    preparada = _preparar_comparacion(sesion, grupo_id, datos)
    try:
        return _correr_comparacion(preparada)
    except ValueError as error:
        raise para_el_usuario(error, preparada.nombres) from error
```

Borrar `_error_de_comparacion` (ya no la usa nadie: `grep -n _error_de_comparacion backend/` vacío).

- [ ] **Step 4: Run test to verify it passes**

Run: la suite entera.
Expected: PASS. La prueba de seccionado que lee `["detail"]["piezas_invalidas"]` sigue pasando.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/traducir_errores.py backend/app/api/rutas_nesting.py backend/tests/api/
git commit -m "feat(anidado): los errores del calculo nombran las piezas como en el dibujo (A9)"
```

### Task 7: En la comparación, cada chapa falla sola

**Files:**
- Modify: `backend/app/api/esquemas_nesting.py` (`OpcionFormatoLeer.error`)
- Modify: `backend/app/api/rutas_nesting.py` (`_correr_comparacion`)
- Create: `frontend/src/routes/TrabajoWorkspace/filasComparacion.ts`, `frontend/src/routes/TrabajoWorkspace/filasComparacion.test.ts`
- Modify: `frontend/src/api/piezasYgrupos.ts` (`OpcionFormato.error`), `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`
- Test: `backend/tests/api/test_rutas_comparaciones.py`

**Interfaces:**
- Consumes: `para_el_usuario`, `_ComparacionPreparada.nombres` (Task 6); `ErrorLeer` (Task 1).
- Produces: `OpcionFormatoLeer.error: ErrorLeer | None` (con error: sin planchas, consumo, aprovechamiento ni costo, y `recomendado = False`); en la pantalla, `OpcionFormato.error?: ErrorDelServidor | null` y `ordenarFilas(opciones: OpcionFormato[]): OpcionFormato[]`.

- [ ] **Step 1: Write the failing tests**

En `backend/tests/api/test_rutas_comparaciones.py`, reemplazar `test_una_falla_a_mitad_de_camino_queda_en_la_comparacion` por:

```python
def test_una_chapa_que_no_llega_queda_en_su_fila_y_las_demas_se_muestran(cliente, tmp_path, monkeypatch):
    from app.api import rutas_nesting
    from app.services.nesting.sparrow import TiempoAgotado

    original = rutas_nesting.anidar_sparrow

    def falla_la_chica(piezas, geometrias, plancha, params, opciones, **kw):
        if plancha.ancho_mm == 500:
            raise TiempoAgotado(opciones.tiempo_maximo_s)
        return original(piezas, geometrias, plancha, params, opciones, **kw)

    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", falla_la_chica)
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    grande, chica = _dos_formatos(cliente)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": [grande, chica], **_SPARROW_RAPIDO,
    }).json()

    final = _esperar_comparacion(cliente, arrancada["id"])

    por_formato = {o["formato_id"]: o for o in final["opciones"]}
    assert final["estado"] == "lista"
    assert por_formato[chica]["error"]["mensaje"] == "No llegó a un resultado en 20 s. Probá con más tiempo."
    assert por_formato[chica]["planchas_usadas"] is None
    assert por_formato[chica]["recomendado"] is False
    assert por_formato[grande]["error"] is None
    assert por_formato[grande]["planchas_usadas"] == 1
    assert por_formato[grande]["recomendado"] is True


def test_si_fallan_todas_las_chapas_cada_fila_dice_su_motivo(cliente, tmp_path, monkeypatch):
    from app.api import rutas_nesting
    from app.services.nesting.sparrow import CalculoInterrumpido

    def falla(*args, **kw):
        raise CalculoInterrumpido("falla de prueba")

    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", falla)
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()

    final = _esperar_comparacion(cliente, arrancada["id"])

    assert final["estado"] == "lista"
    assert [o["error"]["mensaje"] for o in final["opciones"]] == [
        "El cálculo se interrumpió por un error interno. Probá de nuevo; si se repite, avisá."
    ] * 2
    assert all(o["error"]["detalle"] == "falla de prueba" for o in final["opciones"])
    assert not any(o["recomendado"] for o in final["opciones"])


def test_una_falla_que_nadie_previo_deja_la_comparacion_en_error_con_su_traza(cliente, tmp_path, monkeypatch):
    from app.api import rutas_nesting
    from app.mensajes import MENSAJE_INESPERADO

    def bum(*args, **kw):
        raise RuntimeError("bum")

    monkeypatch.setattr(rutas_nesting, "formato_recomendado", bum)
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()

    final = _esperar_comparacion(cliente, arrancada["id"])

    assert final["estado"] == "error"
    assert final["error"]["mensaje"] == MENSAJE_INESPERADO
    assert "RuntimeError: bum" in final["error"]["detalle"]
```

`frontend/src/routes/TrabajoWorkspace/filasComparacion.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { OpcionFormato } from "../../api/piezasYgrupos";
import { ordenarFilas } from "./filasComparacion";

function opcion(formato_id: number, extra: Partial<OpcionFormato> = {}): OpcionFormato {
  return {
    area_total_m2: "1", motor: "sparrow", advertencias: [], formato_id, formato_descripcion: "", material_nombre: "",
    planchas_usadas: 1, aprovechamiento_pct: "50", costo_total: "10", moneda: "ARS", recomendado: false,
    precio_simulado: false, piezas_a_seccionar: [], error: null, ...extra,
  };
}

describe("ordenarFilas", () => {
  it("deja al final las chapas sin números, en el orden en que vinieron", () => {
    const filas = [
      opcion(1, { error: { mensaje: "No llegó", detalle: null, piezas: [], chapas: [] } }),
      opcion(2),
      opcion(3, { piezas_a_seccionar: [{ id: 9, id_origen: "aro", ancho_mm: "4610", alto_mm: "4610" }] }),
      opcion(4),
    ];

    expect(ordenarFilas(filas).map((f) => f.formato_id)).toEqual([2, 4, 1, 3]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: la suite con `tests/api/test_rutas_comparaciones.py`; en `frontend/`, `npm test`.
Expected: FAIL (la comparación termina en `error`; no existe `filasComparacion`).

- [ ] **Step 3: Write minimal implementation**

En `OpcionFormatoLeer` (`esquemas_nesting.py`):

```python
    #: El formato no se pudo anidar (A9): no llegó a tiempo o falló el
    #: cálculo. Como con `piezas_a_seccionar`, sin planchas ni costo.
    error: ErrorLeer | None = None
```

En `rutas_nesting.py`, `_correr_comparacion` entero:

```python
def _correr_comparacion(
    preparada: _ComparacionPreparada,
    al_avanzar: Callable[[dict], None] | None = None,
    cancelada: Callable[[], bool] = lambda: False,
) -> list[OpcionFormatoLeer]:
    """Anida cada formato y arma la tabla. No usa la base: corre igual en
    el pedido y en la cola (A7). Un formato que falla queda en su fila con
    el motivo, y los demás se muestran (A9)."""
    a_anidar = [
        (indice, opcion, comunes)
        for indice, (opcion, comunes, a_seccionar) in enumerate(
            zip(preparada.opciones, preparada.comunes, preparada.a_seccionar)
        )
        if not a_seccionar
    ]
    resultados: dict[int, object] = {}
    fallas: dict[int, ErrorLeer] = {}
    if preparada.motor == "sparrow":
        from ..services.nesting.comparador import ResultadoComparacionFormato
        inicio = time.monotonic()
        maximo = len(a_anidar) * preparada.opciones_sparrow.tiempo_maximo_s
        for numero, (indice, opcion, comunes) in enumerate(a_anidar, start=1):
            if cancelada():
                raise ValueError("Comparación cancelada.")

            def avanzar(avance: dict, numero: int = numero, descripcion: str = comunes["formato_descripcion"]) -> None:
                if al_avanzar is not None:
                    al_avanzar({
                        **avance,
                        "segundos": round(time.monotonic() - inicio, 1), "maximo": maximo,
                        "formato": numero, "formatos": len(a_anidar), "descripcion": descripcion,
                    })

            try:
                resultado = anidar_sparrow(
                    preparada.piezas, preparada.geometrias, opcion.plancha, opcion.params, preparada.opciones_sparrow,
                    cancelada=cancelada, al_avanzar=avanzar,
                )
            except Exception as error:  # noqa: BLE001 - la falla de un formato queda en su fila
                if cancelada():
                    raise ValueError("Comparación cancelada.") from error
                falla = para_el_usuario(error, preparada.nombres, plancha=opcion.plancha, material=comunes["material_nombre"])
                registro().warning(
                    "La comparación no pudo anidar %s: %s\n%s", comunes["formato_descripcion"], falla.mensaje, falla.detalle or ""
                )
                fallas[indice] = ErrorLeer(**falla.como_dict())
                continue
            resultados[indice] = ResultadoComparacionFormato(
                opcion, resultado, calcular_aprovechamiento(resultado, opcion.plancha, preparada.geometrias),
                resultado.planchas_usadas * opcion.precio_por_plancha,
            )
    else:
        en_orden = comparar_formatos(
            preparada.piezas, [opcion for _, opcion, _ in a_anidar], tope_planchas_advertencia=_TOPE_PLANCHAS_ADVERTENCIA
        )
        resultados = {indice: resultado for (indice, _, _), resultado in zip(a_anidar, en_orden)}
    recomendado = formato_recomendado(list(resultados.values()), preparada.criterio) if resultados else None

    filas = []
    for indice, (comunes, a_seccionar) in enumerate(zip(preparada.comunes, preparada.a_seccionar)):
        if a_seccionar or indice in fallas:
            filas.append(OpcionFormatoLeer(
                **comunes,
                area_total_m2=None,
                planchas_usadas=None,
                aprovechamiento_pct=None,
                costo_total=None,
                recomendado=False,
                piezas_a_seccionar=a_seccionar,
                error=fallas.get(indice),
            ))
            continue
        resultado = resultados[indice]
        filas.append(OpcionFormatoLeer(
            **comunes,
            advertencias=resultado.resultado_anidado.advertencias,
            area_total_m2=resultado.reporte_aprovechamiento.area_total_planchas_mm2 / Decimal(1000000),
            planchas_usadas=resultado.resultado_anidado.planchas_usadas,
            aprovechamiento_pct=resultado.reporte_aprovechamiento.porcentaje_aprovechamiento,
            costo_total=resultado.costo_total,
            recomendado=resultado is recomendado,
        ))
    return filas
```

con `ErrorLeer` importado de `.esquemas_mensajes` en `rutas_nesting.py`.

En `api/piezasYgrupos.ts`, en `OpcionFormato`:

```ts
  /** El formato no se pudo anidar (A9): no llegó a tiempo o falló el cálculo. Sin planchas ni costo. */
  error?: ErrorDelServidor | null;
```

`frontend/src/routes/TrabajoWorkspace/filasComparacion.ts`:

```ts
import type { OpcionFormato } from "../../api/piezasYgrupos";

/** Una fila sin números para comparar: no se pudo anidar o hay que seccionar. */
export function sinNumeros(opcion: OpcionFormato): boolean {
  return opcion.error != null || opcion.piezas_a_seccionar.length > 0;
}

/** Las chapas con resultado primero; las demás al final, en el orden en que vinieron. */
export function ordenarFilas(opciones: OpcionFormato[]): OpcionFormato[] {
  return [...opciones].sort((a, b) => Number(sinNumeros(a)) - Number(sinNumeros(b)));
}
```

En `GruposTab.tsx`, la tabla de la comparación usa `ordenarFilas(resultado)` en lugar del `.sort(...)` actual, y suma una rama antes de la de seccionar:

```tsx
                    {ordenarFilas(resultado).map((opcion) => opcion.error ? (
                      <tr key={opcion.formato_id} className="border-b border-line text-ink/70">
                        <td>{opcion.material_nombre}</td>
                        <td>{opcion.motor === "sparrow" ? "Sparrow" : "Rectangular"}</td>
                        <td>{opcion.formato_descripcion}</td>
                        <td colSpan={5} className="text-conflict">{opcion.error.mensaje}</td>
                      </tr>
                    ) : opcion.piezas_a_seccionar.length > 0 ? (
```

(el resto de las ramas queda como está).

- [ ] **Step 4: Run tests to verify they pass**

Run: la suite entera; `npm test` y `npx tsc -b`.
Expected: PASS. Las pruebas que ya existen de cancelar una comparación siguen en verde: cancelar a mitad de una chapa cancela la comparación entera.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/ backend/tests/api/test_rutas_comparaciones.py frontend/src/
git commit -m "feat(comparacion): una chapa que falla queda en su fila y las demas se muestran (A9)"
```

### Task 8: Los avisos de un resultado, sin lo técnico

**Files:**
- Modify: `backend/app/services/nesting/sparrow.py` (`convertir_y_validar`, `anidar_sparrow`)
- Modify: `backend/app/services/nesting/sparrow_worker.py` (`resolver`)
- Modify: `backend/app/api/traducir_errores.py` (`con_nombres`)
- Modify: `backend/app/api/rutas_nesting.py` (`_correr_anidado`, `_correr_comparacion`)
- Modify: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx` (texto de ayuda)
- Test: `backend/tests/services/nesting/test_sparrow.py`, `backend/tests/api/test_traducir_errores.py`

**Interfaces:**
- Consumes: `Aviso`, `lista_de_nombres` (Task 1); `registro()` (Task 2).
- Produces: `con_nombres(aviso: Aviso, nombres: dict[str, str]) -> Aviso` (un aviso que nombra piezas termina en «:» y se le agregan los nombres); `ResultadoAnidado.advertencias` puede tener `str` o `Aviso`.

- [ ] **Step 1: Write the failing tests**

En `backend/tests/services/nesting/test_sparrow.py`:

```python
from app.mensajes import Aviso


def test_el_aviso_de_huecos_unidos_nombra_las_piezas_y_ya_no_hay_aviso_fijo():
    p, g, plancha, params = datos()
    g['1'].agujeros_local_mm.extend([[(2, 2), (6, 2), (6, 6), (2, 6)], [(4, 4), (8, 4), (8, 8), (4, 8)]])
    entrada = preparar_entrada(p, g, plancha, params, OpcionesSparrow())
    colocadas = [{'id': '1#0', 'sheet': 0, 'rotation': 0, 'tx': 0, 'ty': 0}, {'id': '1#1', 'sheet': 0, 'rotation': 0, 'tx': 40, 'ty': 0}]

    resultado = convertir_y_validar(entrada, colocadas)

    assert resultado.advertencias == [Aviso(
        "Estas piezas tenían huecos que se pisaban y se calcularon con los huecos unidos (el dibujo guardado no cambia):",
        (1,),
    )]


def test_sin_avisos_si_no_hubo_nada_que_avisar():
    resultado = anidar_sparrow(*datos(3), OpcionesSparrow(segundos_por_busqueda=1, tiempo_maximo_s=20, simplificacion_mm=0))

    assert not any("Sparrow" in str(a) for a in resultado.advertencias)
```

`test_si_el_worker_termina_con_error_vale_lo_que_dejo_escrito` pasa a:

```python
def test_si_el_worker_termina_con_error_vale_lo_que_dejo_escrito(monkeypatch, tmp_path, caplog):
    """Antes se descartaba el anidado de la primera pasada. El aviso no
    trae lo técnico: la causa queda en el registro del servidor."""
    con_worker(monkeypatch, worker_falso(tmp_path, 1, registro='Traceback...\nValueError: causa de prueba'))

    with caplog.at_level("WARNING", logger="carteleria"):
        resultado = anidar_sparrow(*datos(3), OpcionesSparrow(tiempo_maximo_s=20))

    assert resultado.planchas_usadas == 2
    assert "El cálculo se cortó antes de terminar: este es el mejor resultado completo que había encontrado." in resultado.advertencias
    assert "ValueError: causa de prueba" in caplog.text
```

En `backend/tests/api/test_traducir_errores.py`:

```python
from app.api.traducir_errores import con_nombres
from app.mensajes import Aviso


def test_un_aviso_que_nombra_piezas_suma_los_nombres():
    aviso = Aviso("Estas piezas tenían huecos que se pisaban y se calcularon con los huecos unidos (el dibujo guardado no cambia):", (3, 4))

    assert con_nombres(aviso, NOMBRES).mensaje.endswith("no cambia): «aro», «B-3».")


def test_un_aviso_sin_piezas_queda_igual():
    assert con_nombres(Aviso("Se usó todo el tiempo de búsqueda."), NOMBRES) == Aviso("Se usó todo el tiempo de búsqueda.")
```

En las pruebas del worker que comprueban los textos de sus avisos (`grep -n "de Sparrow falló\|vaciar chapas (" backend/tests/services/nesting/test_sparrow.py`), las que comprueban el texto que escribe el propio `resolver` pasan a los textos nuevos del Step 3. `test_los_avisos_del_worker_llegan_al_resultado` no cambia: el aviso lo escribe su worker falso.

- [ ] **Step 2: Run tests to verify they fail**

Run: la suite con `tests/services/nesting/test_sparrow.py` y `tests/api/test_traducir_errores.py`.
Expected: FAIL (sale el aviso de «Sparrow experimental»; no existe `con_nombres`).

- [ ] **Step 3: Write minimal implementation**

En `sparrow.py`, import `from ...mensajes import Aviso` y `from ...registro import registro`. En `convertir_y_validar`, el final queda:

```python
    avisos = []
    if entrada.get('normalizadas'):
        avisos.append(Aviso(
            "Estas piezas tenían huecos que se pisaban y se calcularon con los huecos unidos (el dibujo guardado no cambia):",
            tuple(int(i) for i in entrada['normalizadas']),
        ))
    return ResultadoAnidado(positions, len(sheets), avisos)
```

En `anidar_sparrow`:

| Hoy | Queda |
|---|---|
| `'Se alcanzó el límite de búsqueda: se conserva el mejor anidado completo y validado, sin omitir piezas.'` | `'Se usó todo el tiempo de búsqueda: este es el mejor resultado que encontró. Con más tiempo puede salir mejor.'` |
| `f'El cálculo terminó con un error ({causa}): se conserva el mejor anidado completo y validado que había encontrado.'` | `'El cálculo se cortó antes de terminar: este es el mejor resultado completo que había encontrado.'` (y se borra la línea que arma `causa`) |

y el `finally` del final deja en el registro lo que escribió el worker:

```python
            finally:
                if proc.poll() is None:proc.kill()
                proc.wait()
                # Lo técnico de los avisos (y de cualquier falla) no va a la
                # pantalla: queda acá, en el registro del servidor (A9).
                log.seek(0);escrito=log.read().strip()
                if escrito:registro().warning('Lo que escribió el cálculo de Sparrow:\n%s',escrito[-4000:])
```

En `sparrow_worker.py`, en `resolver`:

| Hoy | Queda |
|---|---|
| `avisar(f'La pasada {intento+1} de Sparrow falló ({_motivo(error)}): queda el mejor anidado de las anteriores.')` | `print(f'pasada {intento+1}:',repr(error),file=sys.stderr)` y `avisar('Una de las vueltas de búsqueda falló: quedó el mejor resultado de las anteriores.')` |
| `avisar(f'No se pudo terminar de vaciar chapas ({_motivo(error)}): el resultado es el mejor anidado completo que se encontró.')` | `avisar('No se pudo terminar de vaciar chapas: este es el mejor resultado completo que encontró.')` (el `print('vaciar_chapas:', …)` de arriba queda) |

Si `_motivo` queda sin uso, borrarlo.

En `traducir_errores.py`:

```python
from ..mensajes import Aviso, ErrorParaElUsuario, error_para_guardar, lista_de_nombres


def con_nombres(aviso: Aviso, nombres: dict[str, str]) -> Aviso:
    """Un aviso de un cálculo que nombra piezas termina en «:»; acá se le
    agregan los nombres del dibujo."""
    if not aviso.piezas or not aviso.mensaje.endswith(":"):
        return aviso
    return Aviso(f"{aviso.mensaje} {lista_de_nombres(aviso.piezas, nombres)}.", aviso.piezas, aviso.chapas)
```

En `rutas_nesting.py`, con `from ..mensajes import aviso_desde` y `con_nombres` importado de `.traducir_errores`:
- `_correr_anidado`: `ejecucion.mensajes = avisos_leer(resultado.advertencias)` pasa a `ejecucion.mensajes = avisos_leer(con_nombres(aviso_desde(a), nombres) for a in resultado.advertencias)`.
- `_correr_comparacion`: `advertencias=resultado.resultado_anidado.advertencias` pasa a `advertencias=[con_nombres(aviso_desde(a), preparada.nombres) for a in resultado.resultado_anidado.advertencias]`.

En `AnidadoTab.tsx`, junto a la explicación del motor, una línea de ayuda fija (lo que decía el aviso que se sacó):

```tsx
<p className="text-xs text-ink/70">El cálculo no pone piezas adentro de los huecos de otras.</p>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: la suite entera; `npx tsc -b`.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nesting/ backend/app/api/ backend/tests/ frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx
git commit -m "feat(anidado): los avisos de un resultado sin lo tecnico, que va al registro (A9)"
```

### Task 9: Ajuste dice con qué pieza choca y en qué chapa

**Files:**
- Modify: `backend/app/services/nesting/validacion_manual.py` (`ResultadoValidacion.choca_con`; textos de margen y veta)
- Modify: `backend/app/api/esquemas_nesting.py` (`ColocacionAjusteLeer.motivo`)
- Modify: `backend/app/api/rutas_ajuste.py` (`ajustar_colocacion`)
- Modify: `frontend/src/api/nesting.ts` (`ColocacionAjustada.motivo`), `frontend/src/routes/TrabajoWorkspace/AjusteTab.tsx` (el tipo del mapa)
- Test: `backend/tests/api/test_rutas_ajuste.py`, `backend/tests/services/nesting/test_validacion_manual.py`

**Interfaces:**
- Consumes: `AvisoLeer` (Task 1).
- Produces: `ResultadoValidacion.choca_con: str | None` (el `pieza_id` «id#instancia» de la otra); `ColocacionAjusteLeer.motivo: AvisoLeer | None`; en la pantalla, `ColocacionAjustada.motivo: Aviso | null`.

- [ ] **Step 1: Write the failing test**

En `backend/tests/api/test_rutas_ajuste.py`, en `test_mover_una_pieza_encima_de_otra_es_invalido_pero_se_aplica_igual`, `assert "superpone" in cuerpo["motivo"]` pasa a:

```python
    piezas = {p["id"]: p["id_origen"] for p in cliente.get(f"/trabajos/{_trabajo['id']}/piezas").json()}
    motivo = cuerpo["motivo"]
    assert motivo["mensaje"] == (
        f"«{piezas[a['pieza_id']]}» se pisa con «{piezas[b['pieza_id']]}» (o queda más cerca que la separación y el kerf)."
    )
    assert motivo["piezas"] == [a["pieza_id"], b["pieza_id"]]
    assert motivo["chapas"] == [{"ejecucion_id": ejecucion_id, "plancha": a["plancha_indice"]}]
```

y en las de margen y veta, `respuesta.json()["motivo"]` pasa a `respuesta.json()["motivo"]["mensaje"]`.

En `backend/tests/services/nesting/test_validacion_manual.py`, en `test_se_superpone_directamente_con_otra_pieza`, sumar:

```python
    assert resultado.choca_con == "p2"
```

(con el `pieza_id` que usa esa prueba para la otra pieza).

- [ ] **Step 2: Run test to verify it fails**

Run: la suite con `tests/api/test_rutas_ajuste.py` y `tests/services/nesting/test_validacion_manual.py`.
Expected: FAIL (`motivo` es texto; no existe `choca_con`).

- [ ] **Step 3: Write minimal implementation**

En `validacion_manual.py`:

```python
@dataclass(frozen=True)
class ResultadoValidacion:
    valida: bool
    motivo: str | None = None
    #: El `pieza_id` («id#instancia») de la pieza con la que choca, si el
    #: motivo es ese (A9: la ruta la nombra como en el dibujo).
    choca_con: str | None = None
```

(si la clase ya tiene decorador, conservar el que tiene y solo sumar el campo).

| Hoy | Queda |
|---|---|
| `"Este material tiene veta (PAR-04): solo admite 0°/180°, no ángulo libre."` | `"Este material tiene veta: la pieza solo se puede girar media vuelta (0° o 180°)."` |
| `"La pieza invade el margen de borde de la plancha."` | `"La pieza pisa el margen de borde de la chapa."` |
| `ResultadoValidacion(False, f"Se superpone con '{otra_posicion.pieza_id}' (o invade su separación/kerf mínimos).")` | `ResultadoValidacion(False, f"Se superpone con '{otra_posicion.pieza_id}' (o invade su separación/kerf mínimos).", choca_con=otra_posicion.pieza_id)` |

En `esquemas_nesting.py`, `ColocacionAjusteLeer.motivo: str | None` pasa a `motivo: AvisoLeer | None`.

En `rutas_ajuste.py`, con `from ..modelos.trabajo import Pieza` (si no está) y `from .esquemas_mensajes import AvisoLeer`:

```python
def _motivo_para_el_usuario(sesion: Session, resultado, colocacion: Colocacion) -> AvisoLeer | None:
    """El motivo de un ajuste que no vale, con las piezas y la chapa (A9)."""
    if resultado.valida:
        return None
    chapas = [{"ejecucion_id": colocacion.ejecucion_id, "plancha": colocacion.plancha_indice}]
    if resultado.choca_con is None:
        return AvisoLeer(mensaje=resultado.motivo, piezas=[colocacion.pieza_id], chapas=chapas)
    otra_id = int(resultado.choca_con.split("#")[0])
    otra = sesion.get(Pieza, otra_id)
    return AvisoLeer(
        mensaje=(
            f"«{colocacion.pieza.id_origen}» se pisa con «{otra.id_origen if otra else 'otra pieza'}» "
            "(o queda más cerca que la separación y el kerf)."
        ),
        piezas=[colocacion.pieza_id, otra_id],
        chapas=chapas,
    )
```

y en `ajustar_colocacion`, `motivo=resultado_validacion.motivo` pasa a `motivo=_motivo_para_el_usuario(sesion, resultado_validacion, colocacion)`.

En la pantalla: `ColocacionAjustada.motivo: Aviso | null` (`api/nesting.ts`, con el import de `./mensajes`), y en `AjusteTab.tsx` el tipo del mapa pasa a `Map<number, { valida: boolean; motivo: Aviso | null }>`.

- [ ] **Step 4: Run test to verify it passes**

Run: la suite entera; `npx tsc -b`.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/ backend/tests/ frontend/src/api/nesting.ts frontend/src/routes/TrabajoWorkspace/AjusteTab.tsx
git commit -m "feat(ajuste): el motivo de un ajuste que no vale nombra las piezas y la chapa (A9)"
```

**Pausa del tramo 2:** suite del servidor, `npm test`, `npx tsc -b`, y el ok de Enzo.

---

## Tramo 3 — La pantalla

### Task 10: El error entero llega a la pantalla, y el servidor apagado se dice

**Files:**
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts`

**Interfaces:**
- Consumes: `ChapaNombrada` (Task 4).
- Produces: `SIN_CONEXION: string`; `ApiError` con `.detalle: string | null`, `.piezas: number[]`, `.chapas: ChapaNombrada[]` (constructor `(status, message, piezasInvalidas = [], extra = {})`, compatible con el de hoy); `errorDesdeCuerpo(status: number, cuerpo: unknown): ApiError`.

- [ ] **Step 1: Write the failing test**

Sumar a `frontend/src/api/client.test.ts`:

```ts
import { errorDesdeCuerpo, SIN_CONEXION } from "./client";

describe("errorDesdeCuerpo", () => {
  it("toma el error entero: mensaje, detalle, piezas y chapas", () => {
    const error = errorDesdeCuerpo(400, {
      detail: { mensaje: "Estas piezas no entran…", detalle: "técnico", piezas: [3], chapas: [{ ejecucion_id: 7, plancha: 0 }] },
    });

    expect(error).toMatchObject({
      status: 400, message: "Estas piezas no entran…", detalle: "técnico", piezas: [3], chapas: [{ ejecucion_id: 7, plancha: 0 }],
    });
  });

  it("un error de texto (antes de A9) queda sin detalle ni piezas", () => {
    expect(errorDesdeCuerpo(404, { detail: "No existe el trabajo 9." })).toMatchObject({
      message: "No existe el trabajo 9.", detalle: null, piezas: [], chapas: [],
    });
  });

  it("sin cuerpo legible dice el código en castellano", () => {
    expect(errorDesdeCuerpo(502, null).message).toBe("El servidor respondió con un error (502).");
  });
});

describe("sin servidor", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("un pedido que no llega dice que el servidor no responde", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(apiGet("/trabajos")).rejects.toMatchObject({ status: 0, message: SIN_CONEXION });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test` en `frontend/`.
Expected: FAIL (`errorDesdeCuerpo` no existe; el `fetch` rechazado sale como `TypeError`).

- [ ] **Step 3: Write minimal implementation**

`frontend/src/api/client.ts`, desde el principio hasta `manejarRespuesta` inclusive:

```ts
import type { ChapaNombrada } from "./mensajes";

const BASE_URL = "http://localhost:8000";

/** Lo que se muestra cuando el pedido no llega al servidor (A9). */
export const SIN_CONEXION = "No se pudo conectar con el servidor: revisá que esté prendido.";

export class ApiError extends Error {
  status: number;
  piezasInvalidas: number[];
  /** Lo técnico, para «Ver detalle técnico» (A9). */
  detalle: string | null;
  /** Las piezas y chapas que nombra el mensaje, para sus miniaturas. */
  piezas: number[];
  chapas: ChapaNombrada[];
  constructor(
    status: number,
    message: string,
    piezasInvalidas: number[] = [],
    extra: { detalle?: string | null; piezas?: number[]; chapas?: ChapaNombrada[] } = {},
  ) {
    super(message);
    this.status = status;
    this.piezasInvalidas = piezasInvalidas;
    this.detalle = extra.detalle ?? null;
    this.piezas = extra.piezas ?? [];
    this.chapas = extra.chapas ?? [];
    this.name = "ApiError";
  }
}

function numeros(valor: unknown): number[] {
  return Array.isArray(valor) ? valor.filter((x): x is number => typeof x === "number") : [];
}

function chapas(valor: unknown): ChapaNombrada[] {
  return Array.isArray(valor)
    ? valor.filter((c): c is ChapaNombrada => typeof c?.ejecucion_id === "number" && typeof c?.plancha === "number")
    : [];
}

/** El error de una respuesta que no salió bien, desde su cuerpo: `detail`
 * como texto (antes de A9) o como `{mensaje, detalle, piezas, chapas, piezas_invalidas}`. */
export function errorDesdeCuerpo(status: number, cuerpo: unknown): ApiError {
  const detalle = (cuerpo as { detail?: unknown } | null)?.detail;
  if (typeof detalle === "string") return new ApiError(status, detalle);
  const d = (detalle ?? {}) as Record<string, unknown>;
  const mensaje = typeof d.mensaje === "string" ? d.mensaje : `El servidor respondió con un error (${status}).`;
  return new ApiError(status, mensaje, numeros(d.piezas_invalidas), {
    detalle: typeof d.detalle === "string" ? d.detalle : null,
    piezas: numeros(d.piezas),
    chapas: chapas(d.chapas),
  });
}

/** `fetch`, pero un pedido que no llega es un `ApiError` en castellano. */
async function pedir(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError(0, SIN_CONEXION);
  }
}

async function manejarRespuesta<T>(respuesta: Response): Promise<T> {
  if (!respuesta.ok) {
    throw errorDesdeCuerpo(respuesta.status, await respuesta.json().catch(() => null));
  }
  if (respuesta.status === 204) {
    return undefined as T;
  }
  return respuesta.json() as Promise<T>;
}
```

y en `apiGet`, `apiGetArchivo`, `apiPost`, `apiPatch`, `apiDelete` y `apiPostForm`, cada `fetch(\`${BASE_URL}${path}\`, …)` pasa a `pedir(path, …)`. Sumar `afterEach` y `vi` al import de `vitest` en la prueba si faltan.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test` y `npx tsc -b`.
Expected: PASS, también las pruebas viejas del cliente y de `comparacionEnCurso`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat(frontend): el error del servidor llega entero, y sin servidor se dice en castellano (A9)"
```

### Task 11: Un componente para mostrar mensajes

**Files:**
- Create: `frontend/src/components/Mensaje/mensaje.ts`, `frontend/src/components/Mensaje/mensaje.test.ts`
- Create: `frontend/src/components/Mensaje/Mensaje.tsx`, `frontend/src/components/Mensaje/ChapaMiniatura.tsx`
- Modify: `frontend/src/api/nesting.ts` (`urlPlanoMiniatura`)

**Interfaces:**
- Consumes: `ApiError` (Task 10); `Aviso`, `ErrorDelServidor`, `ChapaNombrada` (Task 4); `Banner`, `PiezaMiniPreview`, `usePiezas`, `urlPlano` (existentes).
- Produces: `type QueMostrar = string | Aviso | ErrorDelServidor | ApiError`; `interface Contenido { mensaje; detalle; piezas; chapas }`; `contenidoDe(valor: QueMostrar): Contenido`; `piezasNombradas<P extends { id: number }>(ids: number[], piezas: P[]): P[]`; `textoParaCopiar(contenido: Contenido): string`; `falla(e: unknown, siNoEsDelServidor: string): string | ApiError`; `<Mensaje variante="error" | "aviso" que={QueMostrar} trabajoId?={number} />`; `<ChapaMiniatura chapa={ChapaNombrada} />`; `urlPlanoMiniatura(ejecucionId: number, plancha: number): string`.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/Mensaje/mensaje.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { contenidoDe, falla, piezasNombradas, textoParaCopiar } from "./mensaje";

describe("contenidoDe", () => {
  it("un texto de la pantalla no trae detalle ni piezas", () => {
    expect(contenidoDe("No se pudo comparar.")).toEqual({ mensaje: "No se pudo comparar.", detalle: null, piezas: [], chapas: [] });
  });

  it("un error del servidor trae todo", () => {
    const error = new ApiError(400, "m", [], { detalle: "d", piezas: [3], chapas: [{ ejecucion_id: 7, plancha: 1 }] });

    expect(contenidoDe(error)).toEqual({ mensaje: "m", detalle: "d", piezas: [3], chapas: [{ ejecucion_id: 7, plancha: 1 }] });
  });

  it("un aviso no tiene detalle", () => {
    expect(contenidoDe({ mensaje: "a", piezas: [1], chapas: [] }).detalle).toBeNull();
  });
});

describe("piezasNombradas", () => {
  const piezas = [{ id: 1, id_origen: "aro" }, { id: 2, id_origen: "B-3" }];

  it("en el orden del mensaje, sin repetir", () => {
    expect(piezasNombradas([2, 1, 2], piezas).map((p) => p.id_origen)).toEqual(["B-3", "aro"]);
  });

  it("una pieza que ya no está en el trabajo no aparece y no rompe nada", () => {
    expect(piezasNombradas([9, 1], piezas).map((p) => p.id)).toEqual([1]);
  });
});

describe("textoParaCopiar", () => {
  it("el mensaje y el detalle, separados", () => {
    expect(textoParaCopiar({ mensaje: "m", detalle: "d", piezas: [], chapas: [] })).toBe("m\n\nd");
  });

  it("sin detalle, solo el mensaje", () => {
    expect(textoParaCopiar({ mensaje: "m", detalle: null, piezas: [], chapas: [] })).toBe("m");
  });
});

describe("falla", () => {
  it("un error del servidor queda entero", () => {
    const error = new ApiError(400, "m");
    expect(falla(error, "otro")).toBe(error);
  });

  it("cualquier otra cosa da el texto de la pantalla", () => {
    expect(falla(new TypeError("x"), "No se pudo cancelar.")).toBe("No se pudo cancelar.");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`.
Expected: FAIL (no existe `./mensaje`).

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/Mensaje/mensaje.ts`:

```ts
import { ApiError } from "../../api/client";
import type { Aviso, ChapaNombrada, ErrorDelServidor } from "../../api/mensajes";

/** Lo que puede mostrar `Mensaje`: un texto de la propia pantalla, un aviso
 * o un error del servidor (A9). */
export type QueMostrar = string | Aviso | ErrorDelServidor | ApiError;

export interface Contenido {
  mensaje: string;
  detalle: string | null;
  piezas: number[];
  chapas: ChapaNombrada[];
}

export function contenidoDe(valor: QueMostrar): Contenido {
  if (typeof valor === "string") return { mensaje: valor, detalle: null, piezas: [], chapas: [] };
  if (valor instanceof ApiError) {
    return { mensaje: valor.message, detalle: valor.detalle, piezas: valor.piezas, chapas: valor.chapas };
  }
  return {
    mensaje: valor.mensaje,
    detalle: "detalle" in valor ? valor.detalle ?? null : null,
    piezas: valor.piezas ?? [],
    chapas: valor.chapas ?? [],
  };
}

/** Las piezas que nombra un mensaje, en su orden y sin repetir. Una que ya
 * no está en el trabajo (se volvió a cargar el dibujo) no aparece. */
export function piezasNombradas<P extends { id: number }>(ids: number[], piezas: P[]): P[] {
  const porId = new Map(piezas.map((pieza) => [pieza.id, pieza]));
  return [...new Set(ids)].map((id) => porId.get(id)).filter((pieza): pieza is P => pieza !== undefined);
}

export function textoParaCopiar(contenido: Contenido): string {
  return contenido.detalle ? `${contenido.mensaje}\n\n${contenido.detalle}` : contenido.mensaje;
}

/** Para los `catch`: el error del servidor entero (con su detalle y lo que
 * nombra), o el texto de la pantalla si no vino del servidor. */
export function falla(e: unknown, siNoEsDelServidor: string): string | ApiError {
  return e instanceof ApiError ? e : siNoEsDelServidor;
}
```

En `frontend/src/api/nesting.ts`, debajo de `urlPlano`:

```ts
/** El plano de una chapa sin nombres de piezas, para su miniatura (A9). */
export function urlPlanoMiniatura(ejecucionId: number, plancha: number): string {
  return `${urlPlano(ejecucionId, plancha)}&etiquetas=false`;
}
```

`frontend/src/components/Mensaje/ChapaMiniatura.tsx`:

```tsx
import { urlPlanoMiniatura } from "../../api/nesting";
import type { ChapaNombrada } from "../../api/mensajes";

/** Una chapa de un resultado, chica, con sus piezas puestas (A9). */
export default function ChapaMiniatura({ chapa }: { chapa: ChapaNombrada }) {
  return (
    <figure className="text-center">
      <img
        src={urlPlanoMiniatura(chapa.ejecucion_id, chapa.plancha)}
        alt={`Chapa ${chapa.plancha + 1}`}
        className="h-24 border border-line rounded bg-paper"
      />
      <figcaption className="text-xs">Chapa {chapa.plancha + 1}</figcaption>
    </figure>
  );
}
```

`frontend/src/components/Mensaje/Mensaje.tsx`:

```tsx
import { useState } from "react";
import Banner from "../Banner";
import PiezaMiniPreview from "../PiezaMiniPreview";
import ChapaMiniatura from "./ChapaMiniatura";
import { usePiezas } from "../../hooks/usePiezas";
import { contenidoDe, piezasNombradas, textoParaCopiar, type QueMostrar } from "./mensaje";

interface MensajeProps {
  variante: "error" | "aviso";
  que: QueMostrar;
  /** Para dibujar las piezas que nombra. Sin trabajo, solo el texto. */
  trabajoId?: number;
}

/** Un error o aviso: el mensaje, las miniaturas de lo que nombra y, si hay,
 * «Ver detalle técnico» con Copiar (A9). `Banner` es el marco. */
export default function Mensaje({ variante, que, trabajoId }: MensajeProps) {
  const contenido = contenidoDe(que);
  return (
    <Banner variante={variante}>
      <p>{contenido.mensaje}</p>
      {trabajoId !== undefined && contenido.piezas.length > 0 && (
        <PiezasDelMensaje trabajoId={trabajoId} ids={contenido.piezas} />
      )}
      {contenido.chapas.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {contenido.chapas.map((chapa) => (
            <ChapaMiniatura key={`${chapa.ejecucion_id}-${chapa.plancha}`} chapa={chapa} />
          ))}
        </div>
      )}
      {contenido.detalle && <DetalleTecnico detalle={contenido.detalle} paraCopiar={textoParaCopiar(contenido)} />}
    </Banner>
  );
}

function PiezasDelMensaje({ trabajoId, ids }: { trabajoId: number; ids: number[] }) {
  const { data: piezas } = usePiezas(trabajoId);
  const nombradas = piezasNombradas(ids, piezas ?? []);
  if (nombradas.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-3 mt-2 text-ink">
      {nombradas.map((pieza) => (
        <li key={pieza.id} className="flex items-center gap-1">
          <PiezaMiniPreview contornoMm={pieza.contorno_mm} anchoMm={pieza.ancho_mm} altoMm={pieza.alto_mm} />
          <span className="text-xs">{pieza.id_origen}</span>
        </li>
      ))}
    </ul>
  );
}

function DetalleTecnico({ detalle, paraCopiar }: { detalle: string; paraCopiar: string }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <details className="mt-2 text-ink/80">
      <summary className="cursor-pointer text-xs">Ver detalle técnico</summary>
      <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap text-xs bg-paper border border-line rounded p-2">
        {detalle}
      </pre>
      <button
        type="button"
        className="mt-1 text-xs underline"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(paraCopiar);
            setCopiado(true);
          } catch {
            setCopiado(false);
          }
        }}
      >
        {copiado ? "Copiado" : "Copiar"}
      </button>
    </details>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test` y `npx tsc -b`.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Mensaje/ frontend/src/api/nesting.ts
git commit -m "feat(frontend): un componente para mensajes, con miniaturas y el detalle tecnico (A9)"
```

### Task 12: Todas las pestañas muestran los mensajes enteros

**Files:**
- Modify: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`, `GruposTab.tsx`, `AjusteTab.tsx`, `CosteoTab.tsx`, `PiezasTab.tsx`, `PresupuestoClienteSeccion.tsx`
- Modify: `frontend/src/components/ListaDeFormatos/ListaDeFormatos.tsx`, `frontend/src/components/Seccionado/SeccionarPanel.tsx`
- Modify: `frontend/src/routes/TrabajoWorkspace/importes.ts` (`leerPorcentaje`)
- Test: `frontend/src/routes/TrabajoWorkspace/importes.test.ts`

**Interfaces:**
- Consumes: `Mensaje`, `QueMostrar`, `falla` (Task 11); `Ejecucion.mensajes`, `.error` (Task 4); `OpcionFormato.error` (Task 7); `ColocacionAjustada.motivo` (Task 9).
- Produces: `leerPorcentaje(texto: string): string | null`.

- [ ] **Step 1: Write the failing test**

Sumar a `frontend/src/routes/TrabajoWorkspace/importes.test.ts`:

```ts
import { leerPorcentaje } from "./importes";

describe("leerPorcentaje", () => {
  it("acepta coma o punto, y el signo de por ciento", () => {
    expect(leerPorcentaje("10,5")).toBe("10.5");
    expect(leerPorcentaje("10.5")).toBe("10.5");
    expect(leerPorcentaje(" 21 % ")).toBe("21");
  });

  it("rechaza lo que no es un porcentaje", () => {
    expect(leerPorcentaje("diez")).toBeNull();
    expect(leerPorcentaje("")).toBeNull();
    expect(leerPorcentaje("-5")).toBeNull();
    expect(leerPorcentaje("1.000,5")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`.
Expected: FAIL (no existe `leerPorcentaje`).

- [ ] **Step 3: Write minimal implementation**

En `importes.ts`:

```ts
/** Un porcentaje como se escribe acá («10,5», «10.5», «21 %») → el número
 * que espera la API, o `null` si no lo es. Vacío también es `null`. */
export function leerPorcentaje(texto: string): string | null {
  const limpio = texto.trim().replace(/\s*%$/, "").replace(",", ".");
  return /^\d+(\.\d+)?$/.test(limpio) ? limpio : null;
}
```

**El cambio en cada pestaña** (`grep -n "setError\|Banner variante=\"error\"\|mensajeDeError" <archivo>` los muestra todos):

1. `useState<string | null>(null)` del error pasa a `useState<QueMostrar | null>(null)`.
2. `setError(e instanceof ApiError ? e.message : "<texto>")` y `setError(mensajeDeError(e, "<texto>"))` pasan a `setError(falla(e, "<texto>"))`. Las funciones locales `mensajeDeError` (CosteoTab, GruposTab) se borran.
3. `<Banner variante="error">{error}</Banner>` pasa a `<Mensaje variante="error" que={error} trabajoId={<id del trabajo de la pestaña>} />`. En `ListaDeFormatos` y `PresupuestoClienteSeccion`, sin `trabajoId`.
4. Los `setError("<texto fijo>")` de la propia pantalla quedan (son `string`).

**Lo que se muestra de nuevo:**

`AnidadoTab.tsx` — el error y los avisos de la corrida:

```tsx
      {enCurso && (
        <p className="text-sm mb-2">
          Anidado #{enCurso.id}: <EstadoBadge estado={enCurso.estado} />
          {/* …el botón Cancelar, como está, con setError(falla(e, "No se pudo cancelar.")) */}
        </p>
      )}
      {enCurso?.error && <Mensaje variante="error" que={enCurso.error} trabajoId={trabajoId} />}
      {enCurso?.estado === "lista" &&
        (enCurso.mensajes ?? []).map((aviso, i) => <Mensaje key={i} variante="aviso" que={aviso} trabajoId={trabajoId} />)}
```

(`trabajoId` es el id del trabajo que la pestaña ya saca de `useParams`; usar el nombre que tenga ahí.)

`GruposTab.tsx` — el error de la comparación entero, la fila con error y los avisos:

```tsx
    if (comparacion?.estado === "error") setError(comparacion.error ?? "No se pudo comparar.");
```

```tsx
                        <td colSpan={5}><Mensaje variante="error" que={opcion.error} trabajoId={id} /></td>
```

```tsx
                {unicosPorMensaje(resultado.flatMap((opcion) => opcion.advertencias ?? [])).map((aviso) => (
                  <Mensaje key={aviso.mensaje} variante="aviso" que={aviso} trabajoId={id} />
                ))}
```

con, en `filasComparacion.ts` (y su prueba en `filasComparacion.test.ts`):

```ts
import type { Aviso } from "../../api/mensajes";

/** Los avisos de todas las chapas, sin repetir el mismo texto. */
export function unicosPorMensaje(avisos: Aviso[]): Aviso[] {
  const vistos = new Set<string>();
  return avisos.filter((aviso) => {
    if (vistos.has(aviso.mensaje)) return false;
    vistos.add(aviso.mensaje);
    return true;
  });
}
```

```ts
import { ordenarFilas, unicosPorMensaje } from "./filasComparacion";

  it("unicosPorMensaje no repite el mismo texto", () => {
    const a = { mensaje: "a", piezas: [], chapas: [] };
    expect(unicosPorMensaje([a, { ...a }, { mensaje: "b", piezas: [], chapas: [] }]).map((x) => x.mensaje)).toEqual(["a", "b"]);
  });
```

`AjusteTab.tsx` — el motivo de cada pieza en rojo, que hoy no se ve:

```tsx
  const motivos = [...resultadosAjuste.values()].flatMap((r) => (!r.valida && r.motivo ? [r.motivo] : []));
```

```tsx
          {motivos.length > 0 && (
            <div className="space-y-2">
              {motivos.map((motivo, i) => <Mensaje key={i} variante="aviso" que={motivo} trabajoId={trabajoId} />)}
            </div>
          )}
```

en lugar del `<Banner variante="aviso">Hay colocaciones marcadas en rojo — pasá el cursor para ver el motivo.</Banner>`.

`CosteoTab.tsx` — Margen % e IVA % aceptan coma:

```tsx
  async function alCambiarPorcentaje(campo: "margen_pct" | "iva_pct", etiqueta: string, texto: string) {
    if (texto.trim() === "") return;
    const valor = leerPorcentaje(texto);
    if (valor === null) {
      setError(`«${etiqueta}»: escribí un número, como 10,5.`);
      return;
    }
    await alCambiarMargenOIva({ [campo]: valor });
  }
```

con `onBlur={(e) => alCambiarPorcentaje("margen_pct", "Margen %", e.target.value)}` y `onBlur={(e) => alCambiarPorcentaje("iva_pct", "IVA %", e.target.value)}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test` y `npx tsc -b`; `grep -rn "e.message\|mensajeDeError" frontend/src/routes frontend/src/components --include=*.tsx` tiene que dar vacío (o solo usos que no son de mostrar un error).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): todas las pestanas muestran el mensaje entero, Ajuste dice el motivo y Margen e IVA aceptan coma (A9)"
```

**Pausa del tramo 3:** `npm test`, `npx tsc -b`, la suite del servidor, una mirada en Chrome a Anidado, Grupos y Ajuste sobre una copia de la base, y el ok de Enzo.

---

## Tramo 4 — El resto de los mensajes

### Task 13: Los textos que quedan, contra la regla

**Files:**
- Modify: `backend/app/api/rutas_ajuste.py`, `rutas_catalogo.py`, `rutas_comparaciones.py`, `rutas_importacion.py`, `rutas_nesting.py`, `rutas_presupuesto.py`, `rutas_seccionado.py`, `rutas_trabajos.py`, `esquemas_presupuesto.py`
- Modify: `backend/app/costeo.py`, `backend/app/services/ingesta/dxf.py`, `backend/app/services/presupuesto/totales.py`
- Modify: los textos propios de la pantalla (`grep -rn "jecuci" frontend/src --include=*.tsx`)
- Test: las pruebas que comprueban estos textos (`grep -rn "<palabra del texto viejo>" backend/tests`)

**Interfaces:** ninguna nueva; solo cambian textos.

- [ ] **Step 1: Cambiar los textos**

Uno por uno, con la herramienta de edición:

| Archivo | Hoy | Queda |
|---|---|---|
| `rutas_ajuste.py` | «La ejecución no tiene un snapshot de parámetros de corte guardado.» | «Este anidado no guardó con qué parámetros de corte se hizo: volvé a anidar.» |
| `rutas_ajuste.py` | «La ejecución está en estado «{e}», todavía no hay resultado para exportar.» | «Este anidado todavía no terminó: no hay nada para exportar.» |
| `rutas_ajuste.py` | «La ejecución tiene {total} plancha(s); no existe la #{n}.» | «Este anidado tiene {total} chapa(s): no hay una chapa {n + 1}.» |
| `rutas_ajuste.py` | «No existe la colocación {id}.» | «Esa pieza ya no está en el anidado: volvé a cargar la pestaña.» |
| `rutas_ajuste.py` | «La ejecución está en estado «{e}»; solo se puede ajustar una colocación «lista».» | «Solo se pueden mover piezas de un anidado terminado.» |
| `rutas_catalogo.py`, `rutas_nesting.py`, `rutas_seccionado.py` | «No existe el material {id}.» / «No existe el formato {id}.» | «Ese material ya no existe: volvé a cargar la página.» / «Esa chapa ya no existe: volvé a cargar la página.» |
| `rutas_catalogo.py` | «El formato «{a}×{b}» no tiene precio por m²: un retazo se cobra por m² y no habría cómo.» | «La chapa de {medida} no tiene precio por m²: un retazo se cobra por m², así que sin ese precio no se puede crear.» (con `medida` de `traducir_errores`) |
| `rutas_catalogo.py` | «El material {id} todavía no tiene parámetros de corte configurados.» | ««{nombre}» todavía no tiene cargados el kerf, el margen y la separación.» |
| `rutas_comparaciones.py` | «No existe la comparación {id}.» | «Esa comparación ya no está (el servidor se reinició): volvé a comparar.» |
| `rutas_comparaciones.py` | «La comparación ya está en estado «{e}», no se puede cancelar.» | «La comparación ya terminó: no hay nada que cancelar.» |
| `rutas_importacion.py` | «No existe el análisis {token}.» | «Ese análisis del dibujo ya no está: volvé a subir el archivo.» |
| `rutas_importacion.py` | «Las piezas {ids} no son del diseño {i}.» | «Algunas piezas pedidas no son de ese diseño.», con los `id` en `detalle` (`ErrorParaElUsuario`) |
| `rutas_nesting.py` | «El material «X» no tiene parámetros de corte configurados (CART-105).» (dos lugares) | ««X» todavía no tiene cargados el kerf, el margen y la separación: cargalos antes de anidar.» |
| `rutas_nesting.py` | «El grupo «G» no tiene un formato asignado.» | «El grupo «G» todavía no tiene chapa: elegila en la pestaña Grupos.» |
| `rutas_nesting.py` | «No existe la ejecución {id}.» | «Ese anidado ya no existe: volvé a cargar la pestaña.» |
| `rutas_nesting.py` | «La ejecución ya está en estado «{e}», no se puede cancelar.» | «Ese anidado ya terminó: no hay nada que cancelar.» |
| `rutas_nesting.py` | «Solo una ejecución en estado «lista» puede marcarse definitiva.» | «Solo un anidado terminado puede quedar como el que se usa para cotizar.» |
| `rutas_nesting.py` | «La ejecución {id} todavía se está calculando: cancelala antes de borrarla.» | «El anidado #{id} todavía se está calculando: cancelalo antes de borrarlo.» |
| `rutas_nesting.py` | «La comparación todavía no admite la pasada en huecos.» | «La comparación todavía no puede meter piezas adentro de los huecos: destildá esa opción.» |
| `rutas_nesting.py` | «El formato «a×b» no tiene precio de referencia cargado.» | «La chapa de {medida} no tiene precio cargado: no se puede calcular su costo.» |
| `rutas_nesting.py` | «El formato «a×b» se vende por «U», no por m² — el costo no se calcula solo, hay que cargarlo a mano.» | «La chapa de {medida} se vende por «U» y no por m²: su costo no se calcula solo, cargalo a mano en Costeo.» |
| `rutas_nesting.py` | «El ajuste en huecos invade la reserva de borde/kerf.» y `raise ValueError(validacion.motivo)` en `_correr_anidado` | `ErrorParaElUsuario("Al meter piezas en los huecos, una quedó pisando el margen de la chapa: probá sin esa opción.")` y `ErrorParaElUsuario("Al meter piezas en los huecos, una quedó pisando otra: probá sin esa opción.", detalle=validacion.motivo)` |
| `rutas_presupuesto.py` | «No existe el cliente {id}.» / «No existe el presupuesto {id}.» / «No existe la línea de costo {id}.» | «Ese cliente ya no existe: volvé a cargar la página.» / «Ese presupuesto ya no existe: volvé a cargar la página.» / «Esa línea ya no existe: volvé a cargar la página.» |
| `rutas_presupuesto.py` | «El presupuesto no tiene un trabajo asociado; no hay nada que costear.» | «Este presupuesto no está atado a un trabajo: no hay materiales que calcular.» |
| `rutas_presupuesto.py` | «Una línea de rubro MATERIAL no se {accion} a mano — se regenera con recalcular-materiales, o se corrige con un override.» | «Una línea de material no se {accion} a mano: se vuelve a calcular con «Recalcular», o se corrige con un valor a mano.» (usar la etiqueta real del botón de Costeo) |
| `rutas_trabajos.py` | «No existe el trabajo {id}.» / «No existe el grupo de corte {id}.» / «No existe la pieza {id}.» (también en `rutas_seccionado.py`) | «Ese trabajo ya no existe: volvé a la lista de trabajos.» / «Ese grupo ya no existe: volvé a cargar la pestaña.» / «Esa pieza ya no existe: volvé a cargar la pestaña.» |
| `rutas_trabajos.py` | «Las correcciones no son un JSON válido ({msg}).» y «Las correcciones tienen que ser un objeto: …» | «No se pudieron leer las correcciones del dibujo: volvé a marcarlas.», con el motivo en `detalle` |
| `rutas_trabajos.py` | ««{valor}» no es una corrección: para «{forma}» tiene que ser «cortar» o «no_va».» | «No se entendió la corrección de «{forma}»: volvé a marcarla.» |
| `rutas_trabajos.py` | «Las correcciones nombran formas que no están en este archivo: {formas}.» | «Algunas formas marcadas no están en este archivo: {formas}. Volvé a marcarlas.» |
| `esquemas_presupuesto.py` | «{campo} no puede quedar vacío.» | ««{ETIQUETAS_DE_CAMPOS.get(campo, campo)}» no puede quedar vacío.» |
| `esquemas_presupuesto.py` | «override_por es obligatorio para aplicar un override — hay que saber quién lo hizo.» | «Falta quién cargó el valor a mano.» |
| `costeo.py` | «Grupo «G»: el formato no tiene precio de referencia cargado.» | «Grupo «G»: la chapa no tiene precio cargado.» |
| `costeo.py` | «Grupo «G»: se vende por «U», no por m² — el costo no se calcula solo, hay que cargarlo a mano.» | «Grupo «G»: la chapa se vende por «U» y no por m², así que su costo no se calcula solo: cargalo a mano.» |
| `dxf.py` | «{n} contorno(s) no se pudieron cerrar dentro de PAR-06 ({tol} mm) y se excluyeron.» | «{n} contorno(s) quedan abiertos más de {tol} mm y no se cargaron: cerralos en el dibujo.» |
| `dxf.py` | «Se repararon {n} contorno(s) que se cruzaban a sí mismos, corrigiendo a lo sumo PAR-49 ({a} mm²) de área cada uno: {lugares}.» | «Se arreglaron {n} contorno(s) que se cruzaban a sí mismos (cada arreglo cambia a lo sumo {a} mm²): {lugares}.» |
| `dxf.py` | «{n} entidad(es) no se pudieron leer y se excluyeron ({detalle}).» | «{n} elemento(s) del dibujo no se pudieron leer y no se cargaron ({detalle}).» |
| `totales.py` | «El presupuesto no tiene margen configurado (PAR-12); no se calculó el precio de venta.» | «Falta el margen: sin él no se calcula el precio de venta.» |
| `totales.py` | ««D» no tiene costo calculado ni override; no se sumó al total.» | ««D» no tiene costo calculado ni un valor a mano: no se sumó al total.» |
| `totales.py` | «El presupuesto no tiene IVA configurado; no se calculó el total.» | «Falta el IVA: sin él no se calcula el total.» |

Los textos armados en variables (`<mensaje>`, `<str(error)>`, `<sin_reparto>` en el relevamiento: `rutas_catalogo.py:93`, `rutas_importacion.py:124`, `rutas_nesting.py:365`, `rutas_presupuesto.py:75`, `rutas_seccionado.py:67/94`, `rutas_trabajos.py:309/491`, `dxf.py:700`, `totales.py:185`): leer de dónde sale cada uno y pasarlo por la regla. La prueba guardiana de la Tarea 14 no los ve, así que se revisan a mano.

En la pantalla: «Ejecución #» pasa a «Anidado #» y el encabezado «Ejecución» de la tabla de Anidado pasa a «Anidado»; los demás textos fijos de `setError("…")` se leen contra la regla.

- [ ] **Step 2: Correr las pruebas y ajustar las que comprueban los textos viejos**

Run: la suite entera; `npm test` y `npx tsc -b`.
Expected: fallan las pruebas que buscan un texto viejo. Cada una pasa a buscar una palabra del texto nuevo (por ejemplo, `"No existe la ejecución 999" in mensaje_de(r)` → `"Ese anidado ya no existe" in mensaje_de(r)`; `"#{anidado_id}"` sigue estando en los textos que lo traen).

- [ ] **Step 3: Run tests to verify they pass**

Run: la suite entera; `npm test` y `npx tsc -b`.
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/ frontend/src/
git commit -m "fix(mensajes): los textos que quedaban, segun la regla: sin codigos, sin palabras de programacion (A9)"
```

### Task 14: La prueba guardiana y la regla escrita

**Files:**
- Create: `backend/tests/test_mensajes_claros.py`
- Modify: `docs/CONVENCIONES.md` (§6, «Convenciones de código»)

**Interfaces:** ninguna.

- [ ] **Step 1: Write the test**

`backend/tests/test_mensajes_claros.py`:

```python
"""La regla de los mensajes (A9, `CONVENCIONES.md §6`): ningún texto para
el usuario nombra códigos del proyecto, programas, documentos ni palabras
de programación. Recorre el código y junta esos textos."""
from __future__ import annotations

import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

PROHIBIDO = re.compile(
    r"\b(CART|PAR|ADR|SUP|[BDPT])-\d+|\bSparrow\b|\brectpack\b|\bDeepnest\b|\bsnapshot\b|\boverride\b"
    r"|\bJSON\b|\bendpoint\b|\bejecuci[oó]n|\.md\b|§",
    re.IGNORECASE,
)

#: Errores que llevan texto técnico a propósito: va al detalle, nunca al mensaje.
TECNICOS = {"ResultadoQueNoPasaElControl", "CalculoInterrumpido"}

#: Llamadas cuyo primer texto (o segundo, en `HTTPException`) lee una persona.
PARA_EL_USUARIO = {"ErrorParaElUsuario", "Aviso", "AvisoLeer", "avisar"}

#: Listas de avisos que se llenan con `.append(texto)`.
LISTAS_DE_AVISOS = {"advertencias", "avisos"}


def _texto(nodo) -> str | None:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.JoinedStr):
        return "".join(v.value for v in nodo.values if isinstance(v, ast.Constant))
    if isinstance(nodo, ast.BinOp):
        return (_texto(nodo.left) or "") + (_texto(nodo.right) or "")
    if isinstance(nodo, ast.Dict):
        for clave, valor in zip(nodo.keys, nodo.values):
            if isinstance(clave, ast.Constant) and clave.value == "mensaje":
                return _texto(valor)
    return None


def _nombre(funcion) -> str:
    if isinstance(funcion, ast.Attribute):
        return funcion.attr
    return getattr(funcion, "id", "")


def _candidato(nodo):
    if isinstance(nodo, ast.Raise) and isinstance(nodo.exc, ast.Call) and nodo.exc.args:
        return None if _nombre(nodo.exc.func) in TECNICOS else nodo.exc.args[0]
    if not isinstance(nodo, ast.Call):
        return None
    nombre = _nombre(nodo.func)
    if nombre == "HTTPException" and len(nodo.args) >= 2:
        return nodo.args[1]
    if nombre in PARA_EL_USUARIO and nodo.args:
        return nodo.args[0]
    if nombre == "append" and isinstance(nodo.func, ast.Attribute) and _nombre(nodo.func.value) in LISTAS_DE_AVISOS and nodo.args:
        return nodo.args[0]
    for palabra in nodo.keywords:
        if palabra.arg == "mensaje":
            return palabra.value
    return None


def textos_para_el_usuario():
    for archivo in sorted(APP.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            candidato = _candidato(nodo)
            texto = _texto(candidato) if candidato is not None else None
            if texto:
                yield f"{archivo.relative_to(APP.parent)}:{nodo.lineno}", texto


def test_hay_textos_para_revisar():
    """Si esto falla, la búsqueda dejó de encontrar los textos: la otra
    prueba pasaría sin revisar nada."""
    assert len(list(textos_para_el_usuario())) > 60


def test_ningun_texto_para_el_usuario_rompe_la_regla():
    rotos = [f"{lugar}: {texto}" for lugar, texto in textos_para_el_usuario() if PROHIBIDO.search(texto)]

    assert rotos == []
```

- [ ] **Step 2: Run test and fix what it finds**

Run: la suite con `tests/test_mensajes_claros.py`.
Expected: PASS después de la Tarea 13. Si lista algún texto, reescribirlo según la regla (y su prueba, si la tiene) hasta que pase. Si encuentra menos de 60 textos, revisar `_candidato` antes de seguir.

- [ ] **Step 3: Escribir la regla en `CONVENCIONES.md`**

En §6, «Convenciones de código», una sección nueva:

```markdown
### Mensajes para quien usa el sistema

Vale para todo error y aviso que lee una persona (A9, [`historico/A9-mensajes-entendibles/diseno.md`](historico/A9-mensajes-entendibles/diseno.md)):

1. **Primero qué pasó, después qué hacer.** Una o dos oraciones, con voseo («elegí», «probá»).
2. **Se nombra lo que el usuario ve:** la pieza por su nombre del dibujo, el grupo por su nombre, la chapa del catálogo por material y medida, la chapa de un resultado por su número, y el campo con la etiqueta de la pantalla donde se corrige.
3. **Nunca:** `id` de base, códigos del proyecto (`CART-`, `PAR-`, `D-`…), nombres de programas (Sparrow, rectpack, Deepnest), inglés, palabras de programación (ejecución, snapshot, override, JSON) ni referencias a documentos.
4. **Lo técnico va en `detalle`**, nunca en el mensaje: la pantalla lo muestra en «Ver detalle técnico» y queda en el registro del servidor.
5. **Un aviso que sale siempre no es un aviso:** se saca, o pasa a un texto fijo de ayuda.

Un error se tira con `ErrorParaElUsuario` (`backend/app/mensajes.py`), con las piezas y chapas que nombra; un cálculo que solo conoce `id` tira un error con nombre propio y la ruta lo traduce (`backend/app/api/traducir_errores.py`). La prueba `backend/tests/test_mensajes_claros.py` revisa los textos.
```

(El enlace apunta a `historico/` porque la carpeta pasa ahí al cerrar, en la Tarea 15.)

- [ ] **Step 4: Run the whole suite**

Run: la suite entera; `npm test` y `npx tsc -b`.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_mensajes_claros.py docs/CONVENCIONES.md
git commit -m "test(mensajes): la prueba guardiana de la regla, y la regla en CONVENCIONES (A9)"
```

**Pausa del tramo 4:** las dos suites y el ok de Enzo.

---

## Tramo 5 — Recorrido y cierre

### Task 15: Recorrido en el navegador, documentos y PR

**Files:**
- Create (fuera de git): `backend/local/herramientas-a9-<fecha>/` con el guion del recorrido y las capturas
- Modify: `docs/plan/PLAN-MAESTRO.md` (§7), `docs/BITACORA.md`, este plan («Desvíos»)

- [ ] **Step 1: Recorrido sobre una copia de la base**

Antes, mirar quién escucha en 8000 y 5173 (Enzo suele tener la app levantada contra su base real) y levantar todo con `CARTELERIA_DATOS` apuntando a una copia en D:. Con Chrome sin ventana por CDP (como en A7 y A8), en cada caso mirar el mensaje, las miniaturas, «Ver detalle técnico» con Copiar y la línea en `registro/servidor.log`:

1. Servidor apagado y un clic en Anidar: «No se pudo conectar con el servidor…».
2. «10,5» y «abc» en Margen %: el primero se guarda; el segundo dice «Margen %: escribí un número, como 10,5.».
3. Comparación de «Complejo» con 30 s por chapa: las filas que no llegan dicen «No llegó a un resultado en 30 s…» y las demás se muestran.
4. Un worker que se corta (un guion que lo reemplaza y falla, como `worker_que_falla` de las pruebas): «El cálculo se interrumpió por un error interno…», con la traza en el detalle.
5. En Ajuste, una pieza encima de otra: el aviso con las dos miniaturas y la chapa.
6. Una pieza más grande que la chapa con Sparrow: el error con su nombre y su miniatura.
7. Un error inesperado provocado: el mensaje general, la traza en el detalle y en el registro.

- [ ] **Step 2: Documentos**

- `PLAN-MAESTRO.md §7`: en los pendientes del reparto por chapa, «Si un formato de la comparación no llega a ningún resultado dentro de su tiempo máximo, la comparación entera termina en error» pasa a resuelto; en los del PDF del presupuesto, «Los campos «Margen %» e «IVA %» … «10,5» vuelve como error» también. Lo que haya quedado vivo de A9, en una tabla «Pendientes de los mensajes entendibles (A9)».
- `BITACORA.md`: la jornada.
- Este plan: «Estado» y «Desvíos».

- [ ] **Step 3: Revisión de la rama**

Con `superpowers:requesting-code-review`. Arreglar lo que encuentre, cada arreglo con una prueba que falle primero.

- [ ] **Step 4: PR**

Con el ok de Enzo, subir la rama y abrir el PR (`GH_TOKEN="$(gh auth token --user enzopazzelli)" gh pr create …`), con el formato de los PR anteriores. Fusionarlo es de Enzo.

- [ ] **Step 5: Al fusionar**

La carpeta `docs/plan/A9-mensajes-entendibles/` pasa a `docs/historico/`, con el «Estado» de diseño y plan al día.

---

## Desvíos

(Se completa durante la ejecución.)
