# A14 · Las chapas en conjunto y el diseño inicial — plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ver todas las chapas de un anidado con el diseño inicial pintado por chapa, pasar piezas entre chapas, y que toda pieza nombrada muestre su forma y dónde está en el diseño.

**Architecture:** cada pieza guarda cómo pasar de su marco local al dibujo (giro + corrimiento). Un pedido nuevo devuelve el diseño de un trabajo: el fondo del DXF releído, la posición de cada pieza y los cortes del seccionado. La pantalla lo dibuja pintado por chapa o en gris, con un contexto compartido para iluminar. Pasar una pieza de chapa reutiliza la búsqueda por casillas de A13 sobre lo libre de la chapa de destino.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + shapely (backend); React + TanStack Query + Vite + vitest (frontend).

**Spec:** [`diseno.md`](diseno.md), aprobado por Enzo el 2026-10-24 («Sí, lo apruebo»).

## Global Constraints

- Todo texto de pantalla y de error en castellano rioplatense, con la regla de los mensajes de A9 (`ErrorParaElUsuario` / dict `{mensaje, piezas, chapas}`); la prueba guardiana `tests/test_mensajes_claros.py` tiene que seguir en verde.
- Nombres en castellano y sin `ñ` en identificadores y archivos (`disenio`, no `diseño`), como el resto del código.
- La pieza en el diseño: un punto `p` de su marco local va a `girar(p, angulo_grados alrededor de (0,0)) + (x_mm, y_mm)`. La misma cuenta en el backend y en la pantalla.
- Paleta de las chapas: 12 colores fijos; la chapa `i` (desde 0) usa `PALETA_CHAPAS[i % 12]`. Rojo `#d62728` queda reservado para «lo que falta»; naranja `#e8833a` para «iluminado». Ninguno de los dos está en la paleta.
- No se toca la base real. Las pruebas del backend se corren con los temporales en D: (C: está lleno), desde `backend/`:
  `$env:CARTELERIA_DATOS = "D:\User\Desktop\proyectos\cartelería\backend\local\tmp-a14\datos"; python -m pytest <ruta> -q --basetemp=local/tmp-a14/pytest`
- Frontend, desde `frontend/`: `npm test` (vitest) y `npx tsc -b` sin errores.
- Una pausa al final de cada tramo (tareas 5, 7, 10 y 12) para que Enzo lo vea.

## Review Focus

1. **Un trabajo sin DXF guardado, o con piezas cargadas a mano:** el diseño no se cae; esas piezas salen en `sin_lugar` y la pantalla las lista aparte (prueba en Tarea 4).
2. **Una pieza con varias copias en chapas distintas:** se pinta con la chapa de la primera copia, con «×N», y no cuenta como faltante (prueba en Tarea 5).
3. **Pasar una pieza con veta** (`SOLO_0_180`): solo prueba 0° y 180° (pruebas en Tareas 8 y 9).
4. **Una pieza descartada después de anidar:** no ocupa lugar en la chapa de destino ni se puede pasar (prueba en Tarea 9).
5. **Volver a cargar el DXF:** el fondo guardado se tira y el diseño sale del archivo nuevo (prueba en Tarea 4).

---

## Tramo 1 · La base

### Task 1: La posición en el diseño al cargar

**Files:**
- Modify: `backend/app/modelos/trabajo.py` (clase `Pieza`)
- Create: `backend/alembic/versions/d4b2e8a1f630_posicion_en_el_disenio.py`
- Create: `backend/app/services/disenio.py`
- Modify: `backend/app/api/rutas_trabajos.py` (`_normalizar_a_marco_local`, `_pieza_orm_desde_importada`)
- Modify: `backend/app/api/esquemas_trabajos.py` (`PiezaLeer`)
- Test: `backend/tests/services/test_disenio.py`, `backend/tests/api/test_rutas_trabajos.py`, `backend/tests/modelos/test_migracion_disenio.py`

**Interfaces:**
- Produces: columnas `Pieza.disenio_x_mm`, `Pieza.disenio_y_mm`, `Pieza.disenio_angulo_grados` (`Milimetros`, nullable, default `None`); en `PiezaLeer` los mismos tres campos, `Decimal | None = None`.
- Produces: en `app/services/disenio.py` (no conoce la base):
  - `@dataclass(frozen=True) class PosicionEnDisenio: x_mm: float; y_mm: float; angulo_grados: float`
  - `def al_disenio(puntos: Iterable[Sequence[float | Decimal | str]], posicion: PosicionEnDisenio) -> list[tuple[float, float]]`
- Produces: `_normalizar_a_marco_local(pieza) -> tuple[list, list, tuple[Decimal, Decimal]]` (el tercero es la esquina que resta).

- [ ] **Step 1: Write the failing tests**

```python
# tests/services/test_disenio.py
def test_al_disenio_gira_y_corre():
    assert al_disenio([(10, 0)], PosicionEnDisenio(100, 200, 90)) == pytest.approx([(100, 210)])

def test_al_disenio_sin_giro_solo_corre():
    assert al_disenio([("1", "2")], PosicionEnDisenio(5, 5, 0)) == [(6.0, 7.0)]

# tests/api/test_rutas_trabajos.py — DXF con un cuadrado en (0,0) y otro en (500,0)
def test_cargar_guarda_donde_estaba_cada_pieza(cliente, tmp_path):
    ...
    por_x = sorted(piezas, key=lambda p: Decimal(p["disenio_x_mm"]))
    assert [Decimal(p["disenio_x_mm"]) for p in por_x] == [Decimal("0"), Decimal("500")]
    assert all(Decimal(p["disenio_angulo_grados"]) == 0 for p in piezas)

def test_una_pieza_unida_guarda_la_esquina_de_la_union(cliente, tmp_path):
    # dos rectángulos que se pisan, cargados con unir=true: la esquina es la de la unión
```

```python
# tests/modelos/test_migracion_disenio.py, igual a test_migracion_error_datos.py con _ANTES = "c3a91f4e7b20"
def test_la_migracion_agrega_la_posicion_en_el_disenio_y_vuelve(tmp_path, monkeypatch): ...
```

- [ ] **Step 2: Run them to verify they fail** (`tests/services/test_disenio.py tests/api/test_rutas_trabajos.py tests/modelos/test_migracion_disenio.py`): FAIL por import y por clave faltante.
- [ ] **Step 3: Implement** the columns, the migration (revision `d4b2e8a1f630`, down `c3a91f4e7b20`, `batch_alter_table('piezas')` con `app.modelos.tipos.Milimetros(length=40)`), `PosicionEnDisenio` / `al_disenio` with `shapely.affinity` or plain trigonometry, and set `disenio_x_mm`, `disenio_y_mm` from the corner and `disenio_angulo_grados = 0` in `_pieza_orm_desde_importada`.
- [ ] **Step 4: Run them to verify they pass**, and the whole `tests/api/test_rutas_trabajos.py`.
- [ ] **Step 5: Commit** `feat(disenio): cada pieza guarda dónde estaba en el dibujo al cargar (A14, tarea 1)`

### Task 2: La posición de los tramos al seccionar

**Files:**
- Modify: `backend/app/services/seccionado/grilla.py` (`tramo_orientado`)
- Modify: `backend/app/services/disenio.py`
- Modify: `backend/app/api/rutas_seccionado.py` (`_tramo_orm`)
- Test: `backend/tests/services/test_disenio.py`, `backend/tests/api/test_rutas_seccionado.py`

**Interfaces:**
- Consumes: `PosicionEnDisenio`, `al_disenio` (Task 1).
- Produces: `def esquina_girada(tramo: Polygon, grilla: Grilla) -> tuple[float, float]` en `grilla.py` (la `(x0, y0)` que hoy resta `tramo_orientado`, que pasa a usarla).
- Produces: `def posicion_de_tramo(original: PosicionEnDisenio, angulo_grilla: float, esquina: tuple[float, float]) -> PosicionEnDisenio` en `disenio.py`: giro `original.angulo + angulo_grilla`, corrimiento `original + girar(girar(esquina, angulo_grilla), original.angulo)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/api/test_rutas_seccionado.py — reutiliza el armado de las pruebas de seccionado existentes
def test_los_tramos_puestos_en_el_disenio_cubren_la_original(cliente, tmp_path):
    # seccionar con una grilla girada 30°; cada tramo llevado al diseño con al_disenio
    union = unary_union(tramos_en_disenio)
    assert union.symmetric_difference(original_en_disenio).area < 1.0  # mm², sin contar la soldadura
    assert all(original_en_disenio.buffer(0.01).contains(t) for t in tramos_en_disenio)

def test_un_tramo_de_una_original_sin_posicion_queda_sin_posicion(cliente, tmp_path): ...
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** `esquina_girada`, `posicion_de_tramo` and, in `_tramo_orm`, the three fields when the original has them (si no, `None`).
- [ ] **Step 4: Run** `tests/api/test_rutas_seccionado.py tests/services/seccionado tests/services/test_disenio.py`: PASS.
- [ ] **Step 5: Commit** `feat(disenio): los tramos de un seccionado saben dónde estaban (A14, tarea 2)`

### Task 3: Recuperar la posición de los trabajos ya cargados

**Files:**
- Create: `backend/app/api/rutas_disenio.py` (router vacío todavía + la recuperación)
- Modify: `backend/app/api/app.py` (registrar el router)
- Test: `backend/tests/api/test_rutas_disenio.py`

**Interfaces:**
- Consumes: `_leer`, `_formatos_del_catalogo` (`rutas_trabajos.py`); `_chapa_y_parametros`, `_celda`, `_forma`, `_en_orden`, `seccionar_con_grilla`, `esquina_girada`, `Grilla` (seccionado); `posicion_de_tramo`.
- Produces: `def recuperar_posiciones(sesion: Session, trabajo: Trabajo) -> None` — completa, sin commit, las piezas del trabajo con `disenio_x_mm is None`.

Reglas (§5.1 del diseño): número = lo que va después del último `-` del `id_origen` (para un tramo, de la parte antes de `/t`). Se busca en `sin_unir.piezas` una con ese número y el mismo ancho y alto (tolerancia 0,01 mm); si no, en `unida.piezas`. La esquina es el mínimo de su contorno. Un tramo: se vuelve a seccionar la original con `pieza.seccionado` (formato, ángulo, corrimientos), se ordena con `_en_orden` y se toma el `/tN`; si el área no coincide (0,5 %), queda `None`. Cualquier error (sin archivo, formato borrado) deja `None`: nunca 500.

- [ ] **Step 1: Write the failing tests**

```python
def test_recupera_la_posicion_de_un_trabajo_viejo(cliente, tmp_path):
    # cargar el DXF de dos cuadrados; borrar las tres columnas y cambiar "trabajo-1-" por "logo-" en id_origen
    recuperar_posiciones(sesion, trabajo)
    assert {p.disenio_x_mm for p in piezas} == {Decimal("0"), Decimal("500")}

def test_recupera_una_pieza_unida(cliente, tmp_path): ...
def test_recupera_los_tramos_de_un_seccionado(cliente, tmp_path): ...
def test_sin_el_dxf_guardado_queda_sin_posicion(cliente, tmp_path): ...
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** `recuperar_posiciones`.
- [ ] **Step 4: Run** `tests/api/test_rutas_disenio.py`: PASS.
- [ ] **Step 5: Commit** `feat(disenio): recuperar dónde estaba cada pieza en los trabajos ya cargados (A14, tarea 3)`

### Task 4: El pedido del diseño

**Files:**
- Create: `backend/app/api/esquemas_disenio.py`
- Modify: `backend/app/api/rutas_disenio.py`
- Modify: `backend/app/api/rutas_trabajos.py` (`subir_dxf` borra el fondo guardado)
- Test: `backend/tests/api/test_rutas_disenio.py`

**Interfaces:**
- Produces: `GET /trabajos/{trabajo_id}/disenio` → `DisenioLeer`:
  - `fondo: list[FormaDeFondo]` — `FormaDeFondo(contorno_mm: list[list[float]], agujeros_mm: list[list[list[float]]])`, en coordenadas del dibujo, simplificado con `tolerancia_del_dibujo` + `anillo_para_dibujar`;
  - `piezas: list[PiezaEnDisenio]` — `PiezaEnDisenio(pieza_id: int, x_mm: float, y_mm: float, angulo_grados: float)`, solo las no descartadas con posición;
  - `cortes: list[CorteEnDisenio]` — `CorteEnDisenio(pieza_id: int, puntos: list[list[float]])`, los `seccionado["cortes"]` de cada original llevados al diseño con la posición de la original;
  - `sin_lugar: list[int]` — no descartadas sin posición.
- Produces: `def _ruta_del_fondo(trabajo: Trabajo) -> Path` = `Path(trabajo.archivo_guardado).with_suffix(".fondo.json")`.

Antes de responder llama a `recuperar_posiciones` y hace commit si cambió algo. El fondo sale de `parsear_dxf(ruta, escala)` sin correcciones (así entra lo que no va) y se guarda en `_ruta_del_fondo` la primera vez.

- [ ] **Step 1: Write the failing tests**

```python
def test_el_disenio_trae_fondo_piezas_y_nada_sin_lugar(cliente, tmp_path): ...
def test_el_disenio_trae_los_cortes_de_un_seccionado(cliente, tmp_path): ...
def test_un_trabajo_sin_dxf_lista_sus_piezas_sin_lugar(cliente): ...          # Review Focus 1
def test_volver_a_cargar_el_dxf_tira_el_fondo_guardado(cliente, tmp_path): ... # Review Focus 5
def test_el_disenio_de_un_trabajo_que_no_existe_da_404(cliente): ...
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** schemas, route and the delete in `subir_dxf` (`_ruta_del_fondo(...).unlink(missing_ok=True)` antes de escribir el archivo nuevo).
- [ ] **Step 4: Run** `tests/api/test_rutas_disenio.py tests/api/test_rutas_trabajos.py tests/test_mensajes_claros.py`: PASS.
- [ ] **Step 5: Commit** `feat(disenio): el pedido del diseño de un trabajo (A14, tarea 4)`

### Task 5: El diseño inicial en la pantalla

**Files:**
- Create: `frontend/src/api/disenio.ts`, `frontend/src/hooks/useDisenio.ts`
- Create: `frontend/src/components/Disenio/pintado.ts`, `pintado.test.ts`
- Create: `frontend/src/components/Disenio/Iluminado.tsx`
- Create: `frontend/src/components/Disenio/DisenioInicial.tsx`
- Modify: `frontend/src/api/piezasYgrupos.ts` (`Pieza` suma `disenio_x_mm`, `disenio_y_mm`, `disenio_angulo_grados: string | null`)
- Modify: `frontend/src/hooks/usePiezas.ts` (subir DXF y seccionar invalidan `["disenio", trabajoId]`)

**Interfaces:**
- Produces: `interface Disenio { fondo: FormaDeFondo[]; piezas: PiezaEnDisenio[]; cortes: CorteEnDisenio[]; sin_lugar: number[] }`, `obtenerDisenio(trabajoId: number): Promise<Disenio>`, `useDisenio(trabajoId: number)` (clave `["disenio", trabajoId]`).
- Produces, en `pintado.ts`:
  - `PALETA_CHAPAS: readonly string[]` (12) y `colorDeChapa(indice: number): string`
  - `type EstadoEnDisenio = { tipo: "en_chapa"; chapa: number; copias: number } | { tipo: "falta" } | { tipo: "otro" }`
  - `estadosPorPieza(piezas: Pieza[], colocaciones: Colocacion[], grupoId: number): Map<number, EstadoEnDisenio>`: del grupo y no descartada → `en_chapa` (chapa de la colocación de menor `instancia`, `copias` = colocaciones de esa pieza) o `falta`; de otro grupo, sin grupo o descartada → `otro`.
  - `contornoEnDisenio(contorno: string[][], posicion: PiezaEnDisenio): [number, number][]` (la cuenta de Global Constraints).
- Produces, en `Iluminado.tsx`: `IluminadoProvider({ conDisenioFijo: boolean, children })` y `useIluminado(): { pieza: number | null; chapa: number | null; setPieza(id: number | null): void; setChapa(i: number | null): void; conDisenioFijo: boolean }`. Fuera de un provider devuelve todo en `null` y `conDisenioFijo: false`.
- Produces: `DisenioInicial({ trabajoId, modo: "por_chapa" | "gris" | "mini", estados?: Map<number, EstadoEnDisenio>, piezaMarcada?: number, alClicPieza?: (piezaId: number) => void })`. Dibuja en SVG con la `y` dada vuelta (`yEnPantalla` de `PlanoEditor/geometria.ts`):
  - el fondo en gris muy claro;
  - las piezas según `estados`; la falta en rojo con borde cortado y la leyenda «N pieza(s) sin chapa»; una pieza con `copias > 1` lleva «×N»;
  - los cortes como rayas oscuras;
  - la iluminada del contexto (o `piezaMarcada`) en naranja;
  - en `por_chapa`, al costado la lista de chapas con su color, que ilumina con `setChapa`, y la lista de `sin_lugar` con `PiezaMiniPreview`.
  
  En `por_chapa` y `gris` tiene un botón «Plegar»/«Ver el diseño». En `mini` ocupa 44 px y no tiene leyendas.

- [ ] **Step 1: Write the failing tests** (`pintado.test.ts`)

```ts
it("una pieza con copias en dos chapas se pinta con la de la primera copia y cuenta las copias", () => {
  expect(estadosPorPieza([pieza(1, 7)], [col(1, 0, 2), col(1, 1, 0)], 7).get(1))
    .toEqual({ tipo: "en_chapa", chapa: 2, copias: 2 });              // Review Focus 2
});
it("una pieza del grupo sin colocación falta", ...);
it("una pieza de otro grupo o descartada es otro", ...);
it("colorDeChapa repite la paleta después de 12 y nunca da rojo ni naranja", ...);
it("contornoEnDisenio gira 90° y corre", () => {
  expect(contornoEnDisenio([["10", "0"]], { pieza_id: 1, x_mm: 100, y_mm: 200, angulo_grados: 90 }))
    .toEqual([[100, 210]]);
});
```

- [ ] **Step 2: Run** `npm test -- pintado`: FAIL.
- [ ] **Step 3: Implement** the files above.
- [ ] **Step 4: Run** `npm test` and `npx tsc -b`: PASS, sin errores.
- [ ] **Step 5: Commit** `feat(disenio): el diseño inicial en la pantalla, pintado o en gris (A14, tarea 5)`
- [ ] **Pausa del tramo 1:** mostrarle a Enzo el pedido del diseño de Complejo y del parador sobre una copia de la base (aro entero con sus cortes), y esperar su ok.

## Tramo 2 · Ver

### Task 6: La pestaña Chapas con el mosaico

**Files:**
- Create: `frontend/src/routes/TrabajoWorkspace/ChapasTab.tsx`
- Create: `frontend/src/components/Chapas/Mosaico.tsx`, `mosaico.ts`, `mosaico.test.ts`
- Modify: `frontend/src/App.tsx` (`chapas` → `ChapasTab`; `ajuste` → `<Navigate to="../chapas" replace />`)
- Modify: `frontend/src/routes/TrabajoWorkspace/WorkspaceLayout.tsx` (pestaña «Chapas» en lugar de «Ajuste»)

**Interfaces:**
- Consumes: `DisenioInicial`, `estadosPorPieza`, `colorDeChapa`, `IluminadoProvider` (Task 5); `useEjecucionesDeGrupo`, `useColocaciones`, `useFormato`.
- Produces, en `mosaico.ts`:
  - `anidadoParaMostrar(historial: Ejecucion[] | undefined): Ejecucion | undefined` (la regla de hoy de `AjusteTab`: la definitiva lista, si no la última lista)
  - `areaDePieza(pieza: Pieza): number` (contorno menos agujeros, en mm²)
  - `aprovechamientoDeChapa(colocaciones: Colocacion[], piezas: Pieza[], indice: number, anchoMm: number, altoMm: number): number` (0 a 100)
- Produces: `Mosaico({ ejecucion, piezas, colocaciones, anchoMm, altoMm, alDobleClic: (indice: number) => void })`. Cada chapa es un SVG con `data-chapa={indice}`, borde de `colorDeChapa(indice)`, «N · xx %» abajo, y las piezas con `data-colocacion={id}`.

`ChapasTab` (envuelto en `IluminadoProvider conDisenioFijo`):
- arriba, una pastilla por grupo: «nombre · N chapas», o apagada con «sin anidar» si `anidadoParaMostrar` no da nada;
- abajo, `DisenioInicial modo="por_chapa"` con los estados del grupo elegido;
- abajo, el `Mosaico`;
- con faltantes, un `Mensaje` con sus `id`.

- [ ] **Step 1: Write the failing tests** (`mosaico.test.ts`)

```ts
it("anidadoParaMostrar prefiere la definitiva lista y si no la última lista", ...);
it("anidadoParaMostrar no da nada si ninguna está lista", ...);                 // grupo «sin anidar»
it("areaDePieza resta los agujeros", () => expect(areaDePieza(cuadradoConHueco(100, 20))).toBe(9600));
it("aprovechamientoDeChapa cuenta solo las piezas de esa chapa", ...);
```

- [ ] **Step 2: Run** `npm test -- mosaico`: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `npm test` and `npx tsc -b`: PASS.
- [ ] **Step 5: Commit** `feat(chapas): la pestaña Chapas con todas las chapas y el diseño pintado (A14, tarea 6)`

### Task 7: Iluminar de los dos lados y abrir una chapa grande

**Files:**
- Create: `frontend/src/components/Chapas/ChapaGrande.tsx` (el editor y los controles que hoy están en `AjusteTab`)
- Delete: `frontend/src/routes/TrabajoWorkspace/AjusteTab.tsx`
- Modify: `Mosaico.tsx`, `ChapasTab.tsx`, `DisenioInicial.tsx`, `frontend/src/components/PlanoEditor/PlanoEditor.tsx` (prop opcional `iluminada?: number | null`, en naranja)

**Interfaces:**
- Consumes: `useIluminado` (Task 5).
- Produces: `ChapaGrande({ ejecucion, grupo, piezas, colocaciones, indice, alVolver: () => void })`. Mantiene lo de `AjusteTab`: mover, girar, los motivos con `Mensaje` y los enlaces al plano y al DXF de la chapa.

Comportamiento:
- **Pieza bajo el mouse**, en el mosaico, en el editor o en el diseño: `setPieza(pieza_id)`.
- **Chapa bajo el mouse**, en su borde o su número: `setChapa(indice)`.
- **En el diseño, en el mosaico y en el editor**, la pieza iluminada va en naranja con todas sus copias. Con una chapa iluminada, sus piezas van en naranja en el diseño y el resto se atenúa.
- **Clic en una pieza del diseño** hace `scrollIntoView` del `[data-chapa]` de su primera copia.
- **Doble clic en una chapa** muestra `ChapaGrande` en lugar del mosaico, con «Volver a todas las chapas».

- [ ] **Step 1:** no hay lógica pura nueva. La verificación es `npx tsc -b` y el recorrido del Step 3.
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Verify** levantando backend y frontend sobre una copia de la base (puertos libres, nunca contra la base real) y recorriendo en Chrome sin ventana con un guion en `backend/local/herramientas-a14/`, fuera de git:
  - pasar el mouse por un tramo de Complejo lo ilumina en la chapa y en el aro;
  - pasar por la chapa 2 ilumina sus piezas;
  - doble clic abre la chapa grande y «Volver» regresa.
  
  Guardar capturas y cerrar los servidores propios.
- [ ] **Step 4: Run** `npm test` and `npx tsc -b`: PASS.
- [ ] **Step 5: Commit** `feat(chapas): iluminar en el diseño y en las chapas, y abrir una chapa grande (A14, tarea 7)`
- [ ] **Pausa del tramo 2:** capturas a Enzo y esperar su ok.

## Tramo 3 · Mover

### Task 8: Buscar lugar en una chapa

**Files:**
- Modify: `backend/app/services/nesting/huecos_primero.py`
- Create: `backend/app/services/nesting/mover_entre_chapas.py`
- Test: `backend/tests/services/nesting/test_mover_entre_chapas.py`

**Interfaces:**
- Produces, en `huecos_primero.py`: `def lugar_libre(libre: Polygon, exterior: Polygon, angulos: list[float]) -> tuple[float, float, float] | None`. Arma un `_Hueco(dueno="chapa", poligono=libre, util=libre, angulos=tuple(angulos))` y una sola `_Pieza` y llama a `_llenar_hueco(..., gap=0.0, seguir=lambda: True)`. Devuelve `(angulo, tx, ty)` de su `Adentro`: girar `exterior` sobre (0,0) y trasladar.
- Produces, en `mover_entre_chapas.py`:
  - `def angulos_permitidos(rotaciones: RotacionPermitida, giro_libre: bool) -> list[float]`: `SOLO_0_180` → `[0, 180]`; `giro_libre` → de a 15° (0 a 345); si no → `[0, 90, 180, 270]`
  - `def libre_de_chapa(plancha: Plancha, params: ParametrosCorte, ocupadas: list[Polygon]) -> Polygon`: la chapa achicada en `margen_borde_mm`, menos cada ocupada agrandada en `kerf_mm + separacion_piezas_mm` (el mismo gap que controla `validar_posicion_manual`)

- [ ] **Step 1: Write the failing tests**

```python
def test_en_una_chapa_vacia_va_abajo_a_la_izquierda():
    libre = libre_de_chapa(Plancha(Decimal(1000), Decimal(1000)), params(margen=5), [])
    angulo, x, y = lugar_libre(libre, cuadrado_centrado(100), [0.0])
    assert (angulo, round(x), round(y)) == (0.0, 55, 55)   # centro: margen 5 + medio lado 50

def test_no_pisa_lo_ocupado_ni_se_acerca_mas_que_el_gap(): ...
def test_sin_lugar_devuelve_none(): ...
def test_con_veta_solo_media_vuelta():
    assert angulos_permitidos(RotacionPermitida.SOLO_0_180, giro_libre=True) == [0, 180]   # Review Focus 3
def test_giro_libre_de_a_15(): assert len(angulos_permitidos(RotacionPermitida.LIBRE_0_90, True)) == 24
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `tests/services/nesting/test_mover_entre_chapas.py tests/services/nesting/test_huecos_primero.py`: PASS.
- [ ] **Step 5: Commit** `feat(anidado): buscar lugar para una pieza en una chapa (A14, tarea 8)`

### Task 9: Pasar una pieza a otra chapa

**Files:**
- Modify: `backend/app/api/rutas_ajuste.py`
- Modify: `backend/app/api/esquemas_nesting.py`
- Test: `backend/tests/api/test_rutas_ajuste.py`

**Interfaces:**
- Consumes: `lugar_libre`, `angulos_permitidos`, `libre_de_chapa` (Task 8); `_las_de_adentro`, `_llevada_con`, `_resultado_y_geometrias`, `_plancha_de`, `_parametros_desde_snapshot`, `poligono_colocado`, `_poligono_centrado`, `calcular_aprovechamiento`, `rechazar_si_hay_anidado_en_curso`.
- Produces: `POST /colocaciones/{colocacion_id}/a-otra-chapa`, cuerpo `ColocacionAOtraChapa(plancha_destino: int)`; respuesta `MovidaDeChapaLeer(colocaciones: list[ColocacionLeer], planchas_usadas: int, aprovechamiento_pct: Decimal | None, chapa_quitada: int | None)`.

Pasos:
1. **Controles.**
   - La colocación no existe → 404.
   - El anidado no está listo → 409.
   - Corre un anidado del mismo grupo → 409 (`rechazar_si_hay_anidado_en_curso`).
   - La pieza está descartada → 409.
   - `plancha_destino` fuera de `0..planchas_usadas` → 404; igual a la propia → 400. `plancha_destino == planchas_usadas` es la chapa nueva.
2. **Lo libre.** `ocupadas` son los polígonos de las colocaciones de la chapa de destino cuya pieza no está descartada.
3. **La búsqueda.** El exterior de `_poligono_centrado` de la pieza (`angulos_permitidos` con `RotacionPermitida(parametros["rotaciones_permitidas"])` y `opciones.get("giro_libre", False)`). Con resultado `(a, x, y)`, la pieza queda con `centro = (x, y)` y `angulo = a`.
4. **Lo de adentro** pasa a la misma chapa con `_llevada_con`.
5. **Sin lugar:** 409 con `{"mensaje": f"No hay lugar para «{id_origen}» en la chapa {destino + 1}.", "piezas": [pieza_id], "chapas": [{"ejecucion_id": ..., "plancha": destino}]}`, sin cambiar nada.
6. **Después de mover:**
   - Si se usó la chapa nueva, suma 1 a `planchas_usadas`.
   - Si la chapa de origen quedó sin colocaciones, baja en 1 el `plancha_indice` de las mayores, resta 1 y devuelve `chapa_quitada`.
   - Recalcula `aprovechamiento_pct` como `_ejecutar_anidado` (`calcular_aprovechamiento` sobre `_resultado_y_geometrias`).
   - Deja `movida_a_mano = True` en todas las que se movieron.

- [ ] **Step 1: Write the failing tests** (chapa de 150 × 150, margen 5, dos cuadrados de 100: una pieza por chapa)

```python
def test_pasar_a_una_chapa_con_lugar_la_mueve_y_marca_movida(cliente, tmp_path): ...  # chapa 1000×1000, 3 piezas en 2 chapas
def test_sin_lugar_da_409_con_la_pieza_y_no_cambia_nada(cliente, tmp_path): ...
def test_a_la_chapa_nueva_y_vaciar_la_de_origen_deja_las_mismas_chapas_renumeradas(cliente, tmp_path):
    assert cuerpo["planchas_usadas"] == 2 and cuerpo["chapa_quitada"] == 0
def test_lo_de_adentro_viaja_a_la_otra_chapa(cliente, tmp_path): ...       # con _anidado_con_una_adentro
def test_con_veta_la_busqueda_solo_prueba_media_vuelta(cliente, tmp_path): ...  # Review Focus 3
def test_una_descartada_no_ocupa_lugar_ni_se_puede_pasar(cliente, tmp_path): ... # Review Focus 4
def test_destino_inexistente_404_y_la_misma_chapa_400(cliente, tmp_path): ...
def test_recalcula_el_aprovechamiento(cliente, tmp_path): ...
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `tests/api/test_rutas_ajuste.py tests/test_mensajes_claros.py`: PASS.
- [ ] **Step 5: Commit** `feat(chapas): pasar una pieza a otra chapa o a una chapa nueva (A14, tarea 9)`

### Task 10: Arrastrar entre chapas en la pantalla

**Files:**
- Modify: `frontend/src/api/nesting.ts` (`interface MovidaDeChapa { colocaciones: Colocacion[]; planchas_usadas: number; aprovechamiento_pct: string | null; chapa_quitada: number | null }` y `moverAOtraChapa(colocacionId: number, planchaDestino: number): Promise<MovidaDeChapa>`)
- Modify: `frontend/src/hooks/useNesting.ts` (`useMoverAOtraChapa(ejecucionId: number)`: invalida colocaciones, ejecuciones del grupo, material usado y costeo)
- Modify: `Mosaico.tsx`, `ChapasTab.tsx`

**Interfaces:**
- Consumes: `POST /colocaciones/{id}/a-otra-chapa` (Task 9); `usePresupuestosDelTrabajo(trabajoId)`.

Comportamiento:
- **El arrastre** usa eventos de puntero, como `PlanoEditor`, no el arrastre nativo de HTML, que en SVG anda mal.
- **Al soltar**, se busca el `[data-chapa]` bajo el puntero con `document.elementFromPoint`. Soltar en la propia chapa no hace nada.
- **Al final del mosaico** va la chapa nueva: borde punteado, «Chapa nueva» y `data-chapa={planchas_usadas}`.
- **Un 409** se muestra con `Mensaje` (sus miniaturas) y la pieza vuelve a su lugar.
- **Si cambió `planchas_usadas`** y `usePresupuestosDelTrabajo` trae alguno, aparece un aviso: «Cambió la cantidad de chapas: en Costeo, tocá «Recalcular materiales» para actualizar el presupuesto.»

- [ ] **Step 1:** sin lógica pura nueva más allá de lo de Task 6.
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Verify** en Chrome sin ventana, sobre la copia de la base:
  - pasar un tramo de Complejo de una chapa a otra;
  - soltar en una chapa llena (aparece el mensaje);
  - pasar la única pieza de una chapa a la chapa nueva (la cantidad no cambia);
  - vaciar una chapa (baja la cantidad y aparece el aviso del presupuesto).
- [ ] **Step 4: Run** `npm test` and `npx tsc -b`: PASS.
- [ ] **Step 5: Commit** `feat(chapas): arrastrar piezas entre chapas (A14, tarea 10)`
- [ ] **Pausa del tramo 3:** capturas a Enzo y esperar su ok.

## Tramo 4 · Las miniaturas

### Task 11: La pieza nombrada, con su forma y su lugar

**Files:**
- Create: `frontend/src/components/PiezaNombrada.tsx`
- Modify: `frontend/src/components/Mensaje/Mensaje.tsx` (`PiezasDelMensaje` usa `PiezaNombrada`)
- Modify: `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx` (lista sin asignar, «Hay que seccionar…», diseño fijo al costado)
- Modify: `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx` (columna de la tabla, diseño fijo al costado)

**Interfaces:**
- Consumes: `useIluminado`, `DisenioInicial` (Task 5), `PiezaMiniPreview`.
- Produces: `PiezaNombrada({ pieza: Pieza, trabajoId: number })`. Muestra la forma y el `id_origen`.
  - Con `conDisenioFijo`, al pasar el mouse hace `setPieza`.
  - Sin `conDisenioFijo`, suma `DisenioInicial modo="mini" piezaMarcada={pieza.id}`.
  - El nombre queda escrito igual.

`GruposTab` y `PiezasTab` se envuelven en `IluminadoProvider conDisenioFijo` y suman `DisenioInicial modo="gris"` al costado, plegable. En Grupos, `piezas_a_seccionar` trae solo `id`, `id_origen`, `ancho_mm` y `alto_mm`: la pieza entera sale de `usePiezas`.

- [ ] **Step 1:** sin lógica pura nueva. La verificación es `npx tsc -b` y el recorrido del Step 3.
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Verify** en Chrome sin ventana:
  - en Grupos, pasar el mouse por una pieza sin asignar la ilumina en el diseño;
  - el «Hay que seccionar» de Complejo muestra la forma del aro;
  - un mensaje en Anidado trae el diseño chiquito con la pieza en naranja.
- [ ] **Step 4: Run** `npm test` and `npx tsc -b`: PASS.
- [ ] **Step 5: Commit** `feat(piezas): toda pieza nombrada con su forma y su lugar en el diseño (A14, tarea 11)`

### Task 12: Recorrido completo y cierre de la documentación

**Files:**
- Modify: `docs/plan/A14-chapas-en-conjunto/diseno.md` (§9 «Cómo quedó», con lo medido y los desvíos)
- Modify: `docs/plan/PLAN-MAESTRO.md` (§7, fila 6 «construido, sin fusionar»), `README.md`, `docs/BITACORA.md`
- Modify: las guías que nombran la pestaña Ajuste, que pasa a ser Chapas (`grep -rn "Ajuste" README.md docs/GUIA-*.md`)

- [ ] **Step 1: Run** las pruebas enteras: backend `python -m pytest -q` (con los temporales en D:) y frontend `npm test` + `npx tsc -b`. Anotar las cantidades.
- [ ] **Step 2: Recorrido completo** en Chrome sin ventana sobre una copia nueva de la base, con Complejo y el parador, todo lo de §7 del diseño. Capturas en `backend/local/herramientas-a14/`.
- [ ] **Step 3: Write** «Cómo quedó» y los pendientes que hayan aparecido.
- [ ] **Step 4: Commit** `docs: las chapas en conjunto (A14) construido y recorrido (A14, tarea 12)`
- [ ] **Pausa del tramo 4:** Enzo decide si se fusiona en `main`.
