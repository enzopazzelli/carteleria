# A7 · Barra de progreso al anidar y al comparar chapas — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado:** **ejecutado el 2026-10-14,** de la Tarea 1 a la 10, en esta sesión y con una pausa por tramo. **No se ensayó** sobre una copia antes de escribirlo: los bloques salen de leer el código de `main` en `43ed271`. Lo que se apartó está al final, en «Desvíos».

**Goal:** Que al anidar con Sparrow y al comparar chapas se vea una barra que avanza contra el tiempo máximo y dice en qué anda el motor y el mejor resultado hasta ahora; y que la comparación corra en segundo plano, se pueda cancelar y se retome al volver a la pestaña.

**Architecture:** El worker de Sparrow deja un archivo chico de progreso al lado de su resultado; el supervisor lo lee en la vuelta que ya hace cada décima de segundo y lo informa con un `al_avanzar`. Un registro en la memoria del servidor (`app/progreso.py`) guarda cómo va cada anidado o comparación en curso, y las rutas lo devuelven. La comparación se parte en «preparar» (con la sesión de la base, en el pedido) y «correr» (sin la base, en la cola), y unas rutas nuevas la arrancan, la consultan, la cancelan y la retoman.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, pytest; React 18 con TypeScript, TanStack Query, Vitest.

**Spec:** [`diseno.md`](diseno.md), en esta misma carpeta.

## Global Constraints

- Todo texto que ve una persona va en castellano rioplatense.
- Los commits no llevan línea de atribución (`Co-Authored-By`).
- El progreso vive en la memoria del servidor, nunca en la base: no hay migraciones en este plan.
- La ruta de hoy, `POST /grupos/{id}/comparar-formatos`, sigue respondiendo igual (las pruebas que ya existen no cambian, salvo la firma de sus `registrar`).
- La barra no pasa de 99 % mientras la tarea corre; al terminar, 100 %.
- El progreso de una corrida o una comparación terminada no se devuelve (`null`).
- Pruebas del backend sin tocar la base real: desde `backend/`, `mkdir -p local/tmp-a7/datos && CARTELERIA_DATOS="$PWD/local/tmp-a7/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a7/base"`, y después `rm -rf local/tmp-a7`. El disco C: está casi lleno: los temporales van en D:.
- Editar con la herramienta de edición (conserva los finales de línea); nunca `sed -i`.

## Review Focus

- **El archivo de progreso a medias o ausente** (el worker recién arranca, o se lo corta escribiendo): la barra sigue avanzando con el tiempo y el anidado no se entera. Lo prueba la Tarea 3.
- **Pedir el estado de una corrida justo cuando termina:** no tiene que volver con progreso viejo pegado a un estado `lista`. Lo prueba la Tarea 4.
- **Cancelar una comparación mientras busca en un formato:** corta esa búsqueda y no arranca la siguiente. Lo prueba la Tarea 6.
- **Dos comparaciones del mismo grupo a la vez** (doble clic, dos pestañas): la segunda se rechaza y dice cuál está corriendo. Lo prueba la Tarea 6.
- **Una comparación que falla a mitad de camino:** queda en estado `error` con el motivo, no colgada en `corriendo`. Lo prueba la Tarea 6.

---

## Tramo 1 — El progreso en el servidor

### Task 1: El registro de progreso

**Files:**
- Create: `backend/app/progreso.py`
- Test: `backend/tests/test_progreso.py`

**Interfaces:**
- Produces: `progreso.anotar(clave: tuple[str, int], datos: dict) -> None`, `progreso.leer(clave) -> dict | None` (una copia), `progreso.olvidar(clave) -> None`. Claves: `("ejecucion", id)` y `("comparacion", id)`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_progreso.py`:

```python
"""El registro de progreso en memoria (`docs/plan/A7-progreso-del-anidado/diseno.md §5.1`)."""
from __future__ import annotations

from app import progreso


def test_lo_anotado_se_lee_hasta_que_se_olvida():
    clave = ("ejecucion", 990001)

    progreso.anotar(clave, {"segundos": 1.5, "maximo": 240})
    leido = progreso.leer(clave)
    progreso.olvidar(clave)

    assert leido == {"segundos": 1.5, "maximo": 240}
    assert progreso.leer(clave) is None


def test_lo_leido_es_una_copia():
    """La ruta que lo lee no puede cambiar lo que anotó la tarea."""
    clave = ("comparacion", 990002)
    progreso.anotar(clave, {"segundos": 1})

    progreso.leer(clave)["segundos"] = 99

    assert progreso.leer(clave) == {"segundos": 1}
    progreso.olvidar(clave)


def test_olvidar_lo_que_no_esta_no_falla():
    progreso.olvidar(("ejecucion", 990003))
```

- [ ] **Step 2: Run test to verify it fails**

Run (desde `backend/`): `python -m pytest -q -p no:cacheprovider tests/test_progreso.py`
Expected: FAIL con `ImportError: cannot import name 'progreso' from 'app'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/progreso.py`:

```python
"""Cómo va cada tarea larga en curso — `docs/plan/A7-progreso-del-anidado/diseno.md §5.1`.

Vive en la memoria del servidor, no en la base: un anidado o una
comparación en curso tampoco sobreviven a un reinicio (límite conocido de
la cola en proceso, `app/cola/__init__.py`), así que guardar su progreso
no ganaría nada. Las tareas corren en hilos: todo pasa por un candado.
"""
from __future__ import annotations

import threading

#: `("ejecucion", id)` o `("comparacion", id)`.
Clave = tuple[str, int]

_candado = threading.Lock()
_en_curso: dict[Clave, dict] = {}


def anotar(clave: Clave, datos: dict) -> None:
    with _candado:
        _en_curso[clave] = dict(datos)


def leer(clave: Clave) -> dict | None:
    with _candado:
        datos = _en_curso.get(clave)
        return dict(datos) if datos is not None else None


def olvidar(clave: Clave) -> None:
    with _candado:
        _en_curso.pop(clave, None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q -p no:cacheprovider tests/test_progreso.py`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/progreso.py backend/tests/test_progreso.py
git commit -m "feat(progreso): registro en memoria de como va cada tarea larga (A7)"
```

### Task 2: El worker anota cómo va

**Files:**
- Modify: `backend/app/services/nesting/sparrow.py` (agregar `ruta_de_progreso` al lado de `ruta_de_avisos`)
- Modify: `backend/app/services/nesting/sparrow_worker.py` (`resolver`)
- Test: `backend/tests/services/nesting/test_sparrow.py`

**Interfaces:**
- Produces: `sparrow.ruta_de_progreso(salida) -> Path` (`salida.progreso.json`). El archivo es un objeto JSON `{"fase": "pasada" | "vaciar" | null, "pasada": int | null, "pasadas": int, "mejor_chapas": int | null}`.

- [ ] **Step 1: Write the failing test**

Al final de `backend/tests/services/nesting/test_sparrow.py`:

```python
from app.services.nesting.sparrow import ruta_de_progreso


def progreso_escrito(salida):
    return json.loads(ruta_de_progreso(salida).read_text(encoding='utf8'))


def test_el_worker_anota_la_pasada_al_empezarla(monkeypatch,tmp_path):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60,vaciar_chapas=False)
    salida=tmp_path/'salida.json'
    vistos=[]
    def pasada(data):
        vistos.append(progreso_escrito(salida))
        return una_por_chapa(data)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',pasada)

    sparrow_worker.resolver(entrada,salida)

    assert vistos==[{'fase':'pasada','pasada':1,'pasadas':1,'mejor_chapas':None}]


def test_el_worker_anota_el_mejor_resultado_y_la_etapa_de_vaciar(monkeypatch,tmp_path):
    """La primera etapa deja cuatro chapas y vaciar chapas las junta en una."""
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    salida=tmp_path/'salida.json'

    sparrow_worker.resolver(entrada,salida)

    assert progreso_escrito(salida)=={'fase':'vaciar','pasada':1,'pasadas':1,'mejor_chapas':1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q -p no:cacheprovider tests/services/nesting/test_sparrow.py -k anota`
Expected: FAIL con `ImportError: cannot import name 'ruta_de_progreso'`.

- [ ] **Step 3: Write minimal implementation**

En `backend/app/services/nesting/sparrow.py`, debajo de `ruta_de_avisos`:

```python
def ruta_de_progreso(salida):
    """Dónde deja el worker cómo va (A7): pasada, fase y mejor resultado.
    Como los avisos, al lado del resultado y escrito de una vez."""
    return Path(salida).with_suffix('.progreso.json')
```

En `backend/app/services/nesting/sparrow_worker.py`, dentro de `resolver`:

1. La importación del principio de la función pasa a ser:

```python
    from .sparrow import convertir_y_validar, ruta_de_avisos, ruta_de_progreso
```

2. Debajo de la función `avisar`, agregar:

```python
    avance={'fase':None,'pasada':None,'pasadas':opts.get('intentos',3),'mejor_chapas':None}
    def avanzar(**cambios):
        # Para la barra de progreso (A7). Aparte y de una vez, como los
        # avisos; si no se puede escribir, el anidado sigue.
        avance.update(cambios)
        if not salida: return
        ruta=ruta_de_progreso(salida);temporal=ruta.with_suffix('.tmp')
        try:
            temporal.write_text(json.dumps(avance),encoding='utf8');temporal.replace(ruta)
        except OSError as error:
            print('avanzar:',error,file=sys.stderr)
```

3. En `considerar`, después de `best=candidato;score=rank`, agregar `avanzar(mejor_chapas=score[0])` dentro del mismo `if`:

```python
            best=candidato;score=rank
            avanzar(mejor_chapas=score[0])
```

4. En el `for intento in ...`, después de la línea `prueba={**data,...}`, agregar:

```python
        avanzar(fase='pasada',pasada=intento+1)
```

5. Antes de `originals,shapes=formas(prueba);reserva=data['gap']/2` (dentro del `if opts.get('vaciar_chapas',True):`), agregar:

```python
            avanzar(fase='vaciar')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q -p no:cacheprovider tests/services/nesting/test_sparrow.py`
Expected: todas pasan (las 34 de antes más las 2 nuevas).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nesting/sparrow.py backend/app/services/nesting/sparrow_worker.py backend/tests/services/nesting/test_sparrow.py
git commit -m "feat(anidado): el worker de Sparrow anota la pasada, la etapa y el mejor resultado (A7)"
```

### Task 3: El supervisor informa el progreso

**Files:**
- Modify: `backend/app/services/nesting/sparrow.py` (`_leer_progreso` nueva, `anidar_sparrow`)
- Test: `backend/tests/services/nesting/test_sparrow.py`

**Interfaces:**
- Consumes: `ruta_de_progreso` (Task 2).
- Produces: `anidar_sparrow(piezas, geometrias, plancha, params, opciones=None, cancelada=lambda: False, al_avanzar=None)`. `al_avanzar(avance: dict)` recibe `{"segundos": float, "maximo": int}` más, si ya hay, `fase`, `pasada`, `pasadas` y `mejor_chapas`.

- [ ] **Step 1: Write the failing test**

Al final de `backend/tests/services/nesting/test_sparrow.py` (usa `con_worker` y `datos`, que ya están en el archivo):

```python
def worker_que_avanza(tmp_path,progreso,espera=1.5):
    """Un worker que escribe `progreso` (texto, tal cual) como su archivo de
    progreso, espera y recién después deja cada pieza sola en su chapa."""
    guion=tmp_path/'worker_que_avanza.py'
    guion.write_text(
        'import json,sys,time\n'
        'from pathlib import Path\n'
        'data=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))\n'
        'salida=Path(sys.argv[2])\n'
        f'salida.with_suffix(".progreso.json").write_text({progreso!r},encoding="utf8")\n'
        f'time.sleep({espera})\n'
        'salida.write_text(json.dumps([{"id":p["id"],"sheet":n,"rotation":0,"tx":data["borde"],"ty":data["borde"]} for n,p in enumerate(data["items"])]),encoding="utf8")\n',
        encoding='utf8',
    )
    return guion


def test_el_supervisor_informa_lo_que_anota_el_worker(monkeypatch,tmp_path):
    anotado={'fase':'pasada','pasada':2,'pasadas':3,'mejor_chapas':7}
    con_worker(monkeypatch,worker_que_avanza(tmp_path,json.dumps(anotado)))
    avances=[]

    anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20),al_avanzar=avances.append)

    assert any({k:a.get(k) for k in anotado}==anotado for a in avances)
    assert all(a['maximo']==20 and 0<=a['segundos']<=20 for a in avances)


def test_un_progreso_a_medias_no_frena_el_anidado_ni_la_barra(monkeypatch,tmp_path):
    """Si el archivo está cortado, el tiempo se informa igual."""
    con_worker(monkeypatch,worker_que_avanza(tmp_path,'{"fase": "pas'))
    avances=[]

    resultado=anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20),al_avanzar=avances.append)

    assert resultado.planchas_usadas==2
    assert avances and all(set(a)=={'segundos','maximo'} for a in avances)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q -p no:cacheprovider tests/services/nesting/test_sparrow.py -k "informa or a_medias_no_frena"`
Expected: FAIL con `TypeError: anidar_sparrow() got an unexpected keyword argument 'al_avanzar'`.

- [ ] **Step 3: Write minimal implementation**

En `backend/app/services/nesting/sparrow.py`, arriba de `anidar_sparrow`:

```python
#: Cada cuánto el supervisor lee el progreso del worker: la barra no
#: necesita más, y así no se lee el archivo en cada vuelta.
_LEER_PROGRESO_CADA_S=0.5

def _leer_progreso(out):
    """Lo que dejó escrito el worker sobre cómo va, o `None` si todavía no
    está o está a medias: la barra de progreso no vale un error."""
    try:
        datos=json.loads(ruta_de_progreso(out).read_text(encoding='utf8'))
    except (OSError,ValueError):
        return None
    if not isinstance(datos,dict): return None
    return {k:datos[k] for k in ('fase','pasada','pasadas','mejor_chapas') if k in datos}
```

`anidar_sparrow` pasa a ser (cambia la firma y la vuelta de vigilancia; lo demás queda igual):

```python
def anidar_sparrow(piezas,geometrias,plancha,params,opciones=None,cancelada=lambda:False,al_avanzar=None):
    opciones=opciones or OpcionesSparrow()
    entrada=preparar_entrada(piezas,geometrias,plancha,params,opciones)
    with tempfile.TemporaryDirectory(prefix='carteleria-sparrow-') as d:
        inp,out=Path(d)/'entrada.json',Path(d)/'salida.json'
        inp.write_text(json.dumps(entrada),encoding='utf8')
        with (Path(d)/'worker.log').open('w+',encoding='utf8') as log:
            proc=subprocess.Popen([sys.executable,'-m','app.services.nesting.sparrow_worker',str(inp),str(out)],stdout=log,stderr=log)
            start=time.monotonic()
            # Lo último que se leyó bien del progreso: si el archivo está a
            # medias, queda esto y el tiempo se informa igual.
            leido={};ultima_lectura=None
            try:
                while proc.poll() is None:
                    if cancelada():raise ValueError('Anidado cancelado.')
                    ahora=time.monotonic()
                    if ahora-start>opciones.tiempo_maximo_s:
                        if out.exists():
                            proc.kill(); proc.wait()
                            return _lo_que_dejo_el_worker(entrada,out,'Se alcanzó el límite de búsqueda: se conserva el mejor anidado completo y validado, sin omitir piezas.')
                        raise ValueError('Sparrow excedió el tiempo máximo; no se guardó un plano parcial.')
                    if al_avanzar is not None and (ultima_lectura is None or ahora-ultima_lectura>=_LEER_PROGRESO_CADA_S):
                        ultima_lectura=ahora
                        leido=_leer_progreso(out) or leido
                        al_avanzar({**leido,'segundos':round(ahora-start,1),'maximo':opciones.tiempo_maximo_s})
                    time.sleep(0.1)
                if proc.returncode!=0:
                    # Si ya había escrito un anidado, una falla posterior
                    # no lo tira: el worker escribe solo resultados validados.
                    log.seek(0);registro=log.read()
                    if out.exists():
                        # El registro se borra con la carpeta: la causa va en el aviso.
                        causa=next((l.strip() for l in reversed(registro.splitlines()) if l.strip()),'sin detalle')[:200]
                        return _lo_que_dejo_el_worker(entrada,out,f'El cálculo terminó con un error ({causa}): se conserva el mejor anidado completo y validado que había encontrado.')
                    raise ValueError('Sparrow no pudo calcular: '+registro[-2000:])
                return _lo_que_dejo_el_worker(entrada,out)
            finally:
                if proc.poll() is None:proc.kill()
                proc.wait()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q -p no:cacheprovider tests/services/nesting/`
Expected: todas pasan.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nesting/sparrow.py backend/tests/services/nesting/test_sparrow.py
git commit -m "feat(anidado): el supervisor de Sparrow informa como va, aunque el archivo este a medias (A7)"
```

### Task 4: El anidado devuelve su progreso

**Files:**
- Modify: `backend/app/api/esquemas_nesting.py` (`ProgresoLeer` nuevo, arriba de `EjecucionLeer`; campo `progreso` en `EjecucionLeer`)
- Modify: `backend/app/api/rutas_nesting.py` (`_ejecutar_anidado` se parte en `_ejecutar_anidado` y `_correr_anidado`; `obtener_ejecucion`)
- Test: `backend/tests/api/test_rutas_nesting.py`

**Interfaces:**
- Consumes: `progreso.anotar/leer/olvidar` (Task 1); `anidar_sparrow(..., al_avanzar=...)` (Task 3).
- Produces: `ProgresoLeer` (Pydantic) con `segundos: float`, `maximo: int`, `fase: Literal["pasada", "vaciar"] | None`, `pasada`, `pasadas`, `mejor_chapas`, `formato`, `formatos: int | None`, `descripcion: str | None`. `GET /ejecuciones/{id}` trae `progreso: ProgresoLeer | null`, solo mientras la corrida está `encolada` o `corriendo`.

- [ ] **Step 1: Write the failing test**

Al final de `backend/tests/api/test_rutas_nesting.py`:

```python
def test_mientras_corre_el_anidado_trae_su_progreso_y_al_terminar_no(cliente, tmp_path, monkeypatch):
    import threading
    from app.api import rutas_nesting
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    informado, seguir = threading.Event(), threading.Event()
    original = rutas_nesting.anidar_sparrow
    avance = {"segundos": 3.0, "maximo": 20, "fase": "pasada", "pasada": 1, "pasadas": 3, "mejor_chapas": 2}

    def con_progreso(piezas, geometrias, plancha, params, opciones, **kw):
        kw["al_avanzar"](avance)
        informado.set()
        seguir.wait(10)
        return original(piezas, geometrias, plancha, params, opciones, **kw)

    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", con_progreso)
    ejecucion = cliente.post(f"/grupos/{grupo['id']}/anidar", json={
        "motor": "sparrow", "segundos_por_busqueda": 1, "tiempo_maximo_s": 20,
    }).json()
    assert informado.wait(10)

    en_curso = cliente.get(f"/ejecuciones/{ejecucion['id']}").json()
    seguir.set()
    final = _esperar_estado(cliente, ejecucion["id"], timeout=20)

    assert en_curso["progreso"] == {**avance, "formato": None, "formatos": None, "descripcion": None}
    assert final["estado"] == "lista", final.get("error")
    assert final["progreso"] is None


def test_un_anidado_rectangular_no_trae_progreso(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)

    ejecucion = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()
    final = _esperar_estado(cliente, ejecucion["id"])

    assert final["progreso"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `mkdir -p local/tmp-a7/datos && CARTELERIA_DATOS="$PWD/local/tmp-a7/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a7/base" tests/api/test_rutas_nesting.py -k progreso`
Expected: FAIL. La primera, en `assert informado.wait(10)` después de diez segundos: sin `al_avanzar`, el reemplazo de Sparrow falla en el hilo con `KeyError` y nunca avisa. La segunda, con `KeyError: 'progreso'`.

- [ ] **Step 3: Write minimal implementation**

En `backend/app/api/esquemas_nesting.py`, arriba de `class EjecucionLeer`:

```python
class ProgresoLeer(BaseModel):
    """Cómo va un anidado o una comparación en curso (A7). Lo que el motor
    todavía no informó viene vacío."""

    segundos: float
    maximo: int
    fase: Literal["pasada", "vaciar"] | None = None
    pasada: int | None = None
    pasadas: int | None = None
    mejor_chapas: int | None = None
    #: Solo en una comparación: qué formato corre, cuántos hay y cuál es.
    formato: int | None = None
    formatos: int | None = None
    descripcion: str | None = None
```

Y al final de los campos de `EjecucionLeer`, después de `actualizado_en: datetime`:

```python
    #: Mientras corre (A7): lo que anotó la corrida en la memoria del
    #: servidor. No sale de la base: `obtener_ejecucion` lo agrega.
    progreso: ProgresoLeer | None = None
```

En `backend/app/api/rutas_nesting.py`:

1. Importaciones: agregar `from .. import progreso` debajo de `from ..cola import cola_de_trabajos`, y `ProgresoLeer` a la lista de `from .esquemas_nesting import (...)`.

2. La función `_ejecutar_anidado` actual se renombra a `_correr_anidado` (mismo cuerpo), y en su llamada a Sparrow se agrega `al_avanzar`:

```python
                resultado = anidar_sparrow(piezas, geometrias, plancha, params, opciones,
                    cancelada=lambda: _esta_cancelada(ejecucion_id),
                    al_avanzar=lambda avance: progreso.anotar(("ejecucion", ejecucion_id), avance))
```

3. Arriba de `_correr_anidado`, una `_ejecutar_anidado` nueva que lo envuelve (la cola la sigue llamando por este nombre):

```python
def _ejecutar_anidado(ejecucion_id: int) -> None:
    """La tarea que corre en la cola. El progreso (A7) se olvida al
    terminar, salga como salga."""
    try:
        _correr_anidado(ejecucion_id)
    finally:
        progreso.olvidar(("ejecucion", ejecucion_id))
```

4. `obtener_ejecucion` pasa a ser:

```python
@router.get("/ejecuciones/{ejecucion_id}", response_model=EjecucionLeer)
def obtener_ejecucion(ejecucion_id: int, sesion: Session = Depends(obtener_sesion)) -> EjecucionLeer:
    """Con `progreso` mientras corre (A7). Una corrida terminada no lo
    trae, aunque la memoria todavía no lo haya olvidado: entre guardar el
    resultado y olvidar el progreso hay un instante."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    leida = EjecucionLeer.model_validate(ejecucion)
    if ejecucion.estado not in (EstadoEjecucion.ENCOLADA.value, EstadoEjecucion.CORRIENDO.value):
        return leida
    avance = progreso.leer(("ejecucion", ejecucion.id))
    return leida.model_copy(update={"progreso": ProgresoLeer(**avance) if avance else None})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CARTELERIA_DATOS="$PWD/local/tmp-a7/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a7/base" tests/api/test_rutas_nesting.py`
Expected: todas pasan.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/esquemas_nesting.py backend/app/api/rutas_nesting.py backend/tests/api/test_rutas_nesting.py
git commit -m "feat(anidado): la consulta de un anidado en curso trae su progreso (A7)"
```

---

## Tramo 2 — La comparación en segundo plano

### Task 5: La comparación se parte en preparar y correr

Es un cambio de forma, no de comportamiento: la ruta de hoy responde igual. Las pruebas que ya existen son las que lo vigilan; lo único que se les cambia es la firma de los `registrar`, porque ahora la comparación le pasa a Sparrow `cancelada` y `al_avanzar`.

**Files:**
- Modify: `backend/app/api/rutas_nesting.py` (`comparar_formatos_de_grupo`, más `_ComparacionPreparada`, `_preparar_comparacion`, `_correr_comparacion` y `_error_de_comparacion` nuevas)
- Modify: `backend/tests/api/test_rutas_nesting.py` (los cuatro `registrar`)

**Interfaces:**
- Consumes: `anidar_sparrow(..., cancelada=..., al_avanzar=...)` (Task 3).
- Produces:
  - `_preparar_comparacion(sesion: Session, grupo_id: int, datos: ComparacionFormatosCrear) -> _ComparacionPreparada`. Levanta `HTTPException` (404 y 400) igual que hoy.
  - `_correr_comparacion(preparada: _ComparacionPreparada, al_avanzar: Callable[[dict], None] | None = None, cancelada: Callable[[], bool] = lambda: False) -> list[OpcionFormatoLeer]`. No usa la base. Levanta `ValueError` (o `ErrorGeometriaSparrow`) si un motor falla, y `ValueError("Comparación cancelada.")` si `cancelada()` es cierto antes de un formato. A `al_avanzar` le pasa lo del anidado del formato más `formato`, `formatos`, `descripcion`, y `segundos` y `maximo` de toda la comparación.
  - `_error_de_comparacion(error: ValueError) -> HTTPException`: el 400 de hoy.

- [ ] **Step 1: Adaptar las pruebas que ya existen**

En `backend/tests/api/test_rutas_nesting.py` hay cuatro funciones `registrar` (en `test_comparar_formatos_sparrow_real_sin_modificar_grupo`, `test_comparar_sparrow_un_formato_donde_no_entran_piezas_no_frena_a_los_demas`, `test_comparar_formatos_sparrow_pasa_la_opcion_de_vaciar_chapas` y `test_comparar_formatos_sparrow_pasa_la_opcion_de_girar_libre`). A cada una se le agrega `**kw` y se lo pasa al original. Por ejemplo, la primera queda:

```python
    def registrar(piezas, geometrias, plancha, params, opciones, **kw):
        llamadas.append((geometrias, opciones))
        return original(piezas, geometrias, plancha, params, opciones, **kw)
```

y las otras tres, con su propio cuerpo, igual: `**kw` en la firma y `**kw` al final de la llamada a `original`.

- [ ] **Step 2: Correr la suite de anidado antes del cambio**

Run: `CARTELERIA_DATOS="$PWD/local/tmp-a7/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a7/base" tests/api/test_rutas_nesting.py -k comparar`
Expected: todas pasan (con `**kw` siguen andando contra el código de hoy). Es la línea de base del cambio de forma.

- [ ] **Step 3: Partir la comparación**

En `backend/app/api/rutas_nesting.py`:

1. Importaciones: agregar `from collections.abc import Callable` y `from dataclasses import dataclass` junto a `import time`.

2. Reemplazar la función `comparar_formatos_de_grupo` entera por:

```python
@dataclass
class _ComparacionPreparada:
    """Lo que hace falta para correr una comparación sin la sesión de la
    base: así puede correr en la cola (A7), además de dentro del pedido."""

    motor: str
    criterio: str
    piezas: list[PiezaDominio]
    geometrias: dict[str, GeometriaPieza]
    opciones_sparrow: OpcionesSparrow | None
    #: Uno por formato pedido, en el orden en que se pidieron: los datos
    #: de su fila de la tabla, la opción a anidar, y las piezas que no
    #: entran (a seccionar; vacía si entran todas).
    comunes: list[dict]
    opciones: list[OpcionFormato]
    a_seccionar: list[list[PiezaASeccionarLeer]]


def _error_de_comparacion(error: ValueError) -> HTTPException:
    """El 400 de siempre: con las piezas que Sparrow no puede leer, si es eso."""
    if isinstance(error, ErrorGeometriaSparrow):
        return HTTPException(status.HTTP_400_BAD_REQUEST, {
            "mensaje": str(error),
            "piezas_invalidas": [int(i) for i in error.piezas_invalidas],
        })
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(error))


def _preparar_comparacion(sesion: Session, grupo_id: int, datos: ComparacionFormatosCrear) -> _ComparacionPreparada:
    """Todo lo que se valida antes de buscar, con la sesión de la base. Lo
    que falla acá es un 400 o un 404, sin haber arrancado nada."""
    grupo = _grupo_o_404(sesion, grupo_id)
    piezas = [p for p in grupo.piezas if not p.descartada]
    if not piezas:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"El grupo «{grupo.nombre}» no tiene piezas para comparar.")
    if not datos.formato_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Hace falta indicar al menos un formato para comparar.")
    if datos.usar_anidado_en_huecos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La comparación todavía no admite la pasada en huecos.")
    piezas_dominio = [
        PiezaDominio(id=str(p.id), ancho_mm=p.ancho_mm, alto_mm=p.alto_mm, cantidad=p.cantidad) for p in piezas
    ]

    opciones: list[OpcionFormato] = []
    formatos: list[Formato] = []
    for formato_id in datos.formato_ids:
        formato = sesion.get(Formato, formato_id)
        if formato is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el formato {formato_id}.")
        material = formato.material
        if material.parametros is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El material «{material.nombre}» no tiene parámetros de corte configurados (CART-105).",
            )
        # Dos causas distintas de "no se puede calcular un precio por
        # plancha" (ver costeo.py::_linea_de_grupo, misma distinción):
        # sin precio cargado, o vendido por una unidad que no es m².
        # Fusionarlas en un solo mensaje es engañoso — cuando la unidad
        # YA es «M2» pero falta el precio, decir "se vende por «M2», no
        # por m²" es contradictorio.
        if formato.costo_unidad_venta is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El formato «{formato.ancho_mm}×{formato.alto_mm}» no tiene precio de referencia cargado.",
            )
        if formato.unidad_venta != "M2":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El formato «{formato.ancho_mm}×{formato.alto_mm}» se vende por «{formato.unidad_venta}», "
                "no por m² — el costo no se calcula solo, hay que cargarlo a mano.",
            )
        precio_por_plancha = (formato.ancho_mm / Decimal(1000)) * (formato.alto_mm / Decimal(1000)) * formato.costo_unidad_venta
        params = ParametrosCorte(
            kerf_mm=material.parametros.kerf_mm,
            margen_borde_mm=material.parametros.margen_borde_mm,
            separacion_piezas_mm=material.parametros.separacion_piezas_mm,
            rotaciones_permitidas=RotacionPermitida(material.parametros.rotaciones_permitidas),
        )
        opciones.append(
            OpcionFormato(
                plancha=Plancha(ancho_mm=formato.ancho_mm, alto_mm=formato.alto_mm),
                params=params,
                precio_por_plancha=precio_por_plancha,
            )
        )
        formatos.append(formato)

    # Un formato donde alguna pieza no entra ni rotándola no se anida: sale
    # con sus piezas a seccionar y no frena a los demás. Un diseño más
    # grande que la chapa se parte en tramos que se sueldan (A5), desde la
    # pestaña Piezas; hasta que se haga, ese formato queda sin planchas ni
    # costo.
    geometrias = _geometrias_del_grupo(grupo) if datos.motor == "sparrow" else {}
    if datos.motor == "sparrow":
        no_entran = [piezas_que_no_entran(piezas_dominio, geometrias, o.plancha, o.params) for o in opciones]
    else:
        no_entran = [MotorNestingRectangular(o.plancha, o.params).piezas_que_no_entran(piezas_dominio) for o in opciones]

    opciones_sparrow = None
    if datos.motor == "sparrow":
        opciones_sparrow = OpcionesSparrow(**datos.model_dump(exclude={"motor", "formato_ids", "usar_anidado_en_huecos", "criterio"}))
        # Validar todos antes de iniciar búsquedas costosas.
        try:
            for opcion, ids in zip(opciones, no_entran):
                if not ids:
                    preparar_entrada(piezas_dominio, geometrias, opcion.plancha, opcion.params, opciones_sparrow)
        except ValueError as error:
            raise _error_de_comparacion(error) from error

    por_id = {str(p.id): p for p in piezas}
    return _ComparacionPreparada(
        motor=datos.motor,
        criterio=datos.criterio,
        piezas=piezas_dominio,
        geometrias=geometrias,
        opciones_sparrow=opciones_sparrow,
        comunes=[
            dict(
                motor=datos.motor,
                formato_id=formato.id,
                formato_descripcion=f"{formato.ancho_mm}×{formato.alto_mm} mm",
                material_nombre=formato.material.nombre,
                moneda=formato.moneda,
                precio_simulado=formato.precio_simulado,
            )
            for formato in formatos
        ],
        opciones=opciones,
        a_seccionar=[
            [
                PiezaASeccionarLeer(
                    id=por_id[i].id, id_origen=por_id[i].id_origen,
                    ancho_mm=por_id[i].ancho_mm, alto_mm=por_id[i].alto_mm,
                )
                for i in ids
            ]
            for ids in no_entran
        ],
    )


def _correr_comparacion(
    preparada: _ComparacionPreparada,
    al_avanzar: Callable[[dict], None] | None = None,
    cancelada: Callable[[], bool] = lambda: False,
) -> list[OpcionFormatoLeer]:
    """Anida cada formato y arma la tabla. No usa la base: corre igual en
    el pedido y en la cola (A7)."""
    a_anidar = [
        (opcion, comunes)
        for opcion, comunes, a_seccionar in zip(preparada.opciones, preparada.comunes, preparada.a_seccionar)
        if not a_seccionar
    ]
    if preparada.motor == "sparrow":
        from ..services.nesting.comparador import ResultadoComparacionFormato
        inicio = time.monotonic()
        maximo = len(a_anidar) * preparada.opciones_sparrow.tiempo_maximo_s
        resultados = []
        for numero, (opcion, comunes) in enumerate(a_anidar, start=1):
            if cancelada():
                raise ValueError("Comparación cancelada.")

            def avanzar(avance: dict, numero: int = numero, descripcion: str = comunes["formato_descripcion"]) -> None:
                if al_avanzar is not None:
                    al_avanzar({
                        **avance,
                        "segundos": round(time.monotonic() - inicio, 1), "maximo": maximo,
                        "formato": numero, "formatos": len(a_anidar), "descripcion": descripcion,
                    })

            resultado = anidar_sparrow(
                preparada.piezas, preparada.geometrias, opcion.plancha, opcion.params, preparada.opciones_sparrow,
                cancelada=cancelada, al_avanzar=avanzar,
            )
            resultados.append(ResultadoComparacionFormato(
                opcion, resultado, calcular_aprovechamiento(resultado, opcion.plancha, preparada.geometrias),
                resultado.planchas_usadas * opcion.precio_por_plancha,
            ))
    else:
        resultados = comparar_formatos(
            preparada.piezas, [opcion for opcion, _ in a_anidar], tope_planchas_advertencia=_TOPE_PLANCHAS_ADVERTENCIA
        )
    recomendado = formato_recomendado(resultados, preparada.criterio) if resultados else None

    resultados_en_orden = iter(resultados)
    filas = []
    for comunes, a_seccionar in zip(preparada.comunes, preparada.a_seccionar):
        if a_seccionar:
            filas.append(OpcionFormatoLeer(
                **comunes,
                area_total_m2=None,
                planchas_usadas=None,
                aprovechamiento_pct=None,
                costo_total=None,
                recomendado=False,
                piezas_a_seccionar=a_seccionar,
            ))
            continue
        resultado = next(resultados_en_orden)
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


@router.post("/grupos/{grupo_id}/comparar-formatos", response_model=list[OpcionFormatoLeer])
def comparar_formatos_de_grupo(
    grupo_id: int, datos: ComparacionFormatosCrear, sesion: Session = Depends(obtener_sesion)
) -> list[OpcionFormatoLeer]:
    """Compara las piezas de un grupo contra varios formatos candidatos
    SIN persistir nada — ni tocar `grupo.formato_id` ni crear una
    `EjecucionNesting`. Es el paso previo a elegir un material cuando
    se quiere ofrecer una variante más económica o en otro material
    (`docs/historico/frontend-cotizador/diseno.md §5.2`).

    Espera hasta el final dentro del pedido. La pantalla usa la
    comparación en segundo plano (`rutas_comparaciones.py`, A7), que hace
    lo mismo con progreso y cancelación.
    """
    preparada = _preparar_comparacion(sesion, grupo_id, datos)
    try:
        return _correr_comparacion(preparada)
    except ValueError as error:
        raise _error_de_comparacion(error) from error
```

- [ ] **Step 4: Correr la suite de anidado después del cambio**

Run: `CARTELERIA_DATOS="$PWD/local/tmp-a7/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a7/base" tests/api/`
Expected: todas pasan, las mismas que en el Step 2.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/rutas_nesting.py backend/tests/api/test_rutas_nesting.py
git commit -m "refactor(anidado): la comparacion de formatos se parte en preparar y correr (A7)"
```

### Task 6: Las rutas de la comparación en segundo plano

**Files:**
- Modify: `backend/app/api/esquemas_nesting.py` (`ComparacionLeer` nuevo, al final del archivo)
- Create: `backend/app/api/rutas_comparaciones.py`
- Modify: `backend/app/api/app.py` (registrar el router)
- Test: `backend/tests/api/test_rutas_comparaciones.py`

**Interfaces:**
- Consumes: `_ComparacionPreparada`, `_preparar_comparacion`, `_correr_comparacion` (Task 5); `progreso` (Task 1); `ProgresoLeer` (Task 4).
- Produces: las rutas `POST /grupos/{grupo_id}/comparaciones` (202, `ComparacionLeer`), `GET /comparaciones/{id}`, `POST /comparaciones/{id}/cancelar`, `GET /grupos/{grupo_id}/comparacion`. `ComparacionLeer` = `{id: int, grupo_id: int, estado: "corriendo" | "lista" | "cancelada" | "error", progreso: ProgresoLeer | null, opciones: list[OpcionFormatoLeer] | null, error: str | null}`.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_rutas_comparaciones.py`:

```python
"""Comparar formatos en segundo plano (`docs/plan/A7-progreso-del-anidado/diseno.md §5.3`)."""
from __future__ import annotations

import threading
import time

import pytest

from .test_rutas_nesting import _grupo_con_piezas_sin_formato, _material_con_formato_y_parametros, cliente  # noqa: F401


@pytest.fixture(autouse=True)
def _sin_comparaciones_de_otras_pruebas(monkeypatch):
    """Las comparaciones viven en la memoria del servidor, y cada prueba
    arma una base nueva donde los grupos vuelven a empezar en 1."""
    from app.api import rutas_comparaciones

    monkeypatch.setattr(rutas_comparaciones, "_por_id", {})
    monkeypatch.setattr(rutas_comparaciones, "_ultima_de_grupo", {})


def _esperar_comparacion(cliente, comparacion_id, *, timeout=30.0) -> dict:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        cuerpo = cliente.get(f"/comparaciones/{comparacion_id}").json()
        if cuerpo["estado"] != "corriendo":
            return cuerpo
        time.sleep(0.05)
    raise AssertionError(f"la comparación {comparacion_id} no terminó dentro de {timeout}s")


def _dos_formatos(cliente) -> list[int]:
    """De 1000 x 1000 y de 500 x 500: la pieza de 100 x 100 entra en los dos."""
    material, formato = _material_con_formato_y_parametros(cliente)
    segundo = cliente.post(f"/materiales/{material['id']}/formatos", json={
        "ancho_mm": "500", "alto_mm": "500", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()
    return [formato["id"], segundo["id"]]


_SPARROW_RAPIDO = {"motor": "sparrow", "segundos_por_busqueda": 1, "tiempo_maximo_s": 20, "simplificacion_mm": 0}


class _SparrowQueEspera:
    """En lugar de `anidar_sparrow`: informa un avance, avisa y espera a
    que la prueba lo suelte (o a que se cancele la comparación) antes de
    anidar de verdad. Así la prueba ve la comparación a mitad de camino
    sin depender de cuánto tarda Sparrow."""

    def __init__(self, original):
        self.original = original
        self.llamadas = 0
        self.informado = threading.Event()
        self.seguir = threading.Event()
        self.salio = threading.Event()

    def __call__(self, piezas, geometrias, plancha, params, opciones, **kw):
        self.llamadas += 1
        try:
            kw["al_avanzar"]({"fase": "pasada", "pasada": 1, "pasadas": 3, "mejor_chapas": 1})
            self.informado.set()
            while not self.seguir.wait(0.05):
                if kw["cancelada"]():
                    raise ValueError("Anidado cancelado.")
            return self.original(piezas, geometrias, plancha, params, opciones, **kw)
        finally:
            self.salio.set()


@pytest.fixture
def sparrow_que_espera(monkeypatch):
    from app.api import rutas_nesting

    falso = _SparrowQueEspera(rutas_nesting.anidar_sparrow)
    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", falso)
    yield falso
    falso.seguir.set()  # que ningún hilo quede esperando


def test_la_comparacion_arranca_enseguida_y_termina_con_la_misma_tabla_de_siempre(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    pedido = {"formato_ids": _dos_formatos(cliente), "motor": "rectpack"}

    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json=pedido)
    final = _esperar_comparacion(cliente, arrancada.json()["id"])

    assert arrancada.status_code == 202
    assert final["estado"] == "lista", final["error"]
    assert final["opciones"] == cliente.post(f"/grupos/{grupo['id']}/comparar-formatos", json=pedido).json()
    assert final["progreso"] is None


def test_mientras_corre_dice_que_formato_va_y_cuanto_falta_como_mucho(cliente, tmp_path, sparrow_que_espera):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()
    assert sparrow_que_espera.informado.wait(10)

    en_curso = cliente.get(f"/comparaciones/{arrancada['id']}").json()
    sparrow_que_espera.seguir.set()
    final = _esperar_comparacion(cliente, arrancada["id"])

    assert en_curso["estado"] == "corriendo"
    avance = en_curso["progreso"]
    assert (avance["formato"], avance["formatos"], avance["mejor_chapas"]) == (1, 2, 1)
    assert avance["maximo"] == 40 and avance["segundos"] >= 0
    assert final["estado"] == "lista", final["error"]
    assert avance["descripcion"] == final["opciones"][0]["formato_descripcion"]


def test_cancelar_corta_la_busqueda_y_saltea_los_formatos_que_faltan(cliente, tmp_path, sparrow_que_espera):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()
    assert sparrow_que_espera.informado.wait(10)

    cancelada = cliente.post(f"/comparaciones/{arrancada['id']}/cancelar")
    assert sparrow_que_espera.salio.wait(10)
    final = cliente.get(f"/comparaciones/{arrancada['id']}").json()

    assert cancelada.status_code == 200 and cancelada.json()["estado"] == "cancelada"
    assert final["estado"] == "cancelada" and final["opciones"] is None
    assert sparrow_que_espera.llamadas == 1


def test_no_se_arranca_una_segunda_comparacion_en_el_mismo_grupo(cliente, tmp_path, sparrow_que_espera):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    pedido = {"formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO}
    primera = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json=pedido).json()
    assert sparrow_que_espera.informado.wait(10)

    segunda = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json=pedido)

    assert segunda.status_code == 409
    assert f"#{primera['id']}" in segunda.json()["detail"]


def test_la_ultima_comparacion_del_grupo_se_retoma(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    sin_ninguna = cliente.get(f"/grupos/{grupo['id']}/comparacion")
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), "motor": "rectpack",
    }).json()
    _esperar_comparacion(cliente, arrancada["id"])

    retomada = cliente.get(f"/grupos/{grupo['id']}/comparacion")

    assert sin_ninguna.status_code == 404
    assert retomada.status_code == 200
    assert (retomada.json()["id"], retomada.json()["estado"]) == (arrancada["id"], "lista")


def test_una_comparacion_que_no_se_puede_arrancar_da_el_mismo_error_de_siempre(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={"formato_ids": []})

    assert respuesta.status_code == 400
    assert "al menos un formato" in respuesta.json()["detail"]
    assert cliente.get(f"/grupos/{grupo['id']}/comparacion").status_code == 404


def test_una_falla_a_mitad_de_camino_queda_en_la_comparacion(cliente, tmp_path, monkeypatch):
    from app.api import rutas_nesting

    def falla(*args, **kw):
        raise ValueError("Sparrow no pudo calcular: falla de prueba")

    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", falla)
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()

    final = _esperar_comparacion(cliente, arrancada["id"])

    assert final["estado"] == "error"
    assert "falla de prueba" in final["error"]


def test_una_comparacion_que_no_existe_da_404(cliente):
    assert cliente.get("/comparaciones/999").status_code == 404
    assert cliente.post("/comparaciones/999/cancelar").status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CARTELERIA_DATOS="$PWD/local/tmp-a7/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a7/base" tests/api/test_rutas_comparaciones.py`
Expected: FAIL: el fixture `_sin_comparaciones_de_otras_pruebas` da `ImportError: cannot import name 'rutas_comparaciones'`.

- [ ] **Step 3: Write minimal implementation**

Al final de `backend/app/api/esquemas_nesting.py`:

```python
class ComparacionLeer(BaseModel):
    """Una comparación de formatos en segundo plano (A7)."""

    id: int
    grupo_id: int
    estado: Literal["corriendo", "lista", "cancelada", "error"]
    progreso: ProgresoLeer | None = None
    #: La tabla de la comparación, cuando terminó bien: la misma que
    #: devuelve `POST /grupos/{id}/comparar-formatos`.
    opciones: list[OpcionFormatoLeer] | None = None
    error: str | None = None
```

`backend/app/api/rutas_comparaciones.py`:

```python
"""Comparar formatos en segundo plano, con progreso y cancelación —
`docs/plan/A7-progreso-del-anidado/diseno.md §5.3`.

La comparación de siempre (`POST /grupos/{id}/comparar-formatos`) espera
hasta el final dentro del pedido. Esta la arranca en la cola y contesta
enseguida; la pantalla pregunta cómo va. Vive en la memoria del servidor,
como el progreso (`app/progreso.py`): se guarda solo la última de cada
grupo, y un reinicio la pierde.
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import progreso
from ..cola import cola_de_trabajos
from .dependencias import obtener_sesion
from .esquemas_nesting import ComparacionFormatosCrear, ComparacionLeer, OpcionFormatoLeer, ProgresoLeer
from .rutas_nesting import _ComparacionPreparada, _correr_comparacion, _preparar_comparacion
from .rutas_trabajos import _grupo_o_404

router = APIRouter(tags=["nesting"])


@dataclass
class _Comparacion:
    id: int
    grupo_id: int
    estado: str = "corriendo"
    opciones: list[OpcionFormatoLeer] | None = None
    error: str | None = None
    cancelar: threading.Event = field(default_factory=threading.Event)


_candado = threading.Lock()
_por_id: dict[int, _Comparacion] = {}
_ultima_de_grupo: dict[int, int] = {}
_numeros = itertools.count(1)


def _leer(comparacion: _Comparacion) -> ComparacionLeer:
    avance = progreso.leer(("comparacion", comparacion.id)) if comparacion.estado == "corriendo" else None
    return ComparacionLeer(
        id=comparacion.id,
        grupo_id=comparacion.grupo_id,
        estado=comparacion.estado,
        progreso=ProgresoLeer(**avance) if avance else None,
        opciones=comparacion.opciones,
        error=comparacion.error,
    )


def _comparacion_o_404(comparacion_id: int) -> _Comparacion:
    with _candado:
        comparacion = _por_id.get(comparacion_id)
    if comparacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la comparación {comparacion_id}.")
    return comparacion


def _correr(comparacion: _Comparacion, preparada: _ComparacionPreparada) -> None:
    """La tarea de la cola. Una comparación cancelada queda cancelada,
    termine como termine la búsqueda que se cortó."""
    clave = ("comparacion", comparacion.id)
    try:
        opciones = _correr_comparacion(
            preparada,
            al_avanzar=lambda avance: progreso.anotar(clave, avance),
            cancelada=comparacion.cancelar.is_set,
        )
        if not comparacion.cancelar.is_set():
            comparacion.opciones = opciones
            comparacion.estado = "lista"
    except Exception as error:  # noqa: BLE001 - cualquier falla queda en la comparación, no se pierde
        if not comparacion.cancelar.is_set():
            comparacion.error = str(error)
            comparacion.estado = "error"
    finally:
        progreso.olvidar(clave)


@router.post(
    "/grupos/{grupo_id}/comparaciones",
    response_model=ComparacionLeer,
    status_code=status.HTTP_202_ACCEPTED,
)
def iniciar_comparacion(
    grupo_id: int, datos: ComparacionFormatosCrear, sesion: Session = Depends(obtener_sesion)
) -> ComparacionLeer:
    """Valida igual que la comparación de siempre (los mismos 400 y 404) y
    la arranca en la cola. Una por grupo a la vez."""
    preparada = _preparar_comparacion(sesion, grupo_id, datos)
    with _candado:
        anterior = _por_id.get(_ultima_de_grupo.get(grupo_id, -1))
        if anterior is not None and anterior.estado == "corriendo":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya hay una comparación en curso en este grupo (#{anterior.id}): esperá a que termine o cancelala.",
            )
        comparacion = _Comparacion(id=next(_numeros), grupo_id=grupo_id)
        if anterior is not None:
            del _por_id[anterior.id]  # se guarda solo la última de cada grupo
        _por_id[comparacion.id] = comparacion
        _ultima_de_grupo[grupo_id] = comparacion.id
    cola_de_trabajos().encolar(lambda: _correr(comparacion, preparada))
    return _leer(comparacion)


@router.get("/comparaciones/{comparacion_id}", response_model=ComparacionLeer)
def obtener_comparacion(comparacion_id: int) -> ComparacionLeer:
    return _leer(_comparacion_o_404(comparacion_id))


@router.post("/comparaciones/{comparacion_id}/cancelar", response_model=ComparacionLeer)
def cancelar_comparacion(comparacion_id: int) -> ComparacionLeer:
    """Corta la búsqueda en curso y saltea los formatos que faltan."""
    comparacion = _comparacion_o_404(comparacion_id)
    if comparacion.estado != "corriendo":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La comparación ya está en estado «{comparacion.estado}», no se puede cancelar.",
        )
    comparacion.cancelar.set()
    comparacion.estado = "cancelada"
    return _leer(comparacion)


@router.get("/grupos/{grupo_id}/comparacion", response_model=ComparacionLeer)
def ultima_comparacion(grupo_id: int, sesion: Session = Depends(obtener_sesion)) -> ComparacionLeer:
    """La última comparación del grupo, corriendo o terminada: la pantalla
    la retoma al volver a la pestaña."""
    _grupo_o_404(sesion, grupo_id)
    with _candado:
        comparacion = _por_id.get(_ultima_de_grupo.get(grupo_id, -1))
    if comparacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este grupo no tiene una comparación.")
    return _leer(comparacion)
```

En `backend/app/api/app.py`, junto a las otras importaciones de routers:

```python
from .rutas_comparaciones import router as router_comparaciones
```

y debajo de `app.include_router(router_nesting)`:

```python
app.include_router(router_comparaciones)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CARTELERIA_DATOS="$PWD/local/tmp-a7/datos" python -m pytest -q -p no:cacheprovider --basetemp="$PWD/local/tmp-a7/base" tests/api/`
Expected: todas pasan.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/esquemas_nesting.py backend/app/api/rutas_comparaciones.py backend/app/api/app.py backend/tests/api/test_rutas_comparaciones.py
git commit -m "feat(anidado): comparar formatos en segundo plano, con progreso, cancelacion y retomar (A7)"
```

---

## Tramo 3 — La pantalla

### Task 7: La barra de progreso

**Files:**
- Modify: `frontend/src/api/nesting.ts` (tipo `Progreso`; campo `progreso` en `Ejecucion`)
- Create: `frontend/src/components/progreso.ts`
- Create: `frontend/src/components/progreso.test.ts`
- Create: `frontend/src/components/BarraDeProgreso.tsx`

**Interfaces:**
- Consumes: la forma de `ProgresoLeer` (Task 4).
- Produces: `type Progreso` (en `api/nesting.ts`); `porcentajeDeProgreso(progreso: Progreso | null | undefined, terminado: boolean): number`; `minutosYSegundos(segundos: number): string`; `textoDeProgreso(progreso: Progreso | null | undefined): string`; el componente `BarraDeProgreso({ progreso, terminado? })`.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/progreso.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { Progreso } from "../api/nesting";
import { minutosYSegundos, porcentajeDeProgreso, textoDeProgreso } from "./progreso";

function progreso(extra: Partial<Progreso> = {}): Progreso {
  return {
    segundos: 80, maximo: 240, fase: null, pasada: null, pasadas: null,
    mejor_chapas: null, formato: null, formatos: null, descripcion: null, ...extra,
  };
}

describe("porcentajeDeProgreso", () => {
  it("es el tiempo que pasó sobre el máximo", () => {
    expect(porcentajeDeProgreso(progreso({ segundos: 60 }), false)).toBe(25);
  });

  it("no llega a 100 mientras corre, aunque se pase del máximo", () => {
    expect(porcentajeDeProgreso(progreso({ segundos: 300 }), false)).toBe(99);
  });

  it("al terminar es 100, aunque haya sobrado tiempo", () => {
    expect(porcentajeDeProgreso(progreso({ segundos: 10 }), true)).toBe(100);
  });

  it("sin progreso todavía es 0", () => {
    expect(porcentajeDeProgreso(null, false)).toBe(0);
  });
});

describe("minutosYSegundos", () => {
  it("escribe minutos y segundos con dos cifras", () => {
    expect(minutosYSegundos(80)).toBe("1:20");
    expect(minutosYSegundos(5.7)).toBe("0:05");
    expect(minutosYSegundos(240)).toBe("4:00");
  });
});

describe("textoDeProgreso", () => {
  it("sin progreso dice que está calculando", () => {
    expect(textoDeProgreso(undefined)).toBe("Calculando…");
  });

  it("nombra la pasada, el mejor resultado y el tiempo", () => {
    expect(textoDeProgreso(progreso({ pasada: 2, pasadas: 3, fase: "pasada", mejor_chapas: 9 }))).toBe(
      "Pasada 2 de 3 · mejor: 9 chapas · 1:20 de 4:00",
    );
  });

  it("dice cuando está vaciando chapas, y una chapa en singular", () => {
    expect(textoDeProgreso(progreso({ pasada: 1, pasadas: 3, fase: "vaciar", mejor_chapas: 1 }))).toBe(
      "Pasada 1 de 3, vaciando chapas · mejor: 1 chapa · 1:20 de 4:00",
    );
  });

  it("en una comparación nombra el formato", () => {
    expect(textoDeProgreso(progreso({ formato: 2, formatos: 4, descripcion: "1220×2440 mm" }))).toBe(
      "Formato 2 de 4 · 1220×2440 mm · 1:20 de 4:00",
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (desde `frontend/`): `npx vitest run src/components/progreso.test.ts`
Expected: FAIL con `Failed to load url ./progreso`.

- [ ] **Step 3: Write minimal implementation**

En `frontend/src/api/nesting.ts`, arriba de `export interface Ejecucion`:

```ts
/** Cómo va un anidado o una comparación en curso (A7). Lo que el motor
 * todavía no informó viene en `null`. */
export interface Progreso {
  segundos: number;
  maximo: number;
  fase: "pasada" | "vaciar" | null;
  pasada: number | null;
  pasadas: number | null;
  mejor_chapas: number | null;
  /** Solo en una comparación. */
  formato: number | null;
  formatos: number | null;
  descripcion: string | null;
}
```

y en `Ejecucion`, debajo de `creado_en: string;`:

```ts
  /** Solo mientras corre (A7). */
  progreso?: Progreso | null;
```

`frontend/src/components/progreso.ts`:

```ts
import type { Progreso } from "../api/nesting";

/** Cuánto se llena la barra, de 0 a 100, contra el tiempo máximo. El
 * máximo es un tope y no una estimación: mientras corre no pasa de 99, y
 * al terminar salta a 100 aunque haya sobrado tiempo. */
export function porcentajeDeProgreso(progreso: Progreso | null | undefined, terminado: boolean): number {
  if (terminado) return 100;
  if (!progreso || progreso.maximo <= 0) return 0;
  return Math.min(99, Math.floor((progreso.segundos / progreso.maximo) * 100));
}

/** «1:20». */
export function minutosYSegundos(segundos: number): string {
  const enteros = Math.max(0, Math.floor(segundos));
  return `${Math.floor(enteros / 60)}:${String(enteros % 60).padStart(2, "0")}`;
}

/** Lo que va al lado de la barra: «Pasada 2 de 3 · mejor: 9 chapas ·
 * 1:20 de 4:00». Lo que el motor todavía no informó no se nombra. */
export function textoDeProgreso(progreso: Progreso | null | undefined): string {
  if (!progreso) return "Calculando…";
  const partes: string[] = [];
  if (progreso.formato !== null && progreso.formatos !== null) {
    partes.push(`Formato ${progreso.formato} de ${progreso.formatos}`);
    if (progreso.descripcion) partes.push(progreso.descripcion);
  }
  if (progreso.pasada !== null && progreso.pasadas !== null) {
    partes.push(`Pasada ${progreso.pasada} de ${progreso.pasadas}${progreso.fase === "vaciar" ? ", vaciando chapas" : ""}`);
  }
  if (progreso.mejor_chapas !== null) {
    partes.push(`mejor: ${progreso.mejor_chapas} ${progreso.mejor_chapas === 1 ? "chapa" : "chapas"}`);
  }
  partes.push(`${minutosYSegundos(progreso.segundos)} de ${minutosYSegundos(progreso.maximo)}`);
  return partes.join(" · ");
}
```

`frontend/src/components/BarraDeProgreso.tsx`:

```tsx
import type { Progreso } from "../api/nesting";
import { porcentajeDeProgreso, textoDeProgreso } from "./progreso";

/** La barra de una espera larga (A7): se llena contra el tiempo máximo y
 * dice en qué anda el motor. */
export default function BarraDeProgreso({
  progreso,
  terminado = false,
}: {
  progreso: Progreso | null | undefined;
  terminado?: boolean;
}) {
  const porcentaje = porcentajeDeProgreso(progreso, terminado);
  return (
    <div className="my-2">
      <div
        className="h-2 w-full rounded bg-line/40 overflow-hidden"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={porcentaje}
      >
        <div className="h-full bg-cut transition-[width] duration-500" style={{ width: `${porcentaje}%` }} />
      </div>
      <p className="text-xs mt-1 font-mono">{textoDeProgreso(progreso)}</p>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run && npx tsc -b`
Expected: todas pasan y `tsc` termina sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/nesting.ts frontend/src/components/progreso.ts frontend/src/components/progreso.test.ts frontend/src/components/BarraDeProgreso.tsx
git commit -m "feat(frontend): la barra de progreso y sus cuentas (A7)"
```

### Task 8: La barra en Anidado

**Files:**
- Modify: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`

**Interfaces:**
- Consumes: `BarraDeProgreso` (Task 7); `Ejecucion.progreso` (Task 7), que ya llega con la consulta de cada medio segundo de `useEjecucion`.

No lleva prueba propia: el frontend no tiene pruebas de componentes, y las cuentas de la barra ya están probadas en la Task 7. Se mira en el recorrido de la Task 10.

- [ ] **Step 1: Mostrar la barra mientras la corrida sigue**

En `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`, agregar la importación:

```tsx
import BarraDeProgreso from "../../components/BarraDeProgreso";
```

y, justo después del bloque `{enCurso && ( <p className="text-sm mb-2"> … </p> )}`, agregar:

```tsx
      {enCurso && !ESTADOS_TERMINALES.has(enCurso.estado) && <BarraDeProgreso progreso={enCurso.progreso} />}
```

- [ ] **Step 2: Comprobar que compila y que las pruebas siguen**

Run (desde `frontend/`): `npx vitest run && npx tsc -b`
Expected: todas pasan, sin errores de tipos.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx
git commit -m "feat(frontend): barra de progreso mientras corre un anidado (A7)"
```

### Task 9: La comparación en segundo plano, en Grupos

**Files:**
- Modify: `frontend/src/api/piezasYgrupos.ts` (tipo `Comparacion`; `iniciarComparacion`, `obtenerComparacion`, `cancelarComparacion`, `ultimaComparacion`; se va `compararFormatos`)
- Modify: `frontend/src/hooks/useGrupos.ts` (`useIniciarComparacion`, `useComparacion`, `useUltimaComparacion`; se va `useCompararFormatos`)
- Modify: `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`

**Interfaces:**
- Consumes: las rutas de la Task 6; `BarraDeProgreso` (Task 7).
- Produces: `type Comparacion = { id: number; grupo_id: number; estado: "corriendo" | "lista" | "cancelada" | "error"; progreso: Progreso | null; opciones: OpcionFormato[] | null; error: string | null }`.

No lleva prueba propia, por lo mismo que la Task 8: la pantalla no tiene pruebas de componentes. Se mira en el recorrido de la Task 10.

- [ ] **Step 1: Las llamadas a la API**

En `frontend/src/api/piezasYgrupos.ts`, la primera línea pasa a ser:

```ts
import { ApiError, apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from "./client";
```

Y la función `compararFormatos` (ya no la usa nadie) se reemplaza por:

```ts
/** Una comparación de formatos en segundo plano (A7). */
export interface Comparacion {
  id: number;
  grupo_id: number;
  estado: "corriendo" | "lista" | "cancelada" | "error";
  progreso: import("./nesting").Progreso | null;
  opciones: OpcionFormato[] | null;
  error: string | null;
}

export function iniciarComparacion(
  grupoId: number,
  formatoIds: number[],
  opciones: import("./nesting").OpcionesAnidado = {},
): Promise<Comparacion> {
  return apiPost<Comparacion>(`/grupos/${grupoId}/comparaciones`, { formato_ids: formatoIds, ...opciones });
}

export function obtenerComparacion(comparacionId: number): Promise<Comparacion> {
  return apiGet<Comparacion>(`/comparaciones/${comparacionId}`);
}

export function cancelarComparacion(comparacionId: number): Promise<Comparacion> {
  return apiPost<Comparacion>(`/comparaciones/${comparacionId}/cancelar`);
}

/** La última comparación del grupo, o `null` si no tiene. */
export async function ultimaComparacion(grupoId: number): Promise<Comparacion | null> {
  try {
    return await apiGet<Comparacion>(`/grupos/${grupoId}/comparacion`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}
```

- [ ] **Step 2: Los hooks**

En `frontend/src/hooks/useGrupos.ts`, en la importación de `../api/piezasYgrupos`, se saca `compararFormatos` y se agregan `iniciarComparacion`, `obtenerComparacion`, `ultimaComparacion` y `type Comparacion`. La función `useCompararFormatos` se reemplaza por:

```ts
export function useIniciarComparacion() {
  return useMutation({
    mutationFn: ({ grupoId, formatoIds, opciones }: { grupoId: number; formatoIds: number[]; opciones?: import("../api/nesting").OpcionesAnidado }) =>
      iniciarComparacion(grupoId, formatoIds, opciones),
  });
}

/** Pregunta cada segundo mientras la comparación corre. */
export function useComparacion(comparacionId: number | null) {
  return useQuery({
    queryKey: ["comparacion", comparacionId],
    queryFn: () => obtenerComparacion(comparacionId as number),
    enabled: comparacionId !== null,
    refetchInterval: (query) => ((query.state.data as Comparacion | undefined)?.estado === "corriendo" ? 1000 : false),
  });
}

/** La última comparación del grupo, para retomarla al abrir «Comparar formatos». */
export function useUltimaComparacion(grupoId: number | null) {
  return useQuery({
    queryKey: ["ultima-comparacion", grupoId],
    queryFn: () => ultimaComparacion(grupoId as number),
    enabled: grupoId !== null,
    staleTime: 0,
  });
}
```

- [ ] **Step 3: La pantalla de Grupos**

En `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`:

1. Importaciones. La primera línea pasa a ser `import { useEffect, useState } from "react";`. En la importación de `../../hooks/useGrupos`, `useCompararFormatos` se reemplaza por `useComparacion, useIniciarComparacion, useUltimaComparacion`. Y se agregan:

```tsx
import { useQueryClient } from "@tanstack/react-query";
import { cancelarComparacion } from "../../api/piezasYgrupos";
import BarraDeProgreso from "../../components/BarraDeProgreso";
```

2. Donde estaba `const compararFormatos = useCompararFormatos();`:

```tsx
  const queryClient = useQueryClient();
  const iniciarComparacion = useIniciarComparacion();
```

3. Debajo de `const [grupoComparando, setGrupoComparando] = useState<number | null>(null);`:

```tsx
  const [comparacionId, setComparacionId] = useState<number | null>(null);
  const { data: comparacion } = useComparacion(comparacionId);
  const { data: ultima } = useUltimaComparacion(grupoComparando);
  const comparando = iniciarComparacion.isPending || comparacion?.estado === "corriendo";

  // Al abrir «Comparar formatos» de un grupo se retoma su última
  // comparación: la barra si sigue corriendo, la tabla si terminó (A7).
  useEffect(() => {
    if (ultima && ultima.grupo_id === grupoComparando && comparacionId === null) setComparacionId(ultima.id);
  }, [ultima, grupoComparando, comparacionId]);

  // Cuando termina, la tabla o el error pasan a la pantalla como antes.
  useEffect(() => {
    if (comparacion?.estado === "lista") setResultado(comparacion.opciones);
    if (comparacion?.estado === "error") setError(comparacion.error ?? "No se pudo comparar.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [comparacion?.id, comparacion?.estado]);
```

4. `alComparar` pasa a ser, y se agrega `alCancelarComparacion` debajo:

```tsx
  async function alComparar(grupoId: number) {
    setError(null);
    setPiezasInvalidas([]);
    setResultado(null);
    try {
      const arrancada = await iniciarComparacion.mutateAsync({ grupoId, formatoIds: candidatos,
        opciones: { motor, semilla, segundos_por_busqueda: busqueda, tiempo_maximo_s: limite, simplificacion_mm: simplificacion, vaciar_chapas: vaciarChapas, giro_libre: giroLibre, criterio: "material" } });
      setComparacionId(arrancada.id);
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo comparar."));
      if (e instanceof ApiError) setPiezasInvalidas(e.piezasInvalidas);
    }
  }

  async function alCancelarComparacion() {
    if (comparacionId === null) return;
    try {
      await cancelarComparacion(comparacionId);
      await queryClient.invalidateQueries({ queryKey: ["comparacion", comparacionId] });
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo cancelar la comparación."));
    }
  }
```

5. En el botón «Comparar formatos» de cada grupo: `disabled={compararFormatos.isPending}` pasa a `disabled={comparando}`, y su `onClick` agrega `setComparacionId(null);` después de `setCandidatos([]);`.

6. Las otras tres apariciones de `compararFormatos.isPending` (el `fieldset`, el checkbox «Seleccionar todas» y cada checkbox de formato) pasan a `comparando`. El botón «Comparar» queda:

```tsx
              <button
                className="bg-cut text-paper rounded px-3 py-1 text-sm mb-3"
                disabled={candidatos.length < 2 || comparando || cargando || !!errorCatalogo}
                onClick={() => alComparar(grupo.id)}
              >
                {comparando ? "Comparando…" : "Comparar"}
              </button>
              {comparacion?.estado === "corriendo" && (
                <div className="mb-3">
                  <BarraDeProgreso progreso={comparacion.progreso} />
                  <button className="underline text-sm" onClick={() => void alCancelarComparacion()}>
                    Cancelar
                  </button>
                </div>
              )}
              {comparacion?.estado === "cancelada" && <p className="text-sm mb-3">Comparación cancelada.</p>}
```

- [ ] **Step 4: Comprobar que compila y que las pruebas siguen**

Run (desde `frontend/`): `npx vitest run && npx tsc -b && npm run build`
Expected: todas pasan, sin errores de tipos, y compila. `grep -rn "compararFormatos\|useCompararFormatos" src` no encuentra nada.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/piezasYgrupos.ts frontend/src/hooks/useGrupos.ts frontend/src/routes/TrabajoWorkspace/GruposTab.tsx
git commit -m "feat(frontend): comparar chapas en segundo plano, con barra, cancelar y retomar (A7)"
```

---

## Tramo 4 — Recorrido y cierre

### Task 10: Recorrido en el navegador y documentos

**Files:**
- Modify: `docs/plan/PLAN-MAESTRO.md`, `docs/BITACORA.md`, `docs/plan/A7-progreso-del-anidado/diseno.md`, `docs/plan/A7-progreso-del-anidado/plan.md`

- [ ] **Step 1: La suite entera**

Run (desde `backend/`): la suite completa con los temporales en D: (ver «Global Constraints»).
Expected: todas pasan, ninguna salteada.

Run (desde `frontend/`): `npx vitest run && npm run build`
Expected: todas pasan y compila.

- [ ] **Step 2: Recorrido con Chrome sin ventana, sobre una copia de la base**

Antes de levantar nada, mirar quién escucha en 8000 y 5173 (si hay algo, es de Enzo: no tocarlo). Copiar `backend/local/carteleria.db` con el respaldo de SQLite a una carpeta en `backend/local/`, levantar el backend con `CARTELERIA_DATOS` apuntando a esa copia (`python -m uvicorn app.api.app:app --port 8000`, sin `--reload`) y el frontend con `npm run dev`. Con Chrome sin ventana (guiones de `backend/local/herramientas-*/`), en el trabajo «Complejo»:

1. Pestaña Anidado, un grupo con Sparrow y tiempo máximo de 60 s: la barra aparece, avanza, el texto nombra la pasada y el mejor resultado, y al terminar desaparece y la corrida queda en el historial. Captura a mitad de camino.
2. Pestaña Grupos, «Comparar formatos» con dos formatos y 30 s por formato: la barra dice «Formato 1 de 2 · …», avanza, y al terminar aparece la tabla. Captura a mitad de camino.
3. Otra comparación, y a mitad de camino recargar la página y volver a abrir «Comparar formatos» de ese grupo: se ve la barra donde iba.
4. Otra comparación y «Cancelar»: dice «Comparación cancelada» y la barra se va.

No borrar trabajos en la copia: sus DXF apuntan a los archivos reales. Al terminar, cerrar solo los procesos propios (por puerto y hora de inicio) y borrar la copia.

- [ ] **Step 3: Documentos**

- `docs/plan/PLAN-MAESTRO.md` §7, tabla «Pendientes del reparto por chapa»: sale la fila «Una comparación de formatos es un solo pedido que puede durar varias veces `PAR-09`…», y en la nota «Resueltos el 2026-10-14» de esa tabla se agrega: «Y en la rama `feat/progreso-del-anidado` (A7): barra de progreso al anidar y al comparar chapas, y la comparación en segundo plano, con cancelar y retomar».
- `docs/BITACORA.md`: en la entrada del día, un bloque «Barra de progreso (A7)» con qué se hizo, lo que se apartó del plan y lo que queda.
- `diseno.md` y `plan.md`: el renglón de **Estado** pasa a «construido el AAAA-MM-DD» y al final de `plan.md` va «## Desvíos», con un renglón por cosa hecha distinto de lo escrito, o «Ninguno.».

- [ ] **Step 4: Commit**

```bash
git add docs/plan/PLAN-MAESTRO.md docs/BITACORA.md docs/plan/A7-progreso-del-anidado
git commit -m "docs: barra de progreso (A7) construida"
```

---

## Desvíos

Lo que se hizo distinto de lo escrito arriba, el 2026-10-14.

- **Tarea 2: una prueba de antes contaba de más.** `test_lo_que_el_worker_da_por_mejor_es_lo_que_quedo_escrito` hacía fallar el segundo `Path.replace` del worker; con el archivo de progreso, el segundo reemplazo pasó a ser el del progreso. La prueba cuenta ahora solo los reemplazos de `salida.json`, que es lo que quiere probar. El código no cambió por esto.
- **Tarea 5: la función se reemplazó con un guion** (de la línea del decorador al final del archivo), no con la herramienta de edición: la función entera no entraba cómoda en un solo reemplazo. El resultado es el del plan y conserva los finales de línea del archivo.
- **Tarea 8: el registro de avance no anota un comando que no imprime nada.** La Tarea 8 se dio por cumplida con `npx vitest run` además de `npx tsc -b`.
- **Tarea 10, Step 1: la suite del backend no se volvió a correr entera.** Desde la Tarea 6 (675 en verde) no cambió ningún archivo del backend; se comprobó con `git diff 3c3f292..HEAD -- backend`.
- **Tarea 10, Step 2: el recorrido encontró dos avisos que confundían al retomar.** Después de recargar, el formulario de la comparación vuelve a sus valores de fábrica, y con la comparación corriendo aparecían «Seleccioná al menos dos formatos» y «puede demorar hasta 0 segundos». Se ocultan (commit aparte, sin prueba de componente: el frontend no tiene) y se comprobó de nuevo en Chrome sin ventana.
- **Tarea 10, Step 2: la primera vuelta del recorrido usó 30 s por formato** y la comparación terminó en «Sparrow excedió el tiempo máximo»: con «Complejo» la primera pasada tarda unos 30 s. No es de este cambio (la comparación de siempre hace lo mismo cuando un formato no llega a ningún resultado); quedó en los pendientes del reparto por chapa, y el recorrido se repitió con 60 s por formato.
- **El recorrido** (`backend/local/herramientas-progreso-2026-10-14/recorrido.mjs`, fuera de git, con sus capturas) corrió sobre una copia de la base de Enzo, con la migración `7f91bcd3ef15` aplicada en la copia. El anidado de «Complejo» dio 8 chapas en 60 s; la comparación de las chapas negras cal. 22 y cal. 20 de 1220 × 2440, 8 en las dos.
