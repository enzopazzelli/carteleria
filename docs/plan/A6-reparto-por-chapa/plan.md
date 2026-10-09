# A6 · Reparto por chapa — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado:** escrito el 2026-10-08. **Sin empezar.** La Tarea 0 (hablarlo con Vale) frena todo lo demás. El 2026-10-09 se midió con 180 y 240 s (§2 del diseño) y Enzo decidió subir `PAR-09`: es la Tarea 5 bis, agregada ese día.
>
> **El código de este plan está probado.** El 2026-10-08 los bloques de las Tareas 1 a 4 y el script de la Tarea 6 se aplicaron, tal como están escritos acá, sobre una copia del backend fuera del repositorio. Cada test falló y pasó donde el plan dice, las dos roturas a propósito de la Tarea 3 hicieron fallar los tests que corresponden, y la suite completa dio 405 en verde (388 antes). La Tarea 5 (pantalla) no se probó. La medición de punta a punta está en el §2 del diseño.

**Goal:** Que el anidado con Sparrow, después de cortar la franja en chapas, intente vaciar las chapas a medio llenar repartiendo sus piezas en las demás, dentro del mismo tiempo máximo.

**Architecture:** La lógica de vaciar es un módulo nuevo y puro (`sparrow_reparto.py`) que no conoce a Sparrow: recibe una función que responde si un conjunto de piezas entra en una chapa. El worker (`sparrow_worker.py`) se reordena para exponer la búsqueda que hoy hace adentro de `resolver_una_pasada`, arma esa función con Sparrow y llama a la etapa nueva con el tiempo que sobra. Una opción `vaciar_chapas` la prende o la apaga desde la API y las dos pantallas.

**Tech Stack:** Python 3.11+, shapely 2.1, spyrrow 0.9, FastAPI, pytest · React 18, TypeScript, Vite.

**Spec:** [`diseno.md`](diseno.md), en esta misma carpeta.

## Global Constraints

- Rama `feat/reparto-por-chapa`, que sale de `main`. Al final se abre un PR contra `main` con **review pedido a Vale** (`CONVENCIONES.md §3`: es código de su carril).
- Commits **sin** la línea `Co-Authored-By` (regla del proyecto).
- El CI corre con Python 3.11: nada que exista solo en 3.12 o 3.13. Los módulos nuevos empiezan con `from __future__ import annotations`.
- Valores de negocio por ID de `REGISTRO.md`, nunca copiados. El tiempo máximo es `PAR-09`; este plan no agrega parámetros, y a ese le cambia el valor (Tarea 5 bis).
- `sparrow_worker.py` y `test_sparrow.py` están escritos en un estilo compacto. Lo que se agrega ahí sigue ese estilo; el módulo nuevo sigue el del resto del backend.
- **Sparrow corta por tiempo y su resultado depende de la carga de la máquina.** Ninguna prueba automática compara cantidades de chapas de una corrida real, salvo en casos triviales (cuadrados que entran de a cuatro).
- En Windows, **no editar con `sed -i`**: pasa los archivos de CRLF a LF. Editar con el editor.
- Probar siempre contra una **copia** de la base (`CARTELERIA_DATOS`), nunca contra `backend/local/`.
- Comandos de prueba: backend `cd backend && python -m pytest -q`; frontend `cd frontend && npm run build && npm test`.

## Review Focus

1. **El tiempo se acaba en medio de un intento de vaciar.** Las piezas que ya se habían movido de esa chapa no pueden quedar movidas: o se vacía entera o queda como estaba. Test en la Tarea 1 y en la Tarea 3.
2. **Sparrow devuelve posiciones que no validan, o falla.** El anidado de la primera etapa, que ya estaba guardado, tiene que sobrevivir. Test en la Tarea 3.
3. **Una pieza con cantidad mayor que 1** viaja como `"7#0"`, `"7#1"`: cada unidad se reparte por separado. Test en la Tarea 1.
4. **Un anidado que ya usa una sola chapa, o que ya llegó a la cota mínima por área,** no hace ninguna consulta. Test en la Tarea 1; la cota la corta `resolver` antes de entrar.
5. **Una ejecución guardada antes de este cambio** no tiene la opción en sus `opciones`. Tiene que poder volver a leerse y usar el valor por defecto. Lo cubren los valores por defecto de `OpcionesSparrow` y `AnidarCrear` (Tareas 3 y 4).

---

## Archivos

| Archivo | Qué hace |
|---|---|
| `backend/app/services/nesting/sparrow_reparto.py` | **Nuevo.** La lógica de vaciar chapas, sin Sparrow |
| `backend/tests/services/nesting/test_sparrow_reparto.py` | **Nuevo.** Sus tests, con una cuenta simple en lugar de Sparrow |
| `backend/app/services/nesting/sparrow_worker.py` | Expone `formas`, `franja`, `colocacion` y `entra_en_una_chapa`; `resolver` llama a la etapa nueva |
| `backend/app/services/nesting/sparrow.py` | `OpcionesSparrow.vaciar_chapas` |
| `backend/tests/services/nesting/test_sparrow.py` | Tests del worker con Sparrow real, en casos chicos |
| `backend/app/api/esquemas_nesting.py` | `AnidarCrear.vaciar_chapas` |
| `backend/tests/api/test_rutas_nesting.py` | Que la opción llega y se guarda |
| `frontend/src/api/nesting.ts` | El campo en `OpcionesAnidado` |
| `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx` | La casilla y el texto de ayuda |
| `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx` | La casilla en la comparación de formatos |
| `backend/scripts/medir_sparrow_de_un_grupo.py` | **Nuevo.** La medición del criterio de éxito |
| `docs/INCORPORACION-SPARROW-Y-COMPARACION-RECTANGULAR.md` | La etapa y la opción nuevas |
| `docs/REGISTRO.md` | El valor nuevo de `PAR-09` (Tarea 5 bis) |

---

### Task 0: Hablarlo con Vale y abrir la rama

**Files:** ninguno.

- [ ] **Step 1: Mandarle a Vale el diseño y las tres preguntas**

Mensaje, con el enlace a `docs/plan/A6-reparto-por-chapa/diseno.md`:

```
Vale: medí el anidado de Complejo con Sparrow. Más pasadas o más tiempo no bajan de 6 chapas;
repartiendo de otra manera da 5. Antes de tocar nada necesito saber:
1. ¿Tenés algún cambio en curso sobre sparrow_worker.py?
2. ¿Lo hacés vos o lo tomo yo, como el seccionado?
3. ¿Ya probaste repartir de otra forma y lo descartaste por algo?
El diseño y las mediciones están en docs/plan/A6-reparto-por-chapa/diseno.md.
```

No seguir hasta tener su respuesta. Si la construye ella, este plan es suyo; si aparece algo que cambia el diseño, se corrige `diseno.md` antes de la Tarea 1.

- [ ] **Step 2: Abrir la rama desde `main` al día**

```bash
git checkout main
git pull --rebase origin main
git checkout -b feat/reparto-por-chapa
```

- [ ] **Step 3: Confirmar que la base está en verde**

Run: `cd backend && python -m pytest -q`
Expected: todas pasan. Anotar la cantidad: las tareas siguientes suman tests sobre ese número.

---

### Task 1: La lógica de vaciar chapas

**Files:**
- Create: `backend/app/services/nesting/sparrow_reparto.py`
- Test: `backend/tests/services/nesting/test_sparrow_reparto.py`

**Interfaces:**
- Consumes: nada de otras tareas.
- Produces: `vaciar_chapas(chapas, area, area_util, entra_en_una_chapa, hay_tiempo)`, un generador.
  - `chapas: list[list[dict]]`: una lista por chapa, con sus colocaciones `{"id", "rotation", "tx", "ty"}` (sin `sheet`).
  - `area: Callable[[str], float]`: el área de la silueta de búsqueda de una pieza, por id.
  - `area_util: float`: el área donde entran esas siluetas en una chapa.
  - `entra_en_una_chapa: Callable[[list[str]], list[dict] | None]`: las colocaciones de ese conjunto en una chapa, o `None`.
  - `hay_tiempo: Callable[[], bool]`: se consulta antes de cada pregunta.
  - Entrega (`yield`) cada reparto con una chapa menos, con la misma forma que `chapas`.

- [ ] **Step 1: Escribir los tests**

`backend/tests/services/nesting/test_sparrow_reparto.py`:

```python
"""Vaciar chapas (`docs/plan/A6-reparto-por-chapa/`), sin Sparrow: quien
dice si un conjunto entra en una chapa es una cuenta de una dimensión."""
from __future__ import annotations

from app.services.nesting.sparrow_reparto import vaciar_chapas

_CAPACIDAD = 100.0


def _pieza(id_: str) -> dict:
    return {"id": id_, "rotation": 0, "tx": 0.0, "ty": 0.0}


def _chapas(*grupos: str) -> list[list[dict]]:
    """`_chapas("a", "bc")` son dos chapas: una con la pieza a y otra con
    b y c."""
    return [[_pieza(id_) for id_ in grupo] for grupo in grupos]


class _Barras:
    """Piezas de una sola dimensión: un conjunto entra en una chapa si sus
    largos suman a lo sumo `_CAPACIDAD`. Anota cada consulta que recibe."""

    def __init__(self, **largos: float):
        self.largos = largos
        self.consultas: list[frozenset[str]] = []

    def area(self, id_: str) -> float:
        return self.largos[id_]

    def entra(self, ids: list[str]) -> list[dict] | None:
        self.consultas.append(frozenset(ids))
        if sum(self.largos[id_] for id_ in ids) > _CAPACIDAD:
            return None
        return [_pieza(id_) for id_ in ids]


def _repartos(chapas, barras, hay_tiempo=lambda: True) -> list[list[str]]:
    """Cada reparto que entrega `vaciar_chapas`, como chapas ordenadas:
    `["ab", "c"]` es una chapa con a y b y otra con c."""
    return [
        sorted("".join(sorted(q["id"] for q in chapa)) for chapa in reparto)
        for reparto in vaciar_chapas(chapas, barras.area, _CAPACIDAD, barras.entra, hay_tiempo)
    ]


def test_vacia_la_chapa_menos_ocupada_repartiendo_sus_piezas():
    barras = _Barras(a=60, b=30, c=30)

    assert _repartos(_chapas("a", "b", "c"), barras) == [["a", "bc"]]


def test_no_consulta_por_un_conjunto_que_no_entra_ni_por_area():
    barras = _Barras(a=60, b=30, c=30)

    _repartos(_chapas("a", "b", "c"), barras)

    # b va con c; después a no entra con b y c (120), y eso se sabe sin
    # preguntar. La única otra consulta es c con a, al intentar vaciar "bc".
    assert barras.consultas == [frozenset("bc"), frozenset("ac")]


def test_sigue_vaciando_mientras_haya_una_chapa_que_se_pueda():
    barras = _Barras(a=25, b=25, c=25, d=25)

    assert _repartos(_chapas("a", "b", "c", "d"), barras) == [["ab", "c", "d"], ["ab", "cd"], ["abcd"]]


def test_una_chapa_que_no_se_vacia_entera_queda_como_estaba():
    """b entra con a (90), pero c ya no (110): la chapa "bc" no se vacía,
    y b no puede quedar mudada."""
    barras = _Barras(a=70, b=20, c=20)
    chapas = _chapas("a", "bc")

    assert _repartos(chapas, barras) == []
    assert chapas == _chapas("a", "bc")


def test_sin_tiempo_deja_de_consultar_y_descarta_lo_que_estaba_a_medias():
    """Alcanza para tres consultas. La tercera muda b a la chapa "cd"; a se
    queda sin consulta, así que ese reparto a medias no se entrega."""
    barras = _Barras(a=25, b=25, c=25, d=25)

    repartos = _repartos(_chapas("a", "b", "c", "d"), barras, hay_tiempo=lambda: len(barras.consultas) < 3)

    assert repartos == [["ab", "c", "d"], ["ab", "cd"]]
    assert len(barras.consultas) == 3


def test_con_una_sola_chapa_no_consulta_nada():
    barras = _Barras(a=40, b=40)

    assert _repartos(_chapas("ab"), barras) == []
    assert barras.consultas == []


def test_cada_unidad_de_una_pieza_se_reparte_por_separado():
    largos = {"7#0": 50.0, "7#1": 50.0}
    consultas: list[list[str]] = []

    def entra(ids: list[str]) -> list[dict] | None:
        consultas.append(ids)
        return [_pieza(id_) for id_ in ids]

    repartos = list(vaciar_chapas([[_pieza("7#0")], [_pieza("7#1")]], largos.__getitem__, _CAPACIDAD, entra, lambda: True))

    assert [[sorted(q["id"] for q in chapa) for chapa in reparto] for reparto in repartos] == [[["7#0", "7#1"]]]
```

- [ ] **Step 2: Correrlos y verlos fallar**

Run: `cd backend && python -m pytest -q tests/services/nesting/test_sparrow_reparto.py`
Expected: FAIL al importar, con `ModuleNotFoundError: No module named 'app.services.nesting.sparrow_reparto'`.

- [ ] **Step 3: Escribir el módulo**

`backend/app/services/nesting/sparrow_reparto.py`:

```python
"""Segunda etapa del anidado con Sparrow: vaciar chapas.

Sparrow acomoda las piezas en una franja larga, y `sparrow_worker` la
corta en chapas: recorta una ventana del ancho de una chapa, se queda con
las piezas que cayeron enteras y recalcula el resto. Las últimas chapas
quedan a medio llenar. Esta etapa parte de ese resultado y trata de
vaciar una chapa repartiendo sus piezas en las demás, de a una,
preguntando cada vez si «las piezas de esa chapa, más esta» entran en una
sola chapa.

Es lógica pura: no conoce a Sparrow. La pregunta la responde
`entra_en_una_chapa`, que el worker arma con Sparrow y los tests con una
cuenta simple. Mediciones y diseño: `docs/plan/A6-reparto-por-chapa/`.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator

#: Las colocaciones de una chapa: `{"id", "rotation", "tx", "ty"}`, sin `sheet`.
Chapa = list[dict]


def vaciar_chapas(
    chapas: list[Chapa],
    area: Callable[[str], float],
    area_util: float,
    entra_en_una_chapa: Callable[[list[str]], Chapa | None],
    hay_tiempo: Callable[[], bool],
) -> Iterator[list[Chapa]]:
    """Entrega cada reparto que usa una chapa menos que el anterior, a
    medida que aparece. No modifica `chapas`. Termina cuando ninguna chapa
    se puede vaciar o cuando `hay_tiempo()` dice que no.

    Se intenta primero con la chapa que menos área de piezas tiene, que es
    la más barata de vaciar. Sus piezas van de mayor a menor, cada una a
    la chapa menos ocupada que la acepte. Si una pieza no entra en
    ninguna, esa chapa queda como estaba y no se vuelve a intentar: las
    demás solo pueden llenarse más.

    Un `None` de `entra_en_una_chapa` no prueba que el conjunto no entre
    (Sparrow corta por tiempo). El costo de un «no» equivocado es una
    chapa que no se vació."""
    actuales = [list(chapa) for chapa in chapas]
    sin_salida: set[frozenset[str]] = set()

    def ocupado(chapa: Chapa) -> float:
        return sum(area(q["id"]) for q in chapa)

    def ids(chapa: Chapa) -> frozenset[str]:
        return frozenset(q["id"] for q in chapa)

    while len(actuales) > 1:
        donantes = [chapa for chapa in sorted(actuales, key=ocupado) if ids(chapa) not in sin_salida]
        if not donantes:
            return
        donante = donantes[0]
        # Copia de la lista, no de las chapas: una chapa que recibe se
        # reemplaza en `resto`, y `actuales` no cambia hasta que la
        # donante se vació entera.
        resto = [chapa for chapa in actuales if chapa is not donante]
        for pieza in sorted((q["id"] for q in donante), key=area, reverse=True):
            recibida = False
            for indice in sorted(range(len(resto)), key=lambda i: ocupado(resto[i])):
                if ocupado(resto[indice]) + area(pieza) > area_util:
                    continue
                if not hay_tiempo():
                    return
                nueva = entra_en_una_chapa([*(q["id"] for q in resto[indice]), pieza])
                if nueva is not None:
                    resto[indice] = nueva
                    recibida = True
                    break
            if not recibida:
                sin_salida.add(ids(donante))
                break
        else:
            actuales = resto
            yield [list(chapa) for chapa in actuales]
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run: `cd backend && python -m pytest -q tests/services/nesting/test_sparrow_reparto.py`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nesting/sparrow_reparto.py backend/tests/services/nesting/test_sparrow_reparto.py
git commit -m "feat(nesting): vaciar chapas repartiendo sus piezas en las demas"
```

---

### Task 2: El worker expone la búsqueda y responde «¿entra en una chapa?»

**Files:**
- Modify: `backend/app/services/nesting/sparrow_worker.py` (desde el comienzo hasta el final de `resolver_una_pasada`)
- Test: `backend/tests/services/nesting/test_sparrow.py`

**Interfaces:**
- Consumes: nada de otras tareas.
- Produces, en `sparrow_worker`:
  - `formas(data) -> tuple[dict, dict]`: `(originales, de_busqueda)`, los dos por id de pieza.
  - `franja(ids, originales, de_busqueda, data) -> list[tuple]`: una búsqueda de Sparrow; cada elemento es `(colocación de Sparrow, material real ya ubicado)`.
  - `colocacion(pi, izquierda, data) -> dict`: `{"id", "rotation", "tx", "ty"}`.
  - `entra_en_una_chapa(ids, originales, de_busqueda, data) -> list[dict] | None`.
  - `resolver_una_pasada(data)` sigue devolviendo lo mismo que hoy.

- [ ] **Step 1: Escribir los tests**

Agregar al final de `backend/tests/services/nesting/test_sparrow.py`:

```python
from app.services.nesting import sparrow_worker


def entrada_de_cuadrados(cantidad,lado=40,**opciones):
    """`cantidad` cuadrados iguales para una chapa de 100 x 100 con kerf 2:
    de 40 entran cuatro por chapa; de 60, uno."""
    piezas=[Pieza('1',D(lado),D(lado),cantidad)]
    g={'1':GeometriaPieza(D(lado),D(lado),[(D(0),D(0)),(D(lado),D(0)),(D(lado),D(lado)),(D(0),D(lado))])}
    params=ParametrosCorte(D(2),D(0),D(0),RotacionPermitida.LIBRE_0_90)
    return preparar_entrada(piezas,g,Plancha(D(100),D(100)),params,OpcionesSparrow(segundos_por_busqueda=1,simplificacion_mm=0,**opciones))


def test_entra_en_una_chapa_devuelve_posiciones_que_validan():
    entrada=entrada_de_cuadrados(4)
    originales,de_busqueda=sparrow_worker.formas(entrada)
    colocadas=sparrow_worker.entra_en_una_chapa(['1#0','1#1','1#2','1#3'],originales,de_busqueda,entrada)
    assert colocadas is not None
    result=convertir_y_validar(entrada,[{**q,'sheet':0} for q in colocadas])
    assert result.planchas_usadas==1
    assert len(result.posiciones)==4


def test_entra_en_una_chapa_dice_que_no_si_no_caben():
    entrada=entrada_de_cuadrados(2,lado=60)
    originales,de_busqueda=sparrow_worker.formas(entrada)
    assert sparrow_worker.entra_en_una_chapa(['1#0','1#1'],originales,de_busqueda,entrada) is None
```

- [ ] **Step 2: Correrlos y verlos fallar**

Run: `cd backend && python -m pytest -q tests/services/nesting/test_sparrow.py -k entra_en_una_chapa`
Expected: 2 FAIL con `AttributeError: module 'app.services.nesting.sparrow_worker' has no attribute 'formas'`.

- [ ] **Step 3: Reordenar el worker**

En `backend/app/services/nesting/sparrow_worker.py`, reemplazar la función `resolver_una_pasada` entera por estas cinco. `puntaje`, `resolver` y el bloque `if __name__=='__main__'` quedan como están.

```python
def formas(data):
    """`(originales, de_busqueda)` por id: el material real de cada pieza,
    con el que se coloca y se valida, y la silueta con la que busca Sparrow."""
    opts=data['options'];width,height=data['width'],data['height']
    reserva=data['gap']/2
    originals={p['id']:poligono_material(p['shell'],p['holes']) for p in data['items']}
    shapes={}
    for p in data['items']:
        shell=Polygon(p['shell']);tol=opts['simplificacion_mm']
        candidate=shell.buffer(tol).simplify(tol,preserve_topology=True) if tol else shell
        fits=False
        for a in data['rotations']:
            b=affinity.rotate(candidate,a,origin=(0,0)).bounds
            fits |= b[2]-b[0]<=width+1e-8 and b[3]-b[1]<=height+1e-8
        shape=candidate if candidate.geom_type=='Polygon' and candidate.covers(shell) and fits else shell
        # La operación nativa de offset falla con algunos contornos muy
        # pequeños. Reservar aquí medio gap por lado es equivalente y
        # conservador; los contornos originales se validan al terminar.
        shapes[p['id']]=shape.buffer(reserva,join_style=2) if reserva else shape
    return originals,shapes

def franja(ids,originals,shapes,data):
    """Una búsqueda de Sparrow con esas piezas, en una franja del alto de la
    chapa: `[(colocación de Sparrow, material real ya ubicado)]`."""
    import spyrrow
    opts=data['options'];reserva=data['gap']/2
    items=[spyrrow.Item(k,list(shapes[k].exterior.coords),1,data['rotations']) for k in ids]
    config=spyrrow.StripPackingConfig(total_computation_time=opts['segundos_por_busqueda'],num_workers=opts['workers'],seed=opts['semilla'],early_termination=False,min_items_separation=None)
    sol=spyrrow.StripPackingInstance('Carteleria',data['height']+2*reserva+0.001,items).solve(config)
    return [(pi,affinity.translate(affinity.rotate(originals[pi.id],pi.rotation,origin=(0,0)),pi.translation[0],pi.translation[1]-reserva)) for pi in sol.placed_items]

def colocacion(pi,izquierda,data):
    """Dónde queda una pieza en su chapa, tomando `izquierda` (medido en la
    franja) como el borde útil de la chapa."""
    return {'id':pi.id,'rotation':pi.rotation,'tx':pi.translation[0]-izquierda+data['borde'],'ty':pi.translation[1]-data['gap']/2+data['borde']}

def entra_en_una_chapa(ids,originals,shapes,data):
    """Las colocaciones si esas piezas entran juntas en una chapa, o `None`.
    Un `None` no prueba que no entren: Sparrow no lo encontró en
    `segundos_por_busqueda`."""
    parts=franja(ids,originals,shapes,data)
    izquierda=min(g.bounds[0] for _,g in parts)
    if max(g.bounds[2] for _,g in parts)-izquierda>data['width']+0.001:return None
    return [colocacion(pi,izquierda,data) for pi,_ in parts]

def resolver_una_pasada(data):
    width=data['width']
    originals,shapes=formas(data)
    pending=list(shapes);placed=[];sheet=0
    while pending:
        parts=franja(pending,originals,shapes,data)
        bounds=[g.bounds for _,g in parts]
        best=[];offset=0;score=(-1,-1)
        for x in [b[0] for b in bounds]:
            group=[(pi,g) for (pi,g),b in zip(parts,bounds) if b[0]>=x-0.001 and b[2]<=x+width+0.001]
            value=(sum(g.area for _,g in group),len(group))
            if value>score:best=group;offset=x;score=value
        if not best:raise ValueError('No hay piezas completas que entren en una chapa.')
        for pi,g in best:placed.append({**colocacion(pi,offset,data),'sheet':sheet})
        selected={pi.id for pi,_ in best};pending=[k for k in pending if k not in selected];sheet+=1
    return placed
```

Es el mismo cálculo de antes, repartido en funciones: `formas` es el bloque que armaba `originals` y `shapes`, `franja` es la llamada a Sparrow, y `colocacion` es el diccionario que se agregaba a `placed`.

- [ ] **Step 4: Correr los tests del worker y de las rutas que usan Sparrow**

Run: `cd backend && python -m pytest -q tests/services/nesting/test_sparrow.py tests/api/test_rutas_nesting.py`
Expected: todos pasan, incluidos los 2 nuevos. Los que ya existían prueban que `resolver_una_pasada` sigue dando lo mismo.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nesting/sparrow_worker.py backend/tests/services/nesting/test_sparrow.py
git commit -m "refactor(nesting): exponer la busqueda de Sparrow y la consulta de una chapa"
```

---

### Task 3: El worker vacía chapas con el tiempo que sobra

**Files:**
- Modify: `backend/app/services/nesting/sparrow_worker.py` (función `resolver`, y una función nueva antes de ella)
- Modify: `backend/app/services/nesting/sparrow.py` (clase `OpcionesSparrow`)
- Test: `backend/tests/services/nesting/test_sparrow.py`

**Interfaces:**
- Consumes: `vaciar_chapas` (Tarea 1); `formas`, `entra_en_una_chapa` y `entrada_de_cuadrados` (Tarea 2).
- Produces: `OpcionesSparrow.vaciar_chapas: bool = True`, que llega al worker como `data['options']['vaciar_chapas']`. `resolver(data, salida=None)` sigue devolviendo la lista de colocaciones con `sheet`.

- [ ] **Step 1: Escribir los tests**

Agregar al final de `backend/tests/services/nesting/test_sparrow.py`:

```python
def una_por_chapa(data):
    """Un punto de partida malo a propósito: cada pieza sola en su chapa."""
    return [{'id':p['id'],'sheet':n,'rotation':0,'tx':data['borde'],'ty':data['borde']} for n,p in enumerate(data['items'])]

def chapas_usadas(colocadas):
    return len({q['sheet'] for q in colocadas})


def test_resolver_vacia_las_chapas_que_dejo_la_primera_etapa(monkeypatch):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    colocadas=sparrow_worker.resolver(entrada)
    assert convertir_y_validar(entrada,colocadas).planchas_usadas==1


def test_resolver_con_la_etapa_apagada_devuelve_la_primera(monkeypatch):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60,vaciar_chapas=False)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    assert chapas_usadas(sparrow_worker.resolver(entrada))==4


def test_resolver_sin_tiempo_para_consultar_devuelve_la_primera(monkeypatch):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=1)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    assert chapas_usadas(sparrow_worker.resolver(entrada))==4


def encimadas(ids,originals,shapes,data):
    """Todas las piezas en el mismo lugar: no valida."""
    return [{'id':k,'rotation':0,'tx':data['borde'],'ty':data['borde']} for k in ids]

def rota(ids,originals,shapes,data):
    raise RuntimeError('falla de prueba')

@pytest.mark.parametrize('consulta',[encimadas,rota])
def test_un_reparto_que_falla_no_pierde_la_primera_etapa(monkeypatch,consulta):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    monkeypatch.setattr(sparrow_worker,'entra_en_una_chapa',consulta)
    colocadas=sparrow_worker.resolver(entrada)
    assert chapas_usadas(colocadas)==4
    convertir_y_validar(entrada,colocadas)
```

`resolver_una_pasada` se reemplaza para controlar el punto de partida. Lo que se comprueba es la etapa nueva con Sparrow real y con la validación real.

- [ ] **Step 2: Correrlos y ver cuáles fallan**

Run: `cd backend && python -m pytest -q tests/services/nesting/test_sparrow.py -k "resolver or reparto_que_falla"`
Expected:
- `test_resolver_vacia_las_chapas_que_dejo_la_primera_etapa`: FAIL, da 4 chapas y se espera 1.
- `test_resolver_con_la_etapa_apagada_devuelve_la_primera`: FAIL con `TypeError: OpcionesSparrow.__init__() got an unexpected keyword argument 'vaciar_chapas'`.
- Los otros tres **pasan**: todavía no hay etapa que pueda romperlos. Se comprueban en el Step 5.

- [ ] **Step 3: Sumar la opción**

En `backend/app/services/nesting/sparrow.py`, en `OpcionesSparrow`, después de `intentos: int = 3`:

```python
    intentos: int = 3
    #: Segunda etapa (`sparrow_reparto.py`): vaciar chapas repartiendo sus
    #: piezas en las demás, con el tiempo que sobra de `tiempo_maximo_s`.
    vaciar_chapas: bool = True
```

- [ ] **Step 4: Llamar a la etapa desde `resolver`**

En `backend/app/services/nesting/sparrow_worker.py`, reemplazar la función `resolver` entera por estas dos:

```python
def por_chapa(placed):
    """Las colocaciones agrupadas por chapa y sin `sheet`, como las recibe
    `vaciar_chapas`."""
    chapas={}
    for q in placed:chapas.setdefault(q['sheet'],[]).append({k:v for k,v in q.items() if k!='sheet'})
    return [chapas[s] for s in sorted(chapas)]

def resolver(data, salida=None):
    from .sparrow import convertir_y_validar
    from .sparrow_reparto import vaciar_chapas
    opts=data['options']
    inicio=time.monotonic(); best=None; score=None; duracion=0
    limite=inicio+opts['tiempo_maximo_s']-1
    # Cota física por área exterior: Sparrow reserva las siluetas completas.
    area=sum(Polygon(p['shell']).area for p in data['items'])
    minimo=max(1,math.ceil(area/(data['width']*data['height'])))
    def considerar(candidato):
        nonlocal best,score
        convertir_y_validar(data,candidato)  # Nunca guardar demanda parcial o colocaciones inválidas.
        rank=puntaje(candidato,data)
        if score is None or rank<score:
            best=candidato;score=rank
            if salida:
                temporal=salida.with_suffix('.tmp')
                temporal.write_text(json.dumps(best),encoding='utf8');temporal.replace(salida)
    for intento in range(opts.get('intentos',3)):
        # No empezar una pasada que no va a terminar antes del límite.
        if intento and time.monotonic()+duracion>=limite: break
        prueba={**data,'options':{**opts,'semilla':(opts['semilla']+104729*intento)%2147483648}}
        t0=time.monotonic();candidato=resolver_una_pasada(prueba);duracion=time.monotonic()-t0
        considerar(candidato)
        if score[0]==minimo: break
        if opts.get('vaciar_chapas',True):
            originals,shapes=formas(prueba);reserva=data['gap']/2
            try:
                for chapas in vaciar_chapas(
                    por_chapa(candidato),
                    lambda k:shapes[k].area,
                    (data['width']+2*reserva)*(data['height']+2*reserva),
                    lambda ids:entra_en_una_chapa(ids,originals,shapes,prueba),
                    lambda:time.monotonic()+opts['segundos_por_busqueda']<limite,
                ):
                    considerar([{**q,'sheet':s} for s,chapa in enumerate(chapas) for q in chapa])
                    if score[0]==minimo: break
            except Exception as error:
                # La etapa es una mejora: si falla o entrega algo que no
                # valida, vale el mejor resultado ya guardado.
                print('vaciar_chapas:',error,file=sys.stderr)
            if score[0]==minimo: break
    return best
```

Qué cambia respecto del `resolver` de hoy:

- La validación, el puntaje y la escritura atómica pasan a `considerar`, porque ahora se usan dos veces: después de la pasada y después de cada chapa vaciada.
- `limite` es el mismo corte de antes (`tiempo_maximo_s - 1`). La etapa deja de consultar cuando no queda tiempo para una búsqueda más.
- Antes, una pasada podía empezar un segundo antes del límite y la mataba el supervisor. Ahora no empieza si la anterior tardó más que lo que queda.

- [ ] **Step 5: Correr los tests y comprobar los tres que ya pasaban**

Run: `cd backend && python -m pytest -q tests/services/nesting/test_sparrow.py`
Expected: todos pasan.

Los tres tests que pasaban antes de escribir el código se comprueban rompiéndolo a propósito, de a uno, y deshaciendo cada cambio:

| Cambio temporal en `resolver` | Test que tiene que fallar |
|---|---|
| Reemplazar `lambda:time.monotonic()+opts['segundos_por_busqueda']<limite` por `lambda:True` | `test_resolver_sin_tiempo_para_consultar_devuelve_la_primera` |
| Reemplazar `except Exception as error:` por `except KeyboardInterrupt as error:` | `test_un_reparto_que_falla_no_pierde_la_primera_etapa`, en sus dos casos |

Después de deshacer los dos cambios, correr de nuevo y ver todo en verde.

- [ ] **Step 6: Correr toda la suite**

Run: `cd backend && python -m pytest -q`
Expected: todo en verde. Comparar el tiempo total con el de la Tarea 0: si creció más de unos 15 segundos, algún test que ya existía está entrando en la etapa nueva. Buscarlo con `--durations=10` y anotarlo en la sección «Desvíos» antes de seguir.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/nesting/sparrow_worker.py backend/app/services/nesting/sparrow.py backend/tests/services/nesting/test_sparrow.py
git commit -m "feat(nesting): Sparrow vacia chapas con el tiempo que sobra"
```

---

### Task 4: La opción en la API

**Files:**
- Modify: `backend/app/api/esquemas_nesting.py` (clase `AnidarCrear`)
- Test: `backend/tests/api/test_rutas_nesting.py`

**Interfaces:**
- Consumes: `OpcionesSparrow.vaciar_chapas` (Tarea 3).
- Produces: el campo `vaciar_chapas` (booleano, `true` por defecto) en el cuerpo de `POST /grupos/{id}/anidar` y de `POST /grupos/{id}/comparar-formatos`. Queda guardado en `EjecucionNesting.opciones`.

- [ ] **Step 1: Escribir los tests**

Agregar al final de `backend/tests/api/test_rutas_nesting.py`:

```python
@pytest.mark.parametrize("enviado, esperado", [({}, True), ({"vaciar_chapas": False}, False)])
def test_comparar_formatos_sparrow_pasa_la_opcion_de_vaciar_chapas(cliente, tmp_path, monkeypatch, enviado, esperado):
    from app.api import rutas_nesting
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    _material, formato = _material_con_formato_y_parametros(cliente)
    recibidas = []
    original = rutas_nesting.anidar_sparrow

    def registrar(piezas, geometrias, plancha, params, opciones):
        recibidas.append(opciones)
        return original(piezas, geometrias, plancha, params, opciones)

    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", registrar)
    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparar-formatos", json={
        "formato_ids": [formato["id"]], "motor": "sparrow",
        "segundos_por_busqueda": 1, "tiempo_maximo_s": 30, **enviado,
    })

    assert respuesta.status_code == 200, respuesta.text
    assert [o.vaciar_chapas for o in recibidas] == [esperado]


def test_sparrow_por_api_guarda_la_opcion_de_vaciar_chapas(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/anidar", json={
        "motor": "sparrow", "segundos_por_busqueda": 1, "tiempo_maximo_s": 20, "vaciar_chapas": False,
    })

    assert respuesta.status_code == 202
    resultado = _esperar_estado(cliente, respuesta.json()["id"], timeout=20)
    assert resultado["estado"] == "lista", resultado.get("error")
    assert resultado["opciones"].get("vaciar_chapas") is False
```

- [ ] **Step 2: Correrlos y verlos fallar**

Run: `cd backend && python -m pytest -q tests/api/test_rutas_nesting.py -k vaciar_chapas`
Expected: 2 FAIL y 1 pasa. Fallan el caso `{"vaciar_chapas": False}` de la comparación (llega `True`, porque la API todavía ignora el campo) y el de guardar la opción (`None is False`). El caso `{}` pasa: el valor por defecto ya viene de la Tarea 3.

- [ ] **Step 3: Sumar el campo**

En `backend/app/api/esquemas_nesting.py`, en `AnidarCrear`, después de `intentos`:

```python
    intentos: int = Field(default=3, ge=1, le=8)
    #: Segunda etapa de Sparrow (`sparrow_reparto.py`): vaciar chapas
    #: repartiendo sus piezas en las demás. Prendida por defecto; se apaga
    #: para comparar contra el reparto de antes o para terminar antes.
    vaciar_chapas: bool = True
```

`ComparacionFormatosCrear` hereda de `AnidarCrear`, así que la comparación lo recibe sin más cambios.

- [ ] **Step 4: Correr los tests**

Run: `cd backend && python -m pytest -q tests/api/test_rutas_nesting.py`
Expected: todos pasan.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/esquemas_nesting.py backend/tests/api/test_rutas_nesting.py
git commit -m "feat(nesting): opcion para apagar el vaciado de chapas desde la API"
```

---

### Task 5: La casilla en las dos pantallas

**Files:**
- Modify: `frontend/src/api/nesting.ts` (interfaz `OpcionesAnidado`)
- Modify: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`
- Modify: `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`

**Interfaces:**
- Consumes: el campo `vaciar_chapas` de la API (Tarea 4).
- Produces: nada que use otra tarea.

No lleva test automático: es una casilla que agrega un campo al pedido. Se comprueba con el compilador y a mano.

- [ ] **Step 1: El tipo**

En `frontend/src/api/nesting.ts`, en `OpcionesAnidado`, después de `simplificacion_mm`:

```ts
  simplificacion_mm?: number;
  vaciar_chapas?: boolean;
```

- [ ] **Step 2: Anidado**

En `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`:

Después de `const [simplificacion, setSimplificacion] = useState(0.3);`:

```tsx
  const [vaciarChapas, setVaciarChapas] = useState(true);
```

En `const opciones = { ... }`, sumar el campo al final:

```tsx
  const opciones = { motor, usar_anidado_en_huecos: usarHuecos, semilla,
    segundos_por_busqueda: busqueda, tiempo_maximo_s: limite, simplificacion_mm: simplificacion,
    vaciar_chapas: vaciarChapas };
```

Dentro de `{motor === "sparrow" && <>`, después de la etiqueta «Simplificación (mm)», y reemplazando el párrafo `<p>Prueba hasta 3 semillas ...</p>`:

```tsx
          <label
            className="flex items-center gap-1 cursor-pointer"
            title="Después de repartir en chapas, intenta vaciar las que quedaron a medio llenar pasando sus piezas a las demás. Usa el tiempo que sobra del máximo."
          >
            <input type="checkbox" checked={vaciarChapas} onChange={(e) => setVaciarChapas(e.target.checked)} />
            Vaciar chapas
          </label>
          <p>Acomoda las piezas, las reparte en chapas y, si «Vaciar chapas» está marcado, usa el tiempo que sobra para vaciar las que quedaron a medio llenar. Conserva el anidado validado con menos planchas. Más búsqueda por chapa no da menos planchas. No se garantiza el óptimo global.</p>
```

- [ ] **Step 3: Comparación de formatos**

En `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`:

Después de `const [simplificacion, setSimplificacion] = useState(0.3);`:

```tsx
  const [vaciarChapas, setVaciarChapas] = useState(true);
```

En la llamada que arma `opciones: { motor, semilla, ... criterio: "material" }`, sumar `vaciar_chapas: vaciarChapas`:

```tsx
        opciones: { motor, semilla, segundos_por_busqueda: busqueda, tiempo_maximo_s: limite, simplificacion_mm: simplificacion, vaciar_chapas: vaciarChapas, criterio: "material" } });
```

Dentro de `{motor === "sparrow" && <>`, después de la etiqueta «Simplificación (mm)»:

```tsx
                  <label
                    className="flex items-center gap-1 cursor-pointer"
                    title="Intenta vaciar las chapas que quedaron a medio llenar. Cada formato usa su tiempo máximo entero."
                  >
                    <input type="checkbox" checked={vaciarChapas} onChange={(e) => setVaciarChapas(e.target.checked)} />
                    Vaciar chapas
                  </label>
```

- [ ] **Step 4: Compilar y correr los tests del frontend**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores de tipos y los tests existentes pasan.

- [ ] **Step 5: Verlo en la app, contra una copia de los datos**

Con los puertos 8000 y 5173 libres (si están ocupados, son los servidores de Enzo contra su base real: no usarlos ni cerrarlos):

```bash
# copiar backend/local/carteleria.db y backend/local/archivos/ a una carpeta de prueba
set CARTELERIA_DATOS=<carpeta de prueba>
cd backend && python -m uvicorn app.api.app:app --port 8000
cd frontend && npm run dev
```

Comprobar, en un grupo con Sparrow: la casilla aparece marcada en Anidado y en la comparación de Grupos; con la casilla desmarcada el anidado termina antes; el historial muestra las dos ejecuciones.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/nesting.ts frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx frontend/src/routes/TrabajoWorkspace/GruposTab.tsx
git commit -m "feat(nesting): casilla para vaciar chapas en Anidado y en la comparacion"
```

---

### Task 5 bis: Subir `PAR-09`

Agregada el 2026-10-09, después de medir con 180 y 240 s (§2 del diseño). El valor nuevo es el de la fila «Cuánto vale el tiempo máximo» del §4 del diseño. A diferencia de las Tareas 1 a 4, **esta no se probó sobre la copia**; ningún test de hoy depende del valor por defecto (todos pasan el suyo).

**Files:**
- Modify: `docs/REGISTRO.md` (fila de `PAR-09`)
- Modify: `backend/app/services/nesting/sparrow.py` (`OpcionesSparrow.tiempo_maximo_s`)
- Modify: `backend/app/api/esquemas_nesting.py` (`AnidarCrear.tiempo_maximo_s`, el valor por defecto; el tope que acepta no cambia)
- Modify: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx` y `GruposTab.tsx` (el valor inicial de `limite`)

- [ ] **Step 1: Cambiar el valor en los cuatro lugares del código**

Son los cuatro que hoy tienen el valor viejo. Comprobar que no quede otro:

```bash
grep -rn "tiempo_maximo_s" backend/app frontend/src
grep -n "setLimite" frontend/src/routes/TrabajoWorkspace/*.tsx
```

- [ ] **Step 2: Cambiar la fila de `PAR-09` en `docs/REGISTRO.md`**

Solo el valor. Sigue provisorio: salió de un solo trabajo en una sola máquina.

- [ ] **Step 3: Correr las pruebas**

Run: `cd backend && python -m pytest -q` y `cd frontend && npm run build && npm test`
Expected: todo en verde, con la misma cantidad de tests que al terminar la Tarea 5.

- [ ] **Step 4: Si `docs/cliente/GUIA-PARAMETROS-ANIDADO.md` ya está en `main`, corregir su tabla del §10**

Es el único lugar de esa guía donde figura el valor.

- [ ] **Step 5: Commit**

```bash
git add docs/REGISTRO.md backend/app/services/nesting/sparrow.py backend/app/api/esquemas_nesting.py frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx frontend/src/routes/TrabajoWorkspace/GruposTab.tsx
git commit -m "feat(nesting): PAR-09 sube para que la etapa de vaciar chapas llegue"
```

---

### Task 6: Medir el criterio de éxito y documentar

**Files:**
- Create: `backend/scripts/medir_sparrow_de_un_grupo.py`
- Modify: `docs/INCORPORACION-SPARROW-Y-COMPARACION-RECTANGULAR.md`
- Modify: `docs/BITACORA.md`, `docs/plan/PLAN-MAESTRO.md`, `docs/plan/A6-reparto-por-chapa/diseno.md`, este plan

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: los números que cierran el criterio de éxito del §1 del diseño.

- [ ] **Step 1: El script de medición**

`backend/scripts/medir_sparrow_de_un_grupo.py`:

```python
"""Anida con Sparrow un grupo ya cargado, varias veces, con y sin la etapa
de vaciar chapas, y muestra planchas, aprovechamiento y tiempo.

Es la medición del criterio de éxito de `docs/plan/A6-reparto-por-chapa/`.
Corre por el mismo camino que la app (`anidar_sparrow`: worker aparte,
tiempo máximo y validación) y no guarda nada.

**Usar siempre una copia de la base**, con la máquina libre:

    set CARTELERIA_DATOS=<carpeta con una copia de carteleria.db>
    python scripts/medir_sparrow_de_un_grupo.py --grupo 1 --corridas 3
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session  # noqa: E402

from app import config  # noqa: E402
from app.api.rutas_nesting import _datos_para_anidar, _geometrias_del_grupo  # noqa: E402
from app.modelos.base import crear_motor  # noqa: E402
from app.modelos.trabajo import GrupoDeCorte  # noqa: E402
from app.services.nesting.aprovechamiento import calcular_aprovechamiento  # noqa: E402
from app.services.nesting.sparrow import OpcionesSparrow, anidar_sparrow  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--grupo", type=int, required=True)
    parser.add_argument("--corridas", type=int, default=3)
    parser.add_argument("--segundos-por-busqueda", type=int, default=OpcionesSparrow.segundos_por_busqueda)
    parser.add_argument("--tiempo-maximo-s", type=int, default=OpcionesSparrow.tiempo_maximo_s)
    args = parser.parse_args()

    print(f"Datos: {config.DIRECTORIO_DATOS}")
    with Session(crear_motor()) as sesion:
        grupo = sesion.get(GrupoDeCorte, args.grupo)
        if grupo is None:
            sys.exit(f"No existe el grupo {args.grupo}.")
        plancha, params, piezas = _datos_para_anidar(sesion, grupo)
        geometrias = _geometrias_del_grupo(grupo)

    print(f"Grupo «{grupo.nombre}»: {sum(p.cantidad for p in piezas)} piezas, chapa {plancha.ancho_mm} x {plancha.alto_mm}")
    for vaciar in (False, True):
        for corrida in range(args.corridas):
            opciones = OpcionesSparrow(
                semilla=OpcionesSparrow.semilla + corrida,
                segundos_por_busqueda=args.segundos_por_busqueda,
                tiempo_maximo_s=args.tiempo_maximo_s,
                vaciar_chapas=vaciar,
            )
            inicio = time.monotonic()
            resultado = anidar_sparrow(piezas, geometrias, plancha, params, opciones)
            aprovechamiento = calcular_aprovechamiento(resultado, plancha, geometrias).porcentaje_aprovechamiento
            print(
                f"vaciar chapas: {'sí' if vaciar else 'no'} | corrida {corrida + 1} | "
                f"{resultado.planchas_usadas} planchas | {aprovechamiento:.1f} % | {time.monotonic() - inicio:.0f} s"
            )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Medir «Complejo», con la máquina libre**

Copiar `backend/local/carteleria.db` a una carpeta de prueba y correr:

```bash
set CARTELERIA_DATOS=<carpeta de prueba>
cd backend && python scripts/medir_sparrow_de_un_grupo.py --grupo 1 --corridas 3
```

Expected, según el §7 del diseño:
- Con «vaciar chapas: sí», **5 planchas o menos en al menos 2 de las 3 corridas**, dentro del tiempo máximo.
- Con «vaciar chapas: no», lo de hoy: 6 o 7 planchas.
- Ninguna corrida con «sí» da más planchas que la corrida de la misma semilla con «no».

Esta medición ya se repitió el 2026-10-09 con 180 y 240 s (§2 del diseño), y de ahí salió el valor nuevo de `PAR-09` (Tarea 5 bis). Si con ese valor no se llega a 5 en al menos 2 de las 3 corridas, **no seguir subiéndolo:** anotar a partir de cuánto llega y llevarle el número a Enzo.

- [ ] **Step 3: Medir un trabajo más grande**

Restaurar en la carpeta de prueba el respaldo `backend/local/respaldo-2026-10-08-antes-de-borrar-trabajos/` (ahí el trabajo 4 es `Muestra Vectores.dxf`), elegir un grupo de ese trabajo que anide con Sparrow y correr el mismo comando. Anotar planchas y tiempo con y sin la etapa. No tiene valor esperado: es para saber cómo se comporta con muchas piezas.

- [ ] **Step 4: Documentar Sparrow**

En `docs/INCORPORACION-SPARROW-Y-COMPARACION-RECTANGULAR.md`:

- En «Cómo se incorporó», después del punto 4 (la franja y la selección por plancha), agregar un punto:

```markdown
5. Con el tiempo que sobra del máximo, intenta **vaciar chapas**: elige la que tiene menos área de piezas y reparte sus piezas en las demás, de a una, preguntándole a Sparrow si «las piezas de esa chapa, más esta» entran en una sola chapa. Si todas encontraron lugar, hay una chapa menos; si alguna no, esa chapa queda como estaba. Se apaga con `vaciar_chapas`. Mediciones en [`plan/A6-reparto-por-chapa/diseno.md`](plan/A6-reparto-por-chapa/diseno.md).
```

  y renumerar los dos puntos que siguen (pasan a ser 6 y 7).

- En la tabla «Parámetros y validaciones», agregar la fila:

```markdown
| `vaciar_chapas` | sí | sí / no |
```

- Reemplazar la oración «Más tiempo puede mejorar la búsqueda, sin asegurar menos planchas.» por:

```markdown
Más segundos por búsqueda o más intentos no dan menos planchas (medido el 2026-10-08: 6 planchas con 3 intentos y con 8, y con 2, 10 y 30 segundos). Lo que baja planchas es la etapa de vaciar chapas.
```

Si este documento ya se movió a `docs/motor/`, hacer los cambios allá y corregir el enlace relativo del punto 5.

- [ ] **Step 5: Cerrar la documentación del sub-proyecto**

- `docs/BITACORA.md`: entrada del día con lo construido, los números de los Steps 2 y 3 y, en «Cambios en el registro», el valor nuevo de `PAR-09` (Tarea 5 bis).
- Este plan y `diseno.md`: actualizar el bloque **Estado**; si el código se apartó del plan, agregar al final una sección «Desvíos».
- `docs/plan/PLAN-MAESTRO.md`: en la fila de `CART-701` a `CART-705`, cambiar «planificado» por «construido» para A6.
- Cuando el PR se mergee, mover `docs/plan/A6-reparto-por-chapa/` a `docs/historico/` y corregir las rutas que la citan (`CONVENCIONES.md §8 bis`, reglas 2 y 3): el docstring de `sparrow_reparto.py`, el del test, el de `medir_sparrow_de_un_grupo.py`, el comentario de `AnidarCrear` y el enlace del Step 4.

- [ ] **Step 6: Commit y PR**

```bash
git add backend/scripts/medir_sparrow_de_un_grupo.py docs/
git commit -m "docs: reparto por chapa (A6) construido y medido"
git push -u origin feat/reparto-por-chapa
```

Abrir el PR contra `main`, **con el ok explícito de Enzo**, pidiendo review a Vale y diciendo en la descripción que toca `sparrow_worker.py`. En la descripción van los números de los Steps 2 y 3.
