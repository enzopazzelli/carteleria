# A15 · El diseño anidado en PDF — plan

> **Para quien ejecuta:** tarea por tarea, con **pausa al final de cada una** para que Enzo la vea antes de seguir. Así trabaja este proyecto, aunque el skill de ejecución diga otra cosa. Los pasos usan casillas (`- [ ]`) para llevar la cuenta.

**Objetivo:** un PDF por trabajo, en A4 y en color. Por cada material lleva una hoja con el diseño pintado por chapa y después las chapas juntas, a 1:20, con la grilla y el número de cada pieza.

**Cómo:** se arma en tres capas.
1. **Leer de la base** lo que va en el PDF (`rutas_pdf_anidado.py`).
2. **Repartir las hojas**: qué va en cada una y dónde, en mm de papel (`hojas_pdf.py`, puro, se prueba con números).
3. **Dibujarlas con ReportLab** (`pdf_anidado.py`).

Igual que el PDF del presupuesto, que separa `documento.py` de `pdf.py`.

**Herramientas:** Python 3.13, FastAPI, SQLAlchemy, shapely, ReportLab y pypdf (ya instalados). React + TypeScript + vitest.

**Diseño:** [`diseno.md`](diseno.md), aprobado por Enzo el 2026-10-25. Este plan se apoya en él: hay que leer los dos.

## Lo que vale para todas las tareas

- **Hojas A4 con margen de 10 mm.** Las de chapas, siempre apaisadas (297 × 210). La del diseño, apaisada o parada: la que deje el diseño más grande.
- **Escala:** 1:20 para todas las chapas de un material. Si no entran, la primera de 1:25, 1:40 y 1:50 que entre; si ninguna entra, el primer múltiplo de 50 que entre.
- **Hasta 4 chapas por hoja**, las que entren a lo ancho.
- **La grilla:** líneas cada 100 mm de chapa, una más marcada cada 500, y números en cm cada 500, desde la esquina de abajo a la izquierda.
- **El número de cada pieza:** su nombre corto, en negrita, de 7 puntos, con un borde blanco alrededor de cada letra.
- **El texto del pie de las hojas de chapas, tal cual:** «Escala 1:N. Grilla cada 10 cm; los números, en cm desde la esquina de abajo a la izquierda. Imprimir al 100 % (tamaño real).»
- **Los colores son los de `frontend/src/components/Disenio/pintado.ts`:**
  - `PALETA_CHAPAS`: `#4e79a7 #59a14f #b07aa1 #76b7b2 #edc948 #9c755f #ff9da7 #1f4e79 #8cd17d #6f4e7c #499894 #d4a6c8`;
  - `ROJO_FALTA`: `#d62728`;
  - `GRIS_OTRO`: `#d9dee3`.
- **Qué anidado cuenta:** `_ejecucion_para_costear(grupo)` (`app/costeo.py`), el definitivo o el último terminado.
- **La misma cuenta que el DXF:** `_anillos_en_plancha` y `_geometria_de` (`exportacion_dxf.py`) sobre `_resultado_y_geometrias(ejecucion)` (`rutas_ajuste.py`). Una pieza sin contorno va como su rectángulo, igual que en el DXF.
- **Letras:** las Source Sans 3 de `app/services/presupuesto/fuentes/`. No se suman dependencias.
- **Commits sin la línea `Co-Authored-By`**, en la rama `feat/pdf-disenio-anidado`, que sale de `main`.
- **Pruebas con los temporales en D:**, porque C: suele estar lleno. Desde `backend/`:
  `CARTELERIA_DATOS=local/tmp-a15/datos python -m pytest -q --basetemp=local/tmp-a15/pytest <pruebas>`
  Las de la pantalla, desde `frontend/`: `npx vitest run <archivo>` y `npx tsc --noEmit`.

## Lo que más puede fallar sin que ninguna prueba lo mire

Cada uno tiene su prueba en la tarea que lo toca.

1. **Un trabajo con acentos, comillas o espacios en el nombre** («Cartel «Peña» 2»). Tiene que bajar con un nombre de archivo sin acentos y el encabezado tiene que mostrar el nombre tal cual. Está en las tareas 2 y 3.
2. **Textos con `&` o `<`** en el nombre del trabajo, del material o del cliente. Tienen que salir escritos, sin cortar el PDF. Está en la tarea 2.
3. **Un trabajo sin el DXF guardado, o con todas sus piezas sin lugar en el diseño.** La hoja del diseño sale con lo que haya, sin dividir por cero. Está en las tareas 2 y 3.
4. **Una pieza sin contorno**, cargada a mano. En la chapa va como su rectángulo, con su número. Está en la tarea 3.
5. **Una chapa muy grande**, que no entra ni a 1:50. Toma una escala que entre, en vez de salirse de la hoja. Está en la tarea 1.

---

### Tarea 1: Repartir las hojas

**Archivos:**
- Crear: `backend/app/services/nesting/hojas_pdf.py`
- Prueba: `backend/tests/services/nesting/test_hojas_pdf.py`

**Lo que deja para las otras tareas:**

```python
Punto = tuple[float, float]
Anillos = list[list[Punto]]  # el contorno primero, después los agujeros

@dataclass(frozen=True)
class PiezaEnChapa:
    nombre: str            # nombre corto
    anillos: Anillos       # mm de chapa, con la y hacia arriba (como el DXF)

@dataclass(frozen=True)
class ChapaDelPdf:
    indice: int            # desde 0
    piezas: list[PiezaEnChapa]
    usado: str             # "1220 × 2259"
    sobrante: str          # "1220 × 181"
    es_retazo: bool

@dataclass(frozen=True)
class PiezaDelDisenio:
    nombre: str
    anillos: Anillos       # mm del dibujo
    estado: Literal["en_chapa", "falta", "otro"]
    chapa: int | None = None
    copias: int = 1

@dataclass(frozen=True)
class DisenioDelPdf:
    fondo: list[Anillos]
    piezas: list[PiezaDelDisenio]
    cortes: list[list[Punto]]
    sin_lugar: list[str]   # nombres cortos

@dataclass(frozen=True)
class BloqueDelPdf:
    material: str          # "Chapa negra cal. 22"
    grupo: str
    chapa_ancho_mm: float
    chapa_alto_mm: float
    con_veta: bool
    chapas: list[ChapaDelPdf]
    linea: str             # «7 chapas enteras»
    anidado: str           # «anidado #9, elegido para el presupuesto»
    disenio: DisenioDelPdf

@dataclass(frozen=True)
class TrabajoDelPdf:
    nombre: str
    archivo: str | None
    generado: datetime
    presupuesto: str | None  # «P-2026-0003 · Cliente SA»
    bloques: list[BloqueDelPdf]
    sin_anidar: list[str]    # nombres de los grupos

@dataclass(frozen=True)
class Caja:                  # mm de papel, desde la esquina de abajo a la izquierda de la hoja
    x_mm: float
    y_mm: float
    ancho_mm: float
    alto_mm: float

@dataclass(frozen=True)
class ChapaEnHoja:
    indice: int
    caja: Caja               # el rectángulo de la chapa en el papel

@dataclass(frozen=True)
class Hoja:
    numero: int              # desde 1
    total: int
    ancho_mm: float
    alto_mm: float
    bloque: int
    tipo: Literal["disenio", "chapas"]
    escala: int = 0                                    # solo en «chapas»
    chapas: list[ChapaEnHoja] = field(default_factory=list)
    disenio: Caja | None = None                        # solo en «disenio»: el recuadro del diseño
    tabla: Caja | None = None                          # solo en «disenio»: el detalle de chapas

def nombre_corto(id_origen: str) -> str
def escala_para(chapa_ancho_mm: float, chapa_alto_mm: float) -> int
def chapas_por_hoja(chapa_ancho_mm: float, escala: int) -> int
def armar_hojas(trabajo: TrabajoDelPdf) -> list[Hoja]
def al_papel(punto: Punto, chapa: ChapaEnHoja, escala: int) -> Punto
```

**Las medidas de la hoja, en constantes del módulo:**
- margen 10;
- encabezado 12;
- pie 14;
- título de la chapa 5;
- lo de debajo de la chapa 8;
- números de la grilla 5;
- separación entre chapas 3;
- una fila del detalle de chapas 5, más 18 de título y renglones finales.

Con esas medidas, en una hoja apaisada quedan **146 mm de alto y 277 de ancho para las chapas**. Una chapa entra si `alto/escala ≤ 146`. Por hoja van `n` chapas, con `n` el mayor que cumple `n·(ancho/escala + 5) + (n−1)·3 ≤ 277`, y como mucho 4.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_nombre_corto():
    assert nombre_corto("trabajo-1-497") == "497"
    assert nombre_corto("trabajo-1-39/unida") == "39/unida"
    assert nombre_corto("logo-12/t3") == "12/t3"

def test_escala():
    assert escala_para(1220, 2440) == 20
    assert escala_para(1500, 3000) == 25
    assert escala_para(2000, 8000) == 100       # ni a 1:50 entra

def test_chapas_por_hoja():
    assert chapas_por_hoja(1220, 20) == 4
    assert chapas_por_hoja(1500, 20) == 3
    assert chapas_por_hoja(1000, 20) == 4

def test_siete_chapas_dan_tres_hojas():           # Complejo
    hojas = armar_hojas(_trabajo([_bloque(7, 1220, 2440)]))
    assert [h.tipo for h in hojas] == ["disenio", "chapas", "chapas"]
    assert [len(h.chapas) for h in hojas[1:]] == [4, 3]
    assert [(h.numero, h.total) for h in hojas] == [(1, 3), (2, 3), (3, 3)]
    for h in hojas[1:]:
        assert (h.ancho_mm, h.alto_mm) == (297, 210) and h.escala == 20
        for c in h.chapas:
            assert (c.caja.ancho_mm, c.caja.alto_mm) == pytest.approx((61, 122))
            assert 10 <= c.caja.x_mm and c.caja.x_mm + c.caja.ancho_mm <= 287
        assert all(a.caja.x_mm + a.caja.ancho_mm < b.caja.x_mm for a, b in zip(h.chapas, h.chapas[1:]))

def test_tres_chapas_dan_dos_hojas():             # parador1
    assert len(armar_hojas(_trabajo([_bloque(3, 1000, 2000)]))) == 2

def test_dos_materiales_dan_dos_bloques():
    hojas = armar_hojas(_trabajo([_bloque(2, 1220, 2440), _bloque(5, 1220, 2440)]))
    assert [(h.bloque, h.tipo) for h in hojas] == [
        (0, "disenio"), (0, "chapas"), (1, "disenio"), (1, "chapas"), (1, "chapas")]

def test_la_hoja_del_disenio_se_para_si_el_disenio_es_alto():
    alto = armar_hojas(_trabajo([_bloque(7, 1220, 2440, disenio=(1000, 1500))]))[0]
    ancho = armar_hojas(_trabajo([_bloque(3, 1000, 2000, disenio=(3000, 1000))]))[0]
    assert (alto.ancho_mm, alto.alto_mm) == (210, 297)
    assert (ancho.ancho_mm, ancho.alto_mm) == (297, 210)
    assert ancho.disenio.ancho_mm == pytest.approx(277)          # a todo el ancho
    assert ancho.disenio.y_mm >= ancho.tabla.y_mm + ancho.tabla.alto_mm  # el detalle, abajo

def test_al_papel_no_espeja():
    chapa = ChapaEnHoja(0, Caja(10, 40, 61, 122))
    assert al_papel((0, 2440), chapa, 20) == pytest.approx((10, 162))   # arriba sigue arriba
    assert al_papel((1220, 0), chapa, 20) == pytest.approx((71, 40))

def test_sin_bloques_no_hay_hojas():
    assert armar_hojas(_trabajo([])) == []
```

`_trabajo(bloques)` y `_bloque(n, ancho, alto, disenio=(ancho_dibujo, alto_dibujo))` son ayudas de la prueba. `_bloque` arma `n` chapas con una pieza cuadrada cada una, y un diseño cuyo fondo es un rectángulo de esa medida (por defecto 1000 × 1000).

- [ ] **Paso 2: Correrlas y ver que fallan.** Con el comando de arriba sobre `tests/services/nesting/test_hojas_pdf.py`. Tienen que fallar con `ModuleNotFoundError: app.services.nesting.hojas_pdf`.

- [ ] **Paso 3: Escribir `hojas_pdf.py`** con las firmas de arriba.
  - `nombre_corto` es el `nombreCorto` de la pantalla (`LecturaDxf/dibujo.ts`): se corta en «/» y de lo primero queda lo que sigue al último guion.
  - La hoja del diseño prueba las dos orientaciones con el recuadro que queda arriba del detalle de chapas, y elige la que da la escala mayor; si empatan, apaisada.
  - El recuadro va a todo el ancho entre márgenes.
  - Las chapas de una hoja se alinean abajo, sobre el pie.

- [ ] **Paso 4: Correrlas y ver que pasan.** Con el mismo comando. Todas tienen que pasar.

- [ ] **Paso 5: Commit**

```bash
git add backend/app/services/nesting/hojas_pdf.py backend/tests/services/nesting/test_hojas_pdf.py
git commit -m "feat(pdf): repartir las hojas del diseño anidado (A15, tarea 1)"
```

**Pausa: mostrarle a Enzo cómo quedan repartidas Complejo y parador1.**

---

### Tarea 2: Dibujar el PDF

**Archivos:**
- Crear: `backend/app/services/nesting/pdf_anidado.py`
- Prueba: `backend/tests/services/nesting/test_pdf_anidado.py`

**Usa:** todo lo de la tarea 1.

**Deja:**
- `dibujar_pdf(trabajo: TrabajoDelPdf) -> bytes`, que llama a `armar_hojas`;
- `PALETA_CHAPAS: tuple[str, ...]`, `ROJO_FALTA`, `GRIS_OTRO`;
- `color_de_chapa(indice: int) -> str`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_una_pagina_por_hoja_en_a4_apaisada():
    t = _trabajo(n_chapas=5)
    lector = PdfReader(io.BytesIO(dibujar_pdf(t)))
    assert len(lector.pages) == len(armar_hojas(t)) == 3
    caja = lector.pages[1].mediabox
    assert (float(caja.width), float(caja.height)) == pytest.approx((841.9, 595.3), abs=1)

def test_trae_los_textos_de_la_hoja():
    texto = _texto(dibujar_pdf(_trabajo(n_chapas=2, sin_anidar=["Calibre 18"], copias=3,
                                        presupuesto="P-2026-0003 · Cliente SA")))
    for esperado in ["Chapa 1", "Chapa 2", "497", "hoja 1 de 2", "Escala 1:20", "Imprimir al 100 %",
                     "2 chapas enteras", "anidado #9", "Sin anidar", "Calibre 18", "×3", "P-2026-0003 · Cliente SA"]:
        assert esperado in texto

def test_sin_presupuesto_no_queda_un_hueco_con_texto():
    assert "None" not in _texto(dibujar_pdf(_trabajo(n_chapas=1)))

def test_la_veta_solo_si_el_material_la_tiene():
    assert "veta" in _texto(dibujar_pdf(_trabajo(n_chapas=1, con_veta=True)))
    assert "veta" not in _texto(dibujar_pdf(_trabajo(n_chapas=1)))

def test_lo_que_falta_y_lo_sin_lugar():
    texto = _texto(dibujar_pdf(_trabajo(n_chapas=1, falta=["12"], sin_lugar=["7"])))
    assert "1 pieza(s) sin chapa" in texto and "12" in texto
    assert "sin lugar en el diseño" in texto and "7" in texto

def test_un_disenio_vacio_no_corta():
    texto = _texto(dibujar_pdf(_trabajo(n_chapas=1, disenio_vacio=True, sin_lugar=["3"])))
    assert "Chapa 1" in texto

def test_los_textos_raros_salen_tal_cual():
    texto = _texto(dibujar_pdf(_trabajo(n_chapas=1, nombre="A & <B> «Peña»")))
    assert "A & <B> «Peña»" in texto

def test_la_paleta_es_la_de_la_pantalla():
    fuente = (RAIZ / "frontend/src/components/Disenio/pintado.ts").read_text(encoding="utf-8")
    arreglo = re.search(r"PALETA_CHAPAS[^=]*=\s*\[(.*?)\]", fuente, re.S).group(1)
    assert list(PALETA_CHAPAS) == re.findall(r'"(#[0-9a-f]{6})"', arreglo)
    assert ROJO_FALTA in fuente and GRIS_OTRO in fuente
```

`_texto(contenido)` junta `extract_text()` de todas las páginas, como en `tests/services/presupuesto/test_pdf.py`. `RAIZ` es la carpeta del repositorio, `Path(__file__).parents[4]`. `_trabajo(...)` arma un `TrabajoDelPdf`: una pieza «497» por chapa (en el diseño, con las `copias` que se pidan), `linea` «N chapas enteras», `anidado` «anidado #9, elegido para el presupuesto» y `presupuesto` vacío si no se pasa.

- [ ] **Paso 2: Correrlas y ver que fallan.** Tienen que fallar con `ModuleNotFoundError: app.services.nesting.pdf_anidado`.

- [ ] **Paso 3: Escribir `pdf_anidado.py`** con ReportLab, dibujando directo sobre el `Canvas`, sin `Paragraph`: así un «<» no se lee como una etiqueta. Las letras se registran con los mismos nombres que el PDF del presupuesto (`SourceSans3`, `SourceSans3-Bold`). Las medidas son las del diseño §5.2 y §5.3.
  - **Piezas en la chapa:** relleno del color de la chapa con 45 % de opacidad (`setFillAlpha`), borde oscuro de 0,2 mm, y los huecos con `fillMode=FILL_EVEN_ODD`.
  - **Borde de la chapa:** de 0,8 mm, en su color.
  - **Número de cada pieza:** en `representative_point()` de shapely, primero con trazo blanco de 1,2 pt y después relleno negro.
  - **Barra de escala:** 500 mm de chapa, con tramos de 10 cm en blanco y negro.
  - **Hoja del diseño:**
    - el dibujo, encajado en `Hoja.disenio` sin deformarlo;
    - el fondo, en trazo gris claro y sin relleno;
    - las piezas en chapa, al 85 % del color de su chapa, con «×N» si tienen copias;
    - lo que es de otro material, en `GRIS_OTRO`;
    - lo que falta, en `ROJO_FALTA` con borde cortado;
    - los cortes de los seccionados, en raya oscura;
    - en `Hoja.tabla`, el detalle de chapas y las líneas finales;
    - en la primera hoja del PDF, «Sin anidar, no están en este PDF: …».
  - **Encabezado** en todas las hojas, como en el diseño §5.1. «Hoja N de M» sale de `Hoja.numero` y `Hoja.total`.

- [ ] **Paso 4: Correrlas y ver que pasan.** Todas tienen que pasar.

- [ ] **Paso 5: Mirar las hojas.** Pasar un PDF de prueba a imagen con `pypdfium2`, que está instalado, en `backend/local/tmp-a15/` (fuera de git). Mirar que el número se lea, que la grilla no tape, y que la letra «A» de una pieza no salga dada vuelta.

- [ ] **Paso 6: Commit**

```bash
git add backend/app/services/nesting/pdf_anidado.py backend/tests/services/nesting/test_pdf_anidado.py
git commit -m "feat(pdf): dibujar el diseño anidado con ReportLab (A15, tarea 2)"
```

**Pausa: mostrarle a Enzo las imágenes de las hojas.**

---

### Tarea 3: Los datos desde la base y el pedido nuevo

**Archivos:**
- Modificar: `backend/app/api/rutas_disenio.py`. Sacar el cuerpo de `obtener_disenio` a `disenio_del_trabajo(sesion: Session, trabajo: Trabajo) -> DisenioLeer`, que hace también la recuperación y el commit. La ruta lo llama.
- Modificar: `backend/app/api/rutas_ajuste.py`. Sacar a `material_usado_de(sesion: Session, ejecucion) -> MaterialUsado` lo que arma `obtener_material_usado` después de controlar el estado. La ruta lo llama.
- Crear: `backend/app/api/rutas_pdf_anidado.py`.
- Modificar: `backend/app/api/app.py`, para sumar `router_pdf_anidado`.
- Prueba: `backend/tests/api/test_rutas_pdf_anidado.py`.

**Usa:**
- `dibujar_pdf`, `TrabajoDelPdf` y las demás clases de las tareas 1 y 2;
- `_ejecucion_para_costear`, `_resultado_y_geometrias`, `_plancha_de`, `_anillos_en_plancha`, `_geometria_de` y `al_disenio`.

**Deja:**
- `GET /trabajos/{trabajo_id}/pdf-anidado`;
- `datos_del_pdf(sesion: Session, trabajo: Trabajo, ahora: datetime) -> TrabajoDelPdf`;
- `anillos_en_chapa(posicion: PosicionPieza, geometrias: dict[str, GeometriaPieza]) -> Anillos`;
- `nombre_de_archivo_pdf(nombre: str, dia: date) -> str`.

**Cómo se arma cada dato:**
- **Los bloques:** uno por grupo de `trabajo.grupos`, que ya vienen en orden, con la ejecución de `_ejecucion_para_costear`. Un grupo sin ejecución va a `sin_anidar`.
- **`anidado`:** «anidado #N, elegido para el presupuesto» si es la definitiva; si no, «anidado #N, el más reciente, sin elegir para el presupuesto».
- **`material`:** el `material_nombre` guardado con la corrida (`parametros["formato"]`); si no está, el material del formato del grupo, con su espesor si lo tiene.
- **`con_veta`:** si `parametros["rotaciones_permitidas"]` es `"SOLO_0_180"`.
- **Las chapas:** cada posición del resultado, con `anillos_en_chapa`. Sin geometría o sin contorno, va el rectángulo `x, y, ancho_colocado, alto_colocado`. El nombre corto sale del `id_origen` de la pieza (`pieza_id` es «id#copia»). Lo usado y el sobrante salen de `material_usado_de`.
- **El diseño:** sale de `disenio_del_trabajo`. Cada pieza es `al_disenio` de su contorno y de sus agujeros. El estado es el mismo que `estadosPorPieza`: es «otro» si es de otro grupo o está descartada; «falta» si no tiene colocación; si no, la chapa de su primera copia y cuántas copias tiene.
- **`presupuesto`:** el de `id` mayor con ese `trabajo_id`, como «código · cliente».

- [ ] **Paso 1: Escribir las pruebas que fallan.** Usan el `cliente` y `_trabajo_anidado_con_dos_piezas` de `test_rutas_ajuste.py`, como hace `test_rutas_disenio.py` con los de `test_rutas_nesting.py`.

```python
def test_devuelve_el_pdf_del_trabajo(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    r = cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert re.search(r'filename="Prueba-anidado-\d{4}-\d{2}-\d{2}\.pdf"', r.headers["content-disposition"])
    lector = PdfReader(io.BytesIO(r.content))
    assert len(lector.pages) == 2
    assert "Chapa 1" in lector.pages[1].extract_text()

def test_sin_anidado_terminado_da_409(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "Sin anidar"}).json()
    r = cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado")
    assert r.status_code == 409
    assert mensaje_de(r) == "Este trabajo todavía no tiene ningún anidado terminado: anidalo en la pestaña Anidado."

def test_un_trabajo_que_no_existe_da_404(cliente):
    assert cliente.get("/trabajos/999/pdf-anidado").status_code == 404

def test_lo_movido_a_mano_sale_en_su_lugar_nuevo(cliente, tmp_path):
    trabajo, _g, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    colocacion = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]
    # moverla a un lugar libre (centro 800, 800), como en test_mover_una_pieza_a_un_lugar_libre…
    with Session(cliente.motor) as sesion:
        datos = datos_del_pdf(sesion, sesion.get(Trabajo, trabajo["id"]), datetime(2026, 10, 25))
    # la pieza de esa colocación tiene el centro de su caja en (800, 800)

def test_un_grupo_sin_anidar_va_al_pie(cliente, tmp_path):
    # suma un grupo «G2» sin anidar → el texto trae «Sin anidar» y «G2»

def test_un_nombre_con_acentos_baja_con_nombre_de_archivo_simple(cliente, tmp_path):
    # renombrar el trabajo a «Cartel «Peña» 2» → 200, filename "Cartel-Pena-2-anidado-….pdf", y el texto trae el nombre tal cual

def test_sin_el_dxf_guardado_sale_igual(cliente, tmp_path):
    # borrar el archivo guardado del trabajo y el fondo guardado → 200

def test_una_pieza_sin_contorno_va_como_su_rectangulo():
    posicion = PosicionPieza(pieza_id="5#0", plancha_indice=0, x_mm=Decimal(10), y_mm=Decimal(20),
                             ancho_colocado_mm=Decimal(100), alto_colocado_mm=Decimal(50), rotada_90=False)
    assert anillos_en_chapa(posicion, {}) == [[(10, 20), (110, 20), (110, 70), (10, 70)]]

def test_nombre_de_archivo_pdf():
    assert nombre_de_archivo_pdf("Cartel «Peña» 2", date(2026, 10, 25)) == "Cartel-Pena-2-anidado-2026-10-25.pdf"
    assert nombre_de_archivo_pdf("«»", date(2026, 10, 25)) == "trabajo-anidado-2026-10-25.pdf"
```

Las pruebas con comentario se terminan copiando lo que hacen las de `test_rutas_ajuste.py` y `test_rutas_disenio.py` para mover, renombrar o borrar el archivo.

- [ ] **Paso 2: Correrlas y ver que fallan.** Tienen que fallar con 404 en la ruta y con `ImportError` en las funciones.

- [ ] **Paso 3: Escribir el código.**
  - Sacar `disenio_del_trabajo` y `material_usado_de`.
  - Escribir `rutas_pdf_anidado.py` con las firmas de arriba.
  - Sumar el router en `app.py`.
  - El nombre del archivo pasa por `unicodedata.normalize("NFKD")` y se queda con letras, números y guiones; si queda vacío, «trabajo».
  - La respuesta es `Response(media_type="application/pdf")` con `Content-Disposition: attachment`, como el DXF.

- [ ] **Paso 4: Correr la tarea y todo el backend.**
  - Primero las pruebas nuevas.
  - Después `tests/api/test_rutas_disenio.py` y `tests/api/test_rutas_ajuste.py`, que no tienen que cambiar.
  - Por último el backend entero, con el comando de arriba sin archivo, que tiene que dar todo en verde. Hoy son 876.

- [ ] **Paso 5: Commit**

```bash
git add backend/app/api/rutas_pdf_anidado.py backend/app/api/rutas_disenio.py backend/app/api/rutas_ajuste.py backend/app/api/app.py backend/tests/api/test_rutas_pdf_anidado.py
git commit -m "feat(pdf): el pedido del PDF del diseño anidado (A15, tarea 3)"
```

**Pausa: mostrarle a Enzo el PDF de Complejo bajado de una copia de la base.**

---

### Tarea 4: Los botones, el recorrido y el cierre de los documentos

**Archivos:**
- Modificar: `frontend/src/api/nesting.ts`, para sumar `urlPdfAnidado(trabajoId: number): string`, que da `http://localhost:8000/trabajos/${trabajoId}/pdf-anidado`.
- Prueba: `frontend/src/api/nesting.test.ts`, que es nuevo.
- Modificar: `frontend/src/routes/TrabajoWorkspace/ChapasTab.tsx`. En la fila de las pastillas, a la derecha, va el enlace «Descargar PDF» (`<a href>`, como «Descargar DXF»). **Aclaración al diseño:** aparece cuando el grupo que se está viendo tiene un anidado terminado (`anidadoParaMostrar`). Para no mirar todos los grupos desde la cabecera, el enlace se dibuja dentro de `ChapasDelGrupo` y se lleva a la fila con el mismo diseño.
- Modificar: `frontend/src/components/ResumenAnidado.tsx`. Sumar «Descargar PDF» (`urlPdfAnidado(grupo.trabajo_id)`) después de «Descargar DXF».
- Modificar al cerrar:
  - `docs/plan/A15-disenio-anidado-en-pdf/diseno.md`: estado y §10 «Cómo quedó»;
  - `docs/plan/PLAN-MAESTRO.md` §7: la fila 5 y la tabla de pendientes de A15;
  - `README.md`: «En qué estamos».

- [ ] **Paso 1: Escribir la prueba que falla**

```ts
it("arma el enlace del PDF del trabajo", () => {
  expect(urlPdfAnidado(4)).toBe("http://localhost:8000/trabajos/4/pdf-anidado");
});
```

- [ ] **Paso 2: Correrla y ver que falla.** `npx vitest run src/api/nesting.test.ts` tiene que fallar porque `urlPdfAnidado` no existe.

- [ ] **Paso 3: Escribir `urlPdfAnidado` y poner los dos enlaces.**

- [ ] **Paso 4: Correr la pantalla entera.** `npx vitest run` tiene que dar todo en verde (hoy son 209 más esta) y `npx tsc --noEmit` no tiene que mostrar errores.

- [ ] **Paso 5: El recorrido**, sobre una copia nueva de la base y nunca la real. La copia se arma con `backend/local/herramientas-a14/copiar_base.py a15`. Los guiones y las capturas van en `backend/local/herramientas-a15/`, fuera de git.
  - **Antes de levantar nada, mirar quién escucha en 8000 y 5173.** La pantalla llama al 8000 sí o sí: si Enzo tiene la app levantada, pedirle que la cierre.
  - Volver a anidar Complejo en la copia: hoy no tiene un anidado terminado en la base.
  - Bajar el PDF desde los dos botones, con Chrome sin ventana por CDP (las descargas se habilitan con `Browser.setDownloadBehavior`), o con `curl` si no baja.
  - Pasar cada hoja a imagen con `pypdfium2` y mirarlas.
  - **Imprimir una hoja de chapas al 100 % y medir con regla:** la barra, 25 mm; una chapa de 1220 × 2440, 61 × 122 mm. Eso lo hace Enzo.

- [ ] **Paso 6: Los documentos y el commit**

```bash
git add frontend/src/api/nesting.ts frontend/src/api/nesting.test.ts frontend/src/routes/TrabajoWorkspace/ChapasTab.tsx frontend/src/components/ResumenAnidado.tsx docs/plan/A15-disenio-anidado-en-pdf/diseno.md docs/plan/PLAN-MAESTRO.md README.md
git commit -m "feat(pdf): botones para bajar el PDF del diseño anidado (A15, tarea 4)"
```

**Pausa: Enzo decide si se fusiona en `main` y se sube.**
