# A19 · Los presupuestos y el precio sugerido — plan

> **Estado:** escrito y aprobado por Enzo el 2026-11-07 («Si dale»); ejecutado ese día en la rama `feat/a19-presupuestos-y-precio-sugerido`. **Cerrado el 2026-11-07**, con las 7 tareas hechas; cómo quedó, en §10 del diseño.

> **Para quien ejecuta:** tarea por tarea, con **pausa al final de cada una** para que Enzo la vea antes de seguir. Así trabaja este proyecto, aunque el skill de ejecución diga otra cosa (superpowers:executing-plans). Los pasos usan casillas (`- [ ]`) para llevar la cuenta.

**Objetivo:** que el precio de cada producto del presupuesto salga solo con la ganancia de la planilla, que una baja por debajo de ese precio se note, y una lista de todos los presupuestos en «Presupuestos».

**Cómo:** cada línea de material guarda, al recalcular los materiales, el multiplicador de su artículo (`PAR-61`). La cuenta del presupuesto (`totales.py`, la única) arma con él el precio sugerido y marca lo que queda por debajo. La pantalla lo muestra en el Costeo y en una pantalla nueva con la lista.

**Con qué:** FastAPI, SQLAlchemy y Alembic en el servidor; React, TanStack Query y Tailwind en la pantalla; pytest y vitest.

**Diseño:** [`diseno.md`](diseno.md), en esta carpeta. Manda el diseño; el plan lo baja a tareas.

## Lo que vale para todas las tareas

- **Rama `feat/a19-presupuestos-y-precio-sugerido`**, desde `main`. Commits sin la línea `Co-Authored-By`.
- **`PAR-61`** va en `backend/app/config.py`, con el comentario que apunta a `docs/REGISTRO.md`, como `PAR-59`:
  `MARGEN_DEL_PRECIO_SUGERIDO = os.getenv("CARTELERIA_MARGEN_DEL_PRECIO_SUGERIDO", "margen_venta_1")`. Es el nombre de la columna de `Articulo`; si no es una de `margen_venta_1` a `margen_venta_4`, el arranque falla con un mensaje que lo dice.
- **El documento del cliente no cambia:** ni el PDF ni `services/presupuesto/documento.py` muestran el multiplicador, el sugerido ni la ganancia.
- **Los textos al usuario van tal cual los fija este plan.** Los mensajes del servidor son `ErrorParaElUsuario` o entran en `advertencias` y `faltantes`, como hoy.
- **Los importes viajan como texto** (los `Decimal`), como en el resto de la API.
- **Pruebas con los temporales en D:**, porque C: suele estar lleno. Desde `backend/`:
  `CARTELERIA_DATOS=local/tmp-a19/datos python -m pytest -q -p no:cacheprovider --basetemp=local/tmp-a19/pytest <pruebas>`
  Las de la pantalla, desde `frontend/`: `npx vitest run <archivo>` y `npx tsc --noEmit`.
- **Nunca sobre la base real.** La copia para mirar la pantalla sale de la de A18, que ya tiene la planilla cargada: `python -I local/herramientas-a17/copiar_base.py a19 --desde local/tmp-a17/a18-t11` (queda en `local/tmp-a17/a19`). **Antes de levantar la app, mirar quién escucha en 8000 y 5173** (en esta máquina `netstat` dice «ESCUCHANDO»): si hay algo, es de Enzo y corre contra su base real.

## Lo que más puede fallar sin que ninguna prueba lo mire

Cada uno tiene su prueba en la tarea que lo toca.

1. **El centavo del redondeo no es una baja.** Sin total fijado, la cuenta le pasa a un ítem calculado el centavo que sobra (`_ajustar_centavos`): ese ítem puede quedar un centavo abajo de su sugerido sin que nadie lo haya bajado. Una línea calculada (sin precio a mano) y sin total fijado nunca se marca. Prueba en la tarea 3.
2. **Un costo en 0.** La ganancia es precio ÷ costo y el % por debajo divide por el sugerido: con cero, no hay ganancia ni marca, nunca una división por cero. Prueba en la tarea 3.
3. **Los presupuestos que ya existen.** Sus líneas no tienen multiplicador hasta que se recalculen: con margen general dan exactamente lo mismo que antes; sin margen general, el aviso nombra cada línea sin precio. Prueba en la tarea 3.
4. **Un retazo cuya chapa tiene un proveedor marcado a mano.** El multiplicador sale del artículo de ese proveedor, buscado por el código de la chapa. Prueba en la tarea 1.
5. **Un presupuesto cuyo trabajo se borró.** Aparece en la lista con «sin trabajo», no se abre y baja su PDF. Prueba en la tarea 4, y se mira en la tarea 6.

---

## Tramo 1 — El servidor

### Tarea 1: El multiplicador de una medida

**Archivos:**
- Modificar: `backend/app/modelos/presupuesto.py` (`LineaCosto.multiplicador: Mapped[Decimal | None]`, con el mismo tipo que `margen_pct`), `backend/app/config.py` (`PAR-61`)
- Crear: `backend/alembic/versions/<id>_multiplicador_de_la_linea.py` (después de `e7a1c5d9b318`: suma la columna `lineas_costo.multiplicador`, que puede quedar vacía, y la saca al bajar), `backend/app/services/presupuesto/sugerido.py`
- Prueba: `backend/tests/services/presupuesto/test_sugerido.py` y `backend/tests/modelos/test_migracion_multiplicador.py` (como `test_migracion_articulos.py`)

**Deja para las otras tareas:**

```python
# app/services/presupuesto/sugerido.py
@dataclass(frozen=True)
class Multiplicador:
    valor: Decimal | None   # None: la línea usa el margen general
    aviso: str | None       # solo cuando hay un margen y no se usa

def multiplicador_de(sesion: Session, formato: Formato | None) -> Multiplicador
```

**La regla (diseño §5.1):**
- Sin medida, devuelve `Multiplicador(None, None)`.
- **El código:** el de la medida. Para un retazo (`es_retazo`, su código termina en `-R`), el de su chapa, sin el `-R`.
- **El proveedor marcado a mano:** el de la medida, o el de su chapa si es un retazo (la chapa es el `Formato` de ese código que no es retazo, del mismo material).
- **El artículo:** `articulo_que_cuenta(sesion, codigo, proveedor_a_mano)` de `services/catalogo/precios.py`. Sin artículo, `(None, None)`.
- **El margen:** el atributo que dice `config.MARGEN_DEL_PRECIO_SUGERIDO`. Vacío, `(None, None)`. Mayor que 1, ese es el valor. Menor o igual a 1, `(None, aviso)`, con el aviso:
  «El margen de la planilla de CHA0011 (× 0,6) no se usa: va el margen general.»
  (el código y el margen con coma decimal y sin ceros de más).

- [ ] **Paso 1: Escribir las pruebas que fallan.** En `test_sugerido.py`, con una base SQLite como la de `tests/services/catalogo/test_aplicar.py` y los `Articulo` armados a mano (`codigo`, `proveedor`, `descripcion`, `categoria`, `fila`, `precio_cambiado_en`, `en_ultima_planilla=True`, `unidad_compra="PLANCHA"`, `unidad_venta="M2"` y el margen):
  - `test_una_chapa_toma_el_primer_margen` → `Multiplicador(Decimal("3"), None)`
  - `test_un_retazo_toma_el_margen_de_su_chapa` (código `CHA0011-R`)
  - `test_con_un_proveedor_marcado_a_mano_cuenta_el_de_ese_proveedor` (dos artículos del mismo código, × 3 y × 5; marcado el de × 5)
  - `test_un_retazo_usa_el_proveedor_marcado_en_su_chapa` (lo que más puede fallar, punto 4)
  - `test_una_medida_cargada_a_mano_no_tiene_multiplicador` (sin artículo)
  - `test_un_articulo_sin_margen_no_tiene_multiplicador`
  - `test_un_margen_de_uno_o_menos_no_se_usa_y_avisa` (× 1 y × 0,6; el aviso exacto de arriba)
  - `test_sin_medida_no_hay_multiplicador`
  - `test_el_margen_sale_de_la_columna_de_PAR_61` (con `monkeypatch` a `margen_venta_2`, toma el × 6)
  - En `test_migracion_multiplicador.py`: subir de `e7a1c5d9b318` a la nueva suma la columna vacía en las líneas que había; bajar la saca.
- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir la columna, la migración, `PAR-61` y `sugerido.py`.**
- [ ] **Paso 4: Correrlas.** Tienen que pasar. Además, `alembic check` sobre una base nueva llevada a head: «No new upgrade operations detected».
- [ ] **Paso 5: Commit** — `feat(presupuesto): el multiplicador de la planilla para una medida (A19, tarea 1)`

---

### Tarea 2: Recalcular y duplicar guardan el multiplicador

**Archivos:**
- Modificar: `backend/app/api/rutas_presupuesto.py` (`recalcular_materiales` y `duplicar_presupuesto`), `backend/app/api/esquemas_presupuesto.py` (`LineaCostoLeer.multiplicador: Decimal | None`)
- Prueba: `backend/tests/api/test_rutas_presupuesto.py`

**Interfaces:**
- Usa: `multiplicador_de` (tarea 1).
- Deja: cada línea de material con `multiplicador` y, si hubo aviso, el aviso sumado a su `advertencia` (separado con «; », como los avisos de hoy).

**Qué cambia:**
- **`recalcular_materiales`:** por cada línea del resumen, la medida es `sesion.get(Formato, linea.formato_id)` (o ninguna) y su multiplicador se escribe en la línea nueva o en la existente. Lo puesto a mano (`valor_override`, `precio_cliente`, `texto_cliente`) no se toca, como hoy.
- **`duplicar_presupuesto`:** la copia de cada línea lleva también `multiplicador`.

- [ ] **Paso 1: Escribir las pruebas que fallan.** `_trabajo_con_grupo_anidado_y_costeado` suma un parámetro `codigo=None`, que va en el formato que crea. Los artículos se agregan con la `Sesion` de la app (`app.modelos.base.Sesion`), como el anidado de esas pruebas:
  - `test_recalcular_guarda_el_multiplicador_de_la_planilla` (`CHA0011` con × 3 → la línea dice `"3"`)
  - `test_recalcular_sin_articulo_deja_el_multiplicador_vacio`
  - `test_recalcular_actualiza_el_multiplicador_si_cambio_la_planilla_y_conserva_el_precio_a_mano` (× 3, precio a mano, cambiar el artículo a × 5, recalcular: `"5"` y el precio a mano igual)
  - `test_recalcular_suma_el_aviso_de_un_margen_que_no_se_usa` (× 0,6)
  - `test_duplicar_copia_el_multiplicador`
- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir los cambios.**
- [ ] **Paso 4: Correr `tests/api/test_rutas_presupuesto.py` entero.** Tiene que pasar.
- [ ] **Paso 5: Commit** — `feat(presupuesto): recalcular y duplicar guardan el multiplicador (A19, tarea 2)`

---

### Tarea 3: La cuenta con el precio sugerido

**Archivos:**
- Modificar: `backend/app/services/presupuesto/totales.py`, `backend/app/api/esquemas_presupuesto.py` (`ItemClienteLeer` y `TotalesLeer`) y donde se arma `TotalesLeer` en `rutas_presupuesto.py`
- Prueba: `backend/tests/services/presupuesto/test_totales.py` y una de ruta en `test_rutas_presupuesto.py`

**Deja:**

```python
# ItemCuenta suma:
multiplicador: Decimal | None    # el de la línea, si la cuenta lo usó
sugerido: Decimal | None         # redondeado a centavos
ganancia: Decimal | None         # precio_final / costo, redondeada a centavos
por_debajo_pct: int | None       # cuánto por debajo del sugerido, en %
# Cuenta suma:
por_debajo: int                  # cuántos ítems tienen por_debajo_pct
```

`ItemClienteLeer` suma los mismos cuatro campos y `TotalesLeer`, `por_debajo: int`.

**La regla (diseño §5.2)**, solo para las líneas que entran en la cuenta (con costo y en la moneda del presupuesto); las otras quedan con los cuatro en `None`, como hoy sin precio:
- **El sugerido:** `costo × multiplicador`, si la línea lo tiene; si no, `costo × (1 + margen_pct / 100)`, si hay margen general; si no, `None`. El costo es el efectivo (`_costo_efectivo`: el puesto a mano gana).
- **El precio base:** el escrito a mano o, si no hay, el sugerido.
- **Si alguna línea no tiene precio base**, no hay precios (como hoy sin margen), y por cada una van a `advertencias` y a `faltantes`:
  «A «Chapa negra» le falta precio: no tiene margen en la planilla. Cargá el margen general o un precio a mano.»
  (con la descripción de la línea). Reemplazan a «Falta el margen: sin él no se calcula el precio de venta.» y a «Falta cargar el margen, o un precio a mano en cada ítem.».
- **El total fijado y el redondeo,** como hoy, sobre los precios base.
- **Por debajo:** solo si la línea tiene precio a mano o hay total fijado, y `precio_final < sugerido`. El % es `(sugerido − final) / sugerido × 100`, redondeado al entero, y nunca menos de 1. Una línea calculada sin total fijado nunca se marca (lo que más puede fallar, punto 1).
- **La ganancia:** `precio_final / costo`; sin precio final o con costo en 0, `None`.

- [ ] **Paso 1: Escribir las pruebas que fallan.** En `test_totales.py`, con `_linea(..., multiplicador=D("3"))`:
  - `test_con_multiplicador_el_precio_es_el_costo_por_el_multiplicador` (costo 1000, × 3 → sugerido, base y final 3000; ganancia 3)
  - `test_sin_multiplicador_usa_el_margen_general` (costo 1000, margen 50 % → 1500)
  - `test_mezclados_cada_linea_con_el_suyo` (una × 3 y una sin, margen 50 %)
  - `test_sin_multiplicador_ni_margen_general_el_aviso_nombra_la_linea` (el texto exacto, en `faltantes` y en `advertencias`; la otra línea, con × 3, no se nombra)
  - `test_un_precio_a_mano_mas_bajo_queda_por_debajo` (sugerido 3000, a mano 2640 → 12; `por_debajo` 1)
  - `test_un_precio_a_mano_igual_al_sugerido_no_queda_por_debajo`
  - `test_un_total_fijado_mas_bajo_deja_todos_por_debajo`
  - `test_el_centavo_del_redondeo_no_es_una_baja` (tres líneas cuyos sugeridos suman un centavo de más al redondear; ninguna marcada)
  - `test_una_baja_chica_marca_al_menos_un_uno` (3000 → 2999 da 1)
  - `test_con_costo_en_cero_no_hay_ganancia_ni_marca`
  - `test_el_costo_puesto_a_mano_es_el_que_se_multiplica`
  - `test_sin_multiplicadores_da_lo_mismo_que_antes` (el ejemplo de `test_sin_tocar_nada_cada_item_es_su_costo_mas_el_margen`, con los mismos números)
  - En `test_rutas_presupuesto.py`: `test_el_desglose_trae_el_sugerido_y_cuantos_quedan_por_debajo`.
- [ ] **Paso 2: Correrlas y ver que fallan.** Las pruebas de `test_totales.py` que ya había y miran el texto «Falta cargar el margen» se cambian al texto nuevo, y se anota en el commit.
- [ ] **Paso 3: Escribir los cambios.**
- [ ] **Paso 4: La suite entera del servidor.** Tiene que pasar: el PDF y el inicio usan la misma cuenta.
- [ ] **Paso 5: Commit** — `feat(presupuesto): el precio sugerido y lo que queda por debajo, en la cuenta (A19, tarea 3)`

---

### Tarea 4: La lista resumida de presupuestos

**Archivos:**
- Modificar: `backend/app/api/rutas_inicio.py` (`presupuesto_resumido` y la ruta nueva), `backend/app/api/esquemas_inicio.py` (`PresupuestoResumidoLeer`)
- Prueba: `backend/tests/api/test_rutas_inicio.py`

**Deja:**
- `PresupuestoResumidoLeer` suma `creado_en: datetime` (en UTC, con `en_utc`) y `por_debajo: int` (el de la cuenta). Los usan también el inicio y las tarjetas, que lo arman con la misma función.
- `GET /resumen-de-presupuestos` → `list[PresupuestoResumidoLeer]`: todos, del más nuevo al más viejo (por `creado_en` y, a igualdad, por `id`), cada uno armado con `presupuesto_resumido`. *(Fuera de `/presupuestos/...`, para no chocar con `/presupuestos/{presupuesto_id}`.)*

- [ ] **Paso 1: Escribir las pruebas que fallan:**
  - `test_la_lista_trae_todos_del_mas_nuevo_al_mas_viejo`
  - `test_la_lista_cuenta_los_productos_por_debajo` (un precio a mano más bajo que el sugerido → 1)
  - `test_un_presupuesto_cuyo_trabajo_se_borro_queda_en_la_lista` (lo que más puede fallar, punto 5: `trabajo_id` y `trabajo` en `None`)
  - `test_el_inicio_trae_tambien_la_fecha_y_por_debajo`
- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir los cambios.**
- [ ] **Paso 4: Correr `tests/api/test_rutas_inicio.py`.** Tiene que pasar.
- [ ] **Paso 5: Commit** — `feat(presupuesto): la lista resumida de todos los presupuestos (A19, tarea 4)`

**Pausa: fin del tramo 1.**

---

## Tramo 2 — La pantalla

### Tarea 5: El Costeo

**Archivos:**
- Modificar: `frontend/src/api/presupuestos.ts` (`ItemCliente` y `Totales`), `frontend/src/routes/TrabajoWorkspace/importes.ts` (`mostrarMultiplicador`), `frontend/src/routes/TrabajoWorkspace/PresupuestoClienteSeccion.tsx`, `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx`
- Prueba: `frontend/src/routes/TrabajoWorkspace/importes.test.ts`

**Deja:**

```ts
// api/presupuestos.ts
ItemCliente += { multiplicador: string | null; sugerido: string | null; ganancia: string | null; por_debajo_pct: number | null }
Totales += { por_debajo: number }
// importes.ts
export function mostrarMultiplicador(valor: string | null | undefined): string  // "3" → "× 3", "2.64" → "× 2,6", null → "—"
```

**Lo que muestra** (diseño §5.3):
- **Las columnas:** «Texto para el cliente», «Costo», «Sugerido», «Precio», «En el presupuesto» y «Ganancia».
  - **Sugerido:** el importe y, debajo y en chico, `mostrarMultiplicador(item.multiplicador)` si tiene multiplicador, «margen general» si el sugerido salió del margen general, o nada si no hay sugerido.
  - **Precio:** el campo que hoy se llama «Precio base», con su «a mano · quitar» o «calculado».
  - **Ganancia:** `mostrarMultiplicador(item.ganancia)`.
- **Por debajo:** con `por_debajo_pct`, el renglón lleva en `text-bronze` «por debajo del sugerido: −12 %».
- **Arriba de la tabla,** con `totales.por_debajo > 0`, un aviso (`Banner` con la variante aviso): «1 producto queda por debajo del precio sugerido.» o «3 productos quedan por debajo del precio sugerido.».
- **En el desglose por rubro** (`CosteoTab.tsx`), el campo «Margen %» pasa a «Margen para lo que no tiene margen en la planilla (%)», también en el mensaje de error que lo nombra.

- [ ] **Paso 1: Escribir las pruebas que fallan** de `mostrarMultiplicador`: `"3"` → «× 3», `"2.64"` → «× 2,6», `"1.50"` → «× 1,5», `null` → «—».
- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir los cambios.**
- [ ] **Paso 4: `npx vitest run` y `npx tsc --noEmit`.** Tienen que pasar.
- [ ] **Paso 5: Mirarlo en Chrome sin ventana sobre la copia `a19`** (guion `local/herramientas-a19/recorrido-a19.mjs`, a partir de `herramientas-a18/recorrido-a18.mjs`): en el Costeo del Parador, crear un presupuesto y recalcular los materiales (la chapa negra con × 3), bajar a mano un precio (amarillo y el aviso) y fijar un total más bajo. Capturas.
- [ ] **Paso 6: Commit** — `feat(costeo): el precio sugerido, la ganancia y lo que queda por debajo (A19, tarea 5)`

---

### Tarea 6: La pantalla Presupuestos

**Archivos:**
- Crear: `frontend/src/routes/Presupuestos.tsx`, `frontend/src/components/Presupuestos/lista.ts` (y `lista.test.ts`), `frontend/src/components/Presupuestos/BotonPdf.tsx`
- Modificar: `frontend/src/api/inicio.ts` (`PresupuestoResumido` y `listarPresupuestosResumidos`), `frontend/src/hooks/useInicio.ts` (`usePresupuestosResumidos`, `queryKey` `["presupuestos-resumidos"]`), `frontend/src/App.tsx` (ruta `/presupuestos`), `frontend/src/components/Barra.tsx` («Presupuestos» pasa a `NavLink`) y `frontend/src/routes/Inicio.tsx`

**Deja:**

```ts
// api/inicio.ts
PresupuestoResumido += { creado_en: string; por_debajo: number }   // creado_en en UTC
export function listarPresupuestosResumidos(): Promise<PresupuestoResumido[]>  // GET /resumen-de-presupuestos
// components/Presupuestos/lista.ts
export function filtrarPresupuestos(lista: PresupuestoResumido[], texto: string): PresupuestoResumido[]
// components/Presupuestos/BotonPdf.tsx — el «PDF» del inicio, sacado a un componente: baja el PDF y muestra su error
export default function BotonPdf({ presupuesto }: { presupuesto: PresupuestoResumido }): JSX.Element
```

**Lo que muestra** (diseño §5.4):
- **Arriba:** «Presupuestos» y un buscador, «Buscar por código, cliente o trabajo», como el de Trabajos.
- **La lista**, en el orden en que llega. Cada renglón lleva:
  - el código;
  - el cliente y el trabajo, o «sin trabajo»;
  - la fecha con `fechaDeTarjeta` (hora de Argentina);
  - el total con `mostrarImporte`, o «Sin total todavía»;
  - el estado en minúsculas;
  - con `por_debajo > 0`, en `text-bronze`, «1 por debajo del sugerido» o «N por debajo del sugerido».
- **Acciones:** el renglón abre `rutaDelPresupuesto(presupuesto)`; sin trabajo no es enlace. Al costado, `BotonPdf`.
- **Vacía:** «Todavía no hay presupuestos. Se arman en el Costeo de cada trabajo.» Sin coincidencias: «Ningún presupuesto coincide con la búsqueda.».
- **La barra:** «Presupuestos» con `NavLink to="/presupuestos"`; ya no queda nada apagado.
- **El inicio:** «Últimos presupuestos» usa `BotonPdf`, muestra la misma marca de «por debajo del sugerido» y suma, abajo, el enlace «Ver todos».
- **`filtrarPresupuestos`:** con `coincideConLaBusqueda` (sin mayúsculas ni tildes), sobre el código, el cliente y el trabajo. Con el texto vacío devuelve la lista tal cual.

- [ ] **Paso 1: Escribir las pruebas que fallan** de `filtrarPresupuestos`: por código, por cliente con y sin tilde, por trabajo, uno sin trabajo no rompe, y el texto vacío.
- [ ] **Paso 2: Correrlas y ver que fallan.**
- [ ] **Paso 3: Escribir los componentes y los cambios.**
- [ ] **Paso 4: `npx vitest run` y `npx tsc --noEmit`.**
- [ ] **Paso 5: Mirarla en Chrome sobre la copia `a19`:**
  - la barra lleva a Presupuestos;
  - la lista marca el presupuesto de la tarea 5;
  - buscar por el cliente con y sin tilde;
  - abrir uno lleva a su Costeo con ese presupuesto elegido;
  - «PDF» lo baja, y el PDF no tiene ni «Sugerido» ni «Ganancia»;
  - un presupuesto de un trabajo borrado en la copia sale «sin trabajo» y baja su PDF;
  - el inicio tiene «Ver todos».
  
  Capturas.
- [ ] **Paso 6: Commit** — `feat(presupuestos): la pantalla con la lista de todos (A19, tarea 6)`

**Pausa: fin del tramo 2.** Mostrarle a Enzo las capturas.

---

## Tramo 3 — El cierre

### Tarea 7: El recorrido y el cierre

- [ ] **Paso 1: La suite entera.** Servidor (con los temporales en D:), pantalla (`npx vitest run`) y `npx tsc --noEmit`.
- [ ] **Paso 2: El recorrido completo** de §7 del diseño sobre una copia nueva (`copiar_base.py a19 --desde local/tmp-a17/a18-t11`). Capturas en `local/herramientas-a19/`.
- [ ] **Paso 3: La revisión de toda la rama**, con el ok de Enzo. Se arregla lo importante, con su prueba.
- [ ] **Paso 4: Los documentos.**
  - El diseño, con su estado y una sección «Cómo quedó».
  - El `PLAN-MAESTRO.md §7`: la fila 7 y «Lo grande», con Presupuestos hecho.
  - El `README.md`, en «En qué estamos».
  - En el `REGISTRO.md`, la fuente de `PAR-61` y `P-36` pasa de `plan/` a `historico/`.
  - La carpeta pasa a `docs/historico/A19-presupuestos-y-precio-sugerido/`, y los comentarios del código que la nombran, también.
- [ ] **Paso 5: Con el ok de Enzo, fusionar en `main` y subir.** Al arrancar el servidor, la base real se pone al día sola, con respaldo (A17). Los presupuestos que ya tenga toman el multiplicador cuando se les recalculan los materiales.

---

## Desvíos

Lo que se decidió al construir y el plan no decía:
- **Tarea 1.** Una medida sin código tampoco tiene multiplicador. La migración usa `batch_alter_table`, porque SQLite no saca columnas sin él.
- **Tarea 3.**
  - Sin ninguna línea en la cuenta (un presupuesto vacío, o con todas sin costo o en otra moneda) no hay precios ni aviso del margen, haya o no margen general. Antes, con margen general daba $ 0 y sin él avisaba el margen.
  - Cambian a esa regla `test_el_desglose_dice_que_le_falta_al_presupuesto` y la prueba de los totales sin líneas, y al aviso por línea las que miraban «Falta cargar el margen…».
- **Tarea 4.** La prueba que comparaba el renglón del presupuesto de una tarjeta campo por campo suma los dos campos nuevos: las tarjetas usan la misma función.
- **Tarea 5.** «Por debajo del sugerido: −N %» va debajo del importe en «En el presupuesto», y el renglón entero se pinta de amarillo.
- **Tarea 6.**
  - `BotonPdf` le pasa su error a quien lo usa (`alFallar`): el inicio lo muestra debajo de la lista, como antes, y la lista nueva arriba.
  - El renglón de un presupuesto se sacó a `FilaDePresupuesto`, compartido por los dos.
  - Borrar un trabajo también refresca la lista.
- **El cierre.** La revisión de la rama la hizo el mismo que escribió el código, sin un revisor aparte. No encontró nada crítico ni importante; lo chico quedó en §10 del diseño.
