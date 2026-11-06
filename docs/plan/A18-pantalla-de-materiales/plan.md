# A18 · La pantalla de Materiales, con la planilla de precios — plan

> **Estado:** aprobado por Enzo el 2026-10-30, sin empezar: él decide cuándo se arranca.

> **Para quien ejecuta:** tarea por tarea, con **pausa al final de cada una** para que Enzo la vea antes de seguir. Así trabaja este proyecto, aunque el skill de ejecución diga otra cosa. Los pasos usan casillas (`- [ ]`) para llevar la cuenta.

**Objetivo:** que los materiales y sus precios del cotizador salgan de la planilla de la empresa y se pongan al día subiéndola, con una pantalla de Materiales en dos columnas para verlos y cambiar lo que la planilla no tiene. De paso, las opciones del motor en Anidado van a un desplegable.

**Cómo:**
- **La puerta** es `armar_revision(sesion, planilla, archivo)`: recibe renglones con las columnas de la hoja `COTIZADOR` y no sabe si vienen de un Excel o de otro sistema.
- **Los artículos** se guardan tal cual en una tabla nueva (`Articulo`). Lo que agrega la app sigue en `Material`, `Formato` y `ParametrosCorteMaterial`, unido por el código.
- **El precio del proveedor que cuenta se copia** a `Formato.costo_unidad_venta` y a sus retazos, así el costeo, la comparación de chapas y los retazos no cambian.
- **Las reglas puras** (leer la descripción, la categoría, qué se anida, qué proveedor cuenta) viven en `app/services/catalogo/` y se prueban sin base.
- **La pantalla** suma la ruta `/materiales` con su lista y su detalle, y la revisión de la planilla en la misma ruta.

**Herramientas:** Python 3.13, FastAPI, SQLAlchemy, Alembic, `openpyxl` (nueva en `requirements.txt`; ya la usan los guiones), React + TypeScript + React Query + Tailwind, vitest.

**Diseño:** [`diseno.md`](diseno.md), aprobado por Enzo el 2026-10-30. Este plan se apoya en él: hay que leer los dos. Los bocetos están en `.superpowers/brainstorm/1929-1793390824/content/` (`materiales-forma.html`, la forma C, y `actualizar-planilla.html`), fuera de git.

## Lo que vale para todas las tareas

- **La planilla real nunca entra a git** (`CARTELERIA 2026.xlsx`, en la raíz): trae datos de clientes y contraseñas. Las pruebas usan una planilla armada en la prueba (tarea 2), con los encabezados reales y artículos inventados o copiados de los ejemplos del diseño.
- **El costo de unidad de venta está siempre en pesos.** Toda medida que toma precio de la planilla queda con `moneda = "ARS"`.
- **Un costo vacío, en 0 o que no es un número es «sin precio»** (`None`), nunca $ 0.
- **`PAR-59`** va en `backend/app/config.py` como `DIFERENCIA_MAXIMA_CON_EL_FACTOR = Decimal(os.getenv("CARTELERIA_DIFERENCIA_CON_EL_FACTOR", "0.05"))`, con el comentario que apunta a `docs/REGISTRO.md`, como `RETAZO_MINIMO_MM`.
- **Los mensajes al usuario** son `ErrorParaElUsuario` (`app/mensajes.py`) y se prueban con `mensaje_de` (`tests/api/ayudas.py`). Los textos van tal cual los fija este plan.
- **Las rutas que leen un archivo son `def`, no `async def`.** Una lectura larga en `async` traba todo el servidor (A17, tanda 6).
- **Los nombres de materiales se guardan como vienen en la planilla** («CHAPA NEGRA»). La pantalla los muestra con `nombreParaMostrar` (tarea 9).
- **Commits sin la línea `Co-Authored-By`**, en la rama `feat/a18-pantalla-de-materiales`, que sale de `main`.
- **Pruebas con los temporales en D:**, porque C: suele estar lleno. Desde `backend/`:
  `CARTELERIA_DATOS=local/tmp-a18/datos python -m pytest -q --basetemp=local/tmp-a18/pytest <pruebas>`
  Las de la pantalla, desde `frontend/`: `npx vitest run <archivo>` y `npx tsc --noEmit`.
- **Nunca sobre la base real.** Las copias se hacen con `python local/herramientas-a17/copiar_base.py a18` (queda en `local/tmp-a17/a18`). **Antes de levantar la app, mirar quién escucha en 8000 y 5173:** si hay algo, es de Enzo y corre contra su base real.

## Antes de la tarea 1

- [ ] Crear la rama `feat/a18-pantalla-de-materiales` desde `main`. El diseño, este plan y el `REGISTRO.md` (`SUP-19`, `PAR-59`, `P-35`) ya están en `main` desde el 2026-10-30. La planilla de la raíz nunca entra.

## Lo que más puede fallar sin que ninguna prueba lo mire

Cada uno tiene su prueba o su control en la tarea que lo toca.

1. **La lectura del dibujo cambia al entrar las medidas nuevas.** `_formatos_del_catalogo` (`rutas_catalogo.py`) le pasa a la lectura del DXF las medidas de chapa disponibles, para reconocer las hojas del diseñador, adivinar la escala y avisar de las piezas que no entran. Con la planilla entran MDF de 1830 × 2600, 1830 × 2750 y 1830 × 3660, ACM de 5000 × 1500 y PVC. Un rectángulo del diseño de esa medida podría pasar a leerse como hoja. Control en la tarea 8: la lectura del corpus antes y después de cargar la planilla en una copia. **Si cambia algo, se para y se le pregunta a Enzo.**
2. **Subir dos veces la misma planilla.** Tiene que dar todo «sin cambios», sin duplicar artículos, materiales ni medidas, y sin anotar cambios de precio. Prueba en la tarea 6.
3. **Un proveedor marcado a mano que desaparece de la planilla.** El código vuelve a automático y toma el precio del otro proveedor. Si se van todos los proveedores de un código, la medida deja de ofrecerse, pero su grupo la sigue viendo. Prueba en la tarea 6.
4. **Celdas como las de la planilla real:** espacios de más («FUENTE  METALICA»), «LONAS » con espacio al final, códigos en minúscula, renglones sin código, números guardados como texto con coma. Prueba en la tarea 2.
5. **Los retazos cuando cambia el precio o el proveedor de su chapa.** Copian el precio nuevo y nunca aparecen en «ya no están». Prueba en la tarea 6.

---

## Tramo 1 — Leer la planilla y armar la revisión

### Tarea 1: Leer la descripción, la categoría y qué se anida

**Archivos:**
- Crear: `backend/app/services/catalogo/__init__.py` (vacío) y `backend/app/services/catalogo/descripcion.py`
- Modificar: `backend/app/config.py` (`DIFERENCIA_MAXIMA_CON_EL_FACTOR`)
- Prueba: `backend/tests/services/catalogo/__init__.py` (vacío) y `backend/tests/services/catalogo/test_descripcion.py`

**Deja para las otras tareas:**

```python
@dataclass(frozen=True)
class MedidaLeida:
    material: str          # «CHAPA NEGRA», como la planilla, sin espacios de más
    espesor: str | None    # «cal. 20», «3 mm», «2.4 mm», o None (el ACM)
    ancho_mm: Decimal      # el primer número de la descripción
    alto_mm: Decimal       # el segundo

def leer_medida(descripcion: str, factor: Decimal | None) -> MedidaLeida | None: ...
def nombre_de_categoria(categoria: str) -> str: ...
def se_anida(unidad_compra: str | None, unidad_venta: str | None) -> bool: ...
```

- **`leer_medida`:** junta los espacios repetidos y busca `<material> - <a> x <b> - <espesor>`. El guion antes del primer número y el espesor pueden faltar (el ACM). Los números van en metros con coma o punto y pasan a mm. El espesor se normaliza: `cal. N`, o `N mm` con punto decimal. Si hay un tercer número de medida («0.7 x 1,25 m x 2,5 m»), devuelve `None`. Con `factor`, si `|ancho × alto / 1e6 − factor| / factor > config.DIFERENCIA_MAXIMA_CON_EL_FACTOR`, también `None`.
- **`nombre_de_categoria`:** recorta y pasa a mayúsculas para buscar en este diccionario. Si no está, devuelve la primera letra en mayúscula y el resto en minúscula.

```python
NOMBRES_DE_CATEGORIA = {
    "CHAPA": "Chapas", "ACRILICOS": "Acrílicos", "MDF": "MDF", "PVC": "PVC", "ACM": "ACM",
    "POLYFAN": "Polyfan", "METALEX": "Metalex", "ILUMINACION": "Iluminación", "PINTURA": "Pintura",
    "VINILOS DE CORTE": "Vinilos de corte", "VINILOS DE IMPRESION": "Vinilos de impresión",
    "LONAS": "Lonas", "HERRERA": "Herrería", "BULONERIA/ANCLAJE": "Bulonería y anclaje",
    "HERRAMIENTAS": "Herramientas", "PEGAMENTOS": "Pegamentos", "SOLDADURA": "Soldadura",
    "ARTICULOS COMPUESTOS": "Artículos compuestos", "IMPRESION": "Impresión",
}
```

- **`se_anida`:** `True` solo si la unidad de compra es `PLANCHA` y la de venta `M2` (sin importar mayúsculas ni espacios).

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
@pytest.mark.parametrize("descripcion, factor, esperado", [
    ("CHAPA NEGRA - 1,22 x 2,44 - cal. 20", "2.97", ("CHAPA NEGRA", "cal. 20", "1220", "2440")),
    ("ACRILICO CRISTAL - 1,22 x 2,44 - 2,4 mm", "2.97", ("ACRILICO CRISTAL", "2.4 mm", "1220", "2440")),
    ("MDF - 1,83 x 3,66 - 9mm", "6.6", ("MDF", "9 mm", "1830", "3660")),
    ("ACM NEGRO SATINADO 5,00 x 1,50 m", "7.5", ("ACM NEGRO SATINADO", None, "5000", "1500")),
    ("PVC  ESPUMADO - 1,22 x 2,44 - 3mm", None, ("PVC ESPUMADO", "3 mm", "1220", "2440")),
])
def test_lee_material_espesor_y_medida(descripcion, factor, esperado): ...

def test_no_lee_una_medida_con_tres_numeros():
    assert leer_medida("CHAPA ACERO (A_240) ESMERILADO 430 - 0.7 x 1,25 m x 2,5 m", Decimal("3.12")) is None

def test_no_lee_una_medida_que_no_da_los_m2_de_la_planilla():
    assert leer_medida("CHAPA NEGRA - 1,22 x 2,44 - cal. 20", Decimal("4.0")) is None

def test_el_redondeo_de_la_planilla_se_acepta():  # 6,70 m² contra 6,6: 1,5 %
    assert leer_medida("MDF - 1,83 x 3,66 - 9mm", Decimal("6.6")) is not None

def test_nombre_de_categoria():
    assert [nombre_de_categoria(c) for c in ("CHAPA", "LONAS ", "ILUMINACION", "Impresion", "ALGO NUEVO")] == \
        ["Chapas", "Lonas", "Iluminación", "Impresión", "Algo nuevo"]

def test_se_anida_lo_que_se_compra_por_plancha_y_se_vende_por_m2():
    assert se_anida("PLANCHA", "M2") and se_anida(" plancha ", "m2")
    assert not se_anida("UNIDAD", "UNIDAD") and not se_anida("PLANCHA", "METROS LINEALES") and not se_anida(None, "M2")
```

- [ ] **Paso 2: Correrlas y ver que fallan** (`tests/services/catalogo/test_descripcion.py`): `ModuleNotFoundError`.
- [ ] **Paso 3: Escribir `descripcion.py` y la constante en `config.py`.**
- [ ] **Paso 4: Correrlas y ver que pasan.**
- [ ] **Paso 5: Commit** — `feat(catalogo): leer la medida, la categoría y qué se anida de la planilla (A18, tarea 1)`

---

### Tarea 2: Leer el Excel

**Archivos:**
- Crear: `backend/app/services/catalogo/planilla.py`
- Modificar: `backend/requirements.txt` (`openpyxl==3.1.5`, con un comentario que apunta a este diseño)
- Crear: `backend/tests/services/catalogo/planilla_de_prueba.py` (la ayuda de las pruebas)
- Prueba: `backend/tests/services/catalogo/test_planilla.py`

**Deja para las otras tareas:**

```python
@dataclass(frozen=True)
class Renglon:
    fila: int                      # la fila de la hoja (la primera de datos es la 6)
    codigo: str                    # recortado y en mayúsculas
    descripcion: str               # con los espacios repetidos juntados
    proveedor: str                 # recortado, espacios repetidos juntados
    categoria: str                 # recortada
    unidad_compra: str | None
    factor_conversion: Decimal | None
    unidad_venta: str | None
    precio_bruto_compra: Decimal | None
    moneda: str | None
    precio_bruto_ars: Decimal | None
    iva: Decimal | None
    precio_neto_compra: Decimal | None
    porcentaje_costo_1: Decimal | None
    porcentaje_costo_2: Decimal | None
    costo_unidad_venta: Decimal | None   # None si está vacío, en 0 o no es un número
    margen_venta_1: Decimal | None
    margen_venta_2: Decimal | None
    margen_venta_3: Decimal | None
    margen_venta_4: Decimal | None

@dataclass(frozen=True)
class PlanillaLeida:
    renglones: list[Renglon]
    dolar_compra: Decimal | None
    dolar_venta: Decimal | None

def leer_planilla(contenido: bytes) -> PlanillaLeida: ...   # lanza ErrorParaElUsuario (400)

# planilla_de_prueba.py
ENCABEZADOS: list[str]   # los 19 de la fila 5 real, tal cual (con comillas y saltos de línea)
def chapa(codigo: str, descripcion: str, costo, *, proveedor="SIDERMAQ", factor="2.97", moneda="ARS") -> dict: ...
def insumo(codigo: str, descripcion: str, costo, *, proveedor="MAX", categoria="ILUMINACION") -> dict: ...
def planilla_de_prueba(renglones: list[dict], *, dolar_venta=1530, hoja="COTIZADOR", sin_columnas=()) -> bytes: ...
```

- **La forma de la hoja real:** en la columna C, «PAGINA» (fila 1), «COMPRA» (fila 2) y «VENTA» (fila 3), con el valor en la columna D. Encabezados en la fila 5 y datos desde la 6. `planilla_de_prueba` arma eso mismo con `openpyxl` y lo devuelve en bytes. `ENCABEZADOS` se copia de la planilla real: `"CODIGO"`, `"DESCRIPCION"`, `"PROVEEDOR"`, `"CATEGORIA"`, `'"UNIDAD \nDE COMPRA"'`, `'"FACTOR DE\nCONVERSION"'`, `'"UNIDAD \nDE VENTA"'`, `'"PRECIO BRUTO\n DE COMPRA"'`, `"MON.\nARS/USD"`, `"PRECIO BRUTO\nEN ARS"`, `"IVA"`, `'"PRECIO NETO\nDE COMPRA"'`, `"PORCENTAJE\nDE COSTO 1"`, `"PORCENTAJE\nDE COSTO 2"`, `'"COSTO DE UNIDAD\nDE VENTA"'`, `"MARGEN DE \nVENTA 1"` a `"MARGEN DE \nVENTA 4"`.
- **Cómo se encuentran las columnas:** por el nombre, no por la posición. A cada encabezado se le sacan las comillas, los saltos de línea, los espacios repetidos y las tildes, y se pasa a mayúsculas: `'"COSTO DE UNIDAD\nDE VENTA"'` queda `COSTO DE UNIDAD DE VENTA`. La fila de encabezados es la primera de las 10 primeras que tiene `CODIGO` y `DESCRIPCION`.
- **Obligatorias:** `CODIGO`, `DESCRIPCION`, `PROVEEDOR`, `CATEGORIA`, `UNIDAD DE COMPRA`, `FACTOR DE CONVERSION`, `UNIDAD DE VENTA` y `COSTO DE UNIDAD DE VENTA`. Las demás, si faltan, quedan en `None` *(decisión del plan: sin ellas igual se cotiza)*.
- **El dólar:** arriba de los encabezados, la celda que dice `COMPRA` o `VENTA` y el primer número a su derecha.
- **Los renglones:** se saltean los que no tienen código. Si el mismo código y proveedor aparece dos veces, vale el de más abajo.
- **Los mensajes, tal cual:**
  - No se puede abrir como `.xlsx`: «El archivo no es una planilla de Excel (.xlsx). Bajá la planilla de AppSheet como Excel y subila de nuevo.»
  - Sin la hoja: «La planilla no tiene la hoja «COTIZADOR», que es donde están los precios.»
  - Faltan columnas: «A la hoja «COTIZADOR» le faltan estas columnas: «UNIDAD DE VENTA», «COSTO DE UNIDAD DE VENTA».» (los nombres normalizados, en el orden de la lista de obligatorias).
  - Sin renglones: «La hoja «COTIZADOR» no tiene ningún artículo con código.»

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_lee_los_renglones_y_el_dolar():
    leida = leer_planilla(planilla_de_prueba([chapa("CHA0011", "CHAPA NEGRA - 1,22 x 2,44 - cal. 20", 16966.26)], dolar_venta=1530))
    assert leida.dolar_venta == Decimal("1530")
    (r,) = leida.renglones
    assert (r.fila, r.codigo, r.proveedor, r.unidad_compra, r.unidad_venta) == (6, "CHA0011", "SIDERMAQ", "PLANCHA", "M2")
    assert r.costo_unidad_venta == Decimal("16966.26") and r.factor_conversion == Decimal("2.97")

def test_limpia_las_celdas_como_vienen_en_la_planilla_real():
    leida = leer_planilla(planilla_de_prueba([
        insumo(" fue0002 ", "FUENTE  METALICA 12V - 10A", "22968,75", proveedor="MAX ", categoria="LONAS "),
        insumo(None, "renglón sin código", 100),
    ]))
    (r,) = leida.renglones
    assert (r.codigo, r.descripcion, r.proveedor, r.categoria) == ("FUE0002", "FUENTE METALICA 12V - 10A", "MAX", "LONAS")
    assert r.costo_unidad_venta == Decimal("22968.75")

@pytest.mark.parametrize("costo", [None, 0, "", "consultar"])
def test_un_costo_vacio_en_cero_o_que_no_es_numero_es_sin_precio(costo):
    (r,) = leer_planilla(planilla_de_prueba([insumo("LED0001", "LEDS NEON FLEX - FRIO", costo)])).renglones
    assert r.costo_unidad_venta is None

def test_el_mismo_codigo_y_proveedor_dos_veces_vale_el_de_abajo(): ...
def test_dos_proveedores_del_mismo_codigo_son_dos_renglones(): ...

def test_un_archivo_que_no_es_excel():
    with pytest.raises(ErrorParaElUsuario, match=r"no es una planilla de Excel"):
        leer_planilla(b"0\nSECTION\n2\nENTITIES\n")   # el comienzo de un DXF

def test_sin_la_hoja_cotizador(): ...          # hoja="OTRA" → «…no tiene la hoja «COTIZADOR»…»
def test_le_faltan_columnas():                  # sin_columnas=("COSTO DE UNIDAD DE VENTA", "UNIDAD DE VENTA")
    ...  # el mensaje exacto de arriba
def test_sin_ningun_articulo(): ...             # planilla_de_prueba([])
```

- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir `planilla.py` y la ayuda, y sumar `openpyxl` a `requirements.txt`.** Se abre con `openpyxl.load_workbook(BytesIO(contenido), read_only=True, data_only=True)`. Cualquier excepción al abrir (`zipfile.BadZipFile`, `InvalidFileException`, `KeyError`) es el primer mensaje.
- [ ] **Paso 4: Correrlas y ver que pasan.** También `python -I -c "import sys; sys.path.insert(0,'.'); from app.services.catalogo.planilla import leer_planilla; l=leer_planilla(open('../CARTELERIA 2026.xlsx','rb').read()); print(len(l.renglones), l.dolar_venta)"`, que tiene que dar `289 1530`. Es solo para ver: no se escribe en ninguna prueba.
- [ ] **Paso 5: Commit** — `feat(catalogo): leer la hoja COTIZADOR de la planilla (A18, tarea 2)`

---

### Tarea 3: Los artículos en la base

**Archivos:**
- Modificar: `backend/app/modelos/catalogo.py` (`Articulo`, `CargaDePlanilla`, `CambioDePrecio`, y dos columnas en `Formato`), y `backend/app/modelos/__init__.py` si exporta los modelos
- Crear: `backend/alembic/versions/e7a1c5d9b318_articulos_de_la_planilla.py`, con `down_revision = 'd4b2e8a1f630'`
- Prueba: `backend/tests/modelos/test_migracion_articulos.py`

**Deja para las otras tareas:**

```python
class Articulo(Base):                    # __tablename__ = "articulos"
    id: int
    codigo: str                          # String(40)
    proveedor: str                       # String(120)
    # las columnas de `Renglon` (tarea 2), con los mismos nombres y tipos (Milimetros() para los números)
    fila: int                            # la fila en la última planilla en que estuvo
    en_ultima_planilla: bool
    precio_cambiado_en: datetime         # la carga en que apareció o en que cambió su costo
    # UniqueConstraint("codigo", "proveedor", name="uq_articulo_codigo_proveedor")

class CargaDePlanilla(Base):             # __tablename__ = "cargas_de_planilla"
    id: int
    archivo: str                         # el nombre del archivo; el archivo no se guarda
    dolar_compra: Decimal | None
    dolar_venta: Decimal | None
    articulos: int                       # renglones de la planilla
    cambios: int                         # precios que cambiaron
    # la fecha es `creado_en`

class CambioDePrecio(Base):              # __tablename__ = "cambios_de_precio"
    id: int
    carga_id: int                        # FK a cargas_de_planilla, ondelete="CASCADE"
    codigo: str
    proveedor: str
    antes: Decimal | None
    despues: Decimal | None

# en Formato:
    proveedor_a_mano: Mapped[str | None]  # String(120), default None
    medida_a_mano: Mapped[bool]           # default False; la migración pone 0 a las que ya están
```

- **La migración** crea las tres tablas y agrega las dos columnas con `batch_alter_table` (SQLite), con `server_default=sa.false()` en `medida_a_mano`. Al volver, saca todo.

- [ ] **Paso 1: Escribir la prueba que falla**, como `test_migracion_familia.py`:

```python
def test_la_migracion_agrega_los_articulos_y_respeta_las_medidas_que_hay(tmp_path, monkeypatch):
    # subir hasta 'd4b2e8a1f630', insertar un material y una medida con código CHA0011
    # subir a head: la medida sigue, con medida_a_mano = 0 y proveedor_a_mano NULL;
    #   existen articulos, cargas_de_planilla y cambios_de_precio
    # bajar a 'd4b2e8a1f630': las tablas y las dos columnas ya no están, la medida sigue
```

- [ ] **Paso 2: Correrla y ver que falla.**
- [ ] **Paso 3: Escribir los modelos y la migración.**
- [ ] **Paso 4: Correr la prueba y todo `tests/modelos` y `tests/api/test_rutas_catalogo.py`.** Tienen que pasar.
- [ ] **Paso 5: Commit** — `feat(catalogo): los artículos de la planilla en la base (A18, tarea 3)`

---

### Tarea 4: El proveedor que cuenta

**Archivos:**
- Crear: `backend/app/services/catalogo/proveedor.py`
- Prueba: `backend/tests/services/catalogo/test_proveedor.py`

**Deja para las otras tareas:**

```python
@dataclass(frozen=True)
class Opcion:
    proveedor: str
    precio_cambiado_en: datetime
    fila: int

def proveedor_que_cuenta(opciones: Sequence[Opcion], a_mano: str | None) -> str | None: ...
```

- Sin opciones, `None`. Si `a_mano` está entre los proveedores, `a_mano`. Si no, el de `precio_cambiado_en` más reciente y, si empatan, el de `fila` mayor (diseño §5.3).

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_con_un_solo_proveedor_es_ese(): ...
def test_cuenta_el_que_cambio_de_precio_mas_recientemente(): ...
def test_si_cambiaron_en_la_misma_carga_cuenta_el_de_mas_abajo(): ...
def test_el_marcado_a_mano_gana_aunque_el_otro_sea_mas_reciente(): ...
def test_si_el_marcado_a_mano_ya_no_esta_vuelve_a_automatico(): ...
def test_sin_opciones_no_hay_proveedor(): ...
```

- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir `proveedor.py`.**
- [ ] **Paso 4: Correrlas y ver que pasan.**
- [ ] **Paso 5: Commit** — `feat(catalogo): qué proveedor cuenta para el precio (A18, tarea 4)`

---

### Tarea 5: Armar la revisión

**Archivos:**
- Crear: `backend/app/services/catalogo/revision.py`
- Prueba: `backend/tests/services/catalogo/test_revision.py`, con una sesión sobre una base de prueba (`crear_motor` + `Base.metadata.create_all`, como el `cliente` de `test_rutas_catalogo.py`)

**Usa:** `leer_medida`, `nombre_de_categoria`, `se_anida` (tarea 1); `PlanillaLeida`, `Renglon` (tarea 2); los modelos (tarea 3); `proveedor_que_cuenta`, `Opcion` (tarea 4).

**Deja para las otras tareas:**

```python
@dataclass(frozen=True)
class PrecioQueCambia:
    codigo: str; descripcion: str; proveedor: str
    antes: Decimal | None; ahora: Decimal | None
    en_dolares: bool          # la moneda de compra del renglón es USD
    pasa_a_contar: bool       # con la planilla nueva, este proveedor pasa a ser el que cuenta

@dataclass(frozen=True)
class PrecioDePrueba:
    codigo: str; descripcion: str; de_prueba: Decimal; de_la_planilla: Decimal

@dataclass(frozen=True)
class ArticuloNuevo:
    codigo: str; descripcion: str; proveedor: str
    va_a: str                 # «MDF: MDF 25 mm» si se anida; «Iluminación» si no
    costo: Decimal | None; unidad_venta: str | None

@dataclass(frozen=True)
class YaNoEsta:
    codigo: str; descripcion: str; proveedor: str

@dataclass(frozen=True)
class HayQueMirarlo:
    codigo: str; descripcion: str
    motivo: str               # los dos textos de abajo
    medida_antes: tuple[Decimal, Decimal] | None   # la de la medida que ya existe
    medida_leida: tuple[Decimal, Decimal] | None   # la que se leyó, si se leyó

@dataclass
class Revision:
    id: str                   # uuid4().hex
    archivo: str
    planilla: PlanillaLeida
    ultima_carga_id: int | None     # la última CargaDePlanilla al armarla; None si no hubo ninguna
    carga_anterior_en: datetime | None
    dolar_antes: Decimal | None     # el dolar_venta de la carga anterior
    primera_carga: bool
    cambian: list[PrecioQueCambia]
    de_prueba: list[PrecioDePrueba]
    nuevos: list[ArticuloNuevo]
    ya_no_estan: list[YaNoEsta]
    hay_que_mirar: list[HayQueMirarlo]
    sin_cambios: int
    se_enlazan: int           # solo en la primera carga: códigos que ya tenían su medida en la app
    quedan_a_mano: list[str]  # solo en la primera carga: códigos de medidas que no están en la planilla

def armar_revision(sesion: Session, planilla: PlanillaLeida, archivo: str) -> Revision: ...
```

**Las reglas** (diseño §5.4 y §5.5). No se escribe nada en la base.
- **Medidas de la app:** solo las que no son retazo. Un retazo nunca se compara con la planilla.
- **Primera carga** = no hay ninguna `CargaDePlanilla`.
- **Cambia:** el renglón tiene un `Articulo` (mismo código y proveedor) con otro `costo_unidad_venta`. En la primera carga, además, una medida enlazada sin precio de prueba cuyo costo es distinto del costo del proveedor que contaría. `pasa_a_contar` se calcula con `proveedor_que_cuenta`, poniendo `precio_cambiado_en = ahora` a lo que cambia o es nuevo.
- **Precio de prueba:** la medida del código tiene `precio_simulado = True` y el proveedor que contaría trae un costo. No va también en «cambian».
- **Nuevo:** no hay `Articulo` con ese código y proveedor y, si se anida, tampoco una medida con ese código. Un código que ya tiene su medida en la app y aparece en la primera carga no es nuevo: se enlaza.
- **Ya no está:** un `Articulo` con `en_ultima_planilla = True` cuyo código y proveedor no vienen en esta planilla.
- **Hay que mirarlo**, solo para lo que se anida:
  - sin medida en la app, cuando `leer_medida` da `None`: motivo «No queda clara la medida de la chapa», con `medida_antes = None`;
  - con medida en la app y `medida_a_mano = False`, cuando `leer_medida` da `None`: el mismo motivo, con `medida_antes` = la de la app;
  - con medida en la app, `medida_a_mano = False` y una medida leída distinta: motivo «Cambió la medida de la chapa», con las dos medidas;
  - con `medida_a_mano = True` y una descripción distinta de la del `Articulo` guardado: «Cambió la medida de la chapa», con las dos medidas.
- **Sin cambios:** los renglones que no quedaron en ninguna de las otras partes.

- [ ] **Paso 1: Escribir las pruebas que fallan**, cada una con `planilla_de_prueba` → `leer_planilla` → `armar_revision`:

```python
def test_primera_carga_enlaza_por_codigo_y_cuenta_lo_que_queda_a_mano(sesion):
    # en la base: CHA0011 (medida) y POL0006 (medida), y un retazo CHA0011-R; en la planilla: CHA0011 y LED0001
    r = ...
    assert r.primera_carga and r.se_enlazan == 1 and r.quedan_a_mano == ["POL0006"]
    assert [n.codigo for n in r.nuevos] == ["LED0001"] and r.ya_no_estan == []

def test_un_precio_que_cambia(sesion): ...            # segunda carga con otro costo → en `cambian`, con antes y ahora
def test_el_precio_de_prueba_con_precio_de_la_planilla(sesion): ...
def test_el_precio_de_prueba_sigue_si_la_planilla_no_trae_precio(sesion): ...   # no va en de_prueba ni en cambian
def test_un_nuevo_que_se_anida_dice_adonde_va(sesion):   # «MDF: MDF 25 mm»
    ...
def test_el_que_ya_no_esta(sesion): ...
def test_la_misma_planilla_dos_veces_da_todo_sin_cambios(sesion): ...   # (Review Focus 2: aplicar la primera con la tarea 6)
def test_no_se_lee_la_medida_va_a_mirar(sesion): ...     # CHA0013, sin medida y con medida en la app
def test_cambio_la_medida_de_una_chapa_que_existe(sesion): ...
def test_con_dos_proveedores_marca_el_que_pasa_a_contar(sesion): ...
def test_un_articulo_en_dolares_se_marca(sesion): ...
def test_no_escribe_nada_en_la_base(sesion): ...         # cuenta Articulo y Formato antes y después
```

Las pruebas que necesitan una carga anterior la arman a mano con `Articulo` y `CargaDePlanilla`, hasta que exista la tarea 6.

- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir `revision.py`.**
- [ ] **Paso 4: Correrlas y ver que pasan.**
- [ ] **Paso 5: Commit** — `feat(catalogo): armar la revisión de una planilla, sin aplicarla (A18, tarea 5)`

**Pausa: fin del tramo 1.** Contarle a Enzo lo que lee de la planilla real (paso 4 de la tarea 2) y mostrarle la revisión de la primera carga sobre una copia de su base, como texto: cuántos se enlazan, cuántos entran, qué queda a mano y qué hay que mirar.

---

## Tramo 2 — Aplicar

### Tarea 6: Aplicar la revisión

**Archivos:**
- Crear: `backend/app/services/catalogo/aplicar.py`
- Crear: `backend/app/services/catalogo/precios.py`, con lo que hoy está en `rutas_catalogo.py`: `_CAMPOS_DEL_PRECIO` → `CAMPOS_DEL_PRECIO` y `_retazos_de` → `retazos_de`. `rutas_catalogo.py` pasa a importarlos de ahí.
- Prueba: `backend/tests/services/catalogo/test_aplicar.py`

**Usa:** `Revision` y `armar_revision` (tarea 5), `proveedor_que_cuenta` (tarea 4), `leer_medida`, `nombre_de_categoria`, `se_anida` (tarea 1).

**Deja para las otras tareas:**

```python
# precios.py
CAMPOS_DEL_PRECIO = ("moneda", "costo_unidad_venta", "precio_simulado")
def retazos_de(sesion: Session, formato: Formato) -> list[Formato]: ...
def poner_el_precio(sesion: Session, formato: Formato) -> None: ...
    # elige el artículo que cuenta del código del formato (en_ultima_planilla = True) y copia a la medida:
    #   costo_unidad_venta (si el artículo no tiene precio y la medida es de prueba, no la toca),
    #   precio_simulado = False cuando copia un precio, moneda = "ARS", unidad_compra, unidad_venta y
    #   factor_conversion; después copia CAMPOS_DEL_PRECIO a sus retazos. Sin artículos, no hace nada.

# aplicar.py
def aplicar_revision(
    sesion: Session, revision: Revision, medidas: dict[str, tuple[Decimal, Decimal]], ahora: datetime
) -> CargaDePlanilla: ...   # hace commit; lanza ErrorParaElUsuario(estado=409) si la revisión venció
```

**Las reglas:**
- **Venció** si la última `CargaDePlanilla` ya no es `revision.ultima_carga_id`: «Mientras revisabas se cargó otra planilla. Volvé a subirla para ver los cambios de nuevo.» No se escribe nada.
- **Cada renglón** crea o actualiza su `Articulo` con todas sus columnas, `fila`, `en_ultima_planilla = True` y, si es nuevo o cambió su costo, `precio_cambiado_en = ahora`. Si cambió el costo, se anota un `CambioDePrecio`.
- **Lo que se anida sin medida en la app:** con la medida leída, o con la de `medidas[codigo]` si se completó a mano, se busca o se crea el `Material(nombre, espesor)` con `familia = nombre_de_categoria(categoria)`, y se crea la medida con su código. **Una sola medida por código:** el segundo proveedor del mismo código encuentra la que creó el primero. Si se completó a mano, `medida_a_mano = True`. Si no hay medida ni leída ni a mano, no se crea.
- **Lo que se anida con medida en la app:** la familia de su material pasa a `nombre_de_categoria(categoria)`. Si el código está en `medidas`, se cambia la medida y queda `medida_a_mano = True`. Si no está y su caso era «hay que mirarlo», la medida queda como estaba.
- **Lo que ya no está:** `en_ultima_planilla = False`. Si el `proveedor_a_mano` de su medida ya no tiene artículo en la planilla, vuelve a `None`. Si el código se quedó sin ningún proveedor en la planilla, su medida queda `disponible = False`.
- **Lo que vuelve:** una medida que no es retazo, con `disponible = False` y artículos otra vez en la planilla, vuelve a `disponible = True`.
- **Precios:** `poner_el_precio` en cada medida con código de la planilla.
- **La carga:** `CargaDePlanilla(archivo, dolar_compra, dolar_venta, articulos=len(renglones), cambios=len(revision.cambian))`, y una `CotizacionMoneda("USD", dolar_venta, fecha de hoy)`, que si ya existe para esa fecha se actualiza.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_la_primera_carga_enlaza_sin_tocar_grupos_ni_retazos_y_entra_lo_que_falta(sesion): ...
    # un grupo apunta a CHA0011: sigue apuntando a la misma medida; su retazo sigue y toma el precio;
    # POL0006 sigue disponible; LED0001 queda solo como Articulo; un MDF nuevo crea material y medida 1830 × 2600
def test_un_precio_que_cambia_llega_a_la_medida_y_a_sus_retazos_y_se_anota(sesion): ...
def test_el_precio_de_prueba_se_reemplaza(sesion): ...
def test_la_misma_planilla_dos_veces_no_duplica_ni_anota(sesion): ...            # Review Focus 2
def test_con_dos_proveedores_cuenta_el_que_cambio_y_el_marcado_a_mano_gana(sesion): ...
def test_si_el_marcado_a_mano_desaparece_vuelve_a_automatico(sesion): ...        # Review Focus 3
def test_sin_proveedores_la_medida_no_se_ofrece_pero_su_grupo_la_ve(sesion): ...  # Review Focus 3
def test_lo_que_vuelve_se_ofrece_otra_vez(sesion): ...
def test_la_medida_a_mano_se_guarda_y_se_conserva_en_la_siguiente_carga(sesion): ...
def test_hay_que_mirarlo_sin_completar_queda_como_estaba(sesion): ...
def test_el_retazo_sigue_a_su_chapa_cuando_cambia_el_proveedor(sesion): ...      # Review Focus 5
def test_un_articulo_en_dolares_queda_en_pesos(sesion): ...                      # moneda "ARS", costo de la planilla
def test_la_familia_sale_de_la_categoria(sesion): ...                            # ALT0001 en ACRILICOS → «Acrílicos»
def test_guarda_la_carga_y_el_dolar(sesion): ...
def test_una_revision_vencida_no_aplica_nada(sesion): ...
```

- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir `precios.py` y `aplicar.py`, y que `rutas_catalogo.py` use `precios.py`.**
- [ ] **Paso 4: Correrlas, y también `tests/api/test_rutas_catalogo.py` y `tests/test_costeo.py`.** Tienen que pasar.
- [ ] **Paso 5: Commit** — `feat(catalogo): aplicar la planilla: artículos, precios, proveedor y medidas (A18, tarea 6)`

---

### Tarea 7: Las rutas

**Archivos:**
- Crear: `backend/app/api/esquemas_materiales.py`, `backend/app/api/rutas_planilla.py` y `backend/app/api/rutas_materiales.py`
- Modificar: `backend/app/api/app.py` (sumar los dos routers), `backend/app/api/rutas_inicio.py` y `backend/app/api/esquemas_inicio.py` (el resumen de materiales)
- Prueba: `backend/tests/api/test_rutas_planilla.py`, `backend/tests/api/test_rutas_materiales.py` y `backend/tests/api/test_rutas_inicio.py` (ajustar `test_los_conteos_de_materiales` y el de la base vacía)

**Usa:** `leer_planilla` (tarea 2), `armar_revision` (tarea 5), `aplicar_revision` y `poner_el_precio` (tarea 6), `en_utc` (`rutas_inicio.py`).

**Las rutas:**

```python
# rutas_planilla.py — router = APIRouter(tags=["planilla"])
_REVISIONES: dict[str, Revision]   # en memoria; se guardan las últimas 5 (la más vieja se va)
# El archivo subido se lee de `archivo.file` y no se guarda en ningún lado (diseño §5.1): trae datos de clientes.

@router.post("/planilla/revisar", response_model=RevisionLeer)
def revisar_planilla(archivo: UploadFile, sesion: Session = Depends(obtener_sesion)) -> RevisionLeer: ...

@router.post("/planilla/revisiones/{revision_id}/aplicar", response_model=CargaLeer)
def aplicar(revision_id: str, datos: AplicarRevision, sesion: Session = Depends(obtener_sesion)) -> CargaLeer: ...
    # id desconocido → 404 «Esa revisión ya no está: volvé a subir la planilla.»
    # aplicada, se saca de _REVISIONES

# rutas_materiales.py — router = APIRouter(tags=["materiales"])
@router.get("/catalogo", response_model=CatalogoLeer)
def catalogo(sesion: Session = Depends(obtener_sesion)) -> CatalogoLeer: ...

@router.patch("/formatos/{formato_id}/proveedor", response_model=FormatoLeer)
def marcar_proveedor(formato_id: int, datos: ProveedorElegido, sesion: Session = Depends(obtener_sesion)) -> Formato: ...
    # proveedor None → automático. Un proveedor sin artículo en la planilla para ese código →
    # 400 «Ese proveedor no tiene precio para «CHA0011» en la planilla.» Después, poner_el_precio.
```

**Los esquemas** (`esquemas_materiales.py`). Los de la revisión son la forma JSON de las dataclasses de la tarea 5, sin `planilla`; las medidas van como `{"ancho_mm", "alto_mm"}` y los datetime pasan por `en_utc`:

```python
class MedidaAMano(BaseModel): codigo: str; ancho_mm: Decimal; alto_mm: Decimal
class AplicarRevision(BaseModel): medidas: list[MedidaAMano] = []
class ProveedorElegido(BaseModel): proveedor: str | None
class CargaLeer(BaseModel): id: int; archivo: str; cargada_en: datetime; articulos: int; cambios: int; dolar_venta: Decimal | None
class RevisionLeer(BaseModel): ...       # id, archivo, carga_anterior_en, dolar_antes, dolar_ahora, primera_carga,
                                         # cambian, de_prueba, nuevos, ya_no_estan, hay_que_mirar, sin_cambios,
                                         # se_enlazan, quedan_a_mano
class ArticuloLeer(BaseModel): ...       # todas las columnas de Articulo, from_attributes
class ProveedorLeer(BaseModel): proveedor: str; cuenta: bool; articulo: ArticuloLeer
class MedidaLeer(BaseModel):
    formato: FormatoLeer                 # el de esquemas_catalogo
    cargada_a_mano: bool                 # su código no tiene ningún artículo
    ya_no_esta: bool                     # tiene artículos, pero ninguno en la última planilla
    proveedores: list[ProveedorLeer]     # ordenados por fila
    proveedor_a_mano: str | None
    retazos: list[FormatoLeer]           # también los escondidos, con su `disponible`
class EspesorLeer(BaseModel): material: MaterialLeer; corte: ParametrosCorteLeer | None; medidas: list[MedidaLeer]
class MaterialDelCatalogoLeer(BaseModel): nombre: str; espesores: list[EspesorLeer]   # los Material de mismo nombre
class CategoriaLeer(BaseModel): nombre: str; se_corta: bool; materiales: list[MaterialDelCatalogoLeer]; insumos: list[ArticuloLeer]
class CatalogoLeer(BaseModel): ultima_carga: CargaLeer | None; categorias: list[CategoriaLeer]
```

- **Cómo se arma el catálogo:**
  - **Los materiales** van en la categoría de su `familia`. Los insumos, que son los `Articulo` que no se anidan, van en `nombre_de_categoria(categoria)`. Se juntan por nombre.
  - **El orden:** las categorías que se cortan primero, después las otras, cada grupo por nombre; los materiales por nombre; los espesores por `espesor`; las medidas por código.
  - **Solo los insumos que están en la última planilla.** Las medidas que ya no están en la planilla sí van, marcadas.
  - **Se arma con pocas consultas, no una por medida:** con la planilla real son unos 60 materiales y 289 artículos.
- **El resumen del inicio:** `MaterialesResumidosLeer` suma `articulos: int` (los `Articulo` con `en_ultima_planilla`) y `ultima_planilla_en: datetime | None` (`creado_en` de la última carga, con `en_utc`). Lo demás no cambia.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_revisar_y_aplicar_por_http(cliente): ...      # subir con files={"archivo": ("planilla.xlsx", bytes, …)}, aplicar, GET /catalogo
def test_aplicar_con_la_medida_a_mano(cliente): ...
def test_un_archivo_que_no_es_excel_da_su_mensaje(cliente): ...   # 400 y mensaje_de == el texto de la tarea 2
def test_una_revision_que_no_existe(cliente): ...       # 404 y su mensaje
def test_aplicar_dos_revisiones_de_la_misma_base_la_segunda_vence(cliente): ...   # 409
def test_el_catalogo_agrupa_por_categoria_material_y_espesor(cliente): ...
def test_el_catalogo_marca_el_proveedor_que_cuenta_y_lo_que_esta_a_mano(cliente): ...
def test_marcar_un_proveedor_cambia_el_precio_de_la_medida_y_sus_retazos(cliente): ...
def test_marcar_un_proveedor_que_no_esta(cliente): ...
def test_volver_a_automatico(cliente): ...
def test_el_resumen_del_inicio_cuenta_los_articulos_y_la_fecha(cliente): ...
```

- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir los esquemas y las rutas, sumarlas a `app.py` y ajustar el inicio.**
- [ ] **Paso 4: Correr toda la suite del servidor.** Tiene que pasar entera, con las 3 xfail de siempre.
- [ ] **Paso 5: Commit** — `feat(materiales): revisar y aplicar la planilla, el catálogo y el proveedor por la API (A18, tarea 7)`

---

### Tarea 8: La planilla real sobre una copia de la base

Sin código del producto: se prueba lo construido con los datos reales. Las herramientas van en `backend/local/herramientas-a18/`, fuera de git.

- [ ] **Paso 1: Copiar la base:** `python local/herramientas-a17/copiar_base.py a18`.
- [ ] **Paso 2: Guardar la lectura del corpus con las medidas de la copia antes de cargar.** Escribir `local/herramientas-a18/lectura_con_el_catalogo.py guardar|comparar <carpeta de la base>`. Usa `leer()` de `local/herramientas-a17/lectura_del_corpus.py`, pero con `FORMATOS` reemplazado por `_formatos_del_catalogo(sesion)` de esa base, y guarda o compara forma por forma, igual que aquel.
- [ ] **Paso 3: Revisar y aplicar la planilla real en la copia**, con un servidor propio sobre la copia (`CARTELERIA_DATOS=local/tmp-a17/a18`, en un puerto que no sea 8000) o llamando a las funciones. Anotar:
  - cuántos se enlazan, cuántos entran y qué queda a mano (se espera `CHA0016` y `POL0006`);
  - qué hay que mirar (se espera `CHA0013`);
  - que el costeo de Complejo da lo mismo que antes, salvo los precios que cambiaron.
- [ ] **Paso 4: Comparar la lectura del corpus después de cargar** (Review Focus 1). **Si cambia alguna forma o alguna hoja, se para acá y se le muestra a Enzo qué cambió**, antes de seguir con la pantalla.
- [ ] **Paso 5: Subir la misma planilla otra vez:** todo «sin cambios».
- [ ] **Paso 6: Anotar los números en la sección «Desvíos» al final de este plan** y hacer commit de este plan: `docs(a18): la planilla real sobre una copia (A18, tarea 8)`.

**Pausa: fin del tramo 2.**

---

## Tramo 3 — La pantalla de Materiales

### Tarea 9: El cliente, los hooks y el árbol

**Archivos:**
- Modificar: `frontend/src/api/client.ts` (sumar `apiPut<T>(path: string, body: unknown): Promise<T>`, como `apiPatch`)
- Crear: `frontend/src/api/materiales.ts`, `frontend/src/hooks/useMateriales.ts`, `frontend/src/components/Materiales/arbol.ts`
- Prueba: `frontend/src/components/Materiales/arbol.test.ts` y `frontend/src/api/materiales.test.ts` (como `inicio.test.ts`)

**Deja para las otras tareas:**

Los tipos de `api/materiales.ts` copian los esquemas de `esquemas_materiales.py` (tarea 7), con los `Decimal` como `string`. Se llaman: `Carga`, `Revision`, `Articulo`, `ProveedorDelCatalogo`, `MedidaDelCatalogo`, `EspesorDelCatalogo`, `MaterialDelCatalogo`, `Categoria`, `Catalogo`, `MedidaAMano` y `CorteParaGuardar`. `Formato`, `Material` y `ParametrosCorteMaterial` siguen viniendo de `api/catalogo.ts`.

```ts
// api/materiales.ts
export interface Catalogo { ultima_carga: Carga | null; categorias: Categoria[] }
export function obtenerCatalogo(): Promise<Catalogo>;
export function revisarPlanilla(archivo: File): Promise<Revision>;               // apiPostForm, campo "archivo"
export function aplicarRevision(id: string, medidas: MedidaAMano[]): Promise<Carga>;
export function marcarProveedor(formatoId: number, proveedor: string | null): Promise<Formato>;
export function guardarCorte(materialId: number, corte: CorteParaGuardar): Promise<ParametrosCorteMaterial>;  // PUT
export function cambiarSeAnida(materialId: number, valor: boolean): Promise<Material>;                       // PATCH

// hooks/useMateriales.ts — queryKey ["catalogo"]; al terminar cualquier mutación se invalidan
// ["catalogo"], ["materiales"], ["formatos"], ["formato"], ["parametros-corte-material"],
// ["resumen-del-inicio"] y ["a-seccionar"]
export function useCatalogo(): UseQueryResult<Catalogo>;
export function useRevisarPlanilla(); export function useAplicarRevision();
export function useMarcarProveedor(); export function useGuardarCorte(); export function useCambiarSeAnida();

// components/Materiales/arbol.ts
export type Eleccion = { tipo: "material"; categoria: string; nombre: string } | { tipo: "insumo"; codigo: string; proveedor: string };
export function nombreParaMostrar(nombre: string): string;
export function filtrarCatalogo(catalogo: Catalogo, texto: string): Catalogo;
export function primeraEleccion(catalogo: Catalogo): Eleccion | null;
```

- **`nombreParaMostrar`:** la primera letra en mayúscula y el resto en minúscula, salvo las siglas `MDF`, `PVC`, `ACM` y `LED`, que quedan en mayúsculas. «CHAPA NEGRA» → «Chapa negra», «ACM NEGRO SATINADO» → «ACM negro satinado».
- **`filtrarCatalogo`:** sin distinguir mayúsculas ni tildes. Un material queda si su nombre o el código de alguna de sus medidas contiene el texto, y un insumo si su código o su descripción lo contienen. Las categorías que quedan vacías se van. Con el texto vacío devuelve el catálogo tal cual.
- **`primeraEleccion`:** el primer material de la primera categoría que se corta; si no hay ninguno, el primer insumo; si no hay nada, `null`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```ts
it("muestra los nombres como en el boceto", () => {
  expect(nombreParaMostrar("CHAPA NEGRA")).toBe("Chapa negra");
  expect(nombreParaMostrar("ACM NEGRO SATINADO")).toBe("ACM negro satinado");
});
it("filtra por nombre, código o descripción, sin tildes ni mayúsculas", ...);
it("saca las categorías que quedan vacías", ...);
it("elige primero un material que se corta", ...);
it("revisarPlanilla manda el archivo en el campo «archivo»", ...);   // con un fetch falso, como inicio.test.ts
```

- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir el cliente, los hooks y `arbol.ts`.**
- [ ] **Paso 4: Correrlas y correr `npx tsc --noEmit`.** Tienen que pasar.
- [ ] **Paso 5: Commit** — `feat(materiales): el cliente, los hooks y el árbol de la pantalla (A18, tarea 9)`

---

### Tarea 10: La pantalla, la barra y el inicio

**Archivos:**
- Crear: `frontend/src/routes/Materiales.tsx` y, en `frontend/src/components/Materiales/`, `ListaDeCategorias.tsx`, `DetalleDelMaterial.tsx`, `CorteDelEspesor.tsx` y `DetalleDelInsumo.tsx`
- Modificar: `frontend/src/App.tsx` (ruta `/materiales`), `frontend/src/components/Barra.tsx` («Materiales» pasa a `NavLink`) y `frontend/src/routes/Inicio.tsx` (el recuadro), además de `frontend/src/api/inicio.ts` (los dos campos nuevos del resumen)

**Lo que muestra** (diseño §5.6 y §5.7, boceto C):
- **Arriba:**
  - «Materiales»;
  - a la derecha, «Planilla: <archivo>, cargada el dd/mm · N artículos», o «Todavía no se cargó la planilla de precios», y el botón «Actualizar desde la planilla», que en esta tarea no hace nada todavía (lo conecta la tarea 11).
  - La fecha va en hora de Argentina, como las tarjetas de A16.
- **`ListaDeCategorias`:**
  - el buscador («Buscar…») con `filtrarCatalogo`;
  - las categorías, que se abren y se cierran, con cuántos artículos tiene cada una;
  - adentro, los materiales con `nombreParaMostrar` y cuántas medidas tienen, o los insumos con su descripción.
  - La elección queda marcada como en el boceto (fondo verde claro y borde a la izquierda). Al entrar, `primeraEleccion`, con su categoría abierta.
- **`DetalleDelMaterial`:**
  - el nombre, los proveedores y la casilla «Se anida» (`useCambiarSeAnida`);
  - por espesor, un `CorteDelEspesor`;
  - la tabla de medidas: espesor, medida, código, proveedor y costo por m², con «de prueba» o «sin precio» cuando corresponda; con dos proveedores, dos renglones, el que cuenta marcado «el que cuenta» y el otro con «Usar este» (`useMarcarProveedor`); si el que cuenta está marcado a mano, un enlace «Volver a automático»; las medidas que ya no están, marcadas «ya no está en la planilla», y las cargadas a mano, «cargada a mano, no está en la planilla»;
  - los retazos, debajo de su medida, con «+ Retazo» y «Quitar» (`useCrearRetazo` y `useQuitarFormato` de `useCatalogo.ts`; el campo de medida y sus límites, como en `ListaDeFormatos`);
  - «Lo que dice la planilla», plegado (`<details>`): una tabla con todas las columnas de cada proveedor.
- **`CorteDelEspesor`:**
  - lo que se come el corte, el borde que no se usa, la separación entre piezas, el giro («libre» o «solo media vuelta») y «Confirmado con el taller», con «Guardar» (`useGuardarCorte`).
  - Sin corte cargado dice «Sin cargar: el anidado usa el del sistema».
  - El atajo «Usar estos valores en todos los espesores» guarda el mismo corte en cada espesor del material.
- **`DetalleDelInsumo`:** la descripción, el código, la categoría y los proveedores, con la misma tabla plegada de la planilla.
- **La barra:** «Materiales» con `NavLink to="/materiales"`; «Presupuestos» sigue apagado.
- **El inicio:**
  - el recuadro cuenta «N artículos, M materiales para cortar, K medidas de chapa y R retazos», con «Planilla del dd/mm» abajo;
  - sin planilla, como hoy;
  - suma un enlace «Ver materiales».

- [ ] **Paso 1: Escribir las pruebas de pantalla que fallan.** Solo lo que no depende del servidor, en `arbol.test.ts`: los textos de las marcas de una medida, con una función pura `marcasDeLaMedida(medida: MedidaDelCatalogo): string[]` (`["de prueba"]`, `["sin precio"]`, `["ya no está en la planilla"]`, `["cargada a mano, no está en la planilla"]`).
- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir los componentes y los cambios.**
- [ ] **Paso 4: `npx vitest run` y `npx tsc --noEmit`.** Tienen que pasar.
- [ ] **Paso 5: Mirarla en Chrome sin ventana sobre la copia de la tarea 8** (guion `local/herramientas-a18/recorrido-a18.mjs`, a partir de `herramientas-a16/recorrido-a16.mjs`). Capturas del inicio, de Materiales con «Chapa negra», con «PVC espumado» (dos proveedores) y con un insumo.
- [ ] **Paso 6: Commit** — `feat(materiales): la pantalla de Materiales, la barra y el inicio (A18, tarea 10)`

**Pausa: fin del tramo 3.** Mostrarle a Enzo las capturas.

---

## Tramo 4 — Actualizar desde la planilla en la pantalla

### Tarea 11: Subir, revisar y aplicar

**Archivos:**
- Crear: `frontend/src/components/Materiales/RevisionDePlanilla.tsx`
- Modificar: `frontend/src/routes/Materiales.tsx` (el botón abre un `<input type="file" accept=".xlsx">`; con la revisión, la pantalla muestra `RevisionDePlanilla` en lugar de las dos columnas)
- Prueba: `frontend/src/components/Materiales/arbol.test.ts` (las cuentas del resumen)

**Lo que muestra** (diseño §5.4, boceto `actualizar-planilla.html`):
- **«Revisar la planilla nueva»**, con el archivo, el dólar («$ 1.530 → $ 1.580», o solo el nuevo en la primera carga) y «la anterior se cargó el dd/mm».
- **Las cajitas del resumen:** precios que cambian, con precio de verdad (antes «de prueba»), artículos nuevos, ya no están, hay que mirarlo (en amarillo) y sin cambios. En la primera carga, en lugar de «precios que cambian» van «se enlazan» y «quedan a mano», con la lista de los códigos que quedan a mano.
- **Una tabla por parte, solo si tiene algo:**
  - en «Precios que cambian», «Cambio» en % redondeado al entero, rojo si sube y verde si baja, «pasa a ser el de por defecto» y «en USD: cambió el dólar» cuando corresponda;
  - se muestran los primeros 20 renglones de cada parte y «… y N más», que al tocarlo muestra todos *(decisión del plan)*.
- **«Hay que mirarlo»:** un campo «ancho × alto mm» por renglón, que viene con la medida de antes si había. Debajo: «Si no se completa, ese artículo queda como estaba y lo demás se aplica igual.»
- **Abajo:** «Los presupuestos ya armados no cambian solos: toman el precio nuevo si se vuelven a calcular los materiales en el Costeo.», «Cancelar» y «Aplicar los cambios».
- **Al aplicar**, se vuelve a la pantalla con el aviso «Listo: se aplicó la planilla <archivo>.» Los errores del servidor van con `Mensaje` (A9), como el de la revisión vencida.
- **Al subir**, mientras se lee: «Leyendo la planilla…». Un error al leer se muestra arriba de las dos columnas, con `Mensaje`.

**Función pura para probar:** `cuentasDeLaRevision(revision: Revision): { etiqueta: string; cantidad: number; aviso: boolean }[]`, en `arbol.ts`. Da las cajitas, en ese orden, con sus textos y las de la primera carga.

- [ ] **Paso 1: Escribir las pruebas que fallan** de `cuentasDeLaRevision`: una carga común y una primera carga.
- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir `RevisionDePlanilla` y conectarla.**
- [ ] **Paso 4: `npx vitest run` y `npx tsc --noEmit`.**
- [ ] **Paso 5: Recorrido sobre una copia nueva** (`copiar_base.py a18`), con la planilla real:
  - primera carga y aplicar;
  - completar la medida de `CHA0013`;
  - subir otra vez la misma planilla y ver todo «sin cambios»;
  - una copia de la planilla con un precio cambiado a mano (hecha con `openpyxl` en `local/herramientas-a18/`) y ver ese precio en «cambian»;
  - marcar otro proveedor de `PVC0001` y ver el precio en el Costeo de un grupo de prueba con PVC.
- [ ] **Paso 6: Commit** — `feat(materiales): subir la planilla, revisarla y aplicarla en la pantalla (A18, tarea 11)`

**Pausa: fin del tramo 4.**

---

## Tramo 5 — Opciones avanzadas en Anidado

### Tarea 12: El desplegable

**Archivos:**
- Crear: `frontend/src/routes/TrabajoWorkspace/opcionesAvanzadas.ts` y su prueba `opcionesAvanzadas.test.ts`
- Modificar: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`

**Deja:**

```ts
export interface OpcionesAvanzadas { motor: "rectpack" | "sparrow"; semilla: number; busqueda: number; limite: number; simplificacion: number; vaciarChapas: boolean }
export const POR_DEFECTO: OpcionesAvanzadas = { motor: "sparrow", semilla: 42, busqueda: 2, limite: 240, simplificacion: 0.3, vaciarChapas: true };
export function cambiadas(actuales: OpcionesAvanzadas): boolean;
```

- **Los `useState`** de esas seis opciones toman su valor inicial de `POR_DEFECTO`, que reemplaza a los números sueltos de hoy.
- **Quedan a la vista**, como hoy, «Aprovechar huecos» y «Anidar» arriba. Debajo, «Girar a cualquier ángulo» y el sobrante.
- **Dentro de un `<details>` cerrado, con `<summary>` «Opciones avanzadas»:**
  - el motor, la semilla, la búsqueda por chapa, el tiempo máximo total, la simplificación y «Vaciar chapas»;
  - el párrafo «Acomoda las piezas, las reparte en chapas…».
- **Con `cambiadas(...)`**, al lado del título va «cambiadas», en `text-bronze`.
- **«Girar a cualquier ángulo» y el sobrante** siguen apareciendo solo con Sparrow, como hoy.
- **No cambia** lo que se manda al anidar (`opciones`) ni la tabla de anidados.

- [ ] **Paso 1: Escribir las pruebas que fallan:** `cambiadas(POR_DEFECTO)` es `false`; con cualquiera de las seis distinta, `true`.
- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir `opcionesAvanzadas.ts` y cambiar `AnidadoTab.tsx`.**
- [ ] **Paso 4: `npx vitest run` y `npx tsc --noEmit`.** Mirarlo en Chrome sobre la copia: el desplegable cerrado, abrirlo, cambiar la semilla y ver «cambiadas», y anidar el parador o Complejo como siempre.
- [ ] **Paso 5: Commit** — `feat(anidado): las opciones del motor en «Opciones avanzadas» (A18, tarea 12)`

**Pausa: fin del tramo 5.**

---

## Tramo 6 — El cierre

### Tarea 13: El recorrido y el cierre

- [ ] **Paso 1: La suite entera.** Servidor (`python -m pytest -q`, con los temporales en D:), pantalla (`npx vitest run`) y `npx tsc --noEmit`.
- [ ] **Paso 2: El recorrido completo** sobre una copia nueva, con lo del §7 del diseño. Capturas en `local/herramientas-a18/`.
- [ ] **Paso 3: La revisión de toda la rama**, con el ok de Enzo. Arreglar lo importante con su prueba.
- [ ] **Paso 4: Los documentos:**
  - el diseño con su estado y una sección «Cómo quedó»;
  - el `PLAN-MAESTRO.md §7`: la fila de las pantallas y «Lo grande», con Materiales hecho;
  - el `README.md`, en «En qué estamos»;
  - en el `REGISTRO.md`, la fuente de `SUP-19`, `PAR-59` y `P-35` pasa de `plan/` a `historico/`;
  - la carpeta pasa a `docs/historico/A18-pantalla-de-materiales/`.
- [ ] **Paso 5: Con el ok de Enzo, fusionar en `main` y subir.** La base real se pone al día sola al arrancar el servidor, con respaldo (A17). **La primera carga de la planilla en la base real la hace Enzo desde la pantalla**, después de un respaldo (diseño §5.5).

---

## Desvíos

### Tarea 8: la planilla real sobre una copia de la base (2026-11-06)

**Lo que dio bien**, con `CARTELERIA 2026.xlsx` por la app entera, con su arranque real:
- La copia, en `d4b2e8a1f630`, se actualizó sola a `e7a1c5d9b318`, con su respaldo.
- La revisión de la primera carga: 288 renglones, 254 códigos. Se enlazan 27 códigos, entran 261 renglones (231 insumos y 30 que se anidan: 29 medidas y 21 materiales nuevos), quedan a mano `CHA0016` y `POL0006`, hay que mirar `CHA0013` y no cambia ningún precio. Las medidas pasan de 29 a 58, y los materiales de 23 a 44.
- El costeo de Complejo, Parador y Corpóreas da igual, y los grupos siguen con su medida. El catálogo responde en 0,07 s.
- La misma planilla otra vez: 287 renglones sin cambios, `CHA0013` sigue para mirar, y no se duplica ni se anota nada.
- Siguen con precio de prueba `ACR0009`, `CHA0001`, `CHA0002`, `CHA0007`, `CHA0008` y `CHA0009`, porque la planilla no les trae precio, y `CHA0016` y `POL0006`, que no están en ella. Quedan sin precio `MDF0003` a `MDF0006`.

**Lo que paró la tarea (lo que más podía fallar, punto 1).** Con la planilla cargada cambió la lectura de 2 de los 9 DXF de prueba: `Muestra Vectores` (9 formas) y `muestra 2` (33). La regla es que un rectángulo que no entra en ninguna chapa es un tablero de presentación y lo de adentro son piezas (`_marcar_contrapiezas`). Con MDF de 1830 × 2750 y 1830 × 3660 y ACM de 5000 × 1500 esos tableros «entraban»: sus letras pasaban a ser el recorte de un hueco y se descartaban (38 formas, 2,18 m²), y los huecos de las letras pasaban a cortarse (4 formas). Metalex, Polyfan y MDF de 1830 × 2600 no cambiaban nada.

**Lo que decidió Enzo (2026-11-06):** la lectura sigue con las medidas de hoy. `_formatos_del_catalogo` mira solo las familias de `PAR-60` (Chapas, Acrílicos y Policarbonato); las otras se venden pero no cambian cómo se lee un dibujo. Antes de la primera planilla, Alto impacto y Corrugado todavía tienen su propia familia, pero sus medidas ya están en Chapas. Con el cambio, la lectura de los 9 DXF con la planilla cargada no tiene ninguna diferencia, tampoco en la escala sugerida.

**Lo que queda igual que hoy:** una pieza de MDF más grande que las medidas de esas familias figura como que no entra en ninguna chapa, y una hoja de MDF dibujada no se reconoce. Decidir el tablero por lo que tiene adentro y no por la medida quedó en el plan maestro, con «cambiar cómo decide el lector».
