# A16 · La página de inicio — plan

> **Para quien ejecuta:** tarea por tarea, con **pausa al final de cada una** para que Enzo la vea antes de seguir. Así trabaja este proyecto, aunque el skill de ejecución diga otra cosa. Los pasos usan casillas (`- [ ]`) para llevar la cuenta.

**Objetivo:** que la primera pantalla del cotizador sirva para un poco de todo. Lleva una barra fija arriba y un inicio en dos columnas, con las tarjetas de los trabajos, los últimos presupuestos y los materiales. Suma también la sección Trabajos, con todas las tarjetas, un buscador y la opción de borrar.

**Cómo:** **el servidor arma cada tarjeta entera** y la pantalla solo la muestra.
- La regla de los pasos es pura, se prueba sin base y vive en `app/pasos.py`.
- `app/api/rutas_inicio.py` junta de la base lo que va en cada tarjeta y el resumen del inicio.
- La miniatura es un SVG hecho en el servidor con el mismo diseño pintado del PDF de A15.
- La pantalla suma la barra, el inicio y la sección Trabajos, y la tarjeta es un componente propio.

**Herramientas:** Python 3.13, FastAPI, SQLAlchemy, React + TypeScript + React Query + Tailwind, vitest. **No se suman dependencias.**

**Diseño:** [`diseno.md`](diseno.md), aprobado por Enzo el 2026-10-26. Este plan se apoya en él: hay que leer los dos. El boceto de las dos columnas (la forma B) está en `.superpowers/brainstorm/246-1792963667/content/inicio-formas.html`, fuera de git.

## Lo que vale para todas las tareas

- **El inicio muestra 6 tarjetas y 5 presupuestos.** La sección Trabajos muestra todas las tarjetas.
- **Qué anidado cuenta en cada grupo:** `_ejecucion_para_costear(grupo)` (`app/costeo.py`), que es el definitivo o, si no hay, el último terminado. Es la misma regla que usan Chapas, el Costeo y el PDF.
- **Una pieza que se corta** es una pieza que no está descartada (`not pieza.descartada`). Una pieza seccionada queda descartada y sus tramos son los que se cortan.
- **Los colores** son los de `app/services/nesting/pdf_anidado.py`: `PALETA_CHAPAS`, `color_de_chapa`, `ROJO_FALTA` y `GRIS_OTRO`. Una prueba ya los compara con la pantalla.
- **Las horas.** La base devuelve las fechas **sin zona**, aunque estén en UTC (`datetime(2026, 10, 26, 14, 17)` cuando en Argentina son las 11:17). Toda fecha que salga en una tarjeta va **marcada como UTC**. La pantalla la muestra en hora de Argentina (`America/Argentina/Buenos_Aires`).
- **Los textos van tal cual los fija el diseño** (§5). Están copiados en las pruebas.
- **Los colores de los pasos, con los de Tailwind** (`tailwind.config.ts`): hecho `cut`, a medias `bronze`, con error `conflict`, pendiente `line`.
- **Commits sin la línea `Co-Authored-By`**, en la rama `feat/pagina-de-inicio`, que sale de `main`.
- **Pruebas con los temporales en D:**, porque C: suele estar lleno. Desde `backend/`:
  `CARTELERIA_DATOS=local/tmp-a16/datos python -m pytest -q --basetemp=local/tmp-a16/pytest <pruebas>`
  Las de la pantalla, desde `frontend/`: `npx vitest run <archivo>` y `npx tsc --noEmit`.
- **Antes de levantar la app, mirar quién escucha en 8000 y 5173.** Si hay algo, es de Enzo y corre contra su base real.

## Lo que más puede fallar sin que ninguna prueba lo mire

Cada uno tiene su prueba en la tarea que lo toca.

1. **La hora de «cuándo se tocó» corrida 3 horas**, porque la base la devuelve sin zona. La tarjeta tiene que decir la hora de Argentina. Pasa lo mismo con el año: el 1 de enero a las 2 de la mañana en UTC, en Argentina todavía es 31 de diciembre. Las pruebas están en las tareas 2 y 5.
2. **La miniatura vieja después de anidar.** El navegador guarda la imagen y, si la dirección no cambia, no la vuelve a pedir. Por eso la dirección lleva cuándo se tocó el trabajo (`?v=`). Las pruebas están en las tareas 3 y 5.
3. **Un trabajo con dos presupuestos.** Al tocar uno en el inicio tiene que abrirse ese mismo en el Costeo, no el primero de la lista. Para eso va `?presupuesto=` en la dirección. La prueba está en la tarea 5.
4. **Un trabajo cuyo DXF ya no está en el disco.** La miniatura sale igual, sin el fondo, en vez de dar un error 500. La prueba está en la tarea 3.
5. **Un presupuesto cuyo trabajo se borró.** Sigue en «Últimos presupuestos», sin enlace al Costeo y con su PDF, y no rompe ninguna tarjeta. La prueba está en la tarea 4.

---

### Tarea 1: Los pasos de la tarjeta

**Archivos:**
- Crear: `backend/app/pasos.py`, puro, sin base, como `app/progreso.py`.
- Prueba: `backend/tests/test_pasos.py`

**Lo que deja para las otras tareas:**

```python
EstadoPaso = Literal["hecho", "a_medias", "error", "pendiente"]
Destino = Literal["piezas", "grupos", "anidado", "chapas", "costeo"]

@dataclass(frozen=True)
class GrupoParaPasos:
    nombre: str
    con_piezas: bool        # tiene alguna pieza que se corta
    terminado: bool         # _ejecucion_para_costear(grupo) no es None
    ultimo: str | None      # EstadoEjecucion.value del anidado más reciente; None si nunca se anidó

@dataclass(frozen=True)
class TrabajoParaPasos:
    piezas_a_cortar: int
    sin_grupo: int          # piezas que se cortan y no tienen grupo
    grupos: list[GrupoParaPasos]   # en el orden de los grupos
    presupuesto: str | None        # el estado del presupuesto más reciente, o None

@dataclass(frozen=True)
class Pasos:
    piezas: EstadoPaso
    grupos: EstadoPaso
    anidado: EstadoPaso
    presupuesto: EstadoPaso
    frase: str
    destino: Destino

def pasos_del_trabajo(trabajo: TrabajoParaPasos) -> Pasos: ...
```

**Las reglas** (diseño §5.4):
- **Piezas:** hecho si `piezas_a_cortar > 0`, y si no, pendiente.
- **Grupos:**
  - pendiente si no hay piezas o si ninguna tiene grupo (`sin_grupo == piezas_a_cortar`);
  - hecho si `sin_grupo == 0`;
  - si no, a medias.
- **Anidado:** solo cuentan los grupos `con_piezas`. Cada grupo queda en uno de cuatro estados, revisados en este orden:
  1. **anidando**, si `ultimo` es `encolada` o `corriendo`, aunque el grupo tenga otro anidado terminado;
  2. **hecho**, si `terminado`;
  3. **error**, si `ultimo == "error"`;
  4. **falta**, en cualquier otro caso: sin anidar o con el último anidado cancelado.

  El paso queda así:
  - **hecho**, si todos los grupos están hechos y hay al menos uno;
  - **error**, si alguno dio error;
  - **a medias**, si alguno está hecho o anidando;
  - **pendiente**, en cualquier otro caso.
- **Presupuesto:** hecho si `presupuesto is not None`, y si no, pendiente.
- **La frase y el destino** salen del primer paso que no está hecho.
  - **Piezas:** «Falta cargar el dibujo» y lleva a `piezas`.
  - **Grupos:** «Falta armar los grupos» si el paso está pendiente; si está a medias, «Falta 1 pieza sin grupo» o «Faltan N piezas sin grupo». Lleva a `grupos`.
  - **Anidado:** la frase es la del primer grupo, en el orden de los grupos, que no esté hecho:
    - «Anidando {nombre}…», con «…» en un solo carácter;
    - «El anidado de {nombre} terminó con error»;
    - «Falta anidar {nombre}».

    Lleva a `anidado`.
  - **Presupuesto:** «Falta el presupuesto» y lleva a `chapas`.
  - **Con todo hecho:** «Presupuesto en borrador» para `BORRADOR`. Para cualquier otro estado, «Presupuesto: {estado en minúscula}». Lleva a `costeo`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def _grupo(nombre="Calibre 18", *, con_piezas=True, terminado=False, ultimo=None):
    return GrupoParaPasos(nombre, con_piezas, terminado, ultimo)

def _trabajo(*, piezas=2, sin_grupo=0, grupos=(), presupuesto=None):
    return TrabajoParaPasos(piezas, sin_grupo, list(grupos), presupuesto)

def test_sin_piezas_falta_el_dibujo():
    assert pasos_del_trabajo(_trabajo(piezas=0)) == Pasos(
        "pendiente", "pendiente", "pendiente", "pendiente", "Falta cargar el dibujo", "piezas")

def test_sin_grupos_faltan_los_grupos():
    p = pasos_del_trabajo(_trabajo(sin_grupo=2))
    assert (p.piezas, p.grupos, p.frase, p.destino) == ("hecho", "pendiente", "Falta armar los grupos", "grupos")

def test_con_piezas_sin_grupo_las_cuenta():
    p = pasos_del_trabajo(_trabajo(piezas=5, sin_grupo=3, grupos=[_grupo(terminado=True, ultimo="lista")]))
    assert (p.grupos, p.anidado, p.frase) == ("a_medias", "hecho", "Faltan 3 piezas sin grupo")

def test_una_sola_pieza_sin_grupo_va_en_singular():
    assert pasos_del_trabajo(_trabajo(sin_grupo=1, grupos=[_grupo()])).frase == "Falta 1 pieza sin grupo"

def test_sin_anidar():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo()]))
    assert (p.anidado, p.frase, p.destino) == ("pendiente", "Falta anidar Calibre 18", "anidado")

@pytest.mark.parametrize("estado", ["encolada", "corriendo"])
def test_un_anidado_corriendo(estado):
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(ultimo=estado)]))
    assert (p.anidado, p.frase) == ("a_medias", "Anidando Calibre 18…")

def test_anidando_otra_vez_aunque_haya_uno_terminado():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(terminado=True, ultimo="corriendo")]))
    assert (p.anidado, p.frase) == ("a_medias", "Anidando Calibre 18…")

def test_un_anidado_con_error():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo("Chapa20", ultimo="error")]))
    assert (p.anidado, p.frase) == ("error", "El anidado de Chapa20 terminó con error")

def test_un_error_despues_de_uno_terminado_no_cuenta():
    assert pasos_del_trabajo(_trabajo(grupos=[_grupo(terminado=True, ultimo="error")])).anidado == "hecho"

def test_dos_grupos_con_uno_solo_anidado_nombra_el_que_falta():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo("A", terminado=True, ultimo="lista"), _grupo("B")]))
    assert (p.anidado, p.frase) == ("a_medias", "Falta anidar B")

def test_un_anidado_cancelado_cuenta_como_sin_anidar():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(ultimo="cancelada")]))
    assert (p.anidado, p.frase) == ("pendiente", "Falta anidar Calibre 18")

def test_un_grupo_vacio_no_cuenta():
    grupos = [_grupo("A", terminado=True, ultimo="lista"), _grupo("Vacío", con_piezas=False)]
    assert pasos_del_trabajo(_trabajo(grupos=grupos)).anidado == "hecho"

def test_anidado_sin_presupuesto_lleva_a_chapas():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(terminado=True, ultimo="lista")]))
    assert (p.presupuesto, p.frase, p.destino) == ("pendiente", "Falta el presupuesto", "chapas")

def test_con_presupuesto_dice_su_estado_y_lleva_al_costeo():
    p = pasos_del_trabajo(_trabajo(grupos=[_grupo(terminado=True, ultimo="lista")], presupuesto="BORRADOR"))
    assert p == Pasos("hecho", "hecho", "hecho", "hecho", "Presupuesto en borrador", "costeo")
```

- [ ] **Paso 2: Correrlas y ver que fallan.** `python -m pytest -q tests/test_pasos.py` (con los temporales en D:) tiene que fallar porque `app.pasos` no existe.

- [ ] **Paso 3: Escribir `app/pasos.py`** con lo de arriba y las reglas.

- [ ] **Paso 4: Correrlas y ver que pasan.**

- [ ] **Paso 5: Commit**

```bash
git add backend/app/pasos.py backend/tests/test_pasos.py
git commit -m "feat(inicio): los pasos de la tarjeta de un trabajo (A16, tarea 1)"
```

**Pausa: Enzo mira las reglas y las frases.**

---

### Tarea 2: Las tarjetas

**Archivos:**
- Crear: `backend/app/api/esquemas_inicio.py`
- Crear: `backend/app/api/rutas_inicio.py`, con `router = APIRouter(tags=["inicio"])`.
- Modificar: `backend/app/api/app.py`, para sumar `app.include_router(router_inicio)`.
- Prueba: `backend/tests/api/test_rutas_inicio.py`. Usa `cliente` y `_trabajo_anidado_con_dos_piezas` de `test_rutas_ajuste.py`, como `test_rutas_pdf_anidado.py`.

**La ruta es `GET /tarjetas`, no `/trabajos/tarjetas`.** El router de trabajos va antes y su `/trabajos/{trabajo_id}` se quedaría con «tarjetas»: respondería 422 porque no es un número.

**Usa:** `pasos_del_trabajo`, `TrabajoParaPasos` y `GrupoParaPasos` (tarea 1); `_ejecucion_para_costear` (`app/costeo.py`); `_material(sesion, grupo, ejecucion)` (`rutas_pdf_anidado.py`); `calcular` y `_lineas_del_presupuesto` (`rutas_presupuesto.py`), con los que se saca el total igual que en `GET /presupuestos/{id}/totales`.

**Lo que deja para las otras tareas:**

```python
# esquemas_inicio.py
class PresupuestoResumidoLeer(BaseModel):
    id: int
    codigo: str
    cliente: str
    trabajo_id: int | None
    trabajo: str | None        # el nombre del trabajo
    total: Decimal | None      # el `total` de la cuenta; None si todavía no se puede calcular
    moneda: str
    estado: str

class PasosLeer(BaseModel):
    piezas: EstadoPaso
    grupos: EstadoPaso
    anidado: EstadoPaso
    presupuesto: EstadoPaso

class TarjetaLeer(BaseModel):
    id: int
    nombre: str
    tocado_en: datetime        # con zona, en UTC
    pasos: PasosLeer
    frase: str
    destino: Destino
    chapas: list[str]          # un renglón por grupo con anidado que cuenta: «7 chapas · CHAPA NEGRA cal. 22»
    presupuesto: PresupuestoResumidoLeer | None   # el más reciente del trabajo

# rutas_inicio.py
def en_utc(fecha: datetime) -> datetime: ...          # sin zona → la marca UTC; con zona → la pasa a UTC
def tocado_por_trabajo(sesion: Session) -> dict[int, datetime]: ...
def presupuesto_resumido(sesion: Session, presupuesto: Presupuesto) -> PresupuestoResumidoLeer: ...
def tarjeta_de(sesion: Session, trabajo: Trabajo, tocado_en: datetime) -> TarjetaLeer: ...

@router.get("/tarjetas", response_model=list[TarjetaLeer])
def listar_tarjetas(limite: int | None = None, sesion: Session = Depends(obtener_sesion)) -> list[TarjetaLeer]: ...
```

- **`tocado_por_trabajo`:** la fecha más reciente de `actualizado_en` entre el trabajo, sus piezas, sus grupos, sus anidados, sus colocaciones, sus presupuestos y las líneas de esos presupuestos. Se hace **una consulta por tabla**, con `func.max` agrupado por trabajo. No se cargan las colocaciones: Complejo tiene cientos. El resultado pasa por `en_utc`.
- **Las chapas:** «1 chapa · …», «7 chapas · …».
- **El orden:** de la tocada más recientemente a la menos; si empatan, la de `id` mayor primero. Después se corta en `limite`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_las_tarjetas_van_de_la_mas_tocada_a_la_menos_y_respetan_el_limite(cliente):
    a, b, c = (cliente.post("/trabajos", json={"nombre": n}).json() for n in "ABC")
    cliente.post(f"/trabajos/{a['id']}/grupos", json={"nombre": "G"})
    assert [t["nombre"] for t in cliente.get("/tarjetas").json()] == ["A", "C", "B"]
    assert [t["nombre"] for t in cliente.get("/tarjetas?limite=2").json()] == ["A", "C"]

def test_la_hora_va_marcada_como_utc(cliente):
    cliente.post("/trabajos", json={"nombre": "A"})
    tocado = datetime.fromisoformat(cliente.get("/tarjetas").json()[0]["tocado_en"])
    assert tocado.utcoffset() == timedelta(0)

def test_cuando_se_toco_cambia_al_mover_una_pieza_en_chapas(cliente, tmp_path):
    trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    antes = datetime.fromisoformat(cliente.get("/tarjetas").json()[0]["tocado_en"])
    fila_antes = cliente.get(f"/trabajos/{trabajo['id']}").json()["actualizado_en"]
    colocacion = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]
    cliente.patch(f"/colocaciones/{colocacion['id']}", json={"centro_x_mm": "900", "centro_y_mm": "900"})
    assert datetime.fromisoformat(cliente.get("/tarjetas").json()[0]["tocado_en"]) > antes
    assert cliente.get(f"/trabajos/{trabajo['id']}").json()["actualizado_en"] == fila_antes

def test_la_tarjeta_de_un_trabajo_anidado_sin_presupuesto(cliente, tmp_path):
    _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    tarjeta = cliente.get("/tarjetas").json()[0]
    assert tarjeta["pasos"] == {"piezas": "hecho", "grupos": "hecho", "anidado": "hecho", "presupuesto": "pendiente"}
    assert (tarjeta["frase"], tarjeta["destino"]) == ("Falta el presupuesto", "chapas")
    assert tarjeta["chapas"] == ["1 chapa · Chapa"]
    assert tarjeta["presupuesto"] is None

def test_la_tarjeta_trae_el_presupuesto_mas_reciente(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    duenio = cliente.post("/clientes", json={"nombre": "Parador"}).json()
    for _ in range(2):
        ultimo = cliente.post("/presupuestos", json={"cliente_id": duenio["id"], "trabajo_id": trabajo["id"], "validez_dias": 15}).json()
    tarjeta = cliente.get("/tarjetas").json()[0]
    total = cliente.get(f"/presupuestos/{ultimo['id']}/totales").json()["total"]
    assert tarjeta["presupuesto"] == {"id": ultimo["id"], "codigo": ultimo["codigo"], "cliente": "Parador",
        "trabajo_id": trabajo["id"], "trabajo": "Prueba", "total": total, "moneda": "ARS", "estado": "BORRADOR"}
    assert (tarjeta["frase"], tarjeta["destino"]) == ("Presupuesto en borrador", "costeo")

def test_cuando_se_toco_cambia_al_crear_el_presupuesto(cliente, tmp_path): ...
    # igual que la de mover: tocado_en crece y el actualizado_en del trabajo no cambia

def test_un_trabajo_sin_piezas(cliente):
    cliente.post("/trabajos", json={"nombre": "Vacío"})
    tarjeta = cliente.get("/tarjetas").json()[0]
    assert (tarjeta["frase"], tarjeta["chapas"], tarjeta["presupuesto"]) == ("Falta cargar el dibujo", [], None)
```

Antes de comparar, la prueba del presupuesto revisa con qué campos pide `POST /presupuestos` el alta, en `PresupuestoCrear`.

- [ ] **Paso 2: Correrlas y ver que fallan.** Tienen que dar 404, porque `/tarjetas` todavía no existe.

- [ ] **Paso 3: Escribir los esquemas, las funciones y la ruta**, y sumar el router en `app.py`.

- [ ] **Paso 4: Correr estas pruebas y las de `test_rutas_trabajos.py`.**

- [ ] **Paso 5: Commit**

```bash
git add backend/app/api/esquemas_inicio.py backend/app/api/rutas_inicio.py backend/app/api/app.py backend/tests/api/test_rutas_inicio.py
git commit -m "feat(inicio): las tarjetas de los trabajos, armadas en el servidor (A16, tarea 2)"
```

**Pausa.**

---

### Tarea 3: La miniatura

**Archivos:**
- Crear: `backend/app/services/nesting/miniatura_svg.py`
- Prueba: `backend/tests/services/nesting/test_miniatura_svg.py`
- Modificar: `backend/app/api/rutas_pdf_anidado.py`. `_disenio` pasa a aceptar que no haya grupo ni anidado.
- Modificar: `backend/app/api/rutas_inicio.py`, para sumar la ruta.
- Prueba: `backend/tests/api/test_rutas_inicio.py`

**Lo que deja para las otras tareas:**

```python
# miniatura_svg.py
ANCHO_PX = 320
ALTO_PX = 200
MARGEN_PX = 8
def svg_de_miniatura(disenio: DisenioDelPdf) -> str: ...

# rutas_pdf_anidado.py: la firma se amplía y el PDF la sigue llamando igual
def _disenio(sesion: Session, trabajo: Trabajo, grupo: GrupoDeCorte | None, ejecucion: EjecucionNesting | None) -> DisenioDelPdf: ...

# rutas_inicio.py
def disenio_de_miniatura(sesion: Session, trabajo: Trabajo) -> DisenioDelPdf: ...

@router.get("/trabajos/{trabajo_id}/miniatura")
def obtener_miniatura(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> Response: ...  # image/svg+xml
```

- **`_disenio` con `grupo=None`:** toda pieza va como `"otro"`, en gris.
- **`disenio_de_miniatura`:** pinta el primer grupo, en el orden de los grupos, que tenga un anidado que cuente. Si ninguno tiene, usa `_disenio(sesion, trabajo, None, None)`.
- **El SVG:**
  - `viewBox="0 0 320 200"`, con `width` y `height` iguales;
  - el diseño, entero y sin deformar, centrado dentro del margen;
  - con la `y` dada vuelta: en el dibujo crece hacia arriba y en el SVG, hacia abajo;
  - cada pieza es un `<path>` con `fill-rule="evenodd"`, para que los agujeros queden huecos:
    - relleno: `color_de_chapa(chapa)`, `ROJO_FALTA` o `GRIS_OTRO`;
    - borde: `#333333`, o `ROJO_FALTA` punteado si la pieza falta;
  - el fondo, solo con borde `#bbbbbb`;
  - los cortes del seccionado, como líneas negras;
  - los números, redondeados a una décima.
  - **Sin el «×N» de las copias:** a ese tamaño no se lee *(decisión mía)*.
  - **Sin nada que dibujar:** un recuadro con «Sin dibujo» centrado.
- **La ruta no mira `?v=`.** La pantalla lo agrega para que el navegador no muestre una miniatura vieja.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
# test_miniatura_svg.py
CUADRADO = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]]
ARRIBA = [[(0.0, 90.0), (10.0, 90.0), (10.0, 100.0), (0.0, 100.0)]]

def test_es_un_svg_valido_del_tamanio_fijo():
    raiz = ElementTree.fromstring(svg_de_miniatura(DisenioDelPdf([], [PiezaDelDisenio("1", CUADRADO, "otro")], [], [])))
    assert raiz.get("viewBox") == "0 0 320 200"

def test_pinta_cada_pieza_segun_su_estado():
    piezas = [PiezaDelDisenio("1", CUADRADO, "en_chapa", chapa=0), PiezaDelDisenio("2", ARRIBA, "en_chapa", chapa=1),
              PiezaDelDisenio("3", CUADRADO, "falta"), PiezaDelDisenio("4", ARRIBA, "otro")]
    svg = svg_de_miniatura(DisenioDelPdf([], piezas, [], []))
    for color in (PALETA_CHAPAS[0], PALETA_CHAPAS[1], ROJO_FALTA, GRIS_OTRO):
        assert color in svg

def test_lo_de_abajo_en_el_dibujo_queda_abajo_en_el_svg():
    # el cuadrado de y=0..10 tiene que quedar con y de pantalla mayores que el de y=90..100
    ...

def test_los_agujeros_quedan_huecos():
    con_agujero = [CUADRADO[0], [(2.0, 2.0), (8.0, 2.0), (8.0, 8.0), (2.0, 8.0)]]
    assert 'fill-rule="evenodd"' in svg_de_miniatura(DisenioDelPdf([], [PiezaDelDisenio("1", con_agujero, "otro")], [], []))

def test_sin_nada_dice_sin_dibujo():
    svg = svg_de_miniatura(DisenioDelPdf([], [], [], []))
    ElementTree.fromstring(svg)
    assert "Sin dibujo" in svg

# test_rutas_inicio.py
def test_la_miniatura_pinta_las_chapas(cliente, tmp_path):
    trabajo, _, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    r = cliente.get(f"/trabajos/{trabajo['id']}/miniatura?v=2026-10-26T14:17:00Z")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert PALETA_CHAPAS[0] in r.text

def test_sin_anidado_la_miniatura_va_en_gris(cliente, tmp_path): ...
    # trabajo con DXF y sin grupos: GRIS_OTRO aparece y PALETA_CHAPAS[0] no

def test_sin_el_dxf_guardado_la_miniatura_sale_igual(cliente, tmp_path): ...
    # borrar del disco Path(trabajo.archivo_guardado) y _ruta_del_fondo(trabajo): sigue dando 200

def test_la_miniatura_de_un_trabajo_que_no_existe_da_404(cliente):
    assert cliente.get("/trabajos/999/miniatura").status_code == 404
```

- [ ] **Paso 2: Correrlas y ver que fallan.**

- [ ] **Paso 3: Escribir `svg_de_miniatura`, ampliar `_disenio` y sumar la ruta.**

- [ ] **Paso 4: Correr estas pruebas y las de `test_rutas_pdf_anidado.py` y `test_pdf_anidado.py`**, para comprobar que el PDF sigue igual.

- [ ] **Paso 5: Commit**

```bash
git add backend/app/services/nesting/miniatura_svg.py backend/tests/services/nesting/test_miniatura_svg.py backend/app/api/rutas_pdf_anidado.py backend/app/api/rutas_inicio.py backend/tests/api/test_rutas_inicio.py
git commit -m "feat(inicio): la miniatura del diseño pintado, como SVG del servidor (A16, tarea 3)"
```

**Pausa: Enzo puede abrir la miniatura de cada trabajo en el navegador** (sobre la copia de la base, ver la tarea 7).

---

### Tarea 4: El resumen del inicio y el freno al borrar

**Archivos:**
- Modificar: `backend/app/api/esquemas_inicio.py` y `backend/app/api/rutas_inicio.py`
- Modificar: `backend/app/api/rutas_trabajos.py`, en `eliminar_trabajo`.
- Modificar: `backend/app/api/anidado_en_curso.py`. Su descripción suma que también lo usa borrar el trabajo.
- Prueba: `backend/tests/api/test_rutas_inicio.py` y `backend/tests/api/test_rutas_trabajos.py`

**Lo que deja para las otras tareas:**

```python
ULTIMOS_PRESUPUESTOS = 5

class FamiliaLeer(BaseModel):
    familia: str
    materiales: int

class MaterialesResumidosLeer(BaseModel):
    materiales: int
    medidas: int          # formatos que no son retazo
    retazos: int
    por_familia: list[FamiliaLeer]   # por nombre de familia

class ResumenDelInicioLeer(BaseModel):
    presupuestos: list[PresupuestoResumidoLeer]   # los 5 más recientes, por id de mayor a menor
    total_presupuestos: int
    materiales: MaterialesResumidosLeer

@router.get("/resumen-del-inicio", response_model=ResumenDelInicioLeer)
def obtener_resumen_del_inicio(sesion: Session = Depends(obtener_sesion)) -> ResumenDelInicioLeer: ...
```

- **El freno:** `eliminar_trabajo` llama a `rechazar_si_hay_anidado_en_curso(sesion, GrupoDeCorte.trabajo_id == trabajo_id, "borrar el trabajo")` antes de tocar nada. El mensaje sale del que ya existe: «Hay un anidado en curso en el grupo «X» (#N): esperá a que termine, o cancelalo en la pestaña Anidado, antes de borrar el trabajo.» *(Aclaración al diseño: §5.5 lo escribía un poco distinto; se usa el que ya ven cargar el dibujo y seccionar.)*

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
def test_el_resumen_trae_los_5_presupuestos_mas_recientes(cliente):
    # 6 presupuestos de un cliente y un trabajo
    resumen = cliente.get("/resumen-del-inicio").json()
    assert [p["id"] for p in resumen["presupuestos"]] == ids[::-1][:5]
    assert resumen["total_presupuestos"] == 6

def test_un_presupuesto_de_un_trabajo_borrado_queda_sin_trabajo(cliente):
    # crear trabajo + presupuesto, borrar el trabajo
    fila = cliente.get("/resumen-del-inicio").json()["presupuestos"][0]
    assert (fila["trabajo_id"], fila["trabajo"]) == (None, None)
    assert cliente.get("/tarjetas").json() == []

def test_los_conteos_de_materiales(cliente):
    # «Chapa negra» familia «Chapas» con una medida y un retazo; «Acrílico» familia «Acrílicos» con una medida
    assert cliente.get("/resumen-del-inicio").json()["materiales"] == {
        "materiales": 2, "medidas": 2, "retazos": 1,
        "por_familia": [{"familia": "Acrílicos", "materiales": 1}, {"familia": "Chapas", "materiales": 1}]}

def test_el_resumen_sin_nada(cliente):
    assert cliente.get("/resumen-del-inicio").json() == {
        "presupuestos": [], "total_presupuestos": 0,
        "materiales": {"materiales": 0, "medidas": 0, "retazos": 0, "por_familia": []}}

# test_rutas_trabajos.py, armado como test_mientras_corre_un_anidado_del_trabajo_no_se_vuelve_a_cargar
@pytest.mark.parametrize("estado", ["encolada", "corriendo"])
def test_mientras_corre_un_anidado_no_se_borra_el_trabajo(cliente, tmp_path, estado):
    respuesta = cliente.delete(f"/trabajos/{trabajo['id']}")
    assert respuesta.status_code == 409
    assert mensaje_de(respuesta).endswith("antes de borrar el trabajo.")
    assert cliente.get(f"/trabajos/{trabajo['id']}").status_code == 200
    assert Path(archivo_guardado).exists()

@pytest.mark.parametrize("estado", ["lista", "error", "cancelada"])
def test_un_anidado_terminado_no_impide_borrar_el_trabajo(cliente, tmp_path, estado): ...
    # el DELETE da 204
```

- [ ] **Paso 2: Correrlas y ver que fallan.**

- [ ] **Paso 3: Escribir el resumen y poner el freno.**

- [ ] **Paso 4: Correr el servidor entero.** `python -m pytest -q` (con los temporales en D:) tiene que dar todo en verde: hoy son 903, más las nuevas.

- [ ] **Paso 5: Commit**

```bash
git add backend/app/api/esquemas_inicio.py backend/app/api/rutas_inicio.py backend/app/api/rutas_trabajos.py backend/app/api/anidado_en_curso.py backend/tests/api/test_rutas_inicio.py backend/tests/api/test_rutas_trabajos.py
git commit -m "feat(inicio): el resumen del inicio y no borrar un trabajo que se está anidando (A16, tarea 4)"
```

**Pausa: termina el tramo del servidor.**

---

### Tarea 5: La barra y el inicio

**Archivos:**
- Crear: `frontend/src/api/inicio.ts`
- Crear: `frontend/src/hooks/useInicio.ts`
- Crear: `frontend/src/components/Tarjeta/formato.ts`
- Prueba: `frontend/src/components/Tarjeta/formato.test.ts`
- Prueba: `frontend/src/api/inicio.test.ts`
- Crear: `frontend/src/components/Tarjeta/TarjetaTrabajo.tsx` y `frontend/src/components/Tarjeta/NuevoTrabajo.tsx`. El formulario de `TrabajosLista` pasa a `NuevoTrabajo`, con el botón «Crear y cargar el DXF».
- Crear: `frontend/src/components/Barra.tsx` y `frontend/src/routes/ConBarra.tsx`. `ConBarra` es la ruta que envuelve a todas: `<Barra />` y `<Outlet />`.
- Crear: `frontend/src/routes/Inicio.tsx`
- Crear: `frontend/src/components/bajarArchivo.ts`. Ahí se mueve `bajarArchivo` de `PresupuestoClienteSeccion.tsx`, que pasa a importarlo.
- Modificar: `frontend/src/App.tsx`.
  - `/` pasa a ser `Inicio`.
  - `/trabajos` muestra por ahora `TrabajosLista`, hasta la tarea 6.
  - Todas las rutas van dentro de `ConBarra`.
- Modificar: `frontend/src/routes/TrabajoWorkspace/WorkspaceLayout.tsx`. El alto deja lugar a la barra, que mide 3rem: `min-h-[calc(100vh-3rem)]`.
- Modificar: `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx`. `presupuestoActivoId` arranca con `?presupuesto=` si viene en la dirección (`useSearchParams`).

**Lo que deja para la tarea 6:**

```ts
// api/inicio.ts: los mismos campos que los esquemas de la tarea 2 y 4; Decimal y datetime viajan como string
export type EstadoPaso = "hecho" | "a_medias" | "error" | "pendiente";
export type Destino = "piezas" | "grupos" | "anidado" | "chapas" | "costeo";
export interface PresupuestoResumido { id: number; codigo: string; cliente: string; trabajo_id: number | null; trabajo: string | null; total: string | null; moneda: string; estado: string }
export interface Tarjeta { id: number; nombre: string; tocado_en: string; pasos: Record<"piezas" | "grupos" | "anidado" | "presupuesto", EstadoPaso>; frase: string; destino: Destino; chapas: string[]; presupuesto: PresupuestoResumido | null }
export interface ResumenDelInicio { presupuestos: PresupuestoResumido[]; total_presupuestos: number; materiales: { materiales: number; medidas: number; retazos: number; por_familia: { familia: string; materiales: number }[] } }
export function listarTarjetas(limite?: number): Promise<Tarjeta[]>;
export function obtenerResumenDelInicio(): Promise<ResumenDelInicio>;
export function urlMiniatura(trabajoId: number, tocadoEn: string): string;   // …/trabajos/{id}/miniatura?v={tocadoEn codificado}

// hooks/useInicio.ts: las dos con refetchOnWindowFocus: true (en main.tsx está apagado para todo lo demás)
export function useTarjetas(limite?: number);        // queryKey ["tarjetas", limite ?? "todas"]
export function useResumenDelInicio();               // queryKey ["resumen-del-inicio"]

// components/Tarjeta/formato.ts
export function fechaDeTarjeta(iso: string, ahora: Date): string;          // «24/10 16:14»; con el año si no es el actual
export function renglonesDeChapas(chapas: string[]): string[];             // hasta 2 y «y N más»; sin chapas, «Sin chapas»
export function textoDelPresupuesto(p: PresupuestoResumido): string;      // «P-2026-0001 · Parador · $ 300.000,00 · borrador»
export function rutaDelDestino(trabajoId: number, destino: Destino): string;
export function rutaDelPresupuesto(p: PresupuestoResumido): string | null; // al Costeo con ?presupuesto=; null sin trabajo

// components/Tarjeta/TarjetaTrabajo.tsx
export default function TarjetaTrabajo(props: { tarjeta: Tarjeta; ahora: Date }): JSX.Element;
```

- **`fechaDeTarjeta`** usa `Intl.DateTimeFormat("es-AR", { timeZone: "America/Argentina/Buenos_Aires", … })`, y compara el año también en esa zona.
- **`textoDelPresupuesto`** pasa el total por `mostrarImporte` (`TrabajoWorkspace/importes.ts`), igual que el Costeo. Si el total es `null`, lo deja afuera: «P-2026-0001 · Parador · borrador».
- **La barra:**
  - «Cotizador» a la izquierda;
  - los lugares, con `NavLink` y el de donde se está marcado:
    - Inicio, a `/`, marcado solo con `end`;
    - Trabajos, a `/trabajos`, marcado también dentro de un trabajo;
  - Presupuestos y Materiales, como `<span>` apagados con `title="Próximamente"`;
  - fija arriba (`sticky top-0`), de 3rem de alto.
- **El inicio:**
  - dos columnas, con la izquierda en unos dos tercios: las tarjetas `useTarjetas(6)` de a dos;
  - debajo, «Ver todos los trabajos», solo si hay más de 6 trabajos. Para saberlo se pide `useTarjetas(7)` y se muestran las 6 primeras;
  - a la derecha, tres recuadros:
    - `NuevoTrabajo`;
    - «Últimos presupuestos»: cada renglón, con `rutaDelPresupuesto`, y un botón «PDF» que usa `descargarPdf` y `bajarArchivo`. Si da error, lo muestra con `Mensaje`. Abajo, «{total} presupuestos en total»;
    - «Materiales»: «{materiales} materiales · {medidas} medidas de chapa · {retazos} retazos» y un renglón por familia.
  - **Lo que se ve cuando no hay nada**, con las frases del diseño §5.2.
- **La tarjeta:**
  - es entera un `Link` a `rutaDelDestino`;
  - arriba, `<img src={urlMiniatura(...)} alt="">`, a todo el ancho, con proporción 16:10;
  - el nombre y `fechaDeTarjeta`;
  - la barra de los cuatro pasos, con el nombre chiquito debajo de cada tramo y la frase abajo;
  - `renglonesDeChapas`;
  - `textoDelPresupuesto`, o «Sin presupuesto» en gris.
- **El «⋯» para borrar va en la tarea 6.**

- [ ] **Paso 1: Escribir las pruebas que fallan**

```ts
// formato.test.ts
const AHORA = new Date("2026-10-26T12:00:00Z");
it("la fecha va en hora de Argentina y sin el año actual", () => {
  expect(fechaDeTarjeta("2026-10-24T19:14:00Z", AHORA)).toBe("24/10 16:14");
});
it("con el año si es de otro", () => {
  expect(fechaDeTarjeta("2025-12-31T20:30:00Z", AHORA)).toBe("31/12/2025 17:30");
});
it("el año se mira en Argentina: el 1/1 a las 2 en UTC todavía es 31/12", () => {
  expect(fechaDeTarjeta("2026-01-01T02:00:00Z", AHORA)).toBe("31/12/2025 23:00");
});
it("hasta dos renglones de chapas y cuántos más", () => {
  expect(renglonesDeChapas(["a", "b", "c", "d"])).toEqual(["a", "b", "y 2 más"]);
  expect(renglonesDeChapas(["a", "b"])).toEqual(["a", "b"]);
  expect(renglonesDeChapas([])).toEqual(["Sin chapas"]);
});
it("el presupuesto en un renglón", () => {
  const p = { id: 3, codigo: "P-2026-0001", cliente: "Parador", trabajo_id: 4, trabajo: "parador", total: "300000.00", moneda: "ARS", estado: "BORRADOR" };
  expect(textoDelPresupuesto(p)).toBe("P-2026-0001 · Parador · $ 300.000,00 · borrador");
  expect(textoDelPresupuesto({ ...p, total: null })).toBe("P-2026-0001 · Parador · borrador");
  expect(rutaDelPresupuesto(p)).toBe("/trabajos/4/costeo?presupuesto=3");
  expect(rutaDelPresupuesto({ ...p, trabajo_id: null })).toBeNull();
});
it("a dónde lleva la tarjeta", () => {
  expect(rutaDelDestino(4, "chapas")).toBe("/trabajos/4/chapas");
});

// inicio.test.ts
it("la miniatura cambia de dirección cuando se toca el trabajo", () => {
  expect(urlMiniatura(4, "2026-10-24T19:14:00Z")).toBe("http://localhost:8000/trabajos/4/miniatura?v=2026-10-24T19%3A14%3A00Z");
});
```

Antes de fijar el texto del importe, hay que comprobar qué devuelve `mostrarImporte("300000.00", "ARS")`. Si da otra cosa, la prueba sigue a `mostrarImporte`.

- [ ] **Paso 2: Correrlas y ver que fallan.** `npx vitest run src/components/Tarjeta/formato.test.ts src/api/inicio.test.ts`

- [ ] **Paso 3: Escribir la API, los hooks y `formato.ts`.**

- [ ] **Paso 4: Escribir la barra, la tarjeta, el inicio y los cambios en `App.tsx`, `WorkspaceLayout.tsx` y `CosteoTab.tsx`.**

- [ ] **Paso 5: Correr la pantalla entera.** `npx vitest run` tiene que dar todo en verde (hoy son 210, más las nuevas) y `npx tsc --noEmit`, sin errores.

- [ ] **Paso 6: Mirarlo en pantalla** con Chrome sin ventana sobre la copia de la base (tarea 7, paso 2). Capturas:
  - el inicio;
  - el inicio dentro de un trabajo, con la barra arriba y el menú de pasos al costado;
  - un trabajo con dos presupuestos, para ver que abre el que se tocó.

- [ ] **Paso 7: Commit**

```bash
git add frontend/src
git commit -m "feat(inicio): la barra fija y la página de inicio con las tarjetas (A16, tarea 5)"
```

**Pausa: Enzo lo prueba en pantalla.**

---

### Tarea 6: La sección Trabajos y borrar

**Archivos:**
- Crear: `frontend/src/routes/Trabajos.tsx`
- Crear: `frontend/src/components/Tarjeta/ConfirmarBorrado.tsx`
- Modificar:
  - `frontend/src/components/Tarjeta/formato.ts` y su prueba;
  - `frontend/src/api/inicio.ts`;
  - `frontend/src/hooks/useInicio.ts`;
  - `frontend/src/components/Tarjeta/TarjetaTrabajo.tsx`.
- Modificar: `frontend/src/App.tsx`. `/trabajos` pasa a ser `Trabajos`.
- Borrar:
  - `frontend/src/routes/TrabajosLista.tsx`;
  - `useTrabajos` y `listarTrabajos`, si quedan sin uso.

**Usa:** `Tarjeta`, `useTarjetas`, `TarjetaTrabajo` y `NuevoTrabajo` (tarea 5); `Mensaje` (`components/Mensaje`).

```ts
// formato.ts
export function coincideConLaBusqueda(nombre: string, busqueda: string): boolean;  // sin acentos ni mayúsculas; vacía, todo
export function textoDeBorrado(tarjeta: Tarjeta): string[];                         // los renglones de la confirmación

// api/inicio.ts y hooks/useInicio.ts
export function borrarTrabajo(trabajoId: number): Promise<void>;   // apiDelete(`/trabajos/${id}`)
export function useBorrarTrabajo();   // al terminar, invalida ["tarjetas"], ["resumen-del-inicio"], ["trabajos"] y ["presupuestos"]
```

- **La sección Trabajos:**
  - arriba, el título «Trabajos» y el buscador, que filtra mientras se escribe;
  - después, las tarjetas de a tres, con `NuevoTrabajo` como primera tarjeta;
  - si la búsqueda no encuentra nada, «Ningún trabajo se llama así».
- **El «⋯»:** va arriba a la derecha de la tarjeta y abre un menú con «Borrar trabajo». El clic no tiene que seguir el enlace de la tarjeta (`preventDefault` y `stopPropagation`).
- **La confirmación:**
  - es un cuadro sobre la página, no `window.confirm`;
  - muestra `textoDeBorrado`, con «Cancelar» y «Borrar»;
  - mientras borra, el botón dice «Borrando…»;
  - si el servidor responde 409, el mensaje se muestra con `Mensaje variante="error"` dentro del cuadro, y el cuadro queda abierto.
- **El menú también va en las tarjetas del inicio** (diseño §5.5, punto 4).

- [ ] **Paso 1: Escribir las pruebas que fallan**

```ts
it("busca sin acentos ni mayúsculas", () => {
  expect(coincideConLaBusqueda("Cartel Peña", "pena")).toBe(true);
  expect(coincideConLaBusqueda("Parador", "PARA")).toBe(true);
  expect(coincideConLaBusqueda("Complejo", "x")).toBe(false);
  expect(coincideConLaBusqueda("Complejo", "  ")).toBe(true);
});
it("la confirmación nombra el trabajo y su presupuesto", () => {
  expect(textoDeBorrado(tarjeta({ nombre: "parador", presupuesto: null }))).toEqual([
    "¿Borrar «parador»? Se borran sus piezas, sus grupos, sus anidados y el dibujo guardado. No se puede deshacer.",
  ]);
  expect(textoDeBorrado(tarjeta({ nombre: "parador", presupuesto: { codigo: "P-2026-0001" } }))[1]).toBe(
    "Su presupuesto P-2026-0001 no se borra: queda sin trabajo.");
});
```

- [ ] **Paso 2: Correrlas y ver que fallan.**

- [ ] **Paso 3: Escribir todo lo de arriba.**

- [ ] **Paso 4: Correr la pantalla entera**: `npx vitest run` y `npx tsc --noEmit`.

- [ ] **Paso 5: Mirarlo en pantalla** sobre la copia, con capturas:
  - buscar «pena» sin acento;
  - borrar un trabajo de prueba creado en la copia;
  - intentar borrar uno mientras se anida, que tiene que dar el mensaje y dejar el cuadro abierto.

- [ ] **Paso 6: Commit**

```bash
git add -A frontend/src
git commit -m "feat(inicio): la sección Trabajos con buscador y borrar desde la tarjeta (A16, tarea 6)"
```

**Pausa: Enzo lo prueba.**

---

### Tarea 7: El recorrido y el cierre

**Archivos:**
- Fuera de git:
  - `backend/local/herramientas-a16/recorrido-a16.mjs`, armado a partir de `backend/local/herramientas-a15/recorrido-a15.mjs`;
  - las capturas, en la misma carpeta.
- Modificar al cerrar:
  - `docs/plan/A16-pagina-de-inicio/diseno.md`: el estado y una §10 «Cómo quedó»;
  - `docs/plan/PLAN-MAESTRO.md` §7: la fila de la página de inicio y una tabla «Pendientes de la página de inicio (A16)»;
  - `README.md`, en «En qué estamos»: el inicio va a «Ya está»; el paso 1 queda con materiales, presupuestos y retocar el presupuesto, y las tarjetas (paso 3) quedan hechas.

- [ ] **Paso 1: Todo en verde.**
  - El servidor, desde `backend/`: `python -m pytest -q`, con los temporales en D:.
  - La pantalla, desde `frontend/`: `npx vitest run` y `npx tsc --noEmit`.

- [ ] **Paso 2: La copia de la base.** `python local/herramientas-a14/copiar_base.py a16`, desde `backend/`, arma `local/tmp-a14/a16`. **Antes de borrar nada en la copia**, comprobar que el `archivo_guardado` de cada trabajo apunta adentro de la copia, porque borrar un trabajo borra su DXF. **Nunca se usa la base real.**

- [ ] **Paso 3: El recorrido**, en Chrome sin ventana por CDP. **Antes de levantar nada, mirar quién escucha en 8000 y 5173.** Si Enzo tiene la app levantada, pedirle que la cierre: la pantalla llama al 8000 sí o sí. El recorrido revisa, con los trabajos de la copia (Complejo, los dos paradores y parador1):
  - las tarjetas, con sus frases y sus miniaturas;
  - que tocar cada una lleve al paso que dice;
  - la barra en el inicio y dentro de un trabajo;
  - que la hora de cada tarjeta sea la de Argentina;
  - buscar en Trabajos;
  - borrar un trabajo de prueba;
  - que el presupuesto del parador lleve a su Costeo y que su PDF baje;
  - después de anidar de nuevo, que la miniatura cambie;
  - cuánto tarda en aparecer la miniatura de Complejo.

- [ ] **Paso 4: Cerrar lo que se levantó.** Solo los procesos propios, por hora de inicio (8000, 5173 y 9222).

- [ ] **Paso 5: Los documentos y el commit**

```bash
git add docs/plan/A16-pagina-de-inicio/diseno.md docs/plan/PLAN-MAESTRO.md README.md
git commit -m "docs: la página de inicio (A16), cómo quedó"
```

**Pausa: Enzo decide si se fusiona en `main` y se sube.**
