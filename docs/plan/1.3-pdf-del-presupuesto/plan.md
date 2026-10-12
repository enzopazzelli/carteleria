# 1.3 · PDF del presupuesto — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado:** **escrito el 2026-10-12, a la espera de la revisión de Enzo.** Sin ejecutar.
>
> **El código de este plan está probado, con un límite.** El 2026-10-12 los bloques de las Tareas 1 a 9 se aplicaron, tal como están escritos acá, sobre una copia del backend y otra del frontend fuera del repositorio. Se aplicó todo junto y se probó el estado final: backend **492 pruebas en verde** (423 antes), con el PDF generado de verdad y la migración de ida y vuelta; frontend **60** (40 antes) y `npm run build` sin errores. **No se probó:** cada tarea por separado (las corridas de «falla primero» son las esperadas, no las vistas), el recorrido en pantalla del tramo 3 (compila, nadie lo usó en un navegador), el paso de GitHub de la Tarea 5 y el enlace provisorio de la Tarea 6.

**Goal:** Que un presupuesto se baje desde la pestaña Costeo como un PDF para el cliente, con un importe por ítem, y que antes de bajarlo se puedan cambiar el texto y el precio de cada ítem y fijar el total.

**Architecture:** Tres piezas nuevas en `backend/app/services/presupuesto/`, cada una con una sola tarea. `totales.py` es la cuenta (se muda desde el archivo de rutas y se amplía): de los costos saca el precio de cada ítem, el subtotal, el IVA y el total, y la lista de lo que falta. `documento.py` arma lo que ve el cliente, sin ningún campo de costo ni de margen. `pdf.py` vuelca ese documento en una plantilla HTML y la convierte con WeasyPrint. La pantalla lee todo de la respuesta de desglose que ya existe y guarda cada campo al salir de él.

**Tech Stack:** Python 3.11 (CI) y 3.13 (local), FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, WeasyPrint 70, Jinja2 3.1, pypdf (solo pruebas) · React 18, TypeScript, Vite, vitest.

**Spec:** [`diseno.md`](diseno.md), en esta misma carpeta.

## Global Constraints

- Se trabaja en la carpeta `.claude/worktrees/pdf-presupuesto`, rama `worktree-pdf-presupuesto`. **No tocar** `backend/app/services/ingesta/`, `backend/app/api/rutas_importacion.py` ni `esquemas_importacion.py`: son de la otra línea de trabajo en curso (la lectura del DXF).
- **Un paso por vez, con el ok de Enzo.** Al terminar cada tarea se le muestra el resultado y se espera su ok antes del commit y antes de empezar la siguiente.
- Commits **sin** la línea `Co-Authored-By` (regla del proyecto), con mensajes sin acentos como los del historial.
- El CI corre con Python 3.11: nada que exista solo en 3.12 o 3.13. Los módulos nuevos empiezan con `from __future__ import annotations`.
- Valores de negocio por ID de `REGISTRO.md`, nunca copiados: validez `PAR-11`, margen `PAR-12`, IVA `PAR-13`, moneda `PAR-14`, redondeo `PAR-16`.
- **Los textos que lee una persona van sin códigos:** la lista de lo que falta y los errores de pantalla no nombran ningún `PAR-xx`.
- En Windows, **no editar con `sed -i`**: pasa los archivos de CRLF a LF. Editar con el editor.
- Probar siempre contra datos temporales (`CARTELERIA_DATOS=<carpeta temporal>`), nunca contra `backend/local/` de la carpeta principal. Antes de levantar la app, mirar quién escucha en los puertos 8000 y 5173.
- Generar un PDF en Windows necesita `WEASYPRINT_DLL_DIRECTORIES` en el entorno (Tarea 5). Sin la variable, las pruebas marcadas `pango` **se saltean**: correr siempre con `-rs` y no dar por pasada una prueba salteada.
- Comandos de prueba: backend `cd backend && python -m pytest -q -rs`; frontend `cd frontend && npm run build && npm test`.

## Review Focus

1. **Descargar justo después de editar un campo.** El guardado sale al perder el foco, un instante antes del clic en «Descargar PDF». El PDF tiene que traer lo recién escrito. Lo resuelve `ultimoGuardado` en la Tarea 8. El frontend no tiene pruebas con navegador, así que no hay prueba automática: es el primer punto del recorrido a mano de la Tarea 10.
2. **Un importe escrito con punto.** «1.400» es mil cuatrocientos y «12.5» es doce y medio. Si se lee al revés, un precio queda mil veces más chico sin que nada avise. Prueba en la Tarea 7.
3. **Un campo que se deja vacío.** La validez, el cliente o la moneda vacíos llegaban a la base como `null` y volvían como error 500. Prueba en la Tarea 3.
4. **Un presupuesto de muchos renglones.** Ocupa más de una hoja: no se puede perder ningún ítem ni partir el bloque de totales. Prueba en la Tarea 5.
5. **Un «<» o un «&» en el nombre del cliente o en el texto de un ítem.** No tiene que romper la hoja ni meter HTML en ella. Prueba en la Tarea 5.

---

## Archivos

| Archivo | Qué hace |
|---|---|
| `backend/app/modelos/presupuesto.py` | Tres columnas nuevas: `total_fijado`, `texto_cliente`, `precio_cliente` |
| `backend/alembic/versions/7f91bcd3ef15_presupuesto_para_el_cliente.py` | **Nuevo.** La migración de esas columnas |
| `backend/app/services/presupuesto/__init__.py` | **Nuevo.** |
| `backend/app/services/presupuesto/totales.py` | **Nuevo.** La cuenta: precio de cada ítem, subtotal, IVA, total y lo que falta |
| `backend/app/services/presupuesto/documento.py` | **Nuevo.** El documento del cliente, sin costos ni márgenes |
| `backend/app/services/presupuesto/pdf.py` | **Nuevo.** Documento → HTML → PDF |
| `backend/app/services/presupuesto/plantillas/presupuesto.html` | **Nuevo.** La plantilla |
| `backend/app/services/presupuesto/plantillas/fuentes/` | **Nuevo.** Source Sans 3 (dos archivos) y su licencia |
| `backend/app/api/esquemas_presupuesto.py` | Los campos nuevos, `LineaClienteActualizar`, `ItemClienteLeer` |
| `backend/app/api/rutas_presupuesto.py` | La cuenta sale de acá; rutas para lo del cliente y para el PDF |
| `backend/tests/conftest.py` | **Nuevo.** La marca `pango` y cuándo se saltea |
| `backend/pytest.ini` | Declara la marca |
| `backend/tests/services/presupuesto/test_totales.py`, `test_documento.py`, `test_pdf.py` | **Nuevos.** |
| `backend/tests/api/test_rutas_presupuesto.py` | Las pruebas de API de las Tareas 1, 3 y 6 |
| `backend/requirements.txt`, `backend/requirements-dev.txt` | `weasyprint`, `jinja2`; `pypdf` |
| `.github/workflows/ci.yml` | Instala Pango |
| `frontend/src/routes/TrabajoWorkspace/importes.ts` y `importes.test.ts` | **Nuevos.** Leer y mostrar importes |
| `frontend/src/routes/TrabajoWorkspace/PresupuestoClienteSeccion.tsx` | **Nuevo.** La sección de Costeo |
| `frontend/src/api/client.ts`, `api/presupuestos.ts`, `hooks/usePresupuestos.ts` | Lo que la sección le pide a la API |
| `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx` | Muestra la sección; editar y borrar líneas |
| `docs/GUIA-PRUEBAS-LOCALES.md`, `docs/REGISTRO.md`, `docs/plan/PLAN-MAESTRO.md`, `docs/MAPA-DEL-PROYECTO.md`, `docs/BITACORA.md` | Documentos |

---

## Tramo 1 — Reglas y datos

Al terminar este tramo no cambia nada a la vista: Costeo muestra los mismos totales, calculados por la cuenta nueva, y la API ya sabe guardar lo del cliente.

### Task 1: Las tres columnas nuevas

**Files:**
- Modify: `backend/app/modelos/presupuesto.py`
- Modify: `backend/app/api/esquemas_presupuesto.py`
- Create: `backend/alembic/versions/7f91bcd3ef15_presupuesto_para_el_cliente.py`
- Test: `backend/tests/api/test_rutas_presupuesto.py`

**Interfaces:**
- Produces: `Presupuesto.total_fijado: Decimal | None`; `LineaCosto.texto_cliente: str | None`; `LineaCosto.precio_cliente: Decimal | None`. Los tres aparecen en `PresupuestoLeer` y `LineaCostoLeer`.
- Produces (para las pruebas de las Tareas 3 y 6): la función de prueba `_linea_libre(cliente, presupuesto_id, descripcion, precio, rubro="OTRO") -> dict`.

- [ ] **Step 1: Escribir la prueba que falla**

Agregar al final de `backend/tests/api/test_rutas_presupuesto.py`:

```python
# --- Lo que lee el cliente (1.3: docs/plan/1.3-pdf-del-presupuesto/diseno.md) ---


def _linea_libre(cliente, presupuesto_id: int, descripcion: str, precio: str, rubro: str = "OTRO") -> dict:
    respuesta = cliente.post(
        f"/presupuestos/{presupuesto_id}/lineas-costo",
        json={"rubro": rubro, "descripcion": descripcion, "cantidad": "1", "precio_unitario": precio},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_presupuesto_y_linea_nacen_sin_nada_escrito_para_el_cliente(cliente):
    presupuesto = _crear_presupuesto(cliente)
    linea = _linea_libre(cliente, presupuesto["id"], "Flete", "80000", rubro="FLETE")

    assert presupuesto["total_fijado"] is None
    assert linea["texto_cliente"] is None
    assert linea["precio_cliente"] is None
```

- [ ] **Step 2: Correrla y ver que falla**

Run: `cd backend && python -m pytest -q tests/api/test_rutas_presupuesto.py -k nacen_sin_nada`
Expected: FAIL con `KeyError: 'total_fijado'`.

- [ ] **Step 3: Agregar las columnas al modelo**

En `backend/app/modelos/presupuesto.py`:

Reemplazar:

```python
    iva_pct: Mapped[Decimal | None] = mapped_column(Milimetros(), default=Decimal("21"))

    cliente: Mapped[Cliente] = relationship(back_populates="presupuestos")
```

por:

```python
    iva_pct: Mapped[Decimal | None] = mapped_column(Milimetros(), default=Decimal("21"))
    #: El total final, con IVA, escrito a mano (`docs/plan/1.3-pdf-del-
    #: presupuesto/diseno.md §5`). `None` = el total sale de la suma de
    #: los ítems más IVA. Con un valor, todos los ítems se ajustan para
    #: sumar ese total; lo que se escribió a mano en cada línea no se pisa.
    total_fijado: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)

    cliente: Mapped[Cliente] = relationship(back_populates="presupuestos")
```

Reemplazar:

```python
    override_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="lineas")
```

por:

```python
    override_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    #: Lo que lee el cliente en el presupuesto (`diseno.md §5` de 1.3).
    #: Son una capa encima del costo, igual que el override: `None` usa
    #: la descripción de la línea y el costo más el margen. El costo de
    #: la línea no cambia por ninguno de los dos.
    texto_cliente: Mapped[str | None] = mapped_column(String(300), default=None)
    #: Sin IVA, en la moneda del presupuesto.
    precio_cliente: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="lineas")
```

- [ ] **Step 4: Mostrarlas en la API**

En `backend/app/api/esquemas_presupuesto.py`:

Reemplazar:

```python
    margen_pct: Decimal | None
    iva_pct: Decimal | None
    creado_en: datetime
    actualizado_en: datetime


# --- Líneas de costo (paso 2
```

por:

```python
    margen_pct: Decimal | None
    iva_pct: Decimal | None
    total_fijado: Decimal | None
    creado_en: datetime
    actualizado_en: datetime


# --- Líneas de costo (paso 2
```

Reemplazar:

```python
    valor_override: Decimal | None
    override_por: str | None
    override_en: datetime | None


class LineaCostoOverride(BaseModel):
```

por:

```python
    valor_override: Decimal | None
    override_por: str | None
    override_en: datetime | None
    texto_cliente: str | None
    precio_cliente: Decimal | None


class LineaCostoOverride(BaseModel):
```

- [ ] **Step 5: Correr la prueba y ver que pasa**

Run: `cd backend && python -m pytest -q tests/api/test_rutas_presupuesto.py -k nacen_sin_nada`
Expected: `1 passed`. Las pruebas arman la base con `create_all`, por eso pasan sin la migración.

- [ ] **Step 6: Escribir la migración**

Antes, comprobar de dónde sale: `cd backend && python -m alembic heads` tiene que decir `5ecc10ad0a5a (head)`. Si dice otra cosa, es que la otra rama fusionó antes una migración: usar ese identificador en `down_revision` y en el renglón `Revises`.

Crear `backend/alembic/versions/7f91bcd3ef15_presupuesto_para_el_cliente.py`:

```python
"""presupuesto para el cliente

Revision ID: 7f91bcd3ef15
Revises: 5ecc10ad0a5a
Create Date: 2026-10-12 20:15:52.214026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Los tipos propios (Milimetros) aparecen por nombre completo en las
# migraciones autogeneradas; sin este import, `upgrade` falla con
# NameError. Va en la plantilla para que valga para todas.
import app.modelos.tipos


# revision identifiers, used by Alembic.
revision: str = '7f91bcd3ef15'
down_revision: Union[str, Sequence[str], None] = '5ecc10ad0a5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('lineas_costo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('texto_cliente', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('precio_cliente', app.modelos.tipos.Milimetros(length=40), nullable=True))

    with op.batch_alter_table('presupuestos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_fijado', app.modelos.tipos.Milimetros(length=40), nullable=True))

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('presupuestos', schema=None) as batch_op:
        batch_op.drop_column('total_fijado')

    with op.batch_alter_table('lineas_costo', schema=None) as batch_op:
        batch_op.drop_column('precio_cliente')
        batch_op.drop_column('texto_cliente')

    # ### end Alembic commands ###
```

- [ ] **Step 7: Probar la migración de ida y vuelta, sobre una base temporal**

Con `CARTELERIA_DATOS` apuntando a una carpeta temporal vacía, desde `backend/`:

```bash
python -m alembic upgrade head
python -m alembic check
python -m alembic downgrade -1
python -m alembic upgrade head
```

Expected: el primer `upgrade` termina con `Running upgrade 5ecc10ad0a5a -> 7f91bcd3ef15, presupuesto para el cliente`; `check` responde `No new upgrade operations detected.`; el `downgrade` y el segundo `upgrade` no dan error.

- [ ] **Step 8: Correr toda la suite**

Run: `cd backend && python -m pytest -q -rs`
Expected: `424 passed`.

- [ ] **Step 9: Commit** (con el ok de Enzo)

```bash
git add backend/app/modelos/presupuesto.py backend/app/api/esquemas_presupuesto.py backend/alembic/versions/7f91bcd3ef15_presupuesto_para_el_cliente.py backend/tests/api/test_rutas_presupuesto.py
git commit -m "feat(presupuesto): columnas para el texto, el precio y el total del cliente"
```

---

### Task 2: La cuenta

**Files:**
- Create: `backend/app/services/presupuesto/__init__.py`
- Create: `backend/app/services/presupuesto/totales.py`
- Test: `backend/tests/services/presupuesto/test_totales.py`

**Interfaces:**
- Consumes: las columnas de la Tarea 1.
- Produces: `calcular(presupuesto: Presupuesto, lineas: list[LineaCosto]) -> Cuenta` y `redondear(valor: Decimal) -> Decimal`.
- Produces: `Cuenta` con `moneda`, `items: list[ItemCuenta]`, `subtotales_por_rubro`, `costo_total`, `margen_pct`, `monto_margen`, `margen_resultante_pct`, `precio_venta`, `iva_pct`, `monto_iva`, `total`, `total_fijado`, `advertencias: list[str]`, `faltantes: list[str]`.
- Produces: `ItemCuenta` con `linea_id`, `rubro`, `texto`, `costo`, `precio_base`, `a_mano`, `precio_final`.

`rutas_presupuesto.py` sigue usando su propia cuenta hasta la Tarea 3: en esta tarea las dos conviven.

- [ ] **Step 1: Escribir las pruebas que fallan**

Crear `backend/tests/services/presupuesto/test_totales.py` (la carpeta no lleva `__init__.py`, como las demás de `tests/services/`):

```python
"""La cuenta del presupuesto (`diseno.md §5` de 1.3), sin base ni HTTP.

El ejemplo de cuatro líneas es el de la tabla del §5.2 del diseño: si
una de estas pruebas cambia, esa tabla también.
"""
from __future__ import annotations

from decimal import Decimal as D

from app.modelos.presupuesto import LineaCosto, Presupuesto
from app.services.presupuesto.totales import calcular


def _presupuesto(**extra) -> Presupuesto:
    datos = {
        "id": 1,
        "codigo": "P-2026-0001",
        "cliente_id": 1,
        "validez_dias": 15,
        "moneda": "ARS",
        "margen_pct": D(30),
        "iva_pct": D(21),
        "total_fijado": None,
    } | extra
    return Presupuesto(**datos)


def _linea(n: int, descripcion: str, costo: str | None, **extra) -> LineaCosto:
    datos = {
        "id": n,
        "presupuesto_id": 1,
        "rubro": "OTRO",
        "descripcion": descripcion,
        "valor_calculado": None if costo is None else D(costo),
        "valor_override": None,
        "moneda": "ARS",
        "texto_cliente": None,
        "precio_cliente": None,
    } | extra
    return LineaCosto(**datos)


def _ejemplo(**instalacion) -> list[LineaCosto]:
    return [
        _linea(1, "Chapa", "400000"),
        _linea(2, "Mano de obra", "300000"),
        _linea(3, "Flete", "80000"),
        _linea(4, "Instalación", "120000", **instalacion),
    ]


def _finales(cuenta) -> list[D | None]:
    return [item.precio_final for item in cuenta.items]


# --- Las tres columnas del ejemplo ----------------------------------------


def test_sin_tocar_nada_cada_item_es_su_costo_mas_el_margen():
    cuenta = calcular(_presupuesto(), _ejemplo())

    assert _finales(cuenta) == [D("520000.00"), D("390000.00"), D("104000.00"), D("156000.00")]
    assert cuenta.costo_total == D("900000.00")
    assert cuenta.precio_venta == D("1170000.00")
    assert cuenta.monto_iva == D("245700.00")
    assert cuenta.total == D("1415700.00")
    assert cuenta.monto_margen == D("270000.00")
    assert cuenta.margen_resultante_pct == D("30.00")
    assert cuenta.faltantes == []
    assert cuenta.advertencias == []


def test_un_precio_a_mano_se_respeta_y_los_demas_no_cambian():
    cuenta = calcular(_presupuesto(), _ejemplo(precio_cliente=D("150000")))

    assert _finales(cuenta) == [D("520000.00"), D("390000.00"), D("104000.00"), D("150000.00")]
    assert [item.a_mano for item in cuenta.items] == [False, False, False, True]
    assert cuenta.precio_venta == D("1164000.00")
    assert cuenta.monto_iva == D("244440.00")
    assert cuenta.total == D("1408440.00")
    assert cuenta.margen_resultante_pct == D("29.33")


def test_el_total_fijado_ajusta_todos_los_items_tambien_los_escritos_a_mano():
    cuenta = calcular(
        _presupuesto(total_fijado=D("1400000")), _ejemplo(precio_cliente=D("150000"))
    )

    assert cuenta.total == D("1400000.00")
    assert cuenta.precio_venta == D("1157024.79")
    assert cuenta.monto_iva == D("242975.21")
    assert _finales(cuenta) == [D("516883.92"), D("387662.95"), D("103376.79"), D("149101.13")]
    assert sum(_finales(cuenta)) == cuenta.precio_venta, "el documento tiene que sumar"
    assert cuenta.precio_venta + cuenta.monto_iva == cuenta.total
    assert cuenta.margen_resultante_pct == D("28.56")
    # Lo que se escribió a mano sigue ahí: es el precio base, sin ajustar.
    assert cuenta.items[3].precio_base == D("150000.00")
    assert cuenta.faltantes == []


# --- Redondeo --------------------------------------------------------------


def test_con_total_fijado_el_centavo_que_sobra_va_al_item_mas_grande_y_en_empate_al_primero():
    lineas = [_linea(1, "A", "100"), _linea(2, "B", "100"), _linea(3, "C", "100")]

    cuenta = calcular(_presupuesto(margen_pct=D(0), iva_pct=D(0), total_fijado=D("100")), lineas)

    assert _finales(cuenta) == [D("33.34"), D("33.33"), D("33.33")]


def test_sin_total_fijado_el_centavo_no_toca_un_precio_escrito_a_mano():
    # Los dos calculados redondean para arriba y la suma se pasa un
    # centavo. El ítem más grande es el escrito a mano: no se toca.
    lineas = [
        _linea(1, "A", "500", precio_cliente=D("1000.00")),
        _linea(2, "B", "333.335"),
        _linea(3, "C", "333.335"),
    ]

    cuenta = calcular(_presupuesto(margen_pct=D(0)), lineas)

    assert cuenta.precio_venta == D("1666.67")
    assert _finales(cuenta) == [D("1000.00"), D("333.33"), D("333.34")]


def test_sin_precios_a_mano_ni_total_fijado_el_subtotal_y_el_total_dan_lo_mismo_que_antes():
    # La cuenta de antes: costo total, más margen, más IVA, y recién ahí redondear.
    costo, margen, iva = D("1234.567"), D("33.3"), D("21")
    precio_venta = costo * (1 + margen / 100)

    cuenta = calcular(_presupuesto(margen_pct=margen), [_linea(1, "A", "1234.567")])

    assert cuenta.precio_venta == precio_venta.quantize(D("0.01"))
    assert cuenta.total == (precio_venta * (1 + iva / 100)).quantize(D("0.01"))


# --- Qué cuenta como incompleto (§5.4) -------------------------------------


def test_sin_lineas_falta_todo():
    cuenta = calcular(_presupuesto(), [])

    assert cuenta.faltantes == ["El presupuesto no tiene ninguna línea."]
    assert cuenta.items == []
    assert cuenta.costo_total == D("0.00")


def test_una_linea_sin_costo_queda_afuera_y_se_dice_cual():
    cuenta = calcular(_presupuesto(), [_linea(1, "Chapa", None), _linea(2, "Flete", "80000")])

    assert cuenta.faltantes == ["«Chapa» no tiene costo."]
    assert _finales(cuenta) == [None, D("104000.00")]
    assert cuenta.costo_total == D("80000.00")


def test_un_precio_a_mano_no_reemplaza_al_costo_que_falta():
    cuenta = calcular(_presupuesto(), [_linea(1, "Chapa", None, precio_cliente=D("500000"))])

    assert cuenta.faltantes == ["«Chapa» no tiene costo."]
    assert cuenta.items[0].precio_final is None
    assert cuenta.items[0].a_mano is True


def test_una_linea_en_otra_moneda_queda_afuera():
    cuenta = calcular(_presupuesto(), [_linea(1, "Chapa", "400000", moneda="USD")])

    assert cuenta.faltantes == ["«Chapa» está en USD y el presupuesto es en ARS."]
    assert cuenta.costo_total == D("0.00")


def test_sin_iva_no_hay_total():
    cuenta = calcular(_presupuesto(iva_pct=None), _ejemplo())

    assert cuenta.faltantes == ["Falta cargar el IVA."]
    assert cuenta.precio_venta == D("1170000.00")
    assert cuenta.total is None
    assert cuenta.monto_iva is None


def test_sin_margen_falta_si_algun_item_no_tiene_precio_a_mano():
    cuenta = calcular(_presupuesto(margen_pct=None), _ejemplo(precio_cliente=D("150000")))

    assert cuenta.faltantes == ["Falta cargar el margen, o un precio a mano en cada ítem."]
    assert cuenta.precio_venta is None
    assert _finales(cuenta) == [None, None, None, None]


def test_sin_margen_alcanza_si_todos_los_items_tienen_precio_a_mano():
    lineas = [
        _linea(1, "Chapa", "400000", precio_cliente=D("500000")),
        _linea(2, "Flete", "80000", precio_cliente=D("100000")),
    ]

    cuenta = calcular(_presupuesto(margen_pct=None), lineas)

    assert cuenta.faltantes == []
    assert cuenta.precio_venta == D("600000.00")
    assert cuenta.total == D("726000.00")
    assert cuenta.margen_resultante_pct == D("25.00")


def test_con_total_fijado_y_todos_los_items_en_cero_no_hay_como_repartir():
    cuenta = calcular(_presupuesto(total_fijado=D("1000")), [_linea(1, "Bonificado", "0")])

    assert cuenta.faltantes == ["No se puede repartir el total fijado: todos los ítems valen cero."]
    assert cuenta.items[0].precio_final is None


# --- Lo que se ve adentro --------------------------------------------------


def test_avisa_si_el_precio_queda_por_debajo_del_costo_pero_no_lo_impide():
    cuenta = calcular(_presupuesto(total_fijado=D("500000")), _ejemplo())

    assert "El precio de venta queda por debajo del costo." in cuenta.advertencias
    assert cuenta.faltantes == []
    assert cuenta.monto_margen < 0


def test_el_texto_para_el_cliente_reemplaza_a_la_descripcion():
    lineas = [
        _linea(1, "Chapa negra cal. 20 — 1220 × 2440", "400000", texto_cliente="Cartel frontal"),
        _linea(2, "Flete", "80000", texto_cliente=""),
    ]

    cuenta = calcular(_presupuesto(), lineas)

    assert [item.texto for item in cuenta.items] == ["Cartel frontal", "Flete"]


def test_el_costo_es_el_override_si_lo_hay():
    cuenta = calcular(_presupuesto(), [_linea(1, "Chapa", "400000", valor_override=D("300000"))])

    assert cuenta.items[0].costo == D("300000")
    assert cuenta.items[0].precio_final == D("390000.00")


def test_calcular_no_modifica_lo_que_recibe():
    presupuesto = _presupuesto(total_fijado=D("1400000"))
    lineas = _ejemplo(precio_cliente=D("150000"))

    calcular(presupuesto, lineas)

    assert lineas[3].precio_cliente == D("150000")
    assert lineas[0].valor_calculado == D("400000")
    assert presupuesto.total_fijado == D("1400000")
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `cd backend && python -m pytest -q tests/services/presupuesto/test_totales.py`
Expected: error al juntar las pruebas, `ModuleNotFoundError: No module named 'app.services.presupuesto'`.

- [ ] **Step 3: Escribir la cuenta**

Crear `backend/app/services/presupuesto/__init__.py`:

```python
"""El presupuesto que ve el cliente: la cuenta, el documento y el PDF
(`docs/plan/1.3-pdf-del-presupuesto/diseno.md`)."""
```

Crear `backend/app/services/presupuesto/totales.py`:

```python
"""La cuenta del presupuesto: de los costos a lo que paga el cliente.

Las reglas están en `docs/plan/1.3-pdf-del-presupuesto/diseno.md §5`.
Es la única cuenta: la usan los totales de la pantalla y el PDF, así
los dos muestran el mismo número.

No toca la base ni sabe de HTTP: recibe el presupuesto y sus líneas ya
leídos, y nunca modifica ninguno de los dos.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ...modelos.presupuesto import LineaCosto, Presupuesto

#: PAR-16: precisión de redondeo. Se aplica una sola vez, al final —
#: nunca sobre un resultado intermedio que alimente el siguiente cálculo
#: (3er criterio de CART-307).
_DOS_DECIMALES = Decimal("0.01")


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(_DOS_DECIMALES)


@dataclass(frozen=True)
class ItemCuenta:
    """Una línea de costo vista desde el precio.

    `precio_base` es el escrito a mano o, si no hay, el costo más el
    margen. `precio_final` es el que sale en el presupuesto: coincide con
    el base salvo que haya un total fijado, que los ajusta a todos.
    Los dos quedan en `None` si la línea no entra en la cuenta (sin
    costo, o en otra moneda) o si falta el margen para calcularlos.
    """

    linea_id: int
    rubro: str
    texto: str
    costo: Decimal | None
    precio_base: Decimal | None
    a_mano: bool
    precio_final: Decimal | None


@dataclass(frozen=True)
class Cuenta:
    """El resultado. `advertencias` es para quien arma el presupuesto;
    `faltantes` es lo que impide sacar el documento del cliente
    (`diseno.md §5.4`): con la lista vacía, el presupuesto está completo.
    """

    moneda: str
    items: list[ItemCuenta]
    subtotales_por_rubro: dict[str, Decimal]
    costo_total: Decimal
    margen_pct: Decimal | None
    #: Lo que queda entre el precio de venta y el costo. Con precios a
    #: mano o total fijado ya no es `costo × margen_pct`: es un resultado.
    monto_margen: Decimal | None
    margen_resultante_pct: Decimal | None
    #: El subtotal del presupuesto: la suma de los ítems, sin IVA.
    precio_venta: Decimal | None
    iva_pct: Decimal | None
    monto_iva: Decimal | None
    total: Decimal | None
    total_fijado: Decimal | None
    advertencias: list[str]
    faltantes: list[str]


def _costo_efectivo(linea: LineaCosto) -> Decimal | None:
    return linea.valor_override if linea.valor_override is not None else linea.valor_calculado


def _ajustar_centavos(finales: list[Decimal], objetivo: Decimal, candidatos: list[int]) -> None:
    """Si por el redondeo la suma no da `objetivo`, la diferencia va al
    candidato de mayor importe; si hay empate, al primero."""
    diferencia = objetivo - sum(finales, Decimal(0))
    if diferencia and candidatos:
        mayor = max(candidatos, key=lambda i: finales[i])
        finales[mayor] += diferencia


def _sin_total_fijado(bases: list[Decimal], a_mano: list[bool], objetivo: Decimal) -> list[Decimal]:
    """Cada ítem vale su precio base. Un precio escrito a mano se respeta
    exacto: los centavos del redondeo van a un ítem calculado."""
    finales = [redondear(base) for base in bases]
    _ajustar_centavos(finales, objetivo, [i for i, mano in enumerate(a_mano) if not mano])
    return finales


def _con_total_fijado(bases: list[Decimal], objetivo: Decimal) -> list[Decimal]:
    """Todos los ítems por el mismo factor, también los escritos a mano."""
    suma = sum(bases, Decimal(0))
    finales = [redondear(base * objetivo / suma) for base in bases]
    _ajustar_centavos(finales, objetivo, list(range(len(finales))))
    return finales


def calcular(presupuesto: Presupuesto, lineas: list[LineaCosto]) -> Cuenta:
    """Suma los costos por rubro, arma el precio de cada ítem y los
    totales, y redondea una sola vez al final.

    Nunca mezcla monedas sin una cotización explícita de por medio
    (mismo criterio que `costeo.ResumenMateriales.costo_total_por_moneda`):
    una línea en otra moneda que la del presupuesto queda afuera de la
    cuenta, igual que una línea sin costo, y las dos se avisan.
    """
    advertencias: list[str] = []
    faltantes: list[str] = []
    if not lineas:
        faltantes.append("El presupuesto no tiene ninguna línea.")

    # 1. Qué líneas entran en la cuenta, y cuánto cuestan.
    validas: list[int] = []
    costos: dict[int, Decimal] = {}
    subtotales_por_rubro: dict[str, Decimal] = {}
    costo_total = Decimal(0)
    for i, linea in enumerate(lineas):
        costo = _costo_efectivo(linea)
        if costo is None:
            advertencias.append(
                f"«{linea.descripcion}» no tiene costo calculado ni override; no se sumó al total."
            )
            faltantes.append(f"«{linea.descripcion}» no tiene costo.")
            continue
        if linea.moneda != presupuesto.moneda:
            advertencias.append(
                f"«{linea.descripcion}» está en {linea.moneda}, el presupuesto es en "
                f"{presupuesto.moneda}; no se sumó al total."
            )
            faltantes.append(
                f"«{linea.descripcion}» está en {linea.moneda} y el presupuesto es en {presupuesto.moneda}."
            )
            continue
        validas.append(i)
        costos[i] = costo
        subtotales_por_rubro[linea.rubro] = subtotales_por_rubro.get(linea.rubro, Decimal(0)) + costo
        costo_total += costo

    # 2. El precio base de cada una: a mano, o costo más margen.
    margen = presupuesto.margen_pct
    iva = presupuesto.iva_pct
    a_mano = [lineas[i].precio_cliente is not None for i in validas]
    hay_precios = margen is not None or (bool(validas) and all(a_mano))

    bases: list[Decimal] = []
    finales: list[Decimal] = []
    monto_margen = margen_resultante = precio_venta = monto_iva = total = None
    if not hay_precios:
        advertencias.append(
            "El presupuesto no tiene margen configurado (PAR-12); no se calculó el precio de venta."
        )
        faltantes.append("Falta cargar el margen, o un precio a mano en cada ítem.")
    else:
        for i in validas:
            a_mano_i = lineas[i].precio_cliente
            bases.append(a_mano_i if a_mano_i is not None else costos[i] * (1 + margen / 100))
        suma_base = sum(bases, Decimal(0))
        fijado = presupuesto.total_fijado

        # 3. Subtotal, IVA y total, y el precio final de cada ítem.
        if iva is None:
            advertencias.append("El presupuesto no tiene IVA configurado; no se calculó el total.")
            faltantes.append("Falta cargar el IVA.")
            precio_venta = redondear(suma_base)
            finales = _sin_total_fijado(bases, a_mano, precio_venta)
        elif fijado is None:
            precio_venta = redondear(suma_base)
            total = redondear(suma_base * (1 + iva / 100))
            finales = _sin_total_fijado(bases, a_mano, precio_venta)
        else:
            total = redondear(fijado)
            precio_venta = redondear(total / (1 + iva / 100))
            if suma_base != 0:
                finales = _con_total_fijado(bases, precio_venta)
            elif validas:
                sin_reparto = "No se puede repartir el total fijado: todos los ítems valen cero."
                advertencias.append(sin_reparto)
                faltantes.append(sin_reparto)

        # El IVA es total menos subtotal: así el documento siempre suma.
        if total is not None:
            monto_iva = total - precio_venta
        monto_margen = precio_venta - redondear(costo_total)
        if costo_total:
            margen_resultante = redondear(monto_margen / costo_total * 100)
        if monto_margen < 0:
            advertencias.append("El precio de venta queda por debajo del costo.")

    # 4. Una fila por línea, en el orden en que vinieron.
    posicion = {i: n for n, i in enumerate(validas)}
    items: list[ItemCuenta] = []
    for i, linea in enumerate(lineas):
        n = posicion.get(i)
        items.append(
            ItemCuenta(
                linea_id=linea.id,
                rubro=linea.rubro,
                texto=linea.texto_cliente or linea.descripcion,
                costo=_costo_efectivo(linea),
                precio_base=redondear(bases[n]) if n is not None and bases else None,
                a_mano=linea.precio_cliente is not None,
                precio_final=finales[n] if n is not None and finales else None,
            )
        )

    return Cuenta(
        moneda=presupuesto.moneda,
        items=items,
        subtotales_por_rubro={rubro: redondear(valor) for rubro, valor in subtotales_por_rubro.items()},
        costo_total=redondear(costo_total),
        margen_pct=margen,
        monto_margen=monto_margen,
        margen_resultante_pct=margen_resultante,
        precio_venta=precio_venta,
        iva_pct=iva,
        monto_iva=monto_iva,
        total=total,
        total_fijado=presupuesto.total_fijado,
        advertencias=advertencias,
        faltantes=faltantes,
    )
```

- [ ] **Step 4: Correr las pruebas y ver que pasan**

Run: `cd backend && python -m pytest -q tests/services/presupuesto/test_totales.py`
Expected: `18 passed`.

- [ ] **Step 5: Correr toda la suite**

Run: `cd backend && python -m pytest -q -rs`
Expected: `442 passed`.

- [ ] **Step 6: Commit** (con el ok de Enzo)

```bash
git add backend/app/services/presupuesto/__init__.py backend/app/services/presupuesto/totales.py backend/tests/services/presupuesto/test_totales.py
git commit -m "feat(presupuesto): la cuenta de precios para el cliente, en un servicio"
```

---

### Task 3: Las rutas usan la cuenta y guardan lo del cliente

**Files:**
- Modify: `backend/app/api/esquemas_presupuesto.py`
- Modify: `backend/app/api/rutas_presupuesto.py`
- Test: `backend/tests/api/test_rutas_presupuesto.py`

**Interfaces:**
- Consumes: `calcular` y `Cuenta` (Tarea 2); `_linea_libre` (Tarea 1).
- Produces: `PATCH /lineas-costo/{linea_id}/cliente` con `{texto_cliente?, precio_cliente?}`, que devuelve `LineaCostoLeer`.
- Produces: `PATCH /presupuestos/{id}` acepta además `cliente_id` y `total_fijado`.
- Produces: `TotalesLeer` suma `margen_resultante_pct` y `total_fijado`; `DesgloseLeer` suma `items_cliente: list[ItemClienteLeer]` y `faltantes: list[str]`.
- Produces (para la Tarea 6): `_lineas_del_presupuesto(sesion, presupuesto_id) -> list[LineaCosto]` en `rutas_presupuesto.py`, y la función de prueba `_presupuesto_del_ejemplo(cliente) -> tuple[dict, dict[str, dict]]`.

- [ ] **Step 1: Escribir las pruebas que fallan**

Agregar al final de `backend/tests/api/test_rutas_presupuesto.py`:

```python
def _presupuesto_del_ejemplo(cliente) -> tuple[dict, dict[str, dict]]:
    """Las cuatro líneas del §5.2 del diseño, con margen del 30 %."""
    presupuesto = _crear_presupuesto(cliente)
    lineas = {
        nombre: _linea_libre(cliente, presupuesto["id"], nombre, costo)
        for nombre, costo in (
            ("Chapa", "400000"),
            ("Mano de obra", "300000"),
            ("Flete", "80000"),
            ("Instalación", "120000"),
        )
    }
    cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "30"})
    return presupuesto, lineas


def test_guardar_el_texto_y_el_precio_para_el_cliente_no_toca_el_costo(cliente):
    _presupuesto, lineas = _presupuesto_del_ejemplo(cliente)

    respuesta = cliente.patch(
        f"/lineas-costo/{lineas['Instalación']['id']}/cliente",
        json={"texto_cliente": "Colocación en el local", "precio_cliente": "150000"},
    )

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["texto_cliente"] == "Colocación en el local"
    assert Decimal(cuerpo["precio_cliente"]) == Decimal("150000")
    assert cuerpo["descripcion"] == "Instalación"
    assert Decimal(cuerpo["valor_calculado"]) == Decimal("120000")
    assert cuerpo["valor_override"] is None


def test_lo_del_cliente_vale_para_una_linea_de_material_y_recalcular_no_lo_pisa(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    material = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]

    respuesta = cliente.patch(
        f"/lineas-costo/{material['id']}/cliente",
        json={"texto_cliente": "Chapa del frente", "precio_cliente": "9000"},
    )

    assert respuesta.status_code == 200, respuesta.text
    recalculada = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]
    assert recalculada["texto_cliente"] == "Chapa del frente"
    assert Decimal(recalculada["precio_cliente"]) == Decimal("9000")


def test_un_nulo_o_un_texto_en_blanco_limpian_lo_del_cliente(cliente):
    _presupuesto, lineas = _presupuesto_del_ejemplo(cliente)
    ruta = f"/lineas-costo/{lineas['Flete']['id']}/cliente"
    cliente.patch(ruta, json={"texto_cliente": "Traslado", "precio_cliente": "100000"})

    sin_precio = cliente.patch(ruta, json={"precio_cliente": None}).json()
    assert sin_precio["precio_cliente"] is None
    assert sin_precio["texto_cliente"] == "Traslado", "lo que no viaja en el pedido no se toca"

    en_blanco = cliente.patch(ruta, json={"texto_cliente": "   "}).json()
    assert en_blanco["texto_cliente"] is None


@pytest.mark.parametrize("precio", ["-1", "10.123", "mil"])
def test_un_precio_para_el_cliente_que_no_sirve_da_422(cliente, precio):
    _presupuesto, lineas = _presupuesto_del_ejemplo(cliente)

    respuesta = cliente.patch(
        f"/lineas-costo/{lineas['Flete']['id']}/cliente", json={"precio_cliente": precio}
    )

    assert respuesta.status_code == 422


def test_un_texto_para_el_cliente_demasiado_largo_da_422(cliente):
    _presupuesto, lineas = _presupuesto_del_ejemplo(cliente)

    respuesta = cliente.patch(
        f"/lineas-costo/{lineas['Flete']['id']}/cliente", json={"texto_cliente": "x" * 301}
    )

    assert respuesta.status_code == 422


def test_lo_del_cliente_en_una_linea_inexistente_da_404(cliente):
    assert cliente.patch("/lineas-costo/999/cliente", json={"texto_cliente": "x"}).status_code == 404


def test_fijar_y_quitar_el_total(cliente):
    presupuesto, _lineas = _presupuesto_del_ejemplo(cliente)
    ruta = f"/presupuestos/{presupuesto['id']}"

    fijado = cliente.patch(ruta, json={"total_fijado": "1400000"})

    assert fijado.status_code == 200, fijado.text
    assert Decimal(fijado.json()["total_fijado"]) == Decimal("1400000")
    totales = cliente.get(f"{ruta}/totales").json()
    assert Decimal(totales["total"]) == Decimal("1400000.00")
    assert Decimal(totales["precio_venta"]) == Decimal("1157024.79")
    assert Decimal(totales["monto_iva"]) == Decimal("242975.21")

    cliente.patch(ruta, json={"total_fijado": None})

    totales = cliente.get(f"{ruta}/totales").json()
    assert totales["total_fijado"] is None
    assert Decimal(totales["total"]) == Decimal("1415700.00")


@pytest.mark.parametrize("total", ["0", "-100", "1400000.123", "un millón"])
def test_un_total_fijado_que_no_sirve_da_422(cliente, total):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"total_fijado": total})

    assert respuesta.status_code == 422


def test_cambiar_el_cliente_del_presupuesto(cliente):
    presupuesto = _crear_presupuesto(cliente)
    otro = _crear_cliente(cliente, nombre="Farmacia Central")

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"cliente_id": otro["id"]})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["cliente_id"] == otro["id"]
    desglose = cliente.get(f"/presupuestos/{presupuesto['id']}/desglose").json()
    assert desglose["cliente"]["nombre"] == "Farmacia Central"


def test_cambiar_a_un_cliente_inexistente_da_404(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"cliente_id": 999})

    assert respuesta.status_code == 404


@pytest.mark.parametrize(
    "datos",
    [{"cliente_id": None}, {"validez_dias": None}, {"moneda": None}, {"validez_dias": 0}, {"validez_dias": -5}],
)
def test_lo_que_no_puede_quedar_vacio_da_422_y_no_un_error_del_servidor(cliente, datos):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json=datos)

    assert respuesta.status_code == 422


def test_el_desglose_trae_lo_que_lee_el_cliente_y_el_margen_que_queda(cliente):
    presupuesto, lineas = _presupuesto_del_ejemplo(cliente)
    cliente.patch(f"/lineas-costo/{lineas['Instalación']['id']}/cliente", json={"precio_cliente": "150000"})
    cliente.patch(f"/lineas-costo/{lineas['Chapa']['id']}/cliente", json={"texto_cliente": "Cartel frontal"})
    cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"total_fijado": "1400000"})

    cuerpo = cliente.get(f"/presupuestos/{presupuesto['id']}/desglose").json()

    items = cuerpo["items_cliente"]
    assert [item["linea_id"] for item in items] == [linea["id"] for linea in lineas.values()]
    assert [item["texto"] for item in items] == ["Cartel frontal", "Mano de obra", "Flete", "Instalación"]
    assert [Decimal(item["costo"]) for item in items] == [
        Decimal("400000"), Decimal("300000"), Decimal("80000"), Decimal("120000"),
    ]
    assert [item["a_mano"] for item in items] == [False, False, False, True]
    assert Decimal(items[3]["precio_base"]) == Decimal("150000.00")
    assert [Decimal(item["precio_final"]) for item in items] == [
        Decimal("516883.92"), Decimal("387662.95"), Decimal("103376.79"), Decimal("149101.13"),
    ]
    assert Decimal(cuerpo["totales"]["monto_margen"]) == Decimal("257024.79")
    assert Decimal(cuerpo["totales"]["margen_resultante_pct"]) == Decimal("28.56")
    assert cuerpo["faltantes"] == []


def test_el_desglose_dice_que_le_falta_al_presupuesto(cliente):
    presupuesto = _crear_presupuesto(cliente)

    cuerpo = cliente.get(f"/presupuestos/{presupuesto['id']}/desglose").json()

    assert cuerpo["faltantes"] == [
        "El presupuesto no tiene ninguna línea.",
        "Falta cargar el margen, o un precio a mano en cada ítem.",
    ]
    assert cuerpo["items_cliente"] == []


def test_duplicar_copia_lo_escrito_para_el_cliente(cliente):
    presupuesto, lineas = _presupuesto_del_ejemplo(cliente)
    cliente.patch(
        f"/lineas-costo/{lineas['Instalación']['id']}/cliente",
        json={"texto_cliente": "Colocación", "precio_cliente": "150000"},
    )
    cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"total_fijado": "1400000"})

    copia = cliente.post(f"/presupuestos/{presupuesto['id']}/duplicar").json()

    assert Decimal(copia["total_fijado"]) == Decimal("1400000")
    lineas_copia = cliente.get(f"/presupuestos/{copia['id']}/lineas-costo").json()
    instalacion = next(linea for linea in lineas_copia if linea["descripcion"] == "Instalación")
    assert instalacion["texto_cliente"] == "Colocación"
    assert Decimal(instalacion["precio_cliente"]) == Decimal("150000")
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `cd backend && python -m pytest -q tests/api/test_rutas_presupuesto.py`
Expected: fallan las 23 pruebas nuevas menos una. `test_lo_del_cliente_en_una_linea_inexistente_da_404` pasa desde antes, porque la ruta todavía no existe y eso también da 404: se comprueba de verdad en el Step 5.

- [ ] **Step 3: Los esquemas**

En `backend/app/api/esquemas_presupuesto.py`:

Reemplazar:

```python
from pydantic import BaseModel, ConfigDict, model_validator
```

por:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
```

Reemplazar:

```python
    trabajo_id: int | None = None
    validez_dias: int | None = None
    moneda: Moneda | None = None
    #: `PAR-12` sin confirmar — se fija a mano cuando se sabe cuánto
    #: cobrar (`CART-307`, paso 5). `None` explícito lo vuelve a limpiar.
    margen_pct: Decimal | None = None
    iva_pct: Decimal | None = None
```

por:

```python
    cliente_id: int | None = None
    trabajo_id: int | None = None
    validez_dias: int | None = Field(default=None, gt=0)
    moneda: Moneda | None = None
    #: `PAR-12` sin confirmar — se fija a mano cuando se sabe cuánto
    #: cobrar (`CART-307`, paso 5). `None` explícito lo vuelve a limpiar.
    margen_pct: Decimal | None = None
    iva_pct: Decimal | None = None
    #: El total final, con IVA (`diseno.md §5` de 1.3). `None` explícito
    #: lo quita y el total vuelve a salir de la suma de los ítems.
    total_fijado: Decimal | None = Field(default=None, gt=0, decimal_places=2)

    @model_validator(mode="after")
    def _lo_que_no_puede_quedar_vacio(self) -> PresupuestoActualizar:
        # Un `null` explícito sirve para limpiar margen, IVA, trabajo o
        # total fijado. En estos tres la columna no admite vacío: sin
        # este chequeo el `null` llegaba a la base y volvía como error 500.
        for campo in ("cliente_id", "validez_dias", "moneda"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no puede quedar vacío.")
        return self
```

Reemplazar:

```python
# --- Líneas libres (paso 4: `CART-304`/`305`/`306`) -----------------------


class LineaCostoCrear(BaseModel):
```

por:

```python
class LineaClienteActualizar(BaseModel):
    """Lo que lee el cliente en una línea (`diseno.md §5` de 1.3): el
    texto y el precio a mano, sin IVA. Vale para cualquier rubro,
    también `MATERIAL`: no cambia el costo, es una capa encima. Un
    `null` explícito limpia el campo y se vuelve a usar la descripción
    o el costo más el margen."""

    texto_cliente: str | None = Field(default=None, max_length=300)
    precio_cliente: Decimal | None = Field(default=None, ge=0, decimal_places=2)

    @field_validator("texto_cliente")
    @classmethod
    def _un_texto_en_blanco_es_vacio(cls, valor: str | None) -> str | None:
        return (valor or "").strip() or None


# --- Líneas libres (paso 4: `CART-304`/`305`/`306`) -----------------------


class LineaCostoCrear(BaseModel):
```

Reemplazar:

```python
    costo_total: Decimal
    margen_pct: Decimal | None
    monto_margen: Decimal | None
    precio_venta: Decimal | None
    iva_pct: Decimal | None
    monto_iva: Decimal | None
    total: Decimal | None
    advertencias: list[str]
```

por:

```python
    costo_total: Decimal
    margen_pct: Decimal | None
    #: Precio de venta menos costo. Con precios a mano o total fijado ya
    #: no es `costo × margen_pct`: es lo que queda (`diseno.md §5.5`).
    monto_margen: Decimal | None
    margen_resultante_pct: Decimal | None
    #: El subtotal del presupuesto: la suma de los ítems, sin IVA.
    precio_venta: Decimal | None
    iva_pct: Decimal | None
    monto_iva: Decimal | None
    total: Decimal | None
    total_fijado: Decimal | None
    advertencias: list[str]
```

Reemplazar:

```python
    presupuesto: PresupuestoLeer
    cliente: ClienteLeer
    lineas_por_rubro: dict[str, list[LineaCostoLeer]]
    totales: TotalesLeer
```

por:

```python
    presupuesto: PresupuestoLeer
    cliente: ClienteLeer
    lineas_por_rubro: dict[str, list[LineaCostoLeer]]
    totales: TotalesLeer
    #: Una fila por línea, en el orden de carga: lo que va a leer el
    #: cliente al lado de lo que cuesta. Es vista interna, trae el costo.
    items_cliente: list[ItemClienteLeer]
    #: Lo que impide sacar el PDF. Vacía = el presupuesto está completo.
    faltantes: list[str]
```

Reemplazar:

```python
# --- Desglose completo (paso 6: `CART-308`, el último del plan) ----------
```

por:

```python
# --- Desglose completo (paso 6: `CART-308`, el último del plan) ----------


class ItemClienteLeer(BaseModel):
    """Una línea vista desde el precio — `services.presupuesto.totales.ItemCuenta`."""

    model_config = ConfigDict(from_attributes=True)

    linea_id: int
    rubro: str
    texto: str
    costo: Decimal | None
    precio_base: Decimal | None
    a_mano: bool
    precio_final: Decimal | None
```

- [ ] **Step 4: Las rutas**

En `backend/app/api/rutas_presupuesto.py`:

Reemplazar:

```python
from datetime import datetime, timezone
from decimal import Decimal

from fastapi
```

por:

```python
from datetime import datetime, timezone

from fastapi
```

Reemplazar:

```python
from ..modelos.presupuesto import Cliente, LineaCosto, Presupuesto, RubroLineaCosto
from .dependencias import obtener_sesion
from .esquemas_presupuesto import (
    ClienteActualizar,
    ClienteCrear,
    ClienteLeer,
    DesgloseLeer,
    LineaCostoActualizar,
```

por:

```python
from ..modelos.presupuesto import Cliente, LineaCosto, Presupuesto, RubroLineaCosto
from ..services.presupuesto.totales import Cuenta, calcular
from .dependencias import obtener_sesion
from .esquemas_presupuesto import (
    ClienteActualizar,
    ClienteCrear,
    ClienteLeer,
    DesgloseLeer,
    LineaClienteActualizar,
    LineaCostoActualizar,
```

Reemplazar:

```python
    valores = datos.model_dump(exclude_unset=True)
    if "trabajo_id" in valores and valores["trabajo_id"] is not None:
        _trabajo_o_404(sesion, valores["trabajo_id"])
```

por:

```python
    valores = datos.model_dump(exclude_unset=True)
    if "cliente_id" in valores:
        _cliente_o_404(sesion, valores["cliente_id"])
    if "trabajo_id" in valores and valores["trabajo_id"] is not None:
        _trabajo_o_404(sesion, valores["trabajo_id"])
```

Reemplazar:

```python
        margen_pct=original.margen_pct,
        iva_pct=original.iva_pct,
    )
    sesion.add(copia)
```

por:

```python
        margen_pct=original.margen_pct,
        iva_pct=original.iva_pct,
        total_fijado=original.total_fijado,
    )
    sesion.add(copia)
```

Reemplazar:

```python
                override_por=linea.override_por,
                override_en=linea.override_en,
            )
        )
    sesion.commit()
    return copia
```

por:

```python
                override_por=linea.override_por,
                override_en=linea.override_en,
                texto_cliente=linea.texto_cliente,
                precio_cliente=linea.precio_cliente,
            )
        )
    sesion.commit()
    return copia
```

Reemplazar:

```python
# --- Líneas libres (paso 4: `CART-304`/`305`/`306`) -----------------------


@router.post(
    "/presupuestos/{presupuesto_id}/lineas-costo",
```

por:

```python
@router.patch("/lineas-costo/{linea_id}/cliente", response_model=LineaCostoLeer)
def actualizar_linea_para_el_cliente(
    linea_id: int, datos: LineaClienteActualizar, sesion: Session = Depends(obtener_sesion)
) -> LineaCosto:
    """El texto y el precio que lee el cliente en esta línea
    (`docs/plan/1.3-pdf-del-presupuesto/diseno.md §5`) — de cualquier
    rubro, incluido `MATERIAL`. Son una capa encima del costo, como el
    override: `valor_calculado` y `valor_override` no se tocan."""
    linea = _linea_costo_o_404(sesion, linea_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(linea, campo, valor)
    sesion.commit()
    return linea


# --- Líneas libres (paso 4: `CART-304`/`305`/`306`) -----------------------


@router.post(
    "/presupuestos/{presupuesto_id}/lineas-costo",
```

Y mudar la cuenta. Borrar desde el comentario `# --- Totales: margen, IVA, redondeo único (paso 5: `CART-307`) ---` hasta el final del archivo: son `_DOS_DECIMALES`, `_redondear`, `_calcular_totales`, `obtener_totales` y `obtener_desglose`. En su lugar va esto:

```python
# --- Totales (paso 5: `CART-307`) -----------------------------------------
# La cuenta vive en `services/presupuesto/totales.py`: es la misma para
# la pantalla y para el PDF.


def _lineas_del_presupuesto(sesion: Session, presupuesto_id: int) -> list[LineaCosto]:
    consulta = (
        select(LineaCosto).where(LineaCosto.presupuesto_id == presupuesto_id).order_by(LineaCosto.id)
    )
    return list(sesion.execute(consulta).scalars().all())


def _totales_leer(presupuesto: Presupuesto, cuenta: Cuenta) -> TotalesLeer:
    return TotalesLeer(
        presupuesto_id=presupuesto.id,
        moneda=cuenta.moneda,
        subtotales_por_rubro=cuenta.subtotales_por_rubro,
        costo_total=cuenta.costo_total,
        margen_pct=cuenta.margen_pct,
        monto_margen=cuenta.monto_margen,
        margen_resultante_pct=cuenta.margen_resultante_pct,
        precio_venta=cuenta.precio_venta,
        iva_pct=cuenta.iva_pct,
        monto_iva=cuenta.monto_iva,
        total=cuenta.total,
        total_fijado=cuenta.total_fijado,
        advertencias=cuenta.advertencias,
    )


@router.get("/presupuestos/{presupuesto_id}/totales", response_model=TotalesLeer)
def obtener_totales(
    presupuesto_id: int, sesion: Session = Depends(obtener_sesion)
) -> TotalesLeer:
    presupuesto = _presupuesto_o_404(sesion, presupuesto_id)
    return _totales_leer(presupuesto, calcular(presupuesto, _lineas_del_presupuesto(sesion, presupuesto_id)))


@router.get("/presupuestos/{presupuesto_id}/desglose", response_model=DesgloseLeer)
def obtener_desglose(
    presupuesto_id: int, sesion: Session = Depends(obtener_sesion)
) -> DesgloseLeer:
    """`CART-308`: cliente, líneas agrupadas por rubro (con quiénes
    tienen override — se ve directo en cada línea) y los totales, en
    una sola respuesta. Más lo que va a leer el cliente en cada ítem y
    lo que falta para poder sacar el PDF (1.3)."""
    presupuesto = _presupuesto_o_404(sesion, presupuesto_id)
    lineas = _lineas_del_presupuesto(sesion, presupuesto_id)
    cuenta = calcular(presupuesto, lineas)

    lineas_por_rubro: dict[str, list[LineaCosto]] = {}
    for linea in lineas:
        lineas_por_rubro.setdefault(linea.rubro, []).append(linea)

    return DesgloseLeer(
        presupuesto=presupuesto,
        cliente=presupuesto.cliente,
        lineas_por_rubro=lineas_por_rubro,
        totales=_totales_leer(presupuesto, cuenta),
        items_cliente=cuenta.items,
        faltantes=cuenta.faltantes,
    )
```

- [ ] **Step 5: Correr las pruebas y ver que pasan**

Run: `cd backend && python -m pytest -q tests/api/test_rutas_presupuesto.py`
Expected: `78 passed`.

Para comprobar la prueba que pasaba sola: en `actualizar_linea_para_el_cliente`, cambiar un momento `_linea_costo_o_404(sesion, linea_id)` por `sesion.get(LineaCosto, linea_id)` y correr `-k linea_inexistente`. Tiene que fallar `test_lo_del_cliente_en_una_linea_inexistente_da_404`. Deshacer el cambio.

- [ ] **Step 6: Correr toda la suite**

Run: `cd backend && python -m pytest -q -rs`
Expected: `465 passed`. Las pruebas de totales y de desglose que ya existían pasan sin tocarlas: es la comprobación de que la cuenta nueva da lo mismo que la anterior.

- [ ] **Step 7: Commit** (con el ok de Enzo)

```bash
git add backend/app/api/esquemas_presupuesto.py backend/app/api/rutas_presupuesto.py backend/tests/api/test_rutas_presupuesto.py
git commit -m "feat(presupuesto): rutas para editar lo que lee el cliente y fijar el total"
```

**Fin del tramo 1.** Mostrarle a Enzo la salida de `python -m pytest -q tests/services/presupuesto/test_totales.py -v`, que nombra cada regla, y avisarle que Costeo sigue mostrando los mismos totales.

---

## Tramo 2 — El PDF

### Task 4: El documento del cliente

**Files:**
- Create: `backend/app/services/presupuesto/documento.py`
- Test: `backend/tests/services/presupuesto/test_documento.py`

**Interfaces:**
- Consumes: `Cuenta` y `calcular` (Tarea 2).
- Produces: `armar_documento(presupuesto: Presupuesto, cuenta: Cuenta, hoy: date) -> DocumentoCliente`, que tira `PresupuestoIncompleto` (con `.faltantes: list[str]`) si `cuenta.faltantes` no está vacía.
- Produces: `hoy_en_argentina() -> date`.
- Produces: `DocumentoCliente` con `codigo`, `cliente_nombre`, `cliente_contacto`, `fecha`, `valido_hasta`, `moneda`, `items: list[ItemDocumento]`, `subtotal`, `iva_pct`, `monto_iva`, `total`; `ItemDocumento` con `texto` e `importe`.

- [ ] **Step 1: Escribir las pruebas que fallan**

Crear `backend/tests/services/presupuesto/test_documento.py`:

```python
"""El documento del cliente (`diseno.md §7` de 1.3)."""
from __future__ import annotations

from dataclasses import fields
from datetime import date
from decimal import Decimal as D

import pytest

from app.modelos.presupuesto import Cliente, LineaCosto, Presupuesto
from app.services.presupuesto.documento import (
    DocumentoCliente,
    ItemDocumento,
    PresupuestoIncompleto,
    armar_documento,
)
from app.services.presupuesto.totales import calcular

HOY = date(2026, 10, 12)


def _presupuesto(**extra) -> Presupuesto:
    datos = {
        "id": 1,
        "codigo": "P-2026-0007",
        "cliente": Cliente(id=1, nombre="Farmacia Central", contacto="Av. Belgrano 123"),
        "validez_dias": 15,
        "moneda": "ARS",
        "margen_pct": D(30),
        "iva_pct": D(21),
        "total_fijado": None,
    } | extra
    return Presupuesto(**datos)


def _linea(n: int, descripcion: str, costo: str | None, **extra) -> LineaCosto:
    datos = {
        "id": n,
        "rubro": "OTRO",
        "descripcion": descripcion,
        "valor_calculado": None if costo is None else D(costo),
        "valor_override": None,
        "moneda": "ARS",
        "texto_cliente": None,
        "precio_cliente": None,
    } | extra
    return LineaCosto(**datos)


def _documento(presupuesto: Presupuesto, lineas: list[LineaCosto], hoy: date = HOY) -> DocumentoCliente:
    return armar_documento(presupuesto, calcular(presupuesto, lineas), hoy)


def test_el_documento_lleva_lo_que_ve_el_cliente():
    presupuesto = _presupuesto(total_fijado=D("1400000"))
    lineas = [
        _linea(1, "Chapa negra cal. 20", "400000", texto_cliente="Cartel frontal"),
        _linea(2, "Mano de obra", "300000"),
        _linea(3, "Flete", "80000"),
        _linea(4, "Instalación", "120000", precio_cliente=D("150000")),
    ]

    documento = _documento(presupuesto, lineas)

    assert documento.codigo == "P-2026-0007"
    assert documento.cliente_nombre == "Farmacia Central"
    assert documento.cliente_contacto == "Av. Belgrano 123"
    assert documento.fecha == date(2026, 10, 12)
    assert documento.valido_hasta == date(2026, 10, 27)
    assert documento.moneda == "ARS"
    assert documento.items == [
        ItemDocumento("Cartel frontal", D("516883.92")),
        ItemDocumento("Mano de obra", D("387662.95")),
        ItemDocumento("Flete", D("103376.79")),
        ItemDocumento("Instalación", D("149101.13")),
    ]
    assert documento.subtotal == D("1157024.79")
    assert documento.iva_pct == D(21)
    assert documento.monto_iva == D("242975.21")
    assert documento.total == D("1400000.00")


def test_el_documento_no_tiene_donde_llevar_costos_ni_margenes():
    # Si alguien le agrega un campo, esta prueba obliga a pensar si el
    # cliente lo tiene que ver (último criterio de CART-309).
    assert {campo.name for campo in fields(DocumentoCliente)} == {
        "codigo", "cliente_nombre", "cliente_contacto", "fecha", "valido_hasta",
        "moneda", "items", "subtotal", "iva_pct", "monto_iva", "total",
    }
    assert {campo.name for campo in fields(ItemDocumento)} == {"texto", "importe"}


def test_un_presupuesto_incompleto_no_arma_nada_y_dice_que_falta():
    presupuesto = _presupuesto(margen_pct=None)

    with pytest.raises(PresupuestoIncompleto) as error:
        _documento(presupuesto, [_linea(1, "Chapa", None), _linea(2, "Flete", "80000")])

    assert error.value.faltantes == [
        "«Chapa» no tiene costo.",
        "Falta cargar el margen, o un precio a mano en cada ítem.",
    ]


def test_valido_hasta_cruza_de_mes_y_de_anio():
    documento = _documento(_presupuesto(), [_linea(1, "Flete", "80000")], hoy=date(2026, 12, 25))

    assert documento.valido_hasta == date(2027, 1, 9)
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `cd backend && python -m pytest -q tests/services/presupuesto/test_documento.py`
Expected: error al juntar las pruebas, `ModuleNotFoundError: No module named 'app.services.presupuesto.documento'`.

- [ ] **Step 3: Escribir el documento**

Crear `backend/app/services/presupuesto/documento.py`:

```python
"""El documento del cliente: lo que sale en el presupuesto, y nada más.

No tiene ningún campo de costo ni de margen, a propósito
(`docs/plan/1.3-pdf-del-presupuesto/diseno.md §7`): la plantilla no puede
mostrar lo que el documento no trae. Es el último criterio de `CART-309`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from ...modelos.presupuesto import Presupuesto
from .totales import Cuenta

#: Argentina no cambia la hora desde 2009. Con un corrimiento fijo no
#: hace falta la base de zonas horarias, que en Windows no viene con Python.
_HORA_ARGENTINA = timezone(timedelta(hours=-3))


def hoy_en_argentina() -> date:
    return datetime.now(_HORA_ARGENTINA).date()


class PresupuestoIncompleto(Exception):
    """Al presupuesto le falta algo para poder mostrárselo al cliente."""

    def __init__(self, faltantes: list[str]):
        super().__init__("; ".join(faltantes))
        self.faltantes = faltantes


@dataclass(frozen=True)
class ItemDocumento:
    texto: str
    importe: Decimal


@dataclass(frozen=True)
class DocumentoCliente:
    codigo: str
    cliente_nombre: str
    cliente_contacto: str | None
    fecha: date
    valido_hasta: date
    moneda: str
    items: list[ItemDocumento]
    subtotal: Decimal
    iva_pct: Decimal
    monto_iva: Decimal
    total: Decimal


def armar_documento(presupuesto: Presupuesto, cuenta: Cuenta, hoy: date) -> DocumentoCliente:
    """`hoy` es la fecha del presupuesto: el día en que se pide el
    documento. «Válido hasta» sale de sumarle los días de validez
    (`PAR-11`). Cuando exista el envío (1.5), esa fecha se congela ahí.
    """
    if cuenta.faltantes:
        raise PresupuestoIncompleto(cuenta.faltantes)
    return DocumentoCliente(
        codigo=presupuesto.codigo,
        cliente_nombre=presupuesto.cliente.nombre,
        cliente_contacto=presupuesto.cliente.contacto,
        fecha=hoy,
        valido_hasta=hoy + timedelta(days=presupuesto.validez_dias),
        moneda=cuenta.moneda,
        items=[ItemDocumento(texto=item.texto, importe=item.precio_final) for item in cuenta.items],
        subtotal=cuenta.precio_venta,
        iva_pct=cuenta.iva_pct,
        monto_iva=cuenta.monto_iva,
        total=cuenta.total,
    )
```

- [ ] **Step 4: Correr las pruebas y ver que pasan**

Run: `cd backend && python -m pytest -q tests/services/presupuesto/test_documento.py`
Expected: `4 passed`.

- [ ] **Step 5: Correr toda la suite y commit** (con el ok de Enzo)

Run: `cd backend && python -m pytest -q -rs`
Expected: `469 passed`.

```bash
git add backend/app/services/presupuesto/documento.py backend/tests/services/presupuesto/test_documento.py
git commit -m "feat(presupuesto): el documento del cliente, sin costos ni margenes"
```

---

### Task 5: La plantilla y el PDF

**Files:**
- Modify: `backend/requirements.txt`, `backend/requirements-dev.txt`
- Modify: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Create: `backend/app/services/presupuesto/pdf.py`
- Create: `backend/app/services/presupuesto/plantillas/presupuesto.html`
- Create: `backend/app/services/presupuesto/plantillas/fuentes/SourceSans3-Regular.ttf`, `SourceSans3-Bold.ttf`, `LICENSE.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/GUIA-PRUEBAS-LOCALES.md`
- Test: `backend/tests/services/presupuesto/test_pdf.py`

**Interfaces:**
- Consumes: `DocumentoCliente` e `ItemDocumento` (Tarea 4).
- Produces: `renderizar_html(documento: DocumentoCliente) -> str`; `generar_pdf(documento: DocumentoCliente) -> bytes`, que tira `BibliotecasPdfFaltantes` si WeasyPrint no encuentra Pango.
- Produces: `formatear_importe(valor: Decimal, moneda: str) -> str`, `formatear_porcentaje(valor: Decimal) -> str`.
- Produces: la marca de pytest `pango` y, para las pruebas, la función `pdf._cargar_weasyprint`, que se reemplaza para simular que faltan las bibliotecas.

- [ ] **Step 1: Las dependencias**

Agregar al final de `backend/requirements.txt`:

```
# PDF del presupuesto (docs/plan/1.3-pdf-del-presupuesto/diseno.md, D-16).
# WeasyPrint usa además Pango, que no viene con pip: en Windows,
# docs/GUIA-PRUEBAS-LOCALES.md §5; en el CI, .github/workflows/ci.yml.
weasyprint==70.0
jinja2==3.1.6
```

Agregar al final de `backend/requirements-dev.txt`:

```
# Leer el texto de un PDF generado, para comprobar qué trae y qué no.
pypdf==6.19.0
```

Run: `cd backend && python -m pip install -r requirements-dev.txt`
Expected: termina sin error. En esta máquina no hay entorno virtual: se instala en el Python del sistema, como el resto.

- [ ] **Step 2: La variable de entorno en Windows** (con el ok de Enzo: queda fija en su usuario)

MSYS2 con Pango ya está instalado en `D:\msys64` desde el 2026-10-12. Falta decirle a WeasyPrint dónde:

```powershell
setx WEASYPRINT_DLL_DIRECTORIES "D:\msys64\mingw64\bin"
```

`setx` vale para las terminales que se abran después. En la terminal que ya está abierta hay que definirla a mano: en PowerShell, `$env:WEASYPRINT_DLL_DIRECTORIES = 'D:\msys64\mingw64\bin'`; en Git Bash, `export WEASYPRINT_DLL_DIRECTORIES='D:\msys64\mingw64\bin'`.

Run: `python -c "import weasyprint; print(weasyprint.__version__)"`
Expected: `70.0`. Si en cambio aparece `OSError: cannot load library 'libgobject-2.0-0'`, la terminal no tiene la variable.

- [ ] **Step 3: La marca `pango`**

Reemplazar el contenido de `backend/pytest.ini` por:

```ini
[pytest]
pythonpath = .
markers =
    pango: genera un PDF de verdad y necesita las bibliotecas de WeasyPrint (tests/conftest.py)
```

Crear `backend/tests/conftest.py`:

```python
"""Configuración común de las pruebas del backend."""
from __future__ import annotations

import os

import pytest


def _pango_disponible() -> bool:
    try:
        import weasyprint  # noqa: F401
    except OSError:
        return False
    return True


def pytest_collection_modifyitems(config, items):
    """Las pruebas marcadas `pango` generan un PDF de verdad.

    En una máquina sin las bibliotecas de WeasyPrint se saltean, con el
    motivo a la vista. En GitHub (`CI`) no se saltean nunca: ahí las
    bibliotecas se instalan, y si faltan la prueba tiene que fallar.
    """
    con_pango = [item for item in items if "pango" in item.keywords]
    if not con_pango or os.getenv("CI") or _pango_disponible():
        return
    saltear = pytest.mark.skip(
        reason="Faltan las bibliotecas de WeasyPrint (Pango): "
        "docs/GUIA-PRUEBAS-LOCALES.md, sección «El PDF del presupuesto»."
    )
    for item in con_pango:
        item.add_marker(saltear)
```

- [ ] **Step 4: Escribir las pruebas que fallan**

Crear `backend/tests/services/presupuesto/test_pdf.py`:

```python
"""Del documento del cliente al HTML y al PDF (`diseno.md §9` de 1.3).

Las pruebas del HTML corren en cualquier máquina. Las marcadas `pango`
generan un PDF de verdad y necesitan las bibliotecas de WeasyPrint
(`tests/conftest.py`).
"""
from __future__ import annotations

import io
from datetime import date
from decimal import Decimal as D

import pytest
from pypdf import PdfReader

from app.services.presupuesto import pdf
from app.services.presupuesto.documento import DocumentoCliente, ItemDocumento


def _documento(**extra) -> DocumentoCliente:
    datos = {
        "codigo": "P-2026-0007",
        "cliente_nombre": "Farmacia Central",
        "cliente_contacto": "Av. Belgrano 123",
        "fecha": date(2026, 10, 12),
        "valido_hasta": date(2026, 10, 27),
        "moneda": "ARS",
        "items": [
            ItemDocumento("Cartel frontal", D("516883.92")),
            ItemDocumento("Instalación", D("149101.13")),
        ],
        "subtotal": D("1157024.79"),
        "iva_pct": D("21"),
        "monto_iva": D("242975.21"),
        "total": D("1400000.00"),
    } | extra
    return DocumentoCliente(**datos)


def _texto_del_pdf(contenido: bytes) -> str:
    return "\n".join(pagina.extract_text() for pagina in PdfReader(io.BytesIO(contenido)).pages)


# --- Formato ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "moneda", "esperado"),
    [
        ("1234567.8", "ARS", "$ 1.234.567,80"),
        ("0", "ARS", "$ 0,00"),
        ("999.999", "ARS", "$ 1.000,00"),
        ("1500", "USD", "US$ 1.500,00"),
        ("10", "EUR", "EUR 10,00"),
        ("-1234.5", "ARS", "$ -1.234,50"),
    ],
)
def test_formatear_importe(valor, moneda, esperado):
    assert pdf.formatear_importe(D(valor), moneda) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("21", "21"), ("21.00", "21"), ("10.5", "10,5"), ("100", "100"), ("0", "0")],
)
def test_formatear_porcentaje(valor, esperado):
    assert pdf.formatear_porcentaje(D(valor)) == esperado


# --- El HTML ---------------------------------------------------------------


def test_el_html_trae_todo_lo_del_documento():
    html = pdf.renderizar_html(_documento())

    for esperado in (
        "P-2026-0007",
        "Farmacia Central",
        "Av. Belgrano 123",
        "12/10/2026",
        "27/10/2026",
        "Cartel frontal",
        "$ 516.883,92",
        "Instalación",
        "$ 149.101,13",
        "$ 1.157.024,79",
        "IVA 21 %",
        "$ 242.975,21",
        "$ 1.400.000,00",
    ):
        assert esperado in html, esperado


def test_el_html_escapa_lo_que_escribe_una_persona():
    html = pdf.renderizar_html(
        _documento(
            cliente_nombre="Ferretería <b>Hnos</b> & Cía",
            items=[ItemDocumento("Letras <script>alert(1)</script>", D("10"))],
        )
    )

    assert "Ferretería &lt;b&gt;Hnos&lt;/b&gt; &amp; Cía" in html
    assert "<b>Hnos</b>" not in html
    assert "<script>" not in html


def test_sin_contacto_el_cliente_ocupa_un_solo_renglon():
    html = pdf.renderizar_html(_documento(cliente_contacto=None))

    assert "<dd>Farmacia Central</dd>" in html


def test_el_importe_usa_la_moneda_del_documento():
    html = pdf.renderizar_html(_documento(moneda="USD"))

    assert "US$ 1.400.000,00" in html


# --- El PDF ----------------------------------------------------------------


def test_sin_las_bibliotecas_el_error_dice_que_instalar(monkeypatch):
    def _sin_pango():
        raise OSError("cannot load library 'libgobject-2.0-0'")

    monkeypatch.setattr(pdf, "_cargar_weasyprint", _sin_pango)

    with pytest.raises(pdf.BibliotecasPdfFaltantes, match="GUIA-PRUEBAS-LOCALES"):
        pdf.generar_pdf(_documento())


@pytest.mark.pango
def test_genera_un_pdf_con_el_texto_del_documento():
    contenido = pdf.generar_pdf(_documento())

    assert contenido.startswith(b"%PDF")
    texto = _texto_del_pdf(contenido)
    for esperado in ("P-2026-0007", "Farmacia Central", "Instalación", "149.101,13", "1.400.000,00", "Página 1 de 1"):
        assert esperado in texto, esperado


@pytest.mark.pango
def test_la_tipografia_del_repo_queda_dentro_del_pdf():
    # Si la plantilla no encuentra la fuente, WeasyPrint usa otra sin
    # avisar y el PDF sale distinto en cada máquina.
    lector = PdfReader(io.BytesIO(pdf.generar_pdf(_documento())))

    fuentes = {str(fuente.get_object()["/BaseFont"]) for fuente in lector.pages[0]["/Resources"]["/Font"].values()}

    assert fuentes, "el PDF no declara ninguna fuente"
    assert all("Source-Sans-3" in nombre for nombre in fuentes), fuentes


@pytest.mark.pango
def test_muchos_items_ocupan_mas_de_una_hoja_y_no_se_pierde_ninguno():
    items = [ItemDocumento(f"Renglón número {n}", D("1000")) for n in range(1, 81)]

    contenido = pdf.generar_pdf(_documento(items=items))

    lector = PdfReader(io.BytesIO(contenido))
    assert len(lector.pages) > 1
    texto = _texto_del_pdf(contenido)
    for n in (1, 40, 80):
        assert f"Renglón número {n}\n" in texto or f"Renglón número {n} " in texto, n
    assert "1.400.000,00" in texto
    assert f"Página 1 de {len(lector.pages)}" in texto
```

Run: `cd backend && python -m pytest -q tests/services/presupuesto/test_pdf.py`
Expected: error al juntar las pruebas, `ImportError: cannot import name 'pdf' from 'app.services.presupuesto'`.

- [ ] **Step 5: La tipografía**

Desde la raíz del repo:

```bash
mkdir -p backend/app/services/presupuesto/plantillas/fuentes
curl -sSL -o backend/app/services/presupuesto/plantillas/fuentes/SourceSans3-Regular.ttf https://github.com/adobe-fonts/source-sans/raw/release/TTF/SourceSans3-Regular.ttf
curl -sSL -o backend/app/services/presupuesto/plantillas/fuentes/SourceSans3-Bold.ttf https://github.com/adobe-fonts/source-sans/raw/release/TTF/SourceSans3-Bold.ttf
curl -sSL -o backend/app/services/presupuesto/plantillas/fuentes/LICENSE.md https://github.com/adobe-fonts/source-sans/raw/release/LICENSE.md
ls -l backend/app/services/presupuesto/plantillas/fuentes
```

Expected: tres archivos, de 431196, 428176 y 4486 bytes. `LICENSE.md` empieza con `Copyright 2010-2024 Adobe` y nombra la SIL Open Font License 1.1. Si un `.ttf` pesa unos pocos KB, bajó una página de error en lugar de la fuente.

- [ ] **Step 6: El PDF y la plantilla**

Crear `backend/app/services/presupuesto/pdf.py`:

```python
"""Del documento del cliente al PDF, en dos pasos: plantilla → HTML → PDF.

Solo el segundo paso necesita WeasyPrint y las bibliotecas del sistema
que usa (Pango). Por eso son dos funciones: el HTML se puede armar, mirar
en el navegador y probar en cualquier máquina.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .documento import DocumentoCliente

_PLANTILLAS = Path(__file__).parent / "plantillas"

_SIMBOLOS = {"ARS": "$", "USD": "US$"}


def formatear_importe(valor: Decimal, moneda: str) -> str:
    """`1234567.8` en pesos → `$ 1.234.567,80`."""
    entero, _, decimales = f"{valor:,.2f}".partition(".")
    return f"{_SIMBOLOS.get(moneda, moneda)} {entero.replace(',', '.')},{decimales}"


def formatear_porcentaje(valor: Decimal) -> str:
    """`21.00` → `21`; `10.5` → `10,5`."""
    return f"{valor.normalize():f}".replace(".", ",")


def formatear_fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


# Con escapado: el nombre de un cliente o el texto de un ítem los escribe
# una persona, y un «<» no tiene que romper la hoja.
_entorno = Environment(loader=FileSystemLoader(_PLANTILLAS), autoescape=select_autoescape(["html"]))
_entorno.filters["importe"] = formatear_importe
_entorno.filters["porcentaje"] = formatear_porcentaje
_entorno.filters["fecha"] = formatear_fecha


def renderizar_html(documento: DocumentoCliente) -> str:
    return _entorno.get_template("presupuesto.html").render(doc=documento)


class BibliotecasPdfFaltantes(RuntimeError):
    """WeasyPrint está instalado pero no encuentra Pango."""


def _cargar_weasyprint():
    # Se importa recién al generar: WeasyPrint carga Pango al importarse,
    # y sin esas bibliotecas el resto de la app tiene que arrancar igual.
    from weasyprint import HTML

    return HTML


def generar_pdf(documento: DocumentoCliente) -> bytes:
    try:
        HTML = _cargar_weasyprint()
    except OSError as error:
        raise BibliotecasPdfFaltantes(
            "No se puede generar el PDF: faltan las bibliotecas que usa WeasyPrint (Pango). "
            "Cómo instalarlas: docs/GUIA-PRUEBAS-LOCALES.md, sección «El PDF del presupuesto»."
        ) from error
    # `base_url` es contra qué se resuelven las rutas de la plantilla: de
    # ahí sale la tipografía, que está guardada al lado.
    return HTML(string=renderizar_html(documento), base_url=_PLANTILLAS.as_uri() + "/").write_pdf()
```

Crear `backend/app/services/presupuesto/plantillas/presupuesto.html`:

```html
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Presupuesto {{ doc.codigo }}</title>
<style>
  /* La tipografía va guardada al lado para que el PDF salga igual en
     Windows y en el servidor, que no tiene las fuentes de Windows. */
  @font-face { font-family: "Source Sans 3"; font-weight: 400; src: url("fuentes/SourceSans3-Regular.ttf"); }
  @font-face { font-family: "Source Sans 3"; font-weight: 700; src: url("fuentes/SourceSans3-Bold.ttf"); }

  @page {
    size: A4;
    margin: 20mm 18mm;
    @bottom-right {
      content: "Página " counter(page) " de " counter(pages);
      font-family: "Source Sans 3"; font-size: 8pt; color: #777;
    }
  }

  body { font-family: "Source Sans 3"; font-size: 10.5pt; color: #1b1b1b; margin: 0; }

  header { display: flex; justify-content: space-between; align-items: flex-start;
           border-bottom: 2px solid #1b1b1b; padding-bottom: 8mm; }
  h1 { font-size: 20pt; margin: 0 0 2mm; }
  .codigo { font-size: 11pt; letter-spacing: .04em; }
  /* Espacio reservado: el logo y el formato de la empresa llegan en 4.4. */
  .logo { width: 45mm; height: 22mm; border: 1px dashed #999; }

  dl { display: grid; grid-template-columns: 32mm 1fr; row-gap: 1.5mm; margin: 8mm 0; }
  dt { color: #666; }
  dd { margin: 0; }

  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; border-bottom: 1px solid #1b1b1b; padding: 2mm 0;
       font-size: 9pt; text-transform: uppercase; letter-spacing: .04em; }
  td { padding: 2.2mm 0; border-bottom: 1px solid #ddd; vertical-align: top; }
  tr { break-inside: avoid; }
  .importe { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; padding-left: 6mm; }

  .totales { width: 80mm; margin: 8mm 0 0 auto; break-inside: avoid; }
  .totales td { border: 0; padding: 1.2mm 0; }
  .totales tr:last-child td { border-top: 2px solid #1b1b1b; font-weight: 700;
                              font-size: 13pt; padding-top: 2.5mm; }
</style>
</head>
<body>
  <header>
    <div>
      <h1>Presupuesto</h1>
      <div class="codigo">{{ doc.codigo }}</div>
    </div>
    <div class="logo"></div>
  </header>

  <dl>
    <dt>Cliente</dt>
    <dd>{{ doc.cliente_nombre }}{% if doc.cliente_contacto %}<br>{{ doc.cliente_contacto }}{% endif %}</dd>
    <dt>Fecha</dt>
    <dd>{{ doc.fecha | fecha }}</dd>
    <dt>Válido hasta</dt>
    <dd>{{ doc.valido_hasta | fecha }}</dd>
  </dl>

  <table>
    <thead>
      <tr><th>Detalle</th><th class="importe">Importe</th></tr>
    </thead>
    <tbody>
      {% for item in doc.items %}
      <tr><td>{{ item.texto }}</td><td class="importe">{{ item.importe | importe(doc.moneda) }}</td></tr>
      {% endfor %}
    </tbody>
  </table>

  <table class="totales">
    <tr><td>Subtotal</td><td class="importe">{{ doc.subtotal | importe(doc.moneda) }}</td></tr>
    <tr><td>IVA {{ doc.iva_pct | porcentaje }} %</td><td class="importe">{{ doc.monto_iva | importe(doc.moneda) }}</td></tr>
    <tr><td>Total</td><td class="importe">{{ doc.total | importe(doc.moneda) }}</td></tr>
  </table>
</body>
</html>
```

- [ ] **Step 7: Correr las pruebas y ver que pasan, sin ninguna salteada**

Run: `cd backend && python -m pytest -q -rs tests/services/presupuesto/test_pdf.py`
Expected: `19 passed`. Si dice `16 passed, 3 skipped`, falta la variable del Step 2 en esta terminal: no seguir hasta que las tres corran.

- [ ] **Step 8: Mirarlo**

Guardar esto **fuera del repo**, en la carpeta temporal, como `muestra_pdf.py`:

```python
"""Genera un presupuesto de muestra para mirarlo. Descartable: no va al repo.

Uso:  python muestra_pdf.py <carpeta backend> <salida.pdf>
"""
import sys
from datetime import date
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, sys.argv[1])

from app.services.presupuesto.documento import DocumentoCliente, ItemDocumento  # noqa: E402
from app.services.presupuesto.pdf import generar_pdf  # noqa: E402

documento = DocumentoCliente(
    codigo="P-2026-0007",
    cliente_nombre="Farmacia Central",
    cliente_contacto="Av. Belgrano 123 · 381 555-0101",
    fecha=date(2026, 10, 12),
    valido_hasta=date(2026, 10, 27),
    moneda="ARS",
    items=[
        ItemDocumento("Cartel frontal en chapa negra calibre 20, pintado", D("516883.92")),
        ItemDocumento("Mano de obra — armado y soldadura", D("387662.95")),
        ItemDocumento("Flete", D("103376.79")),
        ItemDocumento("Instalación en el local", D("149101.13")),
    ],
    subtotal=D("1157024.79"),
    iva_pct=D("21"),
    monto_iva=D("242975.21"),
    total=D("1400000.00"),
)

salida = Path(sys.argv[2])
salida.write_bytes(generar_pdf(documento))
print(salida)
```

Run: `python <carpeta temporal>/muestra_pdf.py backend <carpeta temporal>/muestra.pdf`, y abrir el PDF.
Expected: una hoja A4 con el título y el código arriba, el recuadro vacío del logo a la derecha, cliente y fechas, cuatro ítems con su importe, y subtotal, IVA y total alineados a la derecha, con el total en negrita. Mostrárselo a Enzo.

- [ ] **Step 9: Que GitHub instale Pango**

En `.github/workflows/ci.yml`, reemplazar:

```yaml
      - run: pip install -r requirements-dev.txt
```

por:

```yaml
      # El PDF del presupuesto se genera con WeasyPrint, que usa Pango: una
      # biblioteca del sistema que no viene con pip. Sin ella, las pruebas
      # marcadas `pango` fallan acá (en el CI no se saltean: tests/conftest.py).
      - run: sudo apt-get update && sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0

      - run: pip install -r requirements-dev.txt
```

Esto no se puede probar en local: se comprueba cuando la rama se sube, mirando que el CI pase y que su salida no tenga pruebas salteadas.

- [ ] **Step 10: La guía**

Agregar al final de `docs/GUIA-PRUEBAS-LOCALES.md`:

````markdown

---

## 5. El PDF del presupuesto

El PDF se genera con WeasyPrint. `pip` instala WeasyPrint, pero no Pango, la biblioteca del sistema que usa para armar el texto. Sin Pango la app arranca igual: la ruta del PDF responde que falta, y las pruebas que generan un PDF se saltean con el motivo a la vista (`backend/tests/conftest.py`). En GitHub no se saltean.

### En Windows

1. Instalar MSYS2. En la máquina de Enzo se hizo con `winget`, en `D:\msys64`, y no pidió permisos de administrador (ocupa unos 800 MB):

   ```powershell
   winget install --id MSYS2.MSYS2 --exact --location "D:\msys64" --silent --accept-package-agreements --accept-source-agreements
   ```

2. Instalar Pango adentro de MSYS2:

   ```powershell
   $env:MSYSTEM = "MSYS"; $env:CHERE_INVOKING = "1"
   & "D:\msys64\usr\bin\bash.exe" -lc "pacman -S --noconfirm --needed mingw-w64-x86_64-pango"
   ```

3. Decirle a WeasyPrint dónde quedaron las bibliotecas, con una variable de entorno del usuario. Vale para las terminales que se abran después:

   ```powershell
   setx WEASYPRINT_DLL_DIRECTORIES "D:\msys64\mingw64\bin"
   ```

**Cómo saber si quedó bien.** Desde `backend/`, `python -m pytest -q -rs tests/services/presupuesto/test_pdf.py` tiene que terminar sin ninguna prueba salteada. Si dice `3 skipped`, esa terminal no tiene la variable: abrir una nueva.

### En Linux y en el CI

```bash
sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

Es el paso que corre `.github/workflows/ci.yml`. La imagen de Docker del servidor (1.1) tiene que instalar lo mismo.

### La tipografía

El PDF usa Source Sans 3, guardada en `backend/app/services/presupuesto/plantillas/fuentes/` con su licencia (SIL Open Font License 1.1). Va en el repo para que el PDF salga igual en Windows y en el servidor.
````

- [ ] **Step 11: Correr toda la suite y commit** (con el ok de Enzo)

Run: `cd backend && python -m pytest -q -rs`
Expected: `488 passed`, ninguna salteada.

```bash
git add backend/requirements.txt backend/requirements-dev.txt backend/pytest.ini backend/tests/conftest.py backend/app/services/presupuesto/pdf.py backend/app/services/presupuesto/plantillas backend/tests/services/presupuesto/test_pdf.py .github/workflows/ci.yml docs/GUIA-PRUEBAS-LOCALES.md
git commit -m "feat(presupuesto): plantilla y PDF del presupuesto con WeasyPrint"
```

---

### Task 6: La ruta del PDF y un enlace en Costeo

**Files:**
- Modify: `backend/app/api/rutas_presupuesto.py`
- Modify: `frontend/src/api/presupuestos.ts`
- Modify: `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx`
- Test: `backend/tests/api/test_rutas_presupuesto.py`

**Interfaces:**
- Consumes: `calcular` (Tarea 2); `_lineas_del_presupuesto` y `_presupuesto_del_ejemplo` (Tarea 3); `armar_documento`, `PresupuestoIncompleto`, `hoy_en_argentina` (Tarea 4); `generar_pdf`, `BibliotecasPdfFaltantes`, `pdf._cargar_weasyprint` (Tarea 5).
- Produces: `GET /presupuestos/{id}/pdf`. 200 con `application/pdf` y `Content-Disposition: attachment; filename="<código>.pdf"`; 409 con `detail = {"mensaje": str, "faltantes": list[str]}` si está incompleto; 503 con `detail: str` si faltan las bibliotecas; 404 si no existe.
- Produces: `urlPdf(presupuestoId: number): string` en `frontend/src/api/presupuestos.ts`. Es provisorio: la Tarea 8 lo reemplaza por `descargarPdf`.

- [ ] **Step 1: Escribir las pruebas que fallan**

En `backend/tests/api/test_rutas_presupuesto.py`, primero los imports:

Reemplazar:

```python
import time
from decimal import Decimal

import ezdxf
import pytest
from fastapi.testclient import TestClient
```

por:

```python
import io
import re
import time
from decimal import Decimal

import ezdxf
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
```

Y agregar al final del archivo:

```python
# --- El PDF para el cliente (1.3, CART-309) --------------------------------


def _importes(texto: str) -> set[str]:
    """Todos los importes que aparecen escritos, enteros: «1.400.000,00»
    cuenta como uno solo y no como si contuviera «400.000,00»."""
    return set(re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", texto))


@pytest.mark.pango
def test_el_pdf_trae_lo_del_cliente_y_nada_de_lo_interno(cliente):
    presupuesto, lineas = _presupuesto_del_ejemplo(cliente)
    cliente.patch(f"/lineas-costo/{lineas['Instalación']['id']}/cliente", json={"precio_cliente": "150000"})
    cliente.patch(f"/lineas-costo/{lineas['Chapa']['id']}/cliente", json={"texto_cliente": "Cartel frontal"})
    cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"total_fijado": "1400000"})

    respuesta = cliente.get(f"/presupuestos/{presupuesto['id']}/pdf")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"] == "application/pdf"
    assert f'filename="{presupuesto["codigo"]}.pdf"' in respuesta.headers["content-disposition"]
    texto = "\n".join(pagina.extract_text() for pagina in PdfReader(io.BytesIO(respuesta.content)).pages)
    for esperado in (presupuesto["codigo"], "Megacarteles", "Cartel frontal", "Mano de obra", "Flete", "Instalación"):
        assert esperado in texto, esperado
    assert _importes(texto) == {
        "516.883,92", "387.662,95", "103.376,79", "149.101,13",  # los ítems
        "1.157.024,79", "242.975,21", "1.400.000,00",  # subtotal, IVA y total
    }, "ni un importe de más: los costos, el margen y el precio base no salen"
    assert "margen" not in texto.lower()
    assert "Chapa" not in texto, "la descripción interna quedó reemplazada por el texto para el cliente"


def test_el_pdf_de_un_presupuesto_incompleto_da_409_y_dice_que_falta(cliente):
    presupuesto = _crear_presupuesto(cliente)
    _linea_libre(cliente, presupuesto["id"], "Flete", "80000")

    respuesta = cliente.get(f"/presupuestos/{presupuesto['id']}/pdf")

    assert respuesta.status_code == 409
    detalle = respuesta.json()["detail"]
    assert detalle["faltantes"] == ["Falta cargar el margen, o un precio a mano en cada ítem."]
    assert "Falta cargar el margen" in detalle["mensaje"]


def test_el_pdf_de_un_presupuesto_inexistente_da_404(cliente):
    assert cliente.get("/presupuestos/999/pdf").status_code == 404


def test_sin_las_bibliotecas_la_ruta_del_pdf_da_503_y_el_resto_sigue_andando(cliente, monkeypatch):
    from app.services.presupuesto import pdf

    def _sin_pango():
        raise OSError("cannot load library 'libgobject-2.0-0'")

    monkeypatch.setattr(pdf, "_cargar_weasyprint", _sin_pango)
    presupuesto, _lineas = _presupuesto_del_ejemplo(cliente)

    respuesta = cliente.get(f"/presupuestos/{presupuesto['id']}/pdf")

    assert respuesta.status_code == 503
    assert "GUIA-PRUEBAS-LOCALES" in respuesta.json()["detail"]
    assert cliente.get(f"/presupuestos/{presupuesto['id']}/desglose").status_code == 200
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `cd backend && python -m pytest -q -rs tests/api/test_rutas_presupuesto.py -k pdf`
Expected: fallan tres de las cuatro, porque la ruta no existe y responde 404. `test_el_pdf_de_un_presupuesto_inexistente_da_404` pasa desde antes por ese mismo motivo.

- [ ] **Step 3: La ruta**

En `backend/app/api/rutas_presupuesto.py`:

Reemplazar:

```python
from fastapi import APIRouter, Depends, HTTPException, status
```

por:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
```

Reemplazar:

```python
from ..services.presupuesto.totales import Cuenta, calcular
```

por:

```python
from ..services.presupuesto.documento import PresupuestoIncompleto, armar_documento, hoy_en_argentina
from ..services.presupuesto.pdf import BibliotecasPdfFaltantes, generar_pdf
from ..services.presupuesto.totales import Cuenta, calcular
```

Y agregar al final del archivo:

```python
# --- El PDF para el cliente (1.3: `CART-309`) -----------------------------


@router.get("/presupuestos/{presupuesto_id}/pdf")
def descargar_pdf(presupuesto_id: int, sesion: Session = Depends(obtener_sesion)) -> Response:
    """El presupuesto como lo ve el cliente
    (`docs/plan/1.3-pdf-del-presupuesto/diseno.md`). Se genera cada vez
    que se pide y no se guarda: el congelado llega con el envío (1.5).

    Si al presupuesto le falta algo responde 409 con la lista
    (`diseno.md §5.4`): nunca sale un PDF con huecos."""
    presupuesto = _presupuesto_o_404(sesion, presupuesto_id)
    cuenta = calcular(presupuesto, _lineas_del_presupuesto(sesion, presupuesto_id))
    try:
        documento = armar_documento(presupuesto, cuenta, hoy_en_argentina())
    except PresupuestoIncompleto as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "mensaje": "No se puede sacar el PDF todavía. " + " ".join(error.faltantes),
                "faltantes": error.faltantes,
            },
        ) from error
    try:
        contenido = generar_pdf(documento)
    except BibliotecasPdfFaltantes as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    return Response(
        contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{presupuesto.codigo}.pdf"'},
    )
```

- [ ] **Step 4: Correr las pruebas y ver que pasan**

Run: `cd backend && python -m pytest -q -rs tests/api/test_rutas_presupuesto.py -k pdf`
Expected: `4 passed`, ninguna salteada.

Run: `cd backend && python -m pytest -q -rs`
Expected: `492 passed`, ninguna salteada.

- [ ] **Step 5: Un enlace en Costeo**

Agregar al final de `frontend/src/api/presupuestos.ts`:

```ts

export function urlPdf(presupuestoId: number): string {
  return `http://localhost:8000/presupuestos/${presupuestoId}/pdf`;
}
```

En `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx`:

Reemplazar:

```tsx
import { urlPlano } from "../../api/nesting";
```

por:

```tsx
import { urlPlano } from "../../api/nesting";
import { urlPdf } from "../../api/presupuestos";
```

Reemplazar:

```tsx
      <div className="mt-4">
        {Object.values(desglose.lineas_por_rubro)
```

por:

```tsx
      <div className="mt-4">
        <a className="text-xs underline mr-3" href={urlPdf(presupuestoId)}>
          Descargar PDF
        </a>
        {Object.values(desglose.lineas_por_rubro)
```

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `40 passed`.

Este enlace es provisorio. Si el presupuesto está incompleto, el navegador muestra la respuesta de la API como texto; la Tarea 8 lo cambia por un botón que avisa en la misma pantalla.

- [ ] **Step 6: Verlo andar** (con datos temporales)

Mirar antes quién escucha en 8000 y 5173; si la otra sesión o Enzo tienen la app levantada, no cerrarla: avisarle. Con `CARTELERIA_DATOS` en una carpeta temporal, desde `backend/`: `python -m alembic upgrade head` y `python -m uvicorn app.api.app:app --port 8000` (sin `--reload`). Desde `frontend/`: `npm run dev`.

Crear un trabajo, ir a Costeo, crear el cliente y la primera opción de presupuesto, agregar una línea de flete de 80000, poner margen 30 y tocar «Descargar PDF».
Expected: se descarga `P-<año>-0001.pdf` con un ítem de `$ 104.000,00`, subtotal `$ 104.000,00`, IVA `$ 21.840,00` y total `$ 125.840,00`.

- [ ] **Step 7: Commit** (con el ok de Enzo)

```bash
git add backend/app/api/rutas_presupuesto.py backend/tests/api/test_rutas_presupuesto.py frontend/src/api/presupuestos.ts frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx
git commit -m "feat(presupuesto): ruta que devuelve el PDF y enlace en Costeo"
```

**Fin del tramo 2.** Enzo baja el PDF de un presupuesto suyo de prueba y lo mira.

---

## Tramo 3 — La edición en Costeo

### Task 7: Leer y mostrar importes

**Files:**
- Create: `frontend/src/routes/TrabajoWorkspace/importes.ts`
- Test: `frontend/src/routes/TrabajoWorkspace/importes.test.ts`

**Interfaces:**
- Produces: `leerImporte(texto: string): string | null` — lo que escribió la persona → `"1400000.50"`, o `null`.
- Produces: `mostrarImporte(valor: string | null | undefined, moneda: string): string` — `"$ 1.400.000,50"`, o `"—"`.
- Produces: `importeParaEditar(valor: string | null | undefined): string` — `"1.400.000,50"`, sin centavos si son cero, o `""`.
- Produces: `mismoImporte(a, b): boolean`, `mostrarPorcentaje(valor): string`, `leerDias(texto: string): number | null`.

- [ ] **Step 1: Escribir las pruebas que fallan**

Crear `frontend/src/routes/TrabajoWorkspace/importes.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  importeParaEditar,
  leerDias,
  leerImporte,
  mismoImporte,
  mostrarImporte,
  mostrarPorcentaje,
} from "./importes";

describe("leerImporte", () => {
  it("lee los puntos como miles cuando arman grupos de tres", () => {
    expect(leerImporte("1.400.000")).toBe("1400000");
    expect(leerImporte("150.000")).toBe("150000");
    expect(leerImporte("1.400")).toBe("1400");
  });

  it("lee la coma como decimal y completa los centavos", () => {
    expect(leerImporte("1400000,50")).toBe("1400000.50");
    expect(leerImporte("1.400.000,5")).toBe("1400000.50");
    expect(leerImporte("0,5")).toBe("0.50");
  });

  it("acepta un solo punto como decimal si tiene uno o dos dígitos detrás", () => {
    // Es lo que devuelve la API y lo que escribe quien viene de una planilla.
    expect(leerImporte("1400000.50")).toBe("1400000.50");
    expect(leerImporte("12.5")).toBe("12.50");
  });

  it("acepta un número sin separadores, el signo de pesos y los espacios", () => {
    expect(leerImporte("150000")).toBe("150000");
    expect(leerImporte("  $ 150.000 ")).toBe("150000");
    expect(leerImporte("0150")).toBe("150");
    expect(leerImporte("0")).toBe("0");
  });

  it("rechaza lo que no se puede leer de una sola manera", () => {
    expect(leerImporte("1.4000")).toBeNull();
    expect(leerImporte("1.234,567")).toBeNull();
    expect(leerImporte("1,2,3")).toBeNull();
    expect(leerImporte("150000,")).toBeNull();
    expect(leerImporte("1 400 000")).toBeNull();
  });

  it("rechaza lo que no es un importe", () => {
    expect(leerImporte("")).toBeNull();
    expect(leerImporte("   ")).toBeNull();
    expect(leerImporte("mil")).toBeNull();
    expect(leerImporte("-100")).toBeNull();
    expect(leerImporte("1e6")).toBeNull();
  });
});

describe("mostrarImporte", () => {
  it("pone el símbolo, los miles y siempre dos decimales", () => {
    expect(mostrarImporte("1400000.5", "ARS")).toBe("$ 1.400.000,50");
    expect(mostrarImporte("516883.92", "ARS")).toBe("$ 516.883,92");
    expect(mostrarImporte("0", "ARS")).toBe("$ 0,00");
    expect(mostrarImporte("999", "ARS")).toBe("$ 999,00");
  });

  it("usa el símbolo de la moneda, o su código si no lo conoce", () => {
    expect(mostrarImporte("1500", "USD")).toBe("US$ 1.500,00");
    expect(mostrarImporte("10", "EUR")).toBe("EUR 10,00");
  });

  it("muestra un negativo con el signo delante del número", () => {
    expect(mostrarImporte("-257024.79", "ARS")).toBe("$ -257.024,79");
  });

  it("muestra una raya cuando no hay valor", () => {
    expect(mostrarImporte(null, "ARS")).toBe("—");
    expect(mostrarImporte(undefined, "ARS")).toBe("—");
    expect(mostrarImporte("", "ARS")).toBe("—");
  });
});

describe("importeParaEditar", () => {
  it("no muestra los centavos si son cero", () => {
    expect(importeParaEditar("150000.00")).toBe("150.000");
    expect(importeParaEditar("1400000")).toBe("1.400.000");
  });

  it("muestra los centavos si los hay", () => {
    expect(importeParaEditar("1400000.5")).toBe("1.400.000,50");
  });

  it("deja el campo vacío cuando no hay valor", () => {
    expect(importeParaEditar(null)).toBe("");
  });

  it("devuelve algo que leerImporte entiende igual", () => {
    for (const valor of ["150000", "1400000.50", "999.99", "0", "1234.5"]) {
      expect(mismoImporte(leerImporte(importeParaEditar(valor)), valor)).toBe(true);
    }
  });
});

describe("mismoImporte", () => {
  it("compara por valor y no por cómo está escrito", () => {
    expect(mismoImporte("150000", "150000.00")).toBe(true);
    expect(mismoImporte("150000.50", "150000.5")).toBe(true);
    expect(mismoImporte("150000", "150000.01")).toBe(false);
  });

  it("nunca da igual si falta alguno de los dos", () => {
    expect(mismoImporte(null, "0")).toBe(false);
    expect(mismoImporte(null, null)).toBe(false);
  });
});

describe("mostrarPorcentaje", () => {
  it("usa coma y dos decimales", () => {
    expect(mostrarPorcentaje("28.56")).toBe("28,56 %");
    expect(mostrarPorcentaje("30")).toBe("30,00 %");
    expect(mostrarPorcentaje("-12.5")).toBe("-12,50 %");
  });

  it("muestra una raya cuando no hay valor", () => {
    expect(mostrarPorcentaje(null)).toBe("—");
  });
});

describe("leerDias", () => {
  it("acepta un entero mayor que cero", () => {
    expect(leerDias("15")).toBe(15);
    expect(leerDias(" 30 ")).toBe(30);
    expect(leerDias("015")).toBe(15);
  });

  it("rechaza cero, negativos, decimales y texto", () => {
    expect(leerDias("0")).toBeNull();
    expect(leerDias("-3")).toBeNull();
    expect(leerDias("1,5")).toBeNull();
    expect(leerDias("1.5")).toBeNull();
    expect(leerDias("")).toBeNull();
    expect(leerDias("quince")).toBeNull();
  });
});
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `cd frontend && npx vitest run src/routes/TrabajoWorkspace/importes.test.ts`
Expected: FAIL, no encuentra `./importes`.

- [ ] **Step 3: Escribir las funciones**

Crear `frontend/src/routes/TrabajoWorkspace/importes.ts`:

```ts
// Leer y mostrar importes como se escriben acá: punto para los miles y
// coma para los decimales. La API habla en el otro formato («1400000.50»),
// y lo que escribe una persona no se le manda sin pasar por acá.

const SIMBOLOS: Record<string, string> = { ARS: "$", USD: "US$" };

/** Lo que escribió la persona → el número que espera la API, o `null` si
 * no es un importe. Vacío también es `null`: quien llama decide si eso
 * quiere decir «quitar».
 *
 * La coma siempre es el decimal. El punto es separador de miles cuando
 * arma grupos de tres («1.400.000», «1.400»), y decimal cuando es uno
 * solo con uno o dos dígitos detrás («1400000.50», «12.5»). */
export function leerImporte(texto: string): string | null {
  const limpio = texto.trim().replace(/^\$\s*/, "");
  if (limpio === "") return null;

  let entero = limpio;
  let decimales = "";
  if (limpio.includes(",")) {
    const partes = limpio.split(",");
    if (partes.length !== 2 || !/^\d{1,2}$/.test(partes[1])) return null;
    [entero, decimales] = partes;
  } else if (/^\d+\.\d{1,2}$/.test(limpio)) {
    [entero, decimales] = limpio.split(".");
  }

  if (/^\d{1,3}(\.\d{3})+$/.test(entero)) entero = entero.replace(/\./g, "");
  if (!/^\d+$/.test(entero)) return null;

  const sinCeros = entero.replace(/^0+(?=\d)/, "");
  return decimales ? `${sinCeros}.${decimales.padEnd(2, "0")}` : sinCeros;
}

function conMiles(valor: number): [string, string] {
  const [entero, decimales] = Math.abs(valor).toFixed(2).split(".");
  return [`${valor < 0 ? "-" : ""}${entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".")}`, decimales];
}

function aNumero(valor: string | null | undefined): number | null {
  if (valor === null || valor === undefined || valor.trim() === "") return null;
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : null;
}

/** «1400000.5» en pesos → «$ 1.400.000,50». Sin `Intl`: el formato no
 * puede depender de qué idiomas trae instalados el navegador. */
export function mostrarImporte(valor: string | null | undefined, moneda: string): string {
  const numero = aNumero(valor);
  if (numero === null) return "—";
  const [entero, decimales] = conMiles(numero);
  return `${SIMBOLOS[moneda] ?? moneda} ${entero},${decimales}`;
}

/** Para poner en un campo de texto: «150000.00» → «150.000», y
 * «1400000.5» → «1.400.000,50». Lo que devuelve lo entiende `leerImporte`. */
export function importeParaEditar(valor: string | null | undefined): string {
  const numero = aNumero(valor);
  if (numero === null) return "";
  const [entero, decimales] = conMiles(numero);
  return decimales === "00" ? entero : `${entero},${decimales}`;
}

/** Si dos importes valen lo mismo, se escriban como se escriban. */
export function mismoImporte(a: string | null | undefined, b: string | null | undefined): boolean {
  const [x, y] = [aNumero(a), aNumero(b)];
  return x !== null && y !== null && Math.round(x * 100) === Math.round(y * 100);
}

/** «28.56» → «28,56 %». */
export function mostrarPorcentaje(valor: string | null | undefined): string {
  const numero = aNumero(valor);
  return numero === null ? "—" : `${numero.toFixed(2).replace(".", ",")} %`;
}

/** Los días de validez: un entero mayor que cero, o `null`. */
export function leerDias(texto: string): number | null {
  const limpio = texto.trim();
  if (!/^\d+$/.test(limpio)) return null;
  const dias = Number(limpio);
  return dias > 0 ? dias : null;
}
```

- [ ] **Step 4: Correr las pruebas y ver que pasan**

Run: `cd frontend && npm test`
Expected: `60 passed`.

- [ ] **Step 5: Commit** (con el ok de Enzo)

```bash
git add frontend/src/routes/TrabajoWorkspace/importes.ts frontend/src/routes/TrabajoWorkspace/importes.test.ts
git commit -m "feat(presupuesto): leer y mostrar importes en la pantalla"
```

---

### Task 8: La sección «Presupuesto para el cliente»

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/presupuestos.ts`
- Modify: `frontend/src/hooks/usePresupuestos.ts`
- Create: `frontend/src/routes/TrabajoWorkspace/PresupuestoClienteSeccion.tsx`
- Modify: `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx`

**Interfaces:**
- Consumes: las rutas de las Tareas 3 y 6; las funciones de `importes.ts` (Tarea 7).
- Produces: `apiGetArchivo(path: string): Promise<Blob>` en `client.ts`.
- Produces: en `api/presupuestos.ts`, los tipos `ItemCliente` y los campos nuevos de `Presupuesto`, `LineaCosto`, `Totales` y `Desglose`; `actualizarPresupuesto(presupuestoId, datos)`, `actualizarLineaCliente(lineaId, datos)`, `descargarPdf(presupuestoId): Promise<Blob>`. Desaparece `urlPdf`.
- Produces: en `hooks/usePresupuestos.ts`, `useActualizarPresupuesto(presupuestoId)`, `useActualizarLineaCliente(presupuestoId)` y la función interna `useRefrescarPresupuesto(presupuestoId)`, que usa también la Tarea 9.

Esta tarea no tiene prueba automática propia: el frontend no tiene pruebas con navegador. Lo que protege es el compilador y el recorrido a mano del Step 6.

- [ ] **Step 1: Bajar un archivo desde la API**

En `frontend/src/api/client.ts`:

Reemplazar:

```ts
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
```

por:

```ts
/** Para bajar un archivo (el PDF del presupuesto). Si la API responde
 * con un error, tira el mismo `ApiError` que el resto. */
export async function apiGetArchivo(path: string): Promise<Blob> {
  const respuesta = await fetch(`${BASE_URL}${path}`);
  if (!respuesta.ok) {
    return manejarRespuesta<never>(respuesta);
  }
  return respuesta.blob();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
```

- [ ] **Step 2: Lo que la sección le pide a la API**

En `frontend/src/api/presupuestos.ts`:

Reemplazar:

```ts
import { apiGet, apiPatch, apiPost } from "./client";
```

por:

```ts
import { apiGet, apiGetArchivo, apiPatch, apiPost } from "./client";
```

Reemplazar:

```ts
  margen_pct: string | null;
  iva_pct: string | null;
}

export interface LineaMaterial {
```

por:

```ts
  margen_pct: string | null;
  iva_pct: string | null;
  total_fijado: string | null;
}

export interface LineaMaterial {
```

Reemplazar:

```ts
  valor_override: string | null;
  override_por: string | null;
}
```

por:

```ts
  valor_override: string | null;
  override_por: string | null;
  texto_cliente: string | null;
  precio_cliente: string | null;
}
```

Reemplazar:

```ts
  monto_margen: string | null;
  precio_venta: string | null;
  iva_pct: string | null;
  monto_iva: string | null;
  total: string | null;
  advertencias: string[];
}

export interface Desglose {
  presupuesto: Presupuesto;
  cliente: Cliente;
  lineas_por_rubro: Record<string, LineaCosto[]>;
  totales: Totales;
}
```

por:

```ts
  monto_margen: string | null;
  margen_resultante_pct: string | null;
  precio_venta: string | null;
  iva_pct: string | null;
  monto_iva: string | null;
  total: string | null;
  total_fijado: string | null;
  advertencias: string[];
}

/** Una línea vista desde el precio: lo que va a leer el cliente al lado
 * de lo que cuesta. `precio_base` es el escrito a mano o costo más margen;
 * `precio_final` es el que sale en el presupuesto. */
export interface ItemCliente {
  linea_id: number;
  rubro: string;
  texto: string;
  costo: string | null;
  precio_base: string | null;
  a_mano: boolean;
  precio_final: string | null;
}

export interface Desglose {
  presupuesto: Presupuesto;
  cliente: Cliente;
  lineas_por_rubro: Record<string, LineaCosto[]>;
  totales: Totales;
  items_cliente: ItemCliente[];
  /** Lo que impide sacar el PDF. Vacía = el presupuesto está completo. */
  faltantes: string[];
}
```

Reemplazar:

```ts
export function urlPdf(presupuestoId: number): string {
  return `http://localhost:8000/presupuestos/${presupuestoId}/pdf`;
}
```

por:

```ts
export function actualizarPresupuesto(
  presupuestoId: number,
  datos: { cliente_id?: number; validez_dias?: number; total_fijado?: string | null }
): Promise<Presupuesto> {
  return apiPatch<Presupuesto>(`/presupuestos/${presupuestoId}`, datos);
}

export function actualizarLineaCliente(
  lineaId: number,
  datos: { texto_cliente?: string | null; precio_cliente?: string | null }
): Promise<LineaCosto> {
  return apiPatch<LineaCosto>(`/lineas-costo/${lineaId}/cliente`, datos);
}

/** El PDF para el cliente. Si al presupuesto le falta algo, la API
 * responde 409 y esto tira un `ApiError` con el motivo. */
export function descargarPdf(presupuestoId: number): Promise<Blob> {
  return apiGetArchivo(`/presupuestos/${presupuestoId}/pdf`);
}
```

En `frontend/src/hooks/usePresupuestos.ts`:

Reemplazar:

```ts
import {
  actualizarMargenEIva,
  aplicarOverride,
```

por:

```ts
import {
  actualizarLineaCliente,
  actualizarMargenEIva,
  actualizarPresupuesto,
  aplicarOverride,
```

Reemplazar:

```ts
export function useDesglose(presupuestoId: number | null) {
```

por:

```ts
/** Lo que hay que volver a pedir cuando cambia algo del presupuesto. */
function useRefrescarPresupuesto(presupuestoId: number) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["presupuestos"] });
    queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] });
    queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] });
  };
}

export function useActualizarPresupuesto(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: (datos: Parameters<typeof actualizarPresupuesto>[1]) => actualizarPresupuesto(presupuestoId, datos),
    onSuccess: refrescar,
  });
}

export function useActualizarLineaCliente(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: ({ lineaId, datos }: { lineaId: number; datos: Parameters<typeof actualizarLineaCliente>[1] }) =>
      actualizarLineaCliente(lineaId, datos),
    onSuccess: refrescar,
  });
}

export function useDesglose(presupuestoId: number | null) {
```

- [ ] **Step 3: La sección**

Crear `frontend/src/routes/TrabajoWorkspace/PresupuestoClienteSeccion.tsx`:

```tsx
import { useRef, useState } from "react";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";
import { descargarPdf, type ItemCliente, type LineaCosto } from "../../api/presupuestos";
import {
  useActualizarLineaCliente,
  useActualizarPresupuesto,
  useClientes,
  useDesglose,
} from "../../hooks/usePresupuestos";
import {
  importeParaEditar,
  leerDias,
  leerImporte,
  mismoImporte,
  mostrarImporte,
  mostrarPorcentaje,
} from "./importes";

function bajarArchivo(contenido: Blob, nombre: string) {
  const url = URL.createObjectURL(contenido);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  // El navegador ya tomó el archivo: se suelta la dirección temporal.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Lo que va a leer el cliente: el texto y el precio de cada ítem y el
 * total, editables, y el PDF (`docs/plan/1.3-pdf-del-presupuesto/diseno.md §8`).
 * Cada campo se guarda al salir de él, igual que el margen y el IVA. */
export default function PresupuestoClienteSeccion({ presupuestoId }: { presupuestoId: number }) {
  const { data: desglose } = useDesglose(presupuestoId);
  const { data: clientes } = useClientes();
  const actualizarPresupuesto = useActualizarPresupuesto(presupuestoId);
  const actualizarLinea = useActualizarLineaCliente(presupuestoId);
  const [error, setError] = useState<string | null>(null);
  const [descargando, setDescargando] = useState(false);
  const ultimoGuardado = useRef<Promise<void>>(Promise.resolve());

  if (!desglose) return null;
  const { presupuesto, totales, items_cliente: items, faltantes } = desglose;
  const moneda = presupuesto.moneda;
  const lineas = new Map<number, LineaCosto>(
    Object.values(desglose.lineas_por_rubro)
      .flat()
      .map((linea) => [linea.id, linea])
  );
  const totalFijado = totales.total_fijado !== null;
  const bajoElCosto = totales.monto_margen !== null && Number(totales.monto_margen) < 0;

  function guardar(accion: () => Promise<unknown>, fallback: string) {
    setError(null);
    ultimoGuardado.current = accion().then(
      () => undefined,
      (e: unknown) => setError(e instanceof ApiError ? e.message : fallback)
    );
  }

  function alSalirDelTexto(item: ItemCliente, campo: HTMLInputElement) {
    const linea = lineas.get(item.linea_id);
    if (!linea) return;
    const escrito = campo.value.trim();
    // Vacío, o igual a la descripción interna: se vuelve a usar la descripción.
    const nuevo = escrito === "" || escrito === linea.descripcion ? null : escrito;
    if (nuevo === linea.texto_cliente) {
      campo.value = item.texto;
      return;
    }
    guardar(
      () => actualizarLinea.mutateAsync({ lineaId: item.linea_id, datos: { texto_cliente: nuevo } }),
      "No se pudo guardar el texto."
    );
  }

  function quitarPrecio(item: ItemCliente) {
    guardar(
      () => actualizarLinea.mutateAsync({ lineaId: item.linea_id, datos: { precio_cliente: null } }),
      "No se pudo quitar el precio."
    );
  }

  function alSalirDelPrecio(item: ItemCliente, campo: HTMLInputElement) {
    const escrito = campo.value.trim();
    const actual = importeParaEditar(item.precio_base);
    if (escrito === "") {
      if (item.a_mano) quitarPrecio(item);
      else campo.value = actual;
      return;
    }
    const importe = leerImporte(escrito);
    if (importe === null) {
      setError(`«${escrito}» no es un importe. Escribilo como 150.000 o como 150000,50.`);
      campo.value = actual;
      return;
    }
    // Entrar y salir del campo sin cambiar el número no lo vuelve «a mano».
    if (mismoImporte(importe, item.precio_base)) {
      campo.value = actual;
      return;
    }
    guardar(
      () => actualizarLinea.mutateAsync({ lineaId: item.linea_id, datos: { precio_cliente: importe } }),
      "No se pudo guardar el precio."
    );
  }

  function quitarTotal() {
    guardar(() => actualizarPresupuesto.mutateAsync({ total_fijado: null }), "No se pudo quitar el total fijado.");
  }

  function alSalirDelTotal(campo: HTMLInputElement) {
    const escrito = campo.value.trim();
    const actual = importeParaEditar(totales.total);
    if (escrito === "") {
      if (totalFijado) quitarTotal();
      else campo.value = actual;
      return;
    }
    const importe = leerImporte(escrito);
    if (importe === null || Number(importe) <= 0) {
      setError(`«${escrito}» no sirve como total. Escribilo como 1.400.000 o como 1400000,50.`);
      campo.value = actual;
      return;
    }
    if (mismoImporte(importe, totales.total)) {
      campo.value = actual;
      return;
    }
    guardar(() => actualizarPresupuesto.mutateAsync({ total_fijado: importe }), "No se pudo fijar el total.");
  }

  function alSalirDeLaValidez(campo: HTMLInputElement) {
    const dias = leerDias(campo.value);
    if (dias === null) {
      setError("La validez tiene que ser una cantidad de días, mayor que cero.");
      campo.value = String(presupuesto.validez_dias);
      return;
    }
    if (dias === presupuesto.validez_dias) return;
    guardar(() => actualizarPresupuesto.mutateAsync({ validez_dias: dias }), "No se pudo cambiar la validez.");
  }

  async function alDescargar() {
    setError(null);
    setDescargando(true);
    try {
      // Al venir de editar un campo, su guardado sale al perder el foco,
      // un instante antes de este clic: se espera a que termine para que
      // el PDF traiga lo recién escrito.
      await ultimoGuardado.current;
      bajarArchivo(await descargarPdf(presupuestoId), `${presupuesto.codigo}.pdf`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo generar el PDF.");
    } finally {
      setDescargando(false);
    }
  }

  return (
    <div className="mt-6 border-t border-line pt-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-medium">Presupuesto para el cliente</h2>
        <label className="text-sm">
          Válido por{" "}
          <input
            key={presupuesto.validez_dias}
            className="border border-line rounded px-2 py-1 w-16 font-mono bg-paper"
            defaultValue={presupuesto.validez_dias}
            onBlur={(e) => alSalirDeLaValidez(e.target)}
          />{" "}
          días
        </label>
      </div>

      <label className="block text-sm mb-4">
        Cliente:{" "}
        <select
          className="border border-line rounded px-2 py-1 bg-paper"
          value={presupuesto.cliente_id}
          onChange={(e) => {
            const clienteId = Number(e.target.value);
            guardar(() => actualizarPresupuesto.mutateAsync({ cliente_id: clienteId }), "No se pudo cambiar el cliente.");
          }}
        >
          {clientes?.map((cliente) => (
            <option key={cliente.id} value={cliente.id}>
              {cliente.nombre}
            </option>
          ))}
        </select>
      </label>

      {error && (
        <div className="mb-4">
          <Banner variante="error">{error}</Banner>
        </div>
      )}

      <table className="w-full text-sm mb-4">
        <thead>
          <tr className="text-left border-b border-line">
            <th>Texto para el cliente</th>
            <th className="text-right">Costo</th>
            <th className="text-right">Precio base</th>
            <th className="text-right">En el presupuesto</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.linea_id} className="border-b border-line">
              <td className="py-1 pr-2">
                <input
                  key={item.texto}
                  className="border border-line rounded px-2 py-1 bg-paper w-full"
                  defaultValue={item.texto}
                  maxLength={300}
                  onBlur={(e) => alSalirDelTexto(item, e.target)}
                />
              </td>
              <td className="font-mono text-right">{mostrarImporte(item.costo, moneda)}</td>
              <td className="text-right whitespace-nowrap">
                <input
                  key={`${item.precio_base}-${item.a_mano}`}
                  className="border border-line rounded px-2 py-1 bg-paper w-32 font-mono text-right"
                  defaultValue={importeParaEditar(item.precio_base)}
                  placeholder="—"
                  onBlur={(e) => alSalirDelPrecio(item, e.target)}
                />
                {item.a_mano ? (
                  <button className="ml-2 text-xs underline text-bronze" onClick={() => quitarPrecio(item)}>
                    a mano · quitar
                  </button>
                ) : (
                  <span className="ml-2 text-xs opacity-60">calculado</span>
                )}
              </td>
              <td className="font-mono text-right">{mostrarImporte(item.precio_final, moneda)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex flex-wrap justify-between items-start gap-4 mb-4 text-sm">
        <div>
          <label>
            Total final:{" "}
            <input
              key={`${totales.total}-${totalFijado}`}
              className="border border-line rounded px-2 py-1 w-36 font-mono text-right bg-paper"
              defaultValue={importeParaEditar(totales.total)}
              placeholder="—"
              onBlur={(e) => alSalirDelTotal(e.target)}
            />
          </label>
          {totalFijado ? (
            <button className="ml-2 text-xs underline text-bronze" onClick={quitarTotal}>
              fijado · quitar
            </button>
          ) : (
            <span className="ml-2 text-xs opacity-60">la suma de los ítems más IVA</span>
          )}
          <p className="font-mono mt-1 opacity-80">
            Subtotal {mostrarImporte(totales.precio_venta, moneda)} · IVA {mostrarImporte(totales.monto_iva, moneda)}
          </p>
        </div>
        <p className={bajoElCosto ? "text-conflict" : ""}>
          Margen resultante:{" "}
          <span className="font-mono">
            {mostrarPorcentaje(totales.margen_resultante_pct)} ({mostrarImporte(totales.monto_margen, moneda)})
          </span>
        </p>
      </div>

      {bajoElCosto && (
        <div className="mb-4">
          <Banner variante="error">El precio queda por debajo del costo.</Banner>
        </div>
      )}

      {faltantes.length > 0 && (
        <div className="mb-4">
          <Banner variante="aviso">
            Para sacar el PDF falta:
            <ul className="list-disc ml-5">
              {faltantes.map((faltante) => (
                <li key={faltante}>{faltante}</li>
              ))}
            </ul>
          </Banner>
        </div>
      )}

      <button
        className="bg-cut text-paper rounded px-4 py-2 text-sm disabled:opacity-50"
        disabled={faltantes.length > 0 || descargando}
        onClick={alDescargar}
      >
        {descargando ? "Generando…" : "Descargar PDF"}
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Mostrarla en Costeo, en lugar del enlace provisorio**

En `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx`:

Reemplazar:

```tsx
import { urlPlano } from "../../api/nesting";
import { urlPdf } from "../../api/presupuestos";
```

por:

```tsx
import { urlPlano } from "../../api/nesting";
```

Reemplazar:

```tsx
import ResumenAnidado from "../../components/ResumenAnidado";
```

por:

```tsx
import ResumenAnidado from "../../components/ResumenAnidado";
import PresupuestoClienteSeccion from "./PresupuestoClienteSeccion";
```

Reemplazar:

```tsx
      <div className="mt-4">
        <a className="text-xs underline mr-3" href={urlPdf(presupuestoId)}>
          Descargar PDF
        </a>
        {Object.values(desglose.lineas_por_rubro)
```

por:

```tsx
      <div className="mt-4">
        {Object.values(desglose.lineas_por_rubro)
```

Reemplazar:

```tsx
          <SeccionDesglose presupuestoId={presupuestoActivo.id} />
```

por:

```tsx
          <SeccionDesglose presupuestoId={presupuestoActivo.id} />
          <PresupuestoClienteSeccion key={presupuestoActivo.id} presupuestoId={presupuestoActivo.id} />
```

- [ ] **Step 5: Compilar y correr las pruebas**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `60 passed`.

- [ ] **Step 6: Recorrerla a mano** (con datos temporales, como en el Step 6 de la Tarea 6)

Sobre un presupuesto nuevo con las cuatro líneas del ejemplo del diseño (Chapa 400000, Mano de obra 300000, Flete 80000, Instalación 120000, cada una con cantidad 1), **todavía sin margen**:

1. El botón «Descargar PDF» está apagado y la lista dice «Falta cargar el margen, o un precio a mano en cada ítem.».
2. Cargar margen 30 en la sección de arriba: la tabla muestra los cuatro ítems con precio base 520.000, 390.000, 104.000 y 156.000, todos «calculado», el total final dice 1.415.700 y el botón se prende.
3. Escribir `150.000` en el precio de Instalación y salir del campo: pasa a «a mano · quitar» y el total baja a 1.408.440.
4. Entrar y salir del precio de Chapa sin cambiarlo: sigue «calculado».
5. Escribir `1.400.000` en el total final y salir: queda «fijado · quitar», la columna «En el presupuesto» muestra 516.883,92 · 387.662,95 · 103.376,79 · 149.101,13 y el margen resultante dice 28,56 %.
6. Escribir `mil` en un precio: aparece el aviso y el campo vuelve a su valor.
7. Cambiar el texto de Chapa por `Cartel frontal`, y sin hacer clic en ningún otro lado tocar «Descargar PDF»: el PDF trae «Cartel frontal». Es el primer punto del Review Focus.
8. Escribir `500.000` en el total final: aparece «El precio queda por debajo del costo» y el botón sigue prendido.
9. Tocar «fijado · quitar»: el total vuelve a 1.408.440 e Instalación sigue en 150.000.

- [ ] **Step 7: Commit** (con el ok de Enzo)

```bash
git add frontend/src/api/client.ts frontend/src/api/presupuestos.ts frontend/src/hooks/usePresupuestos.ts frontend/src/routes/TrabajoWorkspace/PresupuestoClienteSeccion.tsx frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx
git commit -m "feat(presupuesto): seccion Presupuesto para el cliente en Costeo"
```

---

### Task 9: Editar y borrar las líneas cargadas a mano

**Files:**
- Modify: `frontend/src/api/presupuestos.ts`
- Modify: `frontend/src/hooks/usePresupuestos.ts`
- Modify: `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx`

**Interfaces:**
- Consumes: `PATCH /lineas-costo/{id}` y `DELETE /lineas-costo/{id}`, que ya existen en la API y rechazan las líneas de material; `useRefrescarPresupuesto` (Tarea 8); `leerImporte` e `importeParaEditar` (Tarea 7).
- Produces: `actualizarLineaLibre(lineaId, datos)` y `eliminarLineaLibre(lineaId)` en `api/presupuestos.ts`; `useActualizarLineaLibre(presupuestoId)` y `useEliminarLineaLibre(presupuestoId)` en los hooks.

De paso, la cantidad y el precio unitario de una línea nueva pasan por `leerImporte`. Hoy se mandan como se escriben, y «1.500,50» vuelve como «Error 422». Con el cambio, agregar y editar leen los números igual.

- [ ] **Step 1: Lo que le pide a la API**

En `frontend/src/api/presupuestos.ts`:

Reemplazar:

```ts
import { apiGet, apiGetArchivo, apiPatch, apiPost } from "./client";
```

por:

```ts
import { apiDelete, apiGet, apiGetArchivo, apiPatch, apiPost } from "./client";
```

Reemplazar:

```ts
export function aplicarOverride(
```

por:

```ts
export function actualizarLineaLibre(
  lineaId: number,
  datos: { descripcion: string; cantidad: string; precio_unitario: string }
): Promise<LineaCosto> {
  return apiPatch<LineaCosto>(`/lineas-costo/${lineaId}`, datos);
}

export function eliminarLineaLibre(lineaId: number): Promise<void> {
  return apiDelete(`/lineas-costo/${lineaId}`);
}

export function aplicarOverride(
```

En `frontend/src/hooks/usePresupuestos.ts`:

Reemplazar:

```ts
import {
  actualizarLineaCliente,
  actualizarMargenEIva,
```

por:

```ts
import {
  actualizarLineaCliente,
  actualizarLineaLibre,
  actualizarMargenEIva,
```

Reemplazar:

```ts
  duplicarPresupuesto,
  listarClientes,
```

por:

```ts
  duplicarPresupuesto,
  eliminarLineaLibre,
  listarClientes,
```

Reemplazar:

```ts
export function useDesglose(presupuestoId: number | null) {
```

por:

```ts
export function useActualizarLineaLibre(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: ({ lineaId, datos }: { lineaId: number; datos: Parameters<typeof actualizarLineaLibre>[1] }) =>
      actualizarLineaLibre(lineaId, datos),
    onSuccess: refrescar,
  });
}

export function useEliminarLineaLibre(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: (lineaId: number) => eliminarLineaLibre(lineaId),
    onSuccess: refrescar,
  });
}

export function useDesglose(presupuestoId: number | null) {
```

- [ ] **Step 2: Los botones y el renglón de edición**

En `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx`:

Reemplazar:

```tsx
import {
  useAplicarOverride,
  useActualizarMargenEIva,
```

por:

```tsx
import {
  useAplicarOverride,
  useActualizarLineaLibre,
  useActualizarMargenEIva,
```

Reemplazar:

```tsx
  useDuplicarPresupuesto,
  usePresupuestosDelTrabajo,
```

por:

```tsx
  useDuplicarPresupuesto,
  useEliminarLineaLibre,
  usePresupuestosDelTrabajo,
```

Reemplazar:

```tsx
import PresupuestoClienteSeccion from "./PresupuestoClienteSeccion";
```

por:

```tsx
import type { LineaCosto } from "../../api/presupuestos";
import PresupuestoClienteSeccion from "./PresupuestoClienteSeccion";
import { importeParaEditar, leerImporte } from "./importes";
```

Reemplazar:

```tsx
  const margenEIva = useActualizarMargenEIva(presupuestoId);
  const [nuevaLinea, setNuevaLinea] = useState({
```

por:

```tsx
  const margenEIva = useActualizarMargenEIva(presupuestoId);
  const actualizarLinea = useActualizarLineaLibre(presupuestoId);
  const eliminarLinea = useEliminarLineaLibre(presupuestoId);
  // La línea que se está editando, con lo que hay escrito en cada campo.
  const [edicion, setEdicion] = useState<{
    id: number;
    descripcion: string;
    cantidad: string;
    precio_unitario: string;
  } | null>(null);
  const [nuevaLinea, setNuevaLinea] = useState({
```

Reemplazar:

```tsx
  async function alCrearLinea() {
    if (!nuevaLinea.descripcion.trim()) return;
    setError(null);
    try {
      await crearLinea.mutateAsync(nuevaLinea);
      setNuevaLinea((n) => ({ ...n, descripcion: "" }));
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo agregar la línea."));
    }
  }
```

por:

```tsx
  const NUMEROS_INVALIDOS = "La cantidad y el precio unitario tienen que ser números, como 2 o 1.500,50.";

  async function alCrearLinea() {
    if (!nuevaLinea.descripcion.trim()) return;
    const cantidad = leerImporte(nuevaLinea.cantidad);
    const precio = leerImporte(nuevaLinea.precio_unitario);
    if (cantidad === null || precio === null) {
      setError(NUMEROS_INVALIDOS);
      return;
    }
    setError(null);
    try {
      await crearLinea.mutateAsync({ ...nuevaLinea, cantidad, precio_unitario: precio });
      setNuevaLinea((n) => ({ ...n, descripcion: "" }));
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo agregar la línea."));
    }
  }

  function alEmpezarEdicion(linea: LineaCosto) {
    setError(null);
    setEdicion({
      id: linea.id,
      descripcion: linea.descripcion,
      cantidad: importeParaEditar(linea.cantidad),
      precio_unitario: importeParaEditar(linea.precio_unitario),
    });
  }

  async function alGuardarEdicion() {
    if (!edicion) return;
    const descripcion = edicion.descripcion.trim();
    const cantidad = leerImporte(edicion.cantidad);
    const precio = leerImporte(edicion.precio_unitario);
    if (!descripcion) {
      setError("La línea necesita una descripción.");
      return;
    }
    if (cantidad === null || precio === null) {
      setError(NUMEROS_INVALIDOS);
      return;
    }
    setError(null);
    try {
      await actualizarLinea.mutateAsync({
        lineaId: edicion.id,
        datos: { descripcion, cantidad, precio_unitario: precio },
      });
      setEdicion(null);
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo guardar la línea."));
    }
  }

  async function alBorrar(linea: LineaCosto) {
    if (!window.confirm(`¿Borrar la línea «${linea.descripcion}»?`)) return;
    setError(null);
    try {
      await eliminarLinea.mutateAsync(linea.id);
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo borrar la línea."));
    }
  }
```

Reemplazar:

```tsx
              {lineas.map((linea) => (
                <tr key={linea.id} className="border-b border-line">
                  <td>{linea.descripcion}</td>
                  <td className="font-mono">{linea.cantidad ?? "—"}</td>
                  <td className="font-mono">
                    {linea.moneda} {Number(linea.valor_override ?? linea.valor_calculado ?? 0).toFixed(2)}
                    {linea.valor_override !== null && <span className="ml-1 text-bronze text-xs">override</span>}
                  </td>
                  <td>
                    <button className="text-xs underline" onClick={() => alAplicarOverride(linea.id)}>
                      Override
                    </button>
                  </td>
                </tr>
              ))}
```

por:

```tsx
              {lineas.map((linea) =>
                edicion?.id === linea.id ? (
                  <tr key={linea.id} className="border-b border-line">
                    <td className="py-1 pr-2">
                      <input
                        className="border border-line rounded px-2 py-1 bg-paper w-full"
                        value={edicion.descripcion}
                        onChange={(e) => setEdicion({ ...edicion, descripcion: e.target.value })}
                      />
                    </td>
                    <td className="pr-2">
                      <input
                        className="border border-line rounded px-2 py-1 bg-paper w-20 font-mono"
                        value={edicion.cantidad}
                        onChange={(e) => setEdicion({ ...edicion, cantidad: e.target.value })}
                      />
                    </td>
                    <td className="pr-2">
                      <input
                        className="border border-line rounded px-2 py-1 bg-paper w-28 font-mono"
                        value={edicion.precio_unitario}
                        onChange={(e) => setEdicion({ ...edicion, precio_unitario: e.target.value })}
                      />
                    </td>
                    <td className="whitespace-nowrap">
                      <button className="text-xs underline" onClick={alGuardarEdicion}>
                        Guardar
                      </button>
                      <button className="text-xs underline ml-2" onClick={() => setEdicion(null)}>
                        Cancelar
                      </button>
                    </td>
                  </tr>
                ) : (
                  <tr key={linea.id} className="border-b border-line">
                    <td>{linea.descripcion}</td>
                    <td className="font-mono">{linea.cantidad ?? "—"}</td>
                    <td className="font-mono">
                      {linea.moneda} {Number(linea.valor_override ?? linea.valor_calculado ?? 0).toFixed(2)}
                      {linea.valor_override !== null && <span className="ml-1 text-bronze text-xs">override</span>}
                    </td>
                    <td className="whitespace-nowrap">
                      <button className="text-xs underline" onClick={() => alAplicarOverride(linea.id)}>
                        Override
                      </button>
                      {/* Las de material no se editan ni se borran a mano: se
                          regeneran con «Recalcular materiales». */}
                      {linea.rubro !== "MATERIAL" && (
                        <>
                          <button className="text-xs underline ml-2" onClick={() => alEmpezarEdicion(linea)}>
                            Editar
                          </button>
                          <button className="text-xs underline ml-2" onClick={() => alBorrar(linea)}>
                            Borrar
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              )}
```

- [ ] **Step 3: Compilar y correr las pruebas**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `60 passed`.

- [ ] **Step 4: Recorrerlo a mano** (con datos temporales)

1. En «Líneas por rubro», una línea cargada a mano muestra «Override», «Editar» y «Borrar». Una de material muestra solo «Override».
2. «Editar» en Flete: cambiar el precio unitario a `90.000` y «Guardar». El costo pasa a 90000 y, más abajo, su precio base a 117.000.
3. «Editar» y escribir `abc` en la cantidad: aparece el aviso y la línea no cambia. «Cancelar» cierra el renglón.
4. «Borrar» pide confirmación y la línea desaparece de las dos secciones.
5. Agregar una línea con precio unitario `1.500,50`: se guarda con 1500.50.

- [ ] **Step 5: Commit** (con el ok de Enzo)

```bash
git add frontend/src/api/presupuestos.ts frontend/src/hooks/usePresupuestos.ts frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx
git commit -m "feat(presupuesto): editar y borrar las lineas cargadas a mano"
```

**Fin del tramo 3.** Enzo recorre la pantalla sobre un presupuesto suyo de prueba.

---

### Task 10: Documentos y cierre

**Files:**
- Modify: `docs/REGISTRO.md`
- Modify: `docs/plan/PLAN-MAESTRO.md`
- Modify: `docs/MAPA-DEL-PROYECTO.md`
- Modify: `docs/BITACORA.md`
- Modify: `docs/plan/1.3-pdf-del-presupuesto/diseno.md`, `plan.md`

En estos archivos, AAAA-MM-DD es la fecha del día en que se cierra. La otra rama en curso puede haber tocado el plan maestro, el mapa o la bitácora: si al fusionar hay choque, se resuelve conservando los dos cambios.

- [ ] **Step 1: El registro**

En `docs/REGISTRO.md §5`, en la fila de `D-16`, reemplazar la última celda (`Sin elegir. `ADR-05` nombra WeasyPrint`) por:

```
**Cerrada (Enzo, 2026-10-12):** WeasyPrint, con la plantilla en HTML y CSS. En Windows necesita MSYS2 con Pango (`GUIA-PRUEBAS-LOCALES.md §5`); en el servidor, Pango en la imagen de Docker (`plan/1.3-pdf-del-presupuesto/diseno.md §10`)
```

Después de la fila de `D-19`, agregar:

```
| **D-20** | ¿Qué fecha lleva el presupuesto que ve el cliente, y desde cuándo corre la validez (`PAR-11`)? | Conversación con el dueño; el envío (1.5) | 4.5 | El día en que se genera el PDF (`plan/1.3-pdf-del-presupuesto/diseno.md §4`) |
| **D-21** | Cuando se fija a mano el total de un presupuesto, ¿ese número es con IVA o sin IVA? | Conversación con el dueño | 4.5 | Con IVA: es el número final que paga el cliente |
```

En el tablero del §7, la fila de decisiones pasa de `| Decisiones (`D`) | 19 | 18 | 0 | 1 |` a `| Decisiones (`D`) | 21 | 19 | 0 | 2 |`.

- [ ] **Step 2: El plan maestro**

En `docs/plan/PLAN-MAESTRO.md §6`, debajo de la tabla de sub-proyectos y antes de «**Regla para mandar a aprobar.**», agregar:

```
**1.3 quedó construido el AAAA-MM-DD,** en la rama `worktree-pdf-presupuesto`: [`1.3-pdf-del-presupuesto/`](1.3-pdf-del-presupuesto/). Tomó de 1.2 la edición del presupuesto: el texto y el precio de cada ítem para el cliente, el total fijado, editar y borrar líneas, y cambiar la validez y el cliente, todo desde la pestaña Costeo. De 1.2 queda la lista de presupuestos fuera del trabajo.
```

En el §8, la fila de `D-16` pasa a `| `D-16` | Herramienta para generar el PDF. **Cerrada: WeasyPrint** | 1.3 |`, y después de la fila de `D-18` se agregan:

```
| `D-20` | Qué fecha lleva el presupuesto y desde cuándo corre la validez | 4.5 |
| `D-21` | El total fijado a mano, con IVA o sin IVA | 4.5 |
```

- [ ] **Step 3: El mapa**

En `docs/MAPA-DEL-PROYECTO.md §1`, en la frase en negrita del principio, «faltan el PDF, el login, la aprobación del dueño y el envío al cliente» pasa a «faltan el login, la aprobación del dueño y el envío al cliente».

En la fila **Cotizador** de la tabla: a la segunda celda se le agrega, antes del paréntesis de las historias, «, texto y precio por ítem para el cliente, total fijado y PDF (`CART-309`)»; y en la tercera celda se saca «PDF, » del principio.

- [ ] **Step 4: La bitácora**

En `docs/BITACORA.md`, arriba de la entrada más reciente, agregar esta. Si algo salió distinto del plan, se escribe lo que pasó:

```markdown
## AAAA-MM-DD — PDF del presupuesto (1.3) construido: un importe por ítem, texto y precio editables, y total fijado

**Quién:** Enzo · **Carril:** Producto · **Sprint:** — (sub-proyecto 1.3)

### Qué se hizo

- **La cuenta del presupuesto pasó a un servicio** (`backend/app/services/presupuesto/totales.py`) y ahora arma el precio de cada ítem: el escrito a mano o el costo más el margen. Con un total fijado, todos los ítems se ajustan por el mismo factor. La usan la pantalla y el PDF.
- **El documento del cliente** (`documento.py`) no tiene ningún campo de costo ni de margen, y **el PDF** (`pdf.py`) sale de una plantilla HTML con WeasyPrint. Una prueba lee el texto del PDF y comprueba que no trae ni un importe de más.
- **La sección «Presupuesto para el cliente» en Costeo:** texto y precio por ítem, total final, validez, cliente, margen resultante, la lista de lo que falta y el botón del PDF. En «Líneas por rubro» se suman editar y borrar.
- **Se trabajó en una carpeta aparte del repositorio** (un worktree), en paralelo a la lectura del DXF, que siguió en la carpeta principal.
- **El código del plan se probó antes de escribirlo,** sobre una copia fuera del repo. Backend 492 en verde (423 antes), frontend 60 (40 antes).

### Qué se decidió

- **Cada ítem con su importe,** y no solo el total (Enzo).
- **WeasyPrint,** con MSYS2 y Pango instalados en `D:\msys64` para probar en Windows (Enzo). ReportLab andaba sin instalar nada, pero la plantilla hubiera sido código.
- **Un presupuesto incompleto no genera PDF** y dice qué falta (Enzo).
- **Al fijar el total se ajustan todos los ítems,** también los escritos a mano (Enzo). Lo escrito no se pisa: al quitar el total fijado, vuelve.
- **De este diseño, a confirmar con el dueño:** la fecha del presupuesto es el día en que se genera, y el total fijado es con IVA.

### Cambios en el registro

- **`D-16` cerrada:** WeasyPrint.
- **`D-20` y `D-21` nuevas:** la fecha del presupuesto y si el total fijado es con IVA. Se confirman en 4.5.

### Pendiente

- **Antes de usarlo sobre la base real,** respaldarla y correr `alembic upgrade head`: la migración `7f91bcd3ef15` agrega tres columnas.
- **Al fusionar,** si la rama de la lectura del DXF agregó una migración, encadenar la segunda detrás de la primera.
- **La imagen de Docker de 1.1** tiene que instalar Pango.
- **Juntar varias líneas de costo en un solo ítem** y **registrar quién cambió un precio** quedaron afuera (§3 del diseño).
```

- [ ] **Step 5: El estado del diseño y de este plan**

En `diseno.md`, el renglón de **Estado** pasa a: `> **Estado:** **construido el AAAA-MM-DD,** en la rama `worktree-pdf-presupuesto`, con el plan de [`plan.md`](plan.md). Lo que se apartó está al final de ese plan, en «Desvíos».`

En `plan.md`, el renglón de **Estado** pasa a: `> **Estado:** **ejecutado el AAAA-MM-DD,** de la Tarea 1 a la 10.` Y al final del archivo se agrega una sección `## Desvíos`, con un renglón por cada cosa que se hizo distinto de lo escrito, o con «Ninguno.».

- [ ] **Step 6: Verificación final**

Run: `cd backend && python -m pytest -q -rs`
Expected: `492 passed`, ninguna salteada.

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `60 passed`.

Run: `git status --short`
Expected: solo los cinco documentos de esta tarea.

- [ ] **Step 7: Commit** (con el ok de Enzo)

```bash
git add docs/REGISTRO.md docs/plan/PLAN-MAESTRO.md docs/MAPA-DEL-PROYECTO.md docs/BITACORA.md docs/plan/1.3-pdf-del-presupuesto
git commit -m "docs: pdf del presupuesto (1.3) construido"
```

- [ ] **Step 8: Cerrar la rama**

Usar `superpowers:finishing-a-development-branch`. Fusionar es de Enzo: se le deja el comando (`! gh pr merge <n> --merge`), y antes se sube la rama como `feat/pdf-presupuesto`:

```bash
git push -u origin worktree-pdf-presupuesto:feat/pdf-presupuesto
```

Mirar que el CI pase y que su salida no tenga pruebas salteadas: es la única comprobación del Step 9 de la Tarea 5.

Después de fusionar, y **solo con el ok explícito de Enzo**, la base real: copiar `backend/local/carteleria.db` a `backend/local/respaldo-AAAA-MM-DD-antes-de-7f91bcd3ef15/` y recién ahí correr `python -m alembic upgrade head` desde `backend/` en la carpeta principal. Como en A5 y A6, la carpeta del sub-proyecto pasa a `docs/historico/` en un commit aparte, cuando Enzo lo da por cerrado.
