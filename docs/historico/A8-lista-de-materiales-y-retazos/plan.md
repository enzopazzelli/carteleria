# A8 · Lista de materiales con filtros y retazos de medida libre — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado:** **cerrado el 2026-10-14,** en `main` ([PR #24](https://github.com/enzopazzelli/carteleria/pull/24)). Ejecutado ese día, de la Tarea 1 a la 7, en esta sesión y con una pausa por tramo. No se ensayó sobre una copia: los bloques salen de leer el código de `main` en `3f2982d`. Lo que se aparte va al final, en «Desvíos».

**Goal:** Que al comparar chapas se elija desde una tabla con familia, material, espesor, medida y precio por m², con filtros y buscador; y que se pueda agregar un retazo de medida libre que se cobra por m² al precio de su fila.

**Architecture:** El material gana un dato `familia`, que una sola regla deduce del nombre (en el modelo, como valor por defecto, y copiada en la migración que la completa para los materiales que ya existen). Un retazo es un `Formato` con `es_retazo`, que crea el servidor desde otra fila copiando su precio. En la pantalla, un componente `ListaDeFormatos` con sus cuentas en funciones aparte reemplaza las casillas de la comparación.

**Un agregado al diseño:** el diseño dice que la ✕ de un retazo usa la ruta que ya existe para quitar un formato. Esa ruta hoy deja sin material, sin avisar, al grupo que lo usa (la base pone su `formato_id` en vacío). Con la ✕ ese caso se vuelve fácil de provocar, así que la Task 3 hace que la ruta lo rechace con un 409 que nombra los grupos, para cualquier formato.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, Alembic, Pydantic 2, pytest; React 18 con TypeScript, TanStack Query, Vitest.

**Spec:** [`diseno.md`](diseno.md), en esta misma carpeta.

## Global Constraints

- Todo texto que ve una persona va en castellano rioplatense.
- Los commits no llevan línea de atribución (`Co-Authored-By`).
- Familias: CHAPA → «Chapas», ACRILICO → «Acrílicos», ALTO IMPACTO → «Alto impacto», CORRUGADO → «Corrugado», POLICARBONATO → «Policarbonato», cualquier otro → «Otros»; sin importar mayúsculas ni tildes, mirando cómo empieza el nombre.
- Un retazo: medida mayor que 0 y hasta 10 000 mm; copia moneda, unidad de venta, precio por unidad de venta y marca de precio simulado de su fila; código de la fila más «-R».
- Pruebas del backend sin tocar la base real: desde `backend/`, `mkdir -p local/tmp-a8/datos && CARTELERIA_DATOS="$PWD/local/tmp-a8/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a8/base"`, y después `rm -rf local/tmp-a8`.
- Editar con la herramienta de edición (conserva los finales de línea); nunca `sed -i`.

## Review Focus

- **Quitar un retazo (o cualquier formato) que usa un grupo:** hoy la base deja el grupo sin material sin avisar. Tiene que rechazarse diciendo qué grupos lo usan, y el grupo conservar su chapa. Lo prueba la Tarea 3.
- **Una medida de retazo que no es un número, es cero, negativa o absurda:** se rechaza sin crear nada. Lo prueba la Tarea 3.
- **Un retazo de una fila que no se vende por m² o no tiene precio:** se rechaza diciendo por qué. Lo prueba la Tarea 3.
- **Buscar un número que aparece adentro de una medida** («negra 22» no puede traer la chapa de cal. 20 porque «1220» contiene «22»). Lo prueba la Tarea 4.
- **«Seleccionar todas» con un filtro puesto:** tilda o destilda solo lo visible, sin tocar lo tildado que el filtro esconde. Lo prueba la Tarea 4.

---

## Tramo 1 — El servidor

### Task 1: La familia del material

**Files:**
- Modify: `backend/app/modelos/catalogo.py` (`familia_desde_nombre`, `_familia_por_defecto`, columna `Material.familia`)
- Modify: `backend/app/api/esquemas_catalogo.py` (`familia` en `MaterialCrear`, `MaterialActualizar`, `MaterialLeer`)
- Modify: `backend/app/api/rutas_catalogo.py` (`crear_material`, `actualizar_material`)
- Test: `backend/tests/modelos/test_familia.py` (nuevo), `backend/tests/api/test_rutas_catalogo.py`

**Interfaces:**
- Produces: `familia_desde_nombre(nombre: str | None) -> str` en `app/modelos/catalogo.py`; `Material.familia: str` (obligatorio, hasta 40 caracteres); `familia` en la respuesta de las rutas de materiales.

- [ ] **Step 1: Write the failing test**

`backend/tests/modelos/test_familia.py`:

```python
"""La familia de un material sale de cómo empieza su nombre
(`docs/historico/A8-lista-de-materiales-y-retazos/diseno.md §5.1`)."""
from __future__ import annotations

import pytest

from app.modelos.catalogo import familia_desde_nombre


@pytest.mark.parametrize(
    ("nombre", "familia"),
    [
        ("CHAPA NEGRA", "Chapas"),
        ("Chapa galvanizada", "Chapas"),
        ("ACRILICO CRISTAL", "Acrílicos"),
        ("Acrílico blanco", "Acrílicos"),
        ("ALTO IMPACTO BLANCO", "Alto impacto"),
        ("CORRUGADO PLASTICO", "Corrugado"),
        ("POLICARBONATO CRISTAL", "Policarbonato"),
        ("  chapa con espacios", "Chapas"),
        ("MDF", "Otros"),
        ("", "Otros"),
        (None, "Otros"),
    ],
)
def test_la_familia_sale_de_como_empieza_el_nombre(nombre, familia):
    assert familia_desde_nombre(nombre) == familia
```

Al final de `backend/tests/api/test_rutas_catalogo.py`:

```python
# --- Familia del material (A8) -------------------------------------------


def test_un_material_sin_familia_la_toma_del_nombre(cliente):
    material = _crear_material(cliente, nombre="ACRILICO CRISTAL", espesor="3 mm")

    assert material["familia"] == "Acrílicos"


def test_un_material_con_familia_la_respeta(cliente):
    material = _crear_material(cliente, nombre="MDF crudo", espesor="9 mm", familia="Maderas")

    assert material["familia"] == "Maderas"


def test_la_familia_se_corrige_y_no_se_borra(cliente):
    material = _crear_material(cliente, nombre="MDF crudo", espesor="9 mm")

    corregida = cliente.patch(f"/materiales/{material['id']}", json={"familia": "Maderas"}).json()
    sin_tocar = cliente.patch(f"/materiales/{material['id']}", json={"familia": None}).json()

    assert material["familia"] == "Otros"
    assert corregida["familia"] == "Maderas"
    assert sin_tocar["familia"] == "Maderas"


def test_la_lista_de_materiales_trae_la_familia(cliente):
    _crear_material(cliente)

    [material] = cliente.get("/materiales").json()

    assert material["familia"] == "Chapas"
```

- [ ] **Step 2: Run test to verify it fails**

Run (desde `backend/`): `python -m pytest -q -p no:cacheprovider tests/modelos/test_familia.py tests/api/test_rutas_catalogo.py -k "familia"`
Expected: FAIL con `ImportError: cannot import name 'familia_desde_nombre'` (la primera) y `KeyError: 'familia'` (las de la API).

- [ ] **Step 3: Write minimal implementation**

En `backend/app/modelos/catalogo.py`, agregar `import unicodedata` junto a `import enum`, y arriba de `class Material`:

```python
#: Cómo empieza el nombre → familia (A8). Lo que no empieza con ninguno, «Otros».
_FAMILIAS_POR_PREFIJO = (
    ("CHAPA", "Chapas"),
    ("ACRILICO", "Acrílicos"),
    ("ALTO IMPACTO", "Alto impacto"),
    ("CORRUGADO", "Corrugado"),
    ("POLICARBONATO", "Policarbonato"),
)


def familia_desde_nombre(nombre: str | None) -> str:
    """La familia de un material según cómo empieza su nombre, sin importar
    mayúsculas ni tildes (`docs/historico/A8-lista-de-materiales-y-retazos/diseno.md §5.1`).
    La migración que completa la familia de los materiales que ya existían
    tiene una copia de esta regla: si se cambia acá, aquella no cambia."""
    plano = unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode().upper().strip()
    for prefijo, familia in _FAMILIAS_POR_PREFIJO:
        if plano.startswith(prefijo):
            return familia
    return "Otros"


def _familia_por_defecto(contexto) -> str:
    """Un material que se guarda sin familia la toma de su nombre."""
    return familia_desde_nombre(contexto.get_current_parameters().get("nombre"))
```

Y en `class Material`, debajo de `espesor`:

```python
    #: Chapas, Acrílicos… (A8): para filtrar la lista al comparar. Si no se
    #: da, sale del nombre (`familia_desde_nombre`).
    familia: Mapped[str] = mapped_column(String(40), default=_familia_por_defecto)
```

En `backend/app/api/esquemas_catalogo.py`, agregar `Field` a `from pydantic import BaseModel, ConfigDict`, y:

- en `MaterialCrear`, debajo de `espesor`: `familia: str | None = Field(default=None, min_length=1, max_length=40)` con el comentario `#: Sin familia, la deduce el nombre (A8).`
- en `MaterialActualizar`, debajo de `espesor`: `familia: str | None = Field(default=None, min_length=1, max_length=40)`
- en `MaterialLeer`, debajo de `espesor`: `familia: str`

En `backend/app/api/rutas_catalogo.py`, `crear_material` pasa a ser:

```python
def crear_material(datos: MaterialCrear, sesion: Session = Depends(obtener_sesion)) -> Material:
    campos = datos.model_dump()
    # Sin familia, el modelo la deduce del nombre (`familia_desde_nombre`).
    if campos["familia"] is None:
        del campos["familia"]
    material = Material(**campos)
    sesion.add(material)
    _commit_o_409(sesion, "Ya existe un material con ese nombre y espesor.")
    return material
```

y en `actualizar_material`, el `for` pasa a ser:

```python
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        if campo == "familia" and valor is None:
            continue  # la familia es obligatoria: un null no la borra
        setattr(material, campo, valor)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q -p no:cacheprovider tests/modelos/ tests/api/test_rutas_catalogo.py`
Expected: todas pasan.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modelos/catalogo.py backend/app/api/esquemas_catalogo.py backend/app/api/rutas_catalogo.py backend/tests/modelos/test_familia.py backend/tests/api/test_rutas_catalogo.py
git commit -m "feat(catalogo): la familia del material, deducida del nombre si no se da (A8)"
```

### Task 2: La migración de la familia

**Files:**
- Create: `backend/alembic/versions/a8f2c61b9d04_familia_del_material.py`
- Test: `backend/tests/modelos/test_migracion_familia.py`

**Interfaces:**
- Consumes: la regla de la Task 1 (copiada, no importada).
- Produces: la revisión `a8f2c61b9d04` sobre `7f91bcd3ef15`.

- [ ] **Step 1: Write the failing test**

`backend/tests/modelos/test_migracion_familia.py`:

```python
"""La migración de la familia (A8): la completa para los materiales que ya
había, y vuelve atrás sin dejar la columna."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

_ANTES = "7f91bcd3ef15"


def _config() -> Config:
    # Sin archivo .ini: así `env.py` no reconfigura el logging de las pruebas.
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    return config


def _consultar(base: Path, sql: str) -> list:
    conexion = sqlite3.connect(base)
    try:
        return conexion.execute(sql).fetchall()
    finally:
        conexion.close()


def test_la_migracion_completa_la_familia_desde_el_nombre_y_vuelve(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    conexion = sqlite3.connect(base)
    for nombre in ("CHAPA NEGRA", "ACRILICO CRISTAL", "Alto Impacto blanco", "MDF"):
        conexion.execute(
            "insert into materiales (nombre, espesor, nesteable_por_area, provisto_por_cliente, creado_en, actualizado_en)"
            " values (?, '2 mm', 1, 0, '2026-10-14 00:00:00', '2026-10-14 00:00:00')",
            (nombre,),
        )
    conexion.commit()
    conexion.close()

    command.upgrade(config, "head")
    familias = dict(_consultar(base, "select nombre, familia from materiales"))
    command.downgrade(config, _ANTES)
    columnas = [fila[1] for fila in _consultar(base, "pragma table_info(materiales)")]

    assert familias == {
        "CHAPA NEGRA": "Chapas",
        "ACRILICO CRISTAL": "Acrílicos",
        "Alto Impacto blanco": "Alto impacto",
        "MDF": "Otros",
    }
    assert "familia" not in columnas
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q -p no:cacheprovider tests/modelos/test_migracion_familia.py`
Expected: FAIL: la consulta de familias da `sqlite3.OperationalError: no such column: familia` (no hay migración que la agregue).

- [ ] **Step 3: Write minimal implementation**

`backend/alembic/versions/a8f2c61b9d04_familia_del_material.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q -p no:cacheprovider tests/modelos/test_migracion_familia.py`
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/a8f2c61b9d04_familia_del_material.py backend/tests/modelos/test_migracion_familia.py
git commit -m "feat(catalogo): migracion que agrega la familia y la completa desde el nombre (A8)"
```

### Task 3: El retazo, y no quitar un formato que usa un grupo

**Files:**
- Modify: `backend/app/api/esquemas_catalogo.py` (`RetazoCrear`)
- Modify: `backend/app/api/rutas_catalogo.py` (`crear_retazo` nueva; `eliminar_formato` rechaza si un grupo lo usa)
- Test: `backend/tests/api/test_rutas_catalogo.py`

**Interfaces:**
- Produces: `POST /formatos/{formato_id}/retazos` con `{ancho_mm, alto_mm}` → 201 `FormatoLeer`; 404 si no existe el formato; 422 si la medida no es un número mayor que 0 y hasta 10 000; 400 si la fila no se vende por m² o no tiene precio. `DELETE /formatos/{id}` → 409 si un grupo lo usa.

- [ ] **Step 1: Write the failing test**

Al final de `backend/tests/api/test_rutas_catalogo.py`:

```python
# --- Retazos (A8) ----------------------------------------------------------


def _formato_por_m2(cliente, **extra) -> dict:
    material = _crear_material(cliente)
    datos = {
        "codigo": "CHA0012", "ancho_mm": "1220", "alto_mm": "2440", "moneda": "ARS",
        "unidad_venta": "M2", "costo_unidad_venta": "13720.4038",
    } | extra
    respuesta = cliente.post(f"/materiales/{material['id']}/formatos", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _retazo(cliente, formato_id, ancho="1000", alto="1000"):
    return cliente.post(f"/formatos/{formato_id}/retazos", json={"ancho_mm": ancho, "alto_mm": alto})


def test_un_retazo_copia_el_precio_por_m2_de_su_fila(cliente):
    origen = _formato_por_m2(cliente)
    cliente.patch(f"/formatos/{origen['id']}", json={"precio_simulado": True})

    respuesta = _retazo(cliente, origen["id"])

    assert respuesta.status_code == 201, respuesta.text
    retazo = respuesta.json()
    assert retazo["id"] != origen["id"]
    assert retazo["material_id"] == origen["material_id"]
    assert (Decimal(retazo["ancho_mm"]), Decimal(retazo["alto_mm"])) == (Decimal("1000"), Decimal("1000"))
    assert retazo["es_retazo"] is True
    assert retazo["codigo"] == "CHA0012-R"
    assert (retazo["moneda"], retazo["unidad_venta"]) == ("ARS", "M2")
    assert Decimal(retazo["costo_unidad_venta"]) == Decimal("13720.4038")
    assert retazo["precio_simulado"] is True


def test_un_retazo_de_una_fila_sin_codigo_queda_sin_codigo(cliente):
    origen = _formato_por_m2(cliente, codigo=None)

    assert _retazo(cliente, origen["id"]).json()["codigo"] is None


def test_un_retazo_de_un_formato_que_no_existe_da_404(cliente):
    assert _retazo(cliente, 999).status_code == 404


@pytest.mark.parametrize(("ancho", "alto"), [("0", "500"), ("-5", "500"), ("nan", "500"), ("500", "10001"), ("mil", "500")])
def test_una_medida_de_retazo_invalida_da_422(cliente, ancho, alto):
    origen = _formato_por_m2(cliente)

    respuesta = _retazo(cliente, origen["id"], ancho, alto)

    assert respuesta.status_code == 422
    assert len(cliente.get(f"/materiales/{origen['material_id']}/formatos").json()) == 1


@pytest.mark.parametrize("extra", [{"unidad_venta": "PLANCHA"}, {"costo_unidad_venta": None}])
def test_un_retazo_de_una_fila_sin_precio_por_m2_da_400(cliente, extra):
    origen = _formato_por_m2(cliente, **extra)

    respuesta = _retazo(cliente, origen["id"])

    assert respuesta.status_code == 400
    assert "por m²" in respuesta.json()["detail"]


def test_un_formato_que_usa_un_grupo_no_se_quita(cliente):
    """La base dejaba el grupo sin material, sin avisar."""
    origen = _formato_por_m2(cliente)
    retazo = _retazo(cliente, origen["id"]).json()
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa chica", "formato_id": retazo["id"]}).json()

    respuesta = cliente.delete(f"/formatos/{retazo['id']}")

    assert respuesta.status_code == 409
    assert "«Chapa chica»" in respuesta.json()["detail"]
    [mismo] = cliente.get(f"/trabajos/{trabajo['id']}/grupos").json()
    assert mismo["id"] == grupo["id"] and mismo["formato_id"] == retazo["id"]


def test_un_retazo_que_nadie_usa_se_quita(cliente):
    origen = _formato_por_m2(cliente)
    retazo = _retazo(cliente, origen["id"]).json()

    assert cliente.delete(f"/formatos/{retazo['id']}").status_code == 204
    assert cliente.get(f"/formatos/{retazo['id']}").status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q -p no:cacheprovider tests/api/test_rutas_catalogo.py -k "retazo or quita"`
Expected: FAIL: las de retazo con 404/405 (la ruta no existe) y `test_un_formato_que_usa_un_grupo_no_se_quita` con `assert 204 == 409`; `test_un_retazo_que_nadie_usa_se_quita` también falla porque no puede crear el retazo.

- [ ] **Step 3: Write minimal implementation**

En `backend/app/api/esquemas_catalogo.py`, agregar `from typing import Annotated` arriba, y al final de la sección de formatos:

```python
#: La medida de un retazo es libre, pero no absurda (A8, §5.2).
MedidaDeRetazo = Annotated[Decimal, Field(gt=0, le=10000, allow_inf_nan=False)]


class RetazoCrear(BaseModel):
    """Un retazo de medida libre, a partir de otro formato (A8)."""

    ancho_mm: MedidaDeRetazo
    alto_mm: MedidaDeRetazo
```

En `backend/app/api/rutas_catalogo.py`, agregar `RetazoCrear` a la importación de `esquemas_catalogo`, `from ..modelos.trabajo import GrupoDeCorte` debajo de la de `..modelos.catalogo`, y debajo de `eliminar_formato` reemplazado por esta versión:

```python
@router.delete("/formatos/{formato_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_formato(formato_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    """No se quita un formato que usa un grupo: la base lo dejaría sin
    material sin avisar (A8)."""
    formato = _formato_o_404(sesion, formato_id)
    grupos = sesion.execute(select(GrupoDeCorte.nombre).where(GrupoDeCorte.formato_id == formato_id)).scalars().all()
    if grupos:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Lo usan estos grupos: {', '.join(f'«{nombre}»' for nombre in grupos)}. "
            "Elegí otra chapa para ellos antes de quitarlo.",
        )
    sesion.delete(formato)
    sesion.commit()


@router.post("/formatos/{formato_id}/retazos", response_model=FormatoLeer, status_code=status.HTTP_201_CREATED)
def crear_retazo(formato_id: int, datos: RetazoCrear, sesion: Session = Depends(obtener_sesion)) -> Formato:
    """Un retazo de medida libre del mismo material
    (`docs/historico/A8-lista-de-materiales-y-retazos/diseno.md §5.2`). Se cobra
    por m² al precio de la fila de la que sale: se copia acá, así la regla
    no depende de quien lo pide."""
    origen = _formato_o_404(sesion, formato_id)
    if origen.unidad_venta != "M2" or origen.costo_unidad_venta is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El formato «{origen.ancho_mm}×{origen.alto_mm}» no tiene precio por m²: "
            "un retazo se cobra por m² y no habría cómo.",
        )
    retazo = Formato(
        material_id=origen.material_id,
        codigo=f"{origen.codigo}-R" if origen.codigo else None,
        ancho_mm=datos.ancho_mm,
        alto_mm=datos.alto_mm,
        es_retazo=True,
        moneda=origen.moneda,
        unidad_venta=origen.unidad_venta,
        costo_unidad_venta=origen.costo_unidad_venta,
        precio_simulado=origen.precio_simulado,
    )
    sesion.add(retazo)
    sesion.commit()
    return retazo
```

- [ ] **Step 4: Run test to verify it passes**

Run: la suite entera del backend (ver «Global Constraints»).
Expected: todas pasan.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/esquemas_catalogo.py backend/app/api/rutas_catalogo.py backend/tests/api/test_rutas_catalogo.py
git commit -m "feat(catalogo): retazos de medida libre que copian el precio por m2, y un formato en uso no se quita (A8)"
```

---

## Tramo 2 — La pantalla

### Task 4: Las cuentas de la lista

**Files:**
- Modify: `frontend/src/api/catalogo.ts` (`familia` en `Material`; `es_retazo` en `Formato`; `crearRetazo`, `quitarFormato`)
- Create: `frontend/src/components/ListaDeFormatos/filas.ts`
- Create: `frontend/src/components/ListaDeFormatos/filas.test.ts`

**Interfaces:**
- Produces: `interface Fila { formato: Formato; material: Material | undefined }`; `medida(formato): string`; `precioPorM2(formato): string`; `filasDeFormatos(formatos: Formato[], materiales: Material[]): Fila[]`; `familiasDe(filas: Fila[]): string[]`; `filtrarFilas(filas: Fila[], familia: string | null, busqueda: string): Fila[]`; `tildarVisibles(tildados: number[], visibles: Fila[], tildar: boolean): number[]`; `crearRetazo(formatoId: number, anchoMm: string, altoMm: string): Promise<Formato>`; `quitarFormato(formatoId: number): Promise<void>`.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/ListaDeFormatos/filas.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { Formato, Material } from "../../api/catalogo";
import { familiasDe, filasDeFormatos, filtrarFilas, medida, precioPorM2, tildarVisibles } from "./filas";

const materiales: Material[] = [
  { id: 1, nombre: "CHAPA NEGRA", espesor: "cal. 22", familia: "Chapas" },
  { id: 2, nombre: "CHAPA NEGRA", espesor: "cal. 20", familia: "Chapas" },
  { id: 3, nombre: "ACRILICO CRISTAL", espesor: "3 mm", familia: "Acrílicos" },
];

function formato(id: number, material_id: number, extra: Partial<Formato> = {}): Formato {
  return {
    id, material_id, codigo: null, ancho_mm: "1220.00", alto_mm: "2440.00", moneda: "ARS",
    costo_unidad_venta: "13720.4038", unidad_venta: "M2", precio_simulado: false, es_retazo: false, ...extra,
  };
}

const formatos = [
  formato(10, 3),
  formato(11, 1, { es_retazo: true, ancho_mm: "1000.00", alto_mm: "1000.00", codigo: "CHA0012-R" }),
  formato(12, 1, { codigo: "CHA0012" }),
  formato(13, 2, { codigo: "CHA0011" }),
];

describe("medida y precioPorM2", () => {
  it("la medida va en milímetros, sin decimales de más", () => {
    expect(medida(formato(1, 1))).toBe("1220 × 2440");
  });

  it("el precio por m² lleva la moneda y dos decimales", () => {
    expect(precioPorM2(formato(1, 1))).toBe("ARS 13.720,40");
  });

  it("sin precio por m², una raya", () => {
    expect(precioPorM2(formato(1, 1, { unidad_venta: "PLANCHA" }))).toBe("—");
    expect(precioPorM2(formato(1, 1, { costo_unidad_venta: null }))).toBe("—");
  });
});

describe("filasDeFormatos", () => {
  it("ordena por familia, material y espesor, y los retazos van debajo de su material", () => {
    expect(filasDeFormatos(formatos, materiales).map((f) => f.formato.id)).toEqual([10, 13, 12, 11]);
  });

  it("las familias son las que hay, en orden", () => {
    expect(familiasDe(filasDeFormatos(formatos, materiales))).toEqual(["Acrílicos", "Chapas"]);
  });
});

describe("filtrarFilas", () => {
  const filas = filasDeFormatos(formatos, materiales);

  it("filtra por familia", () => {
    expect(filtrarFilas(filas, "Acrílicos", "").map((f) => f.formato.id)).toEqual([10]);
  });

  it("busca todas las palabras, sin importar mayúsculas ni tildes", () => {
    expect(filtrarFilas(filas, null, "Negra 22").map((f) => f.formato.id)).toEqual([12, 11]);
    expect(filtrarFilas(filas, null, "acrílico").map((f) => f.formato.id)).toEqual([10]);
  });

  it("un número no coincide por estar adentro de una medida: «22» no trae la de cal. 20 por su 1220", () => {
    expect(filtrarFilas(filas, null, "negra 22").map((f) => f.formato.id)).not.toContain(13);
  });

  it("busca por código y por medida", () => {
    expect(filtrarFilas(filas, null, "cha0011").map((f) => f.formato.id)).toEqual([13]);
    expect(filtrarFilas(filas, null, "1000").map((f) => f.formato.id)).toEqual([11]);
  });
});

describe("tildarVisibles", () => {
  const filas = filasDeFormatos(formatos, materiales);

  it("tilda lo visible sin perder lo tildado que el filtro esconde", () => {
    expect(tildarVisibles([10], filtrarFilas(filas, "Chapas", ""), true).sort()).toEqual([10, 11, 12, 13]);
  });

  it("destilda solo lo visible", () => {
    expect(tildarVisibles([10, 12, 13], filtrarFilas(filas, "Chapas", ""), false)).toEqual([10]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (desde `frontend/`): `npx vitest run src/components/ListaDeFormatos/filas.test.ts`
Expected: FAIL con `Failed to load url ./filas`.

- [ ] **Step 3: Write minimal implementation**

En `frontend/src/api/catalogo.ts`:

1. La primera línea pasa a ser `import { apiDelete, apiGet, apiPost, ApiError } from "./client";`.
2. En `Material`, debajo de `espesor`: `familia: string;`
3. En `Formato`, debajo de `alto_mm`: `es_retazo: boolean;`
4. Debajo de `obtenerFormato`:

```ts
/** Un retazo de medida libre a partir de un formato: copia su precio por m² (A8). */
export function crearRetazo(formatoId: number, anchoMm: string, altoMm: string): Promise<Formato> {
  return apiPost<Formato>(`/formatos/${formatoId}/retazos`, { ancho_mm: anchoMm, alto_mm: altoMm });
}

export function quitarFormato(formatoId: number): Promise<void> {
  return apiDelete(`/formatos/${formatoId}`);
}
```

`frontend/src/components/ListaDeFormatos/filas.ts`:

```ts
/** Las cuentas de la lista de formatos al comparar (A8). Sin React, para
 * poder probarlas. */
import type { Formato, Material } from "../../api/catalogo";

export interface Fila {
  formato: Formato;
  material: Material | undefined;
}

const sinTildes = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const familiaDe = (fila: Fila) => fila.material?.familia ?? "Otros";

/** «1220 × 2440»: en milímetros, sin los decimales que trae la API. */
export function medida(formato: Pick<Formato, "ancho_mm" | "alto_mm">): string {
  return `${Number(formato.ancho_mm)} × ${Number(formato.alto_mm)}`;
}

/** «ARS 13.720,40», o una raya si no se vende por m². */
export function precioPorM2(formato: Pick<Formato, "moneda" | "costo_unidad_venta" | "unidad_venta">): string {
  if (formato.unidad_venta !== "M2" || formato.costo_unidad_venta === null) return "—";
  const importe = Number(formato.costo_unidad_venta).toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${formato.moneda ?? ""} ${importe}`.trim();
}

/** Por familia, material y espesor; los retazos debajo de los formatos de
 * su material; después, por medida. */
export function filasDeFormatos(formatos: Formato[], materiales: Material[]): Fila[] {
  const porId = new Map(materiales.map((material) => [material.id, material]));
  return formatos
    .map((formato) => ({ formato, material: porId.get(formato.material_id) }))
    .sort(
      (a, b) =>
        familiaDe(a).localeCompare(familiaDe(b), "es") ||
        (a.material?.nombre ?? "").localeCompare(b.material?.nombre ?? "", "es") ||
        (a.material?.espesor ?? "").localeCompare(b.material?.espesor ?? "", "es", { numeric: true }) ||
        Number(a.formato.es_retazo) - Number(b.formato.es_retazo) ||
        Number(a.formato.ancho_mm) - Number(b.formato.ancho_mm) ||
        Number(a.formato.alto_mm) - Number(b.formato.alto_mm),
    );
}

export function familiasDe(filas: Fila[]): string[] {
  return [...new Set(filas.map(familiaDe))].sort((a, b) => a.localeCompare(b, "es"));
}

/** Las filas a la vista: de la familia elegida (o todas, con `null`) y con
 * todas las palabras buscadas. Cada palabra tiene que ser el comienzo de una
 * palabra de la fila: así «22» no coincide con el «1220» de una medida. */
export function filtrarFilas(filas: Fila[], familia: string | null, busqueda: string): Fila[] {
  const buscadas = sinTildes(busqueda).split(/\s+/).filter(Boolean);
  return filas.filter((fila) => {
    if (familia !== null && familiaDe(fila) !== familia) return false;
    const palabras = sinTildes(
      [fila.material?.nombre, fila.material?.espesor, fila.formato.codigo, medida(fila.formato)].filter(Boolean).join(" "),
    )
      .split(/[\s.×]+/)
      .filter(Boolean);
    return buscadas.every((buscada) => palabras.some((palabra) => palabra.startsWith(buscada)));
  });
}

/** «Seleccionar todas»: suma o saca solo las filas a la vista, sin tocar lo
 * tildado que el filtro esconde. */
export function tildarVisibles(tildados: number[], visibles: Fila[], tildar: boolean): number[] {
  const ids = visibles.map((fila) => fila.formato.id);
  return tildar ? [...new Set([...tildados, ...ids])] : tildados.filter((id) => !ids.includes(id));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run && npx tsc -b`
Expected: todas pasan y `tsc` sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/catalogo.ts frontend/src/components/ListaDeFormatos/filas.ts frontend/src/components/ListaDeFormatos/filas.test.ts
git commit -m "feat(frontend): las cuentas de la lista de formatos: orden, filtros y busqueda (A8)"
```

### Task 5: El componente de la lista

**Files:**
- Modify: `frontend/src/hooks/useCatalogo.ts` (`useCrearRetazo`, `useQuitarFormato`)
- Create: `frontend/src/components/ListaDeFormatos/ListaDeFormatos.tsx`

**Interfaces:**
- Consumes: las funciones de `filas.ts` y `crearRetazo`/`quitarFormato` (Task 4).
- Produces: `ListaDeFormatos({ formatos, materiales, tildados, alCambiar, deshabilitada }: { formatos: Formato[]; materiales: Material[]; tildados: number[]; alCambiar: (ids: number[]) => void; deshabilitada: boolean })`.

No lleva prueba propia: el frontend no tiene pruebas de componentes, y sus cuentas están probadas en la Task 4. Se mira en el recorrido de la Task 7.

- [ ] **Step 1: Los hooks**

En `frontend/src/hooks/useCatalogo.ts`, la primera línea pasa a ser `import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";`, se agregan `crearRetazo` y `quitarFormato` a la importación de `../api/catalogo`, y al final:

```ts
/** Un retazo nuevo aparece en la lista de su material. */
export function useCrearRetazo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formatoId, anchoMm, altoMm }: { formatoId: number; anchoMm: string; altoMm: string; materialId: number }) =>
      crearRetazo(formatoId, anchoMm, altoMm),
    onSuccess: (_retazo, { materialId }) => queryClient.invalidateQueries({ queryKey: ["formatos", materialId] }),
  });
}

export function useQuitarFormato() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formatoId }: { formatoId: number; materialId: number }) => quitarFormato(formatoId),
    onSuccess: (_nada, { materialId }) => queryClient.invalidateQueries({ queryKey: ["formatos", materialId] }),
  });
}
```

- [ ] **Step 2: El componente**

`frontend/src/components/ListaDeFormatos/ListaDeFormatos.tsx`:

```tsx
import { useState } from "react";
import { ApiError } from "../../api/client";
import type { Formato, Material } from "../../api/catalogo";
import { useCrearRetazo, useQuitarFormato } from "../../hooks/useCatalogo";
import { familiasDe, filasDeFormatos, filtrarFilas, medida, precioPorM2, tildarVisibles } from "./filas";

interface ListaDeFormatosProps {
  formatos: Formato[];
  materiales: Material[];
  tildados: number[];
  alCambiar: (ids: number[]) => void;
  deshabilitada: boolean;
}

/** La lista de formatos para comparar (A8): una tabla con filtros por
 * familia y buscador, y retazos de medida libre. */
export default function ListaDeFormatos({ formatos, materiales, tildados, alCambiar, deshabilitada }: ListaDeFormatosProps) {
  const [familia, setFamilia] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState("");
  const [retazoDe, setRetazoDe] = useState<number | null>(null);
  const [ancho, setAncho] = useState("");
  const [alto, setAlto] = useState("");
  const [error, setError] = useState<string | null>(null);
  const crear = useCrearRetazo();
  const quitar = useQuitarFormato();

  const filas = filasDeFormatos(formatos, materiales);
  const visibles = filtrarFilas(filas, familia, busqueda);
  const todasVisiblesTildadas = visibles.length > 0 && visibles.every((f) => tildados.includes(f.formato.id));
  const algunaVisibleTildada = visibles.some((f) => tildados.includes(f.formato.id));
  const boton = (activo: boolean) =>
    `border rounded px-2 py-0.5 text-xs ${activo ? "bg-cut text-paper border-cut" : "border-line hover:bg-line/40"}`;

  async function alAgregarRetazo(formato: Formato) {
    setError(null);
    try {
      const nuevo = await crear.mutateAsync({ formatoId: formato.id, anchoMm: ancho, altoMm: alto, materialId: formato.material_id });
      // Se lo crea para compararlo: queda tildado.
      alCambiar([...tildados, nuevo.id]);
      setRetazoDe(null);
      setAncho("");
      setAlto("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo agregar el retazo.");
    }
  }

  async function alQuitar(formato: Formato) {
    if (!window.confirm(`¿Quitar el retazo de ${medida(formato)} mm?`)) return;
    setError(null);
    try {
      await quitar.mutateAsync({ formatoId: formato.id, materialId: formato.material_id });
      alCambiar(tildados.filter((id) => id !== formato.id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo quitar el retazo.");
    }
  }

  return (
    <div className="mb-3">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <button type="button" className={boton(familia === null)} onClick={() => setFamilia(null)}>
          Todas
        </button>
        {familiasDe(filas).map((nombre) => (
          <button key={nombre} type="button" className={boton(familia === nombre)} onClick={() => setFamilia(nombre)}>
            {nombre}
          </button>
        ))}
        <label className="text-xs ml-auto">
          Buscar{" "}
          <input
            className="border border-line rounded p-1 w-48"
            value={busqueda}
            placeholder="negra 22, 1220, CHA0012…"
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </label>
      </div>
      {error && <p className="text-sm text-conflict mb-2">{error}</p>}
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left border-b border-line">
            <th className="py-1">
              <input
                type="checkbox"
                aria-label="Seleccionar todas las que se ven"
                disabled={deshabilitada || visibles.length === 0}
                checked={todasVisiblesTildadas}
                ref={(nodo) => {
                  if (nodo) nodo.indeterminate = algunaVisibleTildada && !todasVisiblesTildadas;
                }}
                onChange={(e) => alCambiar(tildarVisibles(tildados, visibles, e.target.checked))}
              />
            </th>
            <th>Familia</th>
            <th>Material</th>
            <th>Espesor</th>
            <th>Medida (mm)</th>
            <th>Precio por m²</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {visibles.map(({ formato, material }) => (
            <tr key={formato.id} className="border-b border-line">
              <td className="py-1">
                <input
                  type="checkbox"
                  aria-label={`Comparar ${material?.nombre ?? ""} ${material?.espesor ?? ""} ${medida(formato)}`}
                  disabled={deshabilitada}
                  checked={tildados.includes(formato.id)}
                  onChange={(e) =>
                    alCambiar(e.target.checked ? [...tildados, formato.id] : tildados.filter((id) => id !== formato.id))
                  }
                />
              </td>
              <td>{material?.familia ?? "Otros"}</td>
              <td>
                {material?.nombre ?? "?"}
                {formato.es_retazo && <span className="ml-2 rounded bg-bronze/20 px-1">Retazo</span>}
              </td>
              <td>{material?.espesor ?? "—"}</td>
              <td className="font-mono">{medida(formato)}</td>
              <td className="font-mono">
                {precioPorM2(formato)}
                {formato.precio_simulado && <span className="text-conflict ml-1">(simulado)</span>}
              </td>
              <td className="text-right whitespace-nowrap">
                {formato.es_retazo ? (
                  <button type="button" className="underline" disabled={deshabilitada} onClick={() => void alQuitar(formato)} aria-label="Quitar el retazo">
                    ✕
                  </button>
                ) : retazoDe === formato.id ? (
                  <span className="inline-flex items-center gap-1">
                    <input className="border border-line rounded p-0.5 w-16" aria-label="Ancho del retazo (mm)" placeholder="ancho" value={ancho} onChange={(e) => setAncho(e.target.value)} />
                    ×
                    <input className="border border-line rounded p-0.5 w-16" aria-label="Alto del retazo (mm)" placeholder="alto" value={alto} onChange={(e) => setAlto(e.target.value)} />
                    <button type="button" className="underline" disabled={crear.isPending} onClick={() => void alAgregarRetazo(formato)}>
                      Agregar
                    </button>
                    <button type="button" className="underline" onClick={() => setRetazoDe(null)}>
                      Cancelar
                    </button>
                  </span>
                ) : (
                  <button type="button" className="underline" disabled={deshabilitada} onClick={() => setRetazoDe(formato.id)}>
                    Retazo…
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {visibles.length === 0 && filas.length > 0 && <p className="text-sm mt-2">Ningún formato coincide con el filtro.</p>}
    </div>
  );
}
```

- [ ] **Step 3: Comprobar que compila**

Run (desde `frontend/`): `npx vitest run && npx tsc -b`
Expected: todas pasan y `tsc` sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useCatalogo.ts frontend/src/components/ListaDeFormatos/ListaDeFormatos.tsx
git commit -m "feat(frontend): la lista de formatos en tabla, con filtros, buscador y retazos (A8)"
```

### Task 6: La lista en la comparación de Grupos

**Files:**
- Modify: `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`

**Interfaces:**
- Consumes: `ListaDeFormatos` (Task 5).

Sin prueba propia (ver la Task 5). Se mira en el recorrido de la Task 7.

- [ ] **Step 1: Reemplazar las casillas por la tabla**

En `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`:

1. Agregar la importación `import ListaDeFormatos from "../../components/ListaDeFormatos/ListaDeFormatos";`.
2. Reemplazar el bloque que va desde `<label className="text-xs flex items-center gap-1 mb-2 font-medium cursor-pointer">` (el de «Seleccionar todas») hasta el `</div>` que cierra `<div className="flex flex-wrap gap-2 mb-3">` (las casillas de cada formato) por:

```tsx
              {cargando && <p className="text-sm mb-3">Cargando materiales y formatos…</p>}
              {!cargando && !errorCatalogo && formatos.length === 0 && <p className="text-sm mb-3">No hay formatos en el catálogo.</p>}
              {!cargando && formatos.length > 0 && (
                <ListaDeFormatos
                  formatos={formatos}
                  materiales={materiales}
                  tildados={candidatos}
                  alCambiar={setCandidatos}
                  deshabilitada={comparando}
                />
              )}
```

3. La función `etiquetaFormato` y la importación `import type { Formato } from "../../api/catalogo";` quedan sin uso: se borran.

- [ ] **Step 2: Comprobar que compila**

Run (desde `frontend/`): `npx vitest run && npx tsc -b && npm run build`
Expected: todas pasan, sin errores de tipos, y compila.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/TrabajoWorkspace/GruposTab.tsx
git commit -m "feat(frontend): la comparacion de chapas elige desde la lista con filtros (A8)"
```

---

## Tramo 3 — Recorrido y cierre

### Task 7: Recorrido en el navegador y documentos

**Files:**
- Modify: `docs/plan/PLAN-MAESTRO.md`, `docs/MAPA-DEL-PROYECTO.md`, `docs/BITACORA.md`, `docs/historico/A8-lista-de-materiales-y-retazos/diseno.md`, `docs/historico/A8-lista-de-materiales-y-retazos/plan.md`

- [ ] **Step 1: Las suites enteras**

Run: la suite del backend (ver «Global Constraints») y, desde `frontend/`, `npx vitest run && npm run build`.
Expected: todas pasan y compila.

- [ ] **Step 2: Recorrido con Chrome sin ventana, sobre una copia de la base**

Mirar antes quién escucha en 8000 y 5173 (si hay algo, es de Enzo). Copiar la base con el respaldo de SQLite a `backend/local/copia-a8-<fecha>/`, aplicarle `alembic upgrade head` con `CARTELERIA_DATOS` apuntando a la copia (la migración de la familia corre sobre los datos reales), y levantar el backend contra la copia y el frontend. En el trabajo «Complejo», pestaña Grupos, «Comparar formatos»:

1. Aparecen los botones de familia (Acrílicos, Alto impacto, Chapas, Corrugado, Policarbonato) y la tabla. Filtrar por Chapas: solo chapas.
2. Buscar «negra 22»: solo las chapas negras cal. 22.
3. «Retazo…» en la chapa negra cal. 22 de 1220 × 2440, escribir 1000 × 1000, «Agregar»: aparece una fila «Retazo», tildada, con el mismo precio por m².
4. Tildar también la chapa entera y comparar con el motor rectangular: la tabla trae las dos filas, y el retazo cuesta su área por su precio por m² por chapa.
5. «Usar este» en el retazo; en la pestaña Costeo, la línea de material sale del retazo.
6. Volver a Grupos, intentar quitar ese retazo con la ✕: dice que lo usa el grupo y no lo quita.

Capturas de cada paso. Al terminar, cerrar solo los procesos propios y borrar la copia.

- [ ] **Step 3: Documentos**

- `docs/plan/PLAN-MAESTRO.md` §7, tabla del seccionado: la fila «No hay tope para chapas chicas pero válidas, y el selector de chapa del panel lista todo el catálogo» suma al final, en «Depende de»: «La tabla de A8 (`ListaDeFormatos`) sirve para el selector».
- `docs/MAPA-DEL-PROYECTO.md`, fila **Catálogo**: «Qué hay» suma «, familia de cada material, y retazos de medida libre que copian el precio por m² (A8)».
- `docs/BITACORA.md`: en la entrada del día, un bloque «Lista de materiales y retazos (A8)».
- `diseno.md` y `plan.md`: el **Estado** pasa a «construido el AAAA-MM-DD», y al final de `plan.md` va «## Desvíos».

- [ ] **Step 4: Commit**

```bash
git add docs/plan/PLAN-MAESTRO.md docs/MAPA-DEL-PROYECTO.md docs/BITACORA.md docs/historico/A8-lista-de-materiales-y-retazos
git commit -m "docs: lista de materiales y retazos (A8) construida"
```

---

## Desvíos

Lo que se hizo distinto de lo escrito arriba, el 2026-10-14.

- **Un agregado al diseño, ya anotado arriba:** `DELETE /formatos/{id}` rechaza con 409 un formato que usa un grupo, para cualquier formato.
- **Task 3: la prueba del formato que no existe pasaba antes del cambio,** con 404 porque la ruta tampoco existía. Después del cambio da 404 por el motivo correcto; no sirvió para verla fallar.
- **Task 7, el recorrido usó además un trabajo chico armado en la copia** (seis piezas de 300 × 200 mm, `backend/local/herramientas-a8-2026-10-14/armar_trabajo_chico.py`, fuera de git): las piezas de «Complejo» no entran en 1 m × 1 m y la comparación con el retazo solo habría dicho «hay que seccionar». Con «Complejo» se probaron el filtro y la búsqueda.
- **Task 7, el guion del recorrido se corrigió tres veces** (buscaba la medida del retazo con decimales, cambiaba el motor después de retomar la comparación, y buscaba «lista» en la pantalla en lugar de preguntarle al servidor). Ninguna fue una falla de la pantalla.
- **La suite del backend no se volvió a correr entera en la Task 7:** desde la Task 3 (705 en verde) no cambió ningún archivo del backend.
- **El componente no avisa con un callback cuando se crea o se quita un retazo,** como decía §5.3 del diseño: lo resuelve adentro, con los hooks del catálogo y `alCambiar`. En la pantalla no cambia nada.

**La revisión aparte (2026-10-14): «con arreglos», nada crítico.** Se arregló, cada cosa con una prueba que falló primero:

- **Los retazos no cuentan para reconocer hojas al leer un DXF** (`_formatos_del_catalogo`): crear un retazo de 1000 × 1000 hacía que un cartel de esa medida se leyera como hoja en los diseños que vinieran después.
- **El buscador normaliza igual lo buscado y la fila:** la coma decimal como punto y sin el punto final de «cal.». Antes no encontraba «cal. 22», «2,4» ni «0.5 mm», que es como se leen en la tabla.
- **La medida de un retazo se valida en la pantalla** (`medidaDeRetazo`: solo cifras y un decimal, con coma o punto, mayor que 0 y hasta 10 000): una medida mal escrita mostraba «Error 422». De paso, «1e3» ya no llega al servidor.
- **Dos decisiones de Enzo que agregan al diseño** (§3 y §5.2): quitar un retazo que usa un grupo lo esconde (`disponible = False`) en lugar de rechazarlo, y la lista no muestra lo que no está disponible; y un retazo sigue el precio de su chapa cuando `PATCH /formatos/{id}` cambia la moneda, el precio o la marca de simulado.

**Lo que quedó anotado y no se hizo:**

- En la comparación y en el costeo, la medida de un retazo se escribe como se guardó («1000×1000 mm») y la de una chapa del catálogo con decimales («1220.00×2440.00 mm»).
- Después de retomar una comparación, los formatos que se habían tildado no vuelven tildados: para comparar de nuevo hay que tildarlos otra vez.
- El código del formato no es una columna de la tabla; se encuentra con el buscador.
- **Se puede perder un tilde mientras se crea o se quita un retazo:** `alCambiar` usa los tildados de antes de que vuelva el pedido. Pasa solo si se tilda otra fila en ese instante.
- **El 409 de quitar una chapa entera en uso nombra los grupos, pero no el trabajo.** Desde la pantalla no se llega: la ✕ está solo en los retazos.
- **«Retazo…» aparece también en filas sin precio por m²;** recién al «Agregar» llega el aviso. En el catálogo de Enzo todas se venden por m².
- **«Agregar» no se deshabilita mientras se compara;** solo «Retazo…».
- **Una medida de 1 se acepta como 1 mm,** aunque se haya pensado en metros. No hay un mínimo.
- **La familia no se normaliza:** «chapas» y «Chapas» saldrían como dos botones, y una de solo espacios se acepta. Hoy la familia se cambia solo por la API.
- **El buscador no encuentra «retazo»** (la marca no está entre las palabras de la fila) **ni «1220x2440» con x.**
- **`DELETE /materiales/{id}` deja sin chapa a los grupos que usaban sus formatos.** Ya pasaba antes de A8; desde la pantalla no se llega.
- **Un `insert(Material).values([...])` del ORM con varias filas falla** con el valor por defecto de la familia (límite de SQLAlchemy 2.0.41). Nada del proyecto inserta así.
- **Lo que la revisión dejó para decidir más adelante:** el selector de chapa del panel de seccionado lista los retazos sin marcarlos; pedir por la API un retazo de un retazo da el código «X-R-R»; al renombrar un material la familia no se recalcula (pisaría una corrección a mano); seccionar contra un retazo muy chico puede ser lento (ya está en el plan maestro); y llevar stock de retazos queda afuera del diseño.
