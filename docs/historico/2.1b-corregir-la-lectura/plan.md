# 2.1b · Corregir a mano la lectura del DXF — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado:** **cerrado el 2026-10-13.** Ejecutado ese día, de la Tarea 0 a la 8, cada una con el ok de Enzo antes de su commit, y en `main` desde entonces ([PR #20](https://github.com/enzopazzelli/carteleria/pull/20); lo fusioné yo a pedido de Enzo). Un revisor aparte leyó la rama después de la Tarea 7: lo que dejó está en «Desvíos», al final, y con eso el backend quedó en 506 y el frontend en 95. Esta carpeta pasó de `docs/plan/` a `docs/historico/`; lo que quedó pendiente se sigue en [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md). Las rutas `docs/plan/2.1b-corregir-la-lectura/` que aparecen más abajo son las de cuando se escribió el plan.
>
> **El código de este plan está probado.** Entre el 2026-10-12 y el 13 se escribió sobre una copia limpia, fuera del repositorio, tarea por tarea y con las pruebas antes que el código. Cada prueba falló y pasó donde el plan dice. El backend terminó en 500 en verde (467 antes) y el frontend en 97 (56 antes), con `tsc` y `vite build` sin errores. **La pantalla se probó en un navegador sin ventana,** con clics, rueda y arrastre de verdad, contra una copia de la base y con un DXF que trae el logo solo: son el Step 9 de la Tarea 6 y el Step 1 de la Tarea 7. Ese ensayo corrigió el diseño (`diseno.md §8`).

**Goal:** Que quien carga un DXF pueda decir sobre el dibujo qué formas se cortan y cuáles no van, y acercar y mover ese dibujo, para que un diseño que las reglas leen mal entre bien sin tocar código.

**Architecture:** La pantalla no decide nada: cada clic suma o saca una corrección de una lista, y le vuelve a pedir la lectura al servidor con el archivo y la lista entera. En el servidor la lista entra en tres lugares. El lector (`dxf.py`) la usa para decidir qué agujeros salen, además, como formas. El análisis (`analisis.py`) le da a lo marcado el rol que se marcó, por encima de cualquier regla, y vuelve a decidir lo demás alrededor. Y la función `_leer` de las rutas deja lo que no va afuera de la unión y de los agujeros de las otras piezas. La carga recibe la misma lista y pasa por esa misma función, así que guarda lo que se vio. En la pantalla, las cuentas (qué hace un clic, en qué orden se dibuja, acercar, mover, cuál respuesta vale) son funciones puras de `dibujo.ts`; el panel solo las conecta con el ratón.

**Tech Stack:** Python 3.11+, shapely 2.1, ezdxf, FastAPI, pytest · React 18, TypeScript, Vite, vitest.

**Spec:** [`diseno.md`](diseno.md), en esta misma carpeta.

## Global Constraints

- Rama `feat/corregir-la-lectura`. Ya existe: sale de `main` (`27f0a6c`) y tiene el diseño (`31c4740`) y su corrección (`bbbd758`). Al final se abre un PR contra `main`; lo fusiona Enzo.
- **Cada commit espera el ok de Enzo.** Al terminar los pasos de una tarea se le muestra qué quedó (las pruebas; en la Tarea 6, las capturas de la pantalla) y recién con su ok se commitea. No se encadenan tareas.
- Commits y PR **sin** la línea `Co-Authored-By` ni la de «Generated with» (regla del proyecto).
- El CI corre con Python 3.11: nada que exista solo en 3.12 o 3.13.
- Valores por ID de `REGISTRO.md`: `PAR-52` (el detalle del dibujo, que cambia) y `PAR-53` (cuánto se puede acercar, que es nuevo). El número aparece una sola vez en el código, donde se define la constante, con su ID al lado. El registro cambia **en el mismo commit que el código**: `PAR-52` en la Tarea 2 y `PAR-53` en la Tarea 5.
- **El lector (`backend/app/services/ingesta/dxf.py`) se toca en un solo lugar,** la Tarea 3: `_clasificar_piezas_y_agujeros` y la firma de `parsear_dxf`. Sin correcciones tiene que dar, pieza por pieza, lo mismo que hoy: lo comprueba la Tarea 7 contra los DXF reales.
- Los archivos del repo están en CRLF. **No editar con `sed -i`**, que los pasa a LF: usar el editor. Los archivos nuevos también van en CRLF.
- El disco C: está casi lleno: todo lo temporal va en D:. Las pruebas del backend se corren con `--basetemp` y `CARTELERIA_DATOS` en D:.
- Probar siempre con `CARTELERIA_DATOS` apuntando a una carpeta temporal o a una **copia** de los datos, nunca contra `backend/local/`. Antes de levantar la app, mirar si ya hay algo escuchando en 8000 o en 5173: Enzo suele tenerla abierta contra su base, y otra sesión puede estar usando 8001, 5174 y 9222.
- `Presupuesto_Cliente_Carteleria.docx`, en la raíz, es de Enzo: no se toca ni se suma a ningún commit.
- Los textos de pantalla van en castellano y sin códigos (`PAR-xx`, `2.1b`).
- Comandos de prueba: backend `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest"`; frontend `cd frontend && npm run build && npm test`.

## Review Focus

1. **Dos clics seguidos, o cerrar el panel, antes de que llegue la lectura.** Vale la respuesta del último pedido; una que llega tarde no pisa el dibujo ni vuelve a abrir el panel que se canceló. Test en la Tarea 6 (`turnos`); el Step 9 de esa tarea recorre la pantalla con clics de verdad.
2. **Sacar una forma que tiene agujeros chicos** (los puntos de una leyenda, los tornillos de una placa). No se pierden con ella: pasan a ser formas. Y una forma que se marcó sigue a la vista aunque vuelva su contorno. Tests en la Tarea 3.
3. **Una corrección que se queda sin forma:** la de una pieza unida que ya no se arma porque se sacó una de sus formas, o la de una forma que solo está en la otra lectura. No da error y no hace nada. Tests en las Tareas 2 y 4; en la pantalla no figura en la lista (`correccionesALaVista`, Tarea 6).
4. **Cargar con una lista de correcciones que no sirve.** Da 400 diciendo qué, y no toca las piezas que el trabajo ya tenía. Test en la Tarea 2.
5. **Dos formas dibujadas en el mismo lugar** (una chapa dibujada sobre un contorno, una línea doble). La de abajo se tiene que poder tocar: la que se sacó pasa al fondo. Test en la Tarea 5 (`enOrdenDeDibujo`). En esa misma tarea, `sePuedeCargar` apaga «Cargar» cuando se sacó todo.

## Lo que este plan precisa del diseño

Al escribir el código aparecieron estos puntos, que el diseño no dice o dice sin detalle:

- **Los nombres.** El campo de los dos pedidos se llama `correcciones` y es un objeto JSON de nombre de forma a `cortar` o `no_va`. Cada forma de la lectura trae `estado` (`se_corta`, `descartada` o `no_va`) y `corregida`; cada lectura suma `no_van`. El campo `descartada` de la forma deja de existir.
- **Una forma que no va sale del lector con sus propios agujeros,** para dibujarla como es. Lo que deja de pasar es que ella sea el agujero de otra.
- **Qué nombre de forma da 400.** El que no es de una forma de este archivo. El de una pieza unida o de un hueco suyo (`…/unida`, `…/hueco2`) se acepta si su primera parte es una forma del archivo, esté o no armada esa unión ahora.
- **«Quitar todas» saca también las correcciones de la otra lectura** (la unida o la sin unir), que en la lista no se ven.
- **Con el dibujo entero a la vista, alejar con la rueda mueve la página,** como en cualquier otro lugar de la pantalla. La rueda solo queda para el dibujo cuando hay algo que acercar o alejar.
- **«Cargar» se apaga también mientras llega una lectura nueva:** lo que se ve no es todavía lo que se cargaría. Y se carga con la lista de la lectura que se está viendo, no con la del último clic.
- **Si la lectura nueva falla,** se sigue viendo la anterior y la lista de correcciones vuelve a ser la suya.
- **Lo que se corta lleva un fondo blanco** debajo de su relleno, cuando hay algo que no va: sin eso el rayado se ve a través.
- **El aviso de las formas que se pisan** ya no dice «marcá la casilla», que al cargar no está en pantalla: dice que se unen con la casilla «al ver cómo se lee».

---

## Archivos

| Archivo | Qué hace |
|---|---|
| `backend/app/services/ingesta/analisis.py` | El rol «no va», lo corregido manda (Tarea 1), y `sin_los_huecos_de_lo_que_no_va` (Tarea 4) |
| `backend/tests/services/ingesta/test_analisis.py` | Sus tests, al final |
| `backend/app/api/esquemas_trabajos.py` | Los tres estados de `FormaLeida` y el total `no_van` |
| `backend/app/api/rutas_trabajos.py` | El campo `correcciones` en los dos pedidos, `_correcciones`, `_roles`, y en `_leer` lo que pasa con lo que no va |
| `backend/app/services/ingesta/dibujo.py` | El valor de `PAR-52` |
| `backend/tests/api/test_rutas_trabajos.py` | Tests de las dos rutas con correcciones |
| `backend/app/services/ingesta/dxf.py` | `marcadas` y `no_van` en `parsear_dxf` |
| `backend/tests/services/ingesta/test_dxf.py` | Sus tests |
| `frontend/src/api/piezasYgrupos.ts` | Los tipos de la lectura con tres estados, `Correcciones`, y la lista en `leerDxf` y `subirDxf` |
| `frontend/src/api/piezasYgrupos.test.ts` | **Nuevo.** Que la lista viaja en los dos pedidos |
| `frontend/src/hooks/usePiezas.ts` | La lista en `useLeerDxf` y `useSubirDxf` |
| `frontend/src/components/LecturaDxf/dibujo.ts` | Las cuentas: el clic, el orden de dibujo, los textos, acercar y mover, los turnos |
| `frontend/src/components/LecturaDxf/dibujo.test.ts` | Sus tests |
| `frontend/src/components/LecturaDxf/LecturaPanel.tsx` | El panel: tres estados (Tarea 5) y corregir, acercar y mover (Tarea 6) |
| `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx` | Guarda la lista y vuelve a pedir la lectura en cada clic |
| `docs/REGISTRO.md`, `docs/BITACORA.md`, `docs/plan/2.1b-corregir-la-lectura/diseno.md` | Los dos parámetros, lo construido y lo medido |

Fuera del repositorio, en `backend/local/herramientas-2.1b-2026-10-12/`, quedan las herramientas con que se ensayó y que este plan vuelve a usar: `armar_logo_dxf.py` (escribe `logo-awaduct.dxf`, el logo solo, sacado de la muestra), `clics_del_logo.py` (los clics por los pedidos de verdad) y `ver_correcciones.mjs` (los mismos clics, la rueda y el arrastre en un Chrome sin ventana). En ese archivo, el número de cada forma es el que tiene en la muestra menos 497.

**Cómo leer los cambios.** Cada «Reemplazar… por…» y cada «Después de este bloque…» nombra un texto que aparece una sola vez en su archivo. Los bloques se muestran sin los renglones en blanco de arriba y de abajo: al agregar una función o un test hay que dejar los dos renglones en blanco de separación que usa el archivo. Ante la duda, el archivo exacto de cada paso, con sus renglones en blanco y su fin de línea, está en el repo del ensayo, que quedó en esta máquina fuera del repositorio: `git -C .superpowers/ensayo-2.1b show T3-codigo:backend/app/services/ingesta/dxf.py` muestra ese archivo como quedó al terminar la Tarea 3. Hay una marca `Tn-tests` (las pruebas solas) y una `Tn-codigo` por cada tarea de la 1 a la 6.

---

### Task 0: Punto de partida

**Files:** ninguno.

- [x] **Step 1: Pararse en la rama**

```bash
git switch feat/corregir-la-lectura
git status --short
git log --oneline -1
```

Expected: nada modificado, y el último commit es el que guardó este plan, arriba de `bbbd758` (el diseño corregido). Puede figurar `?? Presupuesto_Cliente_Carteleria.docx`: es de Enzo, no se toca ni se suma a ningún commit.

- [x] **Step 2: Confirmar que el backend está en verde**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest"`
Expected: `467 passed`. Las tareas siguientes suman tests sobre ese número.

- [x] **Step 3: Confirmar que el frontend está en verde**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `Tests  56 passed (56)`.

---

### Task 1: El análisis respeta lo que marcó quien carga

**Files:**
- Modify: `backend/app/services/ingesta/analisis.py` (`Rol`, `PiezaConRol`, `sugerir_roles`, `_heredar_referencia_de_gemelas`, `_marcar_contrapiezas`)
- Test: `backend/tests/services/ingesta/test_analisis.py` (al final)

**Interfaces:**
- Consumes: nada de otras tareas.
- Produces: `Rol.NO_VA` (su valor es `"no_va"`). `PiezaConRol.corregida: bool`, por defecto `False`. `sugerir_roles` conserva sus siete parámetros y suma un octavo, opcional: `correcciones: Mapping[str, Rol] | None = None`, de `id` de pieza a `Rol.CORTAR` o `Rol.NO_VA`. Una pieza con corrección sale con ese rol, el motivo `"lo marcó quien carga"` y `corregida=True`.

- [x] **Step 1: Agregar los tests**

En `backend/tests/services/ingesta/test_analisis.py`:

Al final del archivo, agregar:

```python
# --- Correcciones de quien carga (2.1b) -------------------------------------
#
# Quien carga puede forzar una forma a «se corta» o a «no va» mirando el
# dibujo (`docs/plan/2.1b-corregir-la-lectura/diseno.md §5.1`). Lo corregido
# manda, y lo demás se vuelve a decidir alrededor.


def _roles_corregidos(piezas: list[PiezaImportada], correcciones: dict[str, Rol]):
    disenio = DisenioDetectado(piezas=piezas)
    hojas = detectar_hojas(disenio, [_CHAPA], _TOLERANCIA_HOJA_MM)
    return {
        r.pieza_id: r
        for r in sugerir_roles(
            disenio,
            hojas,
            [_CHAPA],
            _TOLERANCIA_GEMELA,
            _AREA_MINIMA_GEMELA_MM2,
            _FRACCION_MINIMA_EN_HOJA,
            _COLORES_DE_ROTULO,
            correcciones,
        )
    }


def _contorno_con_letra():
    """Como el logo de la muestra: un contorno que rodea una letra, y la
    letra con su centro, los tres del mismo color."""
    return [
        _con_color(_octogono("contorno", 0, 0, 900), 7),
        _con_color(_octogono("letra", 200, 200, 500, contenida_en_id="contorno"), 7),
        _con_color(_octogono("centro", 350, 350, 200, contenida_en_id="letra"), 7),
    ]


def test_sin_corregir_un_contorno_con_una_letra_adentro_se_lee_al_reves():
    # No falla ninguna regla: un contorno con una forma de su color adentro
    # se lee igual que una «O» con su centro.
    roles = _roles_corregidos(_contorno_con_letra(), {})

    assert roles["contorno"].rol is Rol.CORTAR
    assert roles["letra"].rol is Rol.CONTRAPIEZA
    assert roles["centro"].rol is Rol.CORTAR
    assert not any(r.corregida for r in roles.values())


def test_sacar_un_contorno_pone_a_cortar_lo_que_encierra():
    roles = _roles_corregidos(_contorno_con_letra(), {"contorno": Rol.NO_VA})

    assert roles["contorno"].rol is Rol.NO_VA
    assert roles["contorno"].corregida
    assert "quien carga" in roles["contorno"].motivo
    # La letra ya no es el recorte de nadie, y su centro pasa a ser el suyo.
    assert roles["letra"].rol is Rol.CORTAR
    assert not roles["letra"].corregida
    assert roles["centro"].rol is Rol.CONTRAPIEZA
    assert roles["centro"].madre_id == "letra"


def test_una_forma_forzada_a_cortar_no_pasa_a_recorte():
    roles = _roles_corregidos(_contorno_con_letra(), {"letra": Rol.CORTAR})

    assert roles["letra"].rol is Rol.CORTAR
    assert roles["letra"].corregida
    assert roles["letra"].madre_id is None
    # El contorno no cambia; y como la letra se corta, su centro es su recorte.
    assert roles["contorno"].rol is Rol.CORTAR
    assert roles["centro"].rol is Rol.CONTRAPIEZA


def test_lo_de_adentro_de_una_forma_forzada_a_cortar_es_su_recorte():
    # Un tablero rectangular de 3 m: solo, es referencia y lo de adentro se
    # corta. Si quien carga dice que el tablero se corta, lo de adentro es
    # su hueco.
    tablero = _con_color(_rectangulo("tablero", 0, 0, 3000, 3000), 250)
    pieza = _con_color(_octogono("pieza", 1000, 1000, 400, contenida_en_id="tablero"), 250)

    sin_corregir = _roles_corregidos([tablero, pieza], {})
    corregido = _roles_corregidos([tablero, pieza], {"tablero": Rol.CORTAR})

    assert sin_corregir["pieza"].rol is Rol.CORTAR
    assert corregido["tablero"].rol is Rol.CORTAR
    assert corregido["pieza"].rol is Rol.CONTRAPIEZA
    assert corregido["pieza"].madre_id == "tablero"


def test_una_hoja_de_chapa_dibujada_tambien_se_puede_sacar():
    # La chapa que el diseñador dibuja para marcar qué entra en cada una.
    hoja, letra = _en_una_hoja([_rectangulo("letra", 100, 100, 400, 400)])

    roles = _roles_corregidos([hoja, letra], {"hoja": Rol.NO_VA})

    assert roles["hoja"].rol is Rol.NO_VA
    assert roles["letra"].rol is Rol.CORTAR


def test_una_forma_forzada_a_cortar_no_hereda_la_referencia_de_su_contenedora():
    # El ojal de una «O» que ya está en una hoja no se corta aparte… salvo
    # que quien carga diga que sí.
    piezas = [*_hoja_y_ensamblado(), _rectangulo("ojal", 3100, 100, 20, 20, contenida_en_id="ensamblada")]

    assert _roles_corregidos(piezas, {})["ojal"].rol is Rol.REFERENCIA
    assert _roles_corregidos(piezas, {"ojal": Rol.CORTAR})["ojal"].rol is Rol.CORTAR


def test_una_correccion_sobre_una_forma_que_no_esta_no_hace_nada():
    piezas = _contorno_con_letra()

    assert _roles_corregidos(piezas, {"otra": Rol.NO_VA}) == _roles_corregidos(piezas, {})
```

- [x] **Step 2: Correr los tests y verlos fallar**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/services/ingesta/test_analisis.py`
Expected: `7 failed, 46 passed`. Cuatro fallan con `TypeError: sugerir_roles() takes 7 positional arguments but 8 were given` y tres con `AttributeError: type object 'Rol' has no attribute 'NO_VA'`:

- `test_sin_corregir_un_contorno_con_una_letra_adentro_se_lee_al_reves`
- `test_sacar_un_contorno_pone_a_cortar_lo_que_encierra`
- `test_una_forma_forzada_a_cortar_no_pasa_a_recorte`
- `test_lo_de_adentro_de_una_forma_forzada_a_cortar_es_su_recorte`
- `test_una_hoja_de_chapa_dibujada_tambien_se_puede_sacar`
- `test_una_forma_forzada_a_cortar_no_hereda_la_referencia_de_su_contenedora`
- `test_una_correccion_sobre_una_forma_que_no_esta_no_hace_nada`

El primero fija lo que pasa hoy sin corregir, pero usa el ayudante nuevo, que le pasa a `sugerir_roles` el parámetro que todavía no existe.

- [x] **Step 3: Cambiar el análisis**

En `backend/app/services/ingesta/analisis.py`:

**Cambio 1 de 8.** Después de este bloque, que queda igual:

```python
import math
```

agregar:

```python
from collections.abc import Mapping
```

**Cambio 2 de 8.** Después de este bloque, que queda igual:

```python
    CONTRAPIEZA = "contrapieza"
```

agregar:

```python
    #: No va: lo sacó quien carga, mirando el dibujo. No lo sugiere ninguna
    #: regla; solo llega como corrección (`sugerir_roles`). Lo que tiene
    #: adentro se lee como si esta forma no estuviera.
    NO_VA = "no_va"
```

**Cambio 3 de 8.** Después de este bloque, que queda igual:

```python
    no_entra_en_ninguna_chapa: bool = False
```

agregar:

```python
    #: El rol no salió de una regla: lo marcó quien carga. Ninguna pasada
    #: posterior lo cambia.
    corregida: bool = False
```

**Cambio 4 de 8.** Después de este bloque, que queda igual:

```python
    colores_de_rotulo: frozenset[int],
```

agregar:

```python
    correcciones: Mapping[str, Rol] | None = None,
```

**Cambio 5 de 8.** Reemplazar:

```python
    pieza que se corta es su contra-pieza (en una hoja armada, o fuera
    con el mismo color). Nunca se excluye nada en silencio: sin señal,
    el default es cortar."""
    por_id = {p.id: p for p in disenio.piezas}
    ids_de_hojas = {h.pieza_id for h in hojas}
```

por:

```python
    pieza que se corta es su contra-pieza (en una hoja armada, o fuera
    con el mismo color). Nunca se excluye nada en silencio: sin señal,
    el default es cortar.

    `correcciones` es lo que marcó quien carga mirando el dibujo: de `id`
    de pieza a `Rol.CORTAR` o `Rol.NO_VA`
    (`docs/plan/2.1b-corregir-la-lectura/diseno.md §5.1`). Lo corregido
    manda sobre cualquier regla, y las dos pasadas vuelven a decidir lo
    demás alrededor: lo que estaba adentro de una forma que ya no va deja
    de ser su recorte. Una corrección sobre una pieza que no está en el
    diseño no hace nada."""
    correcciones = correcciones or {}
    por_id = {p.id: p for p in disenio.piezas}
    ids_de_hojas = {h.pieza_id for h in hojas}
```

**Cambio 6 de 8.** Después de este bloque, que queda igual:

```python
    roles = []
    for pieza in disenio.piezas:
```

agregar:

```python
        if pieza.id in correcciones:
            roles.append(PiezaConRol(pieza.id, correcciones[pieza.id], "lo marcó quien carga", corregida=True))
            continue
```

**Cambio 7 de 8.** Reemplazar:

```python
    resultado = []
    for rol in roles:
        if rol.rol is Rol.CORTAR and rol.gemela_id is None:
            actual = por_id[rol.pieza_id]
            while actual.contenida_en_id is not None and actual.contenida_en_id in por_id:
```

por:

```python
    resultado = []
    for rol in roles:
        if rol.rol is Rol.CORTAR and rol.gemela_id is None and not rol.corregida:
            actual = por_id[rol.pieza_id]
            while actual.contenida_en_id is not None and actual.contenida_en_id in por_id:
```

**Cambio 8 de 8.** Reemplazar:

```python
    for pieza_id in sorted(rol_de, key=_profundidad):
        madre = rol_de.get(por_id[pieza_id].contenida_en_id or "")
        if madre is None or not _se_corta(pieza_id) or not _se_corta(madre.pieza_id):
            continue
        color = por_id[pieza_id].color_aci
```

por:

```python
    for pieza_id in sorted(rol_de, key=_profundidad):
        madre = rol_de.get(por_id[pieza_id].contenida_en_id or "")
        # Lo que marcó quien carga no se toca. Y una forma que no va no se
        # corta, así que no es madre de nadie: lo de adentro queda libre.
        if madre is None or rol_de[pieza_id].corregida:
            continue
        if not _se_corta(pieza_id) or not _se_corta(madre.pieza_id):
            continue
        color = por_id[pieza_id].color_aci
```

- [x] **Step 4: Correr los tests y verlos pasar**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/services/ingesta/test_analisis.py`
Expected: `53 passed`.

Y el backend entero: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest"`
Expected: `474 passed`.

- [x] **Step 5: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/app/services/ingesta/analisis.py backend/tests/services/ingesta/test_analisis.py
git commit -m "feat(ingesta): el analisis respeta lo que marco quien carga (2.1b)"
```

---

### Task 2: Los dos pedidos reciben la lista de correcciones

**Files:**
- Modify: `backend/app/api/esquemas_trabajos.py` (`FormaLeida`, `LecturaLeer`)
- Modify: `backend/app/api/rutas_trabajos.py` (`_hojas_y_roles`, `_roles` en lugar de `_recortes_de_huecos`, `_correcciones`, `_Lectura`, `_lectura`, `_leer`, `_para_dibujar`, `leer_dxf`, `subir_dxf`)
- Modify: `backend/app/services/ingesta/dibujo.py` (`DETALLE_DEL_DIBUJO`)
- Modify: `docs/REGISTRO.md` (la fila de `PAR-52`)
- Test: `backend/tests/api/test_rutas_trabajos.py`

**Interfaces:**
- Consumes: `Rol.NO_VA`, `PiezaConRol.corregida` y el parámetro `correcciones` de `sugerir_roles` (Tarea 1).
- Produces: el campo de formulario `correcciones` en `POST /trabajos/{id}/dxf/lectura` y en `POST /trabajos/{id}/dxf`: un texto con un objeto JSON, `{"<id de forma>": "cortar" | "no_va"}`; sin el campo, ninguna. En la respuesta de la lectura, cada forma trae `estado: "se_corta" | "descartada" | "no_va"`, `corregida: bool` y `motivo: str | None`, y ya no trae `descartada`; cada lectura trae `a_cortar`, `descartadas` y `no_van`. En las rutas: `_correcciones(texto: str | None) -> dict[str, Rol]`, `_roles(piezas, formatos, correcciones) -> dict[str, PiezaConRol]`, `_leer(ruta, escala_a_mm, tamano_maximo_agujero_mm, formatos, correcciones) -> _LecturasDeUnDXF`, y `_Lectura` con `no_van: set[str]` y `corregidas: set[str]`.

- [x] **Step 1: Cambiar y agregar los tests de las rutas**

Seis tests que ya existen leían `forma["descartada"]`; pasan a leer `forma["estado"]`. El resto es nuevo. En `backend/tests/api/test_rutas_trabajos.py`:

**Cambio 1 de 8.** Después de este bloque, que queda igual:

```python
from __future__ import annotations
```

agregar:

```python
import json
```

**Cambio 2 de 8.** Reemplazar:

```python
def _ver_lectura(cliente, trabajo_id, contenido, *, escala_a_mm="1"):
    return cliente.post(
        f"/trabajos/{trabajo_id}/dxf/lectura",
        files={"archivo": ("pieza.dxf", contenido, "application/dxf")},
        data={"escala_a_mm": escala_a_mm},
    )
```

por:

```python
def _ver_lectura(cliente, trabajo_id, contenido, *, escala_a_mm="1", correcciones=None):
    """`correcciones`: lo que viaja en ese campo. Un diccionario se manda
    como JSON; un texto, tal cual (para probar los que no sirven)."""
    datos = {"escala_a_mm": escala_a_mm}
    if correcciones is not None:
        datos["correcciones"] = correcciones if isinstance(correcciones, str) else json.dumps(correcciones)
    return cliente.post(
        f"/trabajos/{trabajo_id}/dxf/lectura",
        files={"archivo": ("pieza.dxf", contenido, "application/dxf")},
        data=datos,
    )
```

**Cambio 3 de 8.** Reemplazar:

```python
    assert (lectura["a_cortar"], lectura["descartadas"]) == (1, 1)
    formas = {round(max(x for x, _ in f["contorno_mm"]) - min(x for x, _ in f["contorno_mm"])): f for f in lectura["formas"]}
    assert formas[600]["descartada"] is False and formas[600]["motivo"] is None
    assert len(formas[600]["agujeros_mm"]) == 1
    assert formas[200]["descartada"] is True and "recorte" in formas[200]["motivo"]
    # En la posición del dibujo, no en el marco local en que se guarda: el
    # centro de la «O» arranca en x = 100.
```

por:

```python
    assert (lectura["a_cortar"], lectura["descartadas"]) == (1, 1)
    formas = {round(max(x for x, _ in f["contorno_mm"]) - min(x for x, _ in f["contorno_mm"])): f for f in lectura["formas"]}
    assert formas[600]["estado"] == "se_corta" and formas[600]["motivo"] is None
    assert len(formas[600]["agujeros_mm"]) == 1
    assert formas[200]["estado"] == "descartada" and "recorte" in formas[200]["motivo"]
    # En la posición del dibujo, no en el marco local en que se guarda: el
    # centro de la «O» arranca en x = 100.
```

**Cambio 4 de 8.** Reemplazar:

```python
    assert any("4 formas que se pisaban quedaron unidas en 1 pieza" in aviso for aviso in unida["advertencias"])
    pieza = next(f for f in unida["formas"] if f["id_origen"].endswith("/unida"))
    assert pieza["descartada"] is False
    assert len(pieza["agujeros_mm"]) == 2
    assert all(f["descartada"] for f in unida["formas"] if "/hueco" in f["id_origen"])
```

por:

```python
    assert any("4 formas que se pisaban quedaron unidas en 1 pieza" in aviso for aviso in unida["advertencias"])
    pieza = next(f for f in unida["formas"] if f["id_origen"].endswith("/unida"))
    assert pieza["estado"] == "se_corta"
    assert len(pieza["agujeros_mm"]) == 2
    assert all(f["estado"] == "descartada" for f in unida["formas"] if "/hueco" in f["id_origen"])
```

**Cambio 5 de 8.** Reemplazar:

```python
    guardadas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert sorted((p["id_origen"], p["descartada"]) for p in guardadas) == sorted(
        (f["id_origen"], f["descartada"]) for f in lectura["formas"]
    )
```

por:

```python
    guardadas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert sorted((p["id_origen"], p["descartada"]) for p in guardadas) == sorted(
        (f["id_origen"], f["estado"] == "descartada") for f in lectura["formas"]
    )
```

**Cambio 6 de 8.** Reemplazar:

```python
    assert (lectura["a_cortar"], lectura["descartadas"]) == (1, 2)
    assert all(f["descartada"] for f in lectura["formas"] if "/hueco" in f["id_origen"])
```

por:

```python
    assert (lectura["a_cortar"], lectura["descartadas"]) == (1, 2)
    assert all(f["estado"] == "descartada" for f in lectura["formas"] if "/hueco" in f["id_origen"])
```

**Cambio 7 de 8.** Reemplazar:

```python
    huecos = [f for f in lectura["formas"] if "/hueco" in f["id_origen"]]
    assert len(huecos) == 2
    assert all(f["descartada"] for f in huecos)
```

por:

```python
    huecos = [f for f in lectura["formas"] if "/hueco" in f["id_origen"]]
    assert len(huecos) == 2
    assert all(f["estado"] == "descartada" for f in huecos)
```

**Cambio 8 de 8.** Después de este bloque, que queda igual:

```python
    respuesta = _ver_lectura(cliente, _crear_trabajo(cliente)["id"], contenido, escala_a_mm="0")

    assert respuesta.status_code == 400
    assert "escala" in respuesta.json()["detail"]
```

agregar:

```python
# --- Corregir la lectura a mano (2.1b) -----------------------------------
#
# `docs/plan/2.1b-corregir-la-lectura/diseno.md`. Quien carga marca formas
# como «se corta» o «no va»; la lectura y la carga reciben la misma lista.


def _logo_chico(msp):
    """Como el logo de la muestra: un contorno de 900 que rodea una letra
    de 500, y la letra con su centro de 200. Sin corregir se lee al revés:
    el contorno se corta y la letra es su recorte."""
    _octogono(msp, 0, 0, 900)
    _octogono(msp, 200, 200, 500)
    _octogono(msp, 350, 350, 200)


def _por_ancho(formas) -> dict:
    """Las formas de una lectura, por su ancho en mm."""
    return {round(max(x for x, _ in f["contorno_mm"]) - min(x for x, _ in f["contorno_mm"])): f for f in formas}


def _totales(lectura) -> tuple[int, int, int]:
    return lectura["a_cortar"], lectura["descartadas"], lectura["no_van"]


def _trabajo_con_el_logo(cliente, tmp_path):
    """El trabajo, el DXF y el nombre de cada forma por su ancho."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "logo.dxf", _logo_chico)
    formas = _por_ancho(_ver_lectura(cliente, trabajo["id"], contenido).json()["sin_unir"]["formas"])
    return trabajo, contenido, {ancho: f["id_origen"] for ancho, f in formas.items()}


def test_la_lectura_dice_de_cada_forma_si_se_corta_entra_descartada_o_no_va(cliente, tmp_path):
    trabajo, contenido, _ = _trabajo_con_el_logo(cliente, tmp_path)

    lectura = _ver_lectura(cliente, trabajo["id"], contenido).json()["sin_unir"]

    formas = _por_ancho(lectura["formas"])
    assert [formas[ancho]["estado"] for ancho in (900, 500, 200)] == ["se_corta", "descartada", "se_corta"]
    assert not any(f["corregida"] for f in lectura["formas"])
    assert _totales(lectura) == (2, 1, 0)


def test_marcar_un_contorno_como_que_no_va_pone_a_cortar_lo_que_encierra(cliente, tmp_path):
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={ids[900]: "no_va"})

    assert respuesta.status_code == 200, respuesta.text
    lectura = respuesta.json()["sin_unir"]
    formas = _por_ancho(lectura["formas"])
    assert formas[900]["estado"] == "no_va" and formas[900]["corregida"] is True
    assert "quien carga" in formas[900]["motivo"]
    assert formas[500]["estado"] == "se_corta" and formas[500]["corregida"] is False
    assert formas[200]["estado"] == "descartada"
    assert _totales(lectura) == (1, 1, 1)
    assert any("1 forma" in aviso and "no va" in aviso for aviso in lectura["advertencias"])


def test_cargar_con_correcciones_no_guarda_lo_que_no_va(cliente, tmp_path):
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)

    respuesta = _subir(cliente, trabajo["id"], contenido, correcciones=json.dumps({ids[900]: "no_va"}))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["piezas_creadas"] == 2
    assert any("no va" in aviso for aviso in cuerpo["advertencias"])
    piezas = {round(Decimal(p["ancho_mm"])): p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()}
    assert sorted(piezas) == [200, 500], "el contorno no se cargó"
    assert piezas[500]["descartada"] is False
    assert piezas[200]["descartada"] is True


def test_lo_que_muestra_la_lectura_corregida_es_lo_que_guarda_la_carga(cliente, tmp_path):
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)
    correcciones = {ids[900]: "no_va", ids[200]: "cortar"}
    lectura = _ver_lectura(cliente, trabajo["id"], contenido, correcciones=correcciones).json()["sin_unir"]

    _subir(cliente, trabajo["id"], contenido, correcciones=json.dumps(correcciones))

    guardadas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert sorted((p["id_origen"], p["descartada"]) for p in guardadas) == sorted(
        (f["id_origen"], f["estado"] == "descartada") for f in lectura["formas"] if f["estado"] != "no_va"
    )
    assert _totales(lectura) == (2, 0, 1), "el centro forzado a cortar no pasa a recorte de la letra"


def test_un_hueco_de_la_pieza_unida_se_puede_poner_a_cortar(cliente, tmp_path):
    """Los huecos de una pieza unida entran descartados por cómo se arman;
    lo que marca quien carga también manda sobre eso. Y la corrección
    nombra una forma que solo existe en la lectura unida: la otra lectura
    no hace nada con ella."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)
    antes = _ver_lectura(cliente, trabajo["id"], contenido).json()
    hueco = next(f["id_origen"] for f in antes["unida"]["formas"] if "/hueco" in f["id_origen"])

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={hueco: "cortar"})

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    forma = next(f for f in cuerpo["unida"]["formas"] if f["id_origen"] == hueco)
    assert forma["estado"] == "se_corta" and forma["corregida"] is True
    assert _totales(cuerpo["unida"]) == (2, 1, 0)
    assert _totales(cuerpo["sin_unir"]) == _totales(antes["sin_unir"])


@pytest.mark.parametrize(
    "correcciones, dice",
    [
        ("esto no es json", "correcciones"),
        ('["una-forma"]', "correcciones"),
        ('{"una-forma": "hueco"}', "hueco"),
        ('{"forma-que-no-existe": "no_va"}', "forma-que-no-existe"),
    ],
)
def test_unas_correcciones_que_no_sirven_dan_400_y_dicen_por_que(cliente, tmp_path, correcciones, dice):
    trabajo, contenido, _ = _trabajo_con_el_logo(cliente, tmp_path)

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones=correcciones)

    assert respuesta.status_code == 400
    assert dice in respuesta.json()["detail"]


def test_cargar_con_unas_correcciones_que_no_sirven_no_toca_las_piezas_del_trabajo(cliente, tmp_path):
    trabajo, pieza = _trabajo_con_una_pieza(cliente, tmp_path)
    contenido = _dxf_bytes(tmp_path, "logo.dxf", _logo_chico)

    respuesta = _subir(cliente, trabajo["id"], contenido, correcciones='{"forma-que-no-existe": "no_va"}')

    assert respuesta.status_code == 400
    assert [p["id"] for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()] == [pieza["id"]]
```

- [x] **Step 2: Correr los tests y verlos fallar**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/api/test_rutas_trabajos.py`
Expected: `16 failed, 35 passed`. Diez fallan con `KeyError: 'estado'`; los demás, porque el pedido todavía no mira el campo `correcciones`: cinco con `assert 200 == 400` y uno con una pieza guardada de más (`assert 3 == 2`). Son:

- los seis que se cambiaron: `test_la_lectura_trae_cada_forma_en_su_lugar_y_cuales_entran_descartadas`, `test_la_lectura_de_formas_que_se_pisan_trae_tambien_la_unida`, `test_lo_que_muestra_la_lectura_es_lo_que_guarda_la_carga` (dos casos), `test_los_huecos_de_la_pieza_unida_entran_descartados_aunque_no_se_sepa_su_color` y `test_un_hueco_rectangular_de_la_pieza_unida_entra_descartado_aunque_no_entre_en_ninguna_chapa`;
- `test_la_lectura_dice_de_cada_forma_si_se_corta_entra_descartada_o_no_va`
- `test_marcar_un_contorno_como_que_no_va_pone_a_cortar_lo_que_encierra`
- `test_cargar_con_correcciones_no_guarda_lo_que_no_va`
- `test_lo_que_muestra_la_lectura_corregida_es_lo_que_guarda_la_carga`
- `test_un_hueco_de_la_pieza_unida_se_puede_poner_a_cortar`
- `test_unas_correcciones_que_no_sirven_dan_400_y_dicen_por_que` (cuatro casos)
- `test_cargar_con_unas_correcciones_que_no_sirven_no_toca_las_piezas_del_trabajo`

- [x] **Step 3: Los tres estados en el esquema**

En `backend/app/api/esquemas_trabajos.py`:

**Cambio 1 de 3.** Después de este bloque, que queda igual:

```python
from decimal import Decimal
```

agregar:

```python
from typing import Literal
```

**Cambio 2 de 3.** Reemplazar:

```python
    contorno_mm: list[list[float]]
    agujeros_mm: list[list[list[float]]]
    descartada: bool
    #: Por qué entra descartada; `None` si se corta.
    motivo: str | None
```

por:

```python
    contorno_mm: list[list[float]]
    agujeros_mm: list[list[list[float]]]
    #: `se_corta`: se carga y se anida. `descartada`: se carga atenuada,
    #: sin cortarse (el recorte de un hueco). `no_va`: la sacó quien
    #: carga, y no se carga.
    estado: Literal["se_corta", "descartada", "no_va"]
    #: El estado no salió de una regla: lo marcó quien carga.
    corregida: bool
    #: Por qué entra descartada o no va; `None` si se corta sin que nadie
    #: lo haya marcado.
    motivo: str | None
```

**Cambio 3 de 3.** Reemplazar:

```python
class LecturaLeer(BaseModel):
    formas: list[FormaLeida]
    #: Todo lo que no entra descartado, igual que al cargar: incluye lo
    #: que después hay que seccionar.
    a_cortar: int
    descartadas: int
    advertencias: list[str]
```

por:

```python
class LecturaLeer(BaseModel):
    formas: list[FormaLeida]
    #: Todo lo que se carga sin descartar, igual que al cargar: incluye
    #: lo que después hay que seccionar.
    a_cortar: int
    descartadas: int
    no_van: int
    advertencias: list[str]
```

- [x] **Step 4: La lista en las rutas**

En `backend/app/api/rutas_trabajos.py`:

**Cambio 1 de 21.** Reemplazar:

```python
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from decimal import Decimal
```

por:

```python
from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
```

**Cambio 2 de 21.** Después de este bloque, que queda igual:

```python
    DisenioDetectado,
```

agregar:

```python
    PiezaConRol,
```

**Cambio 3 de 21.** Reemplazar:

```python
def _hojas_y_roles(disenio: DisenioDetectado, formatos: list[Plancha]):
    hojas = detectar_hojas(disenio, formatos, TOLERANCIA_MEDIDA_DE_HOJA_MM)
    return hojas, sugerir_roles(
```

por:

```python
def _hojas_y_roles(
    disenio: DisenioDetectado, formatos: list[Plancha], correcciones: Mapping[str, Rol] | None = None
):
    hojas = detectar_hojas(disenio, formatos, TOLERANCIA_MEDIDA_DE_HOJA_MM)
    return hojas, sugerir_roles(
```

**Cambio 4 de 21.** Reemplazar:

```python
        FRACCION_MINIMA_EN_HOJA,
        COLORES_DE_ROTULO,
    )


def _recortes_de_huecos(piezas: list[PiezaImportada], formatos: list[Plancha]) -> dict[str, str]:
    """Las formas que son el recorte del agujero de otra pieza que se
    corta (el centro de una «O», el hueco de un aro), cada una con el
    motivo que dio el análisis: el lector las devuelve como agujero de
    esa pieza y además como pieza propia (`_clasificar_piezas_y_agujeros`
    en `dxf.py`), y anidarlas contaría dos veces su área.

    Lo decide el análisis de `CART-511` (`Rol.CONTRAPIEZA`). De sus otros
    roles no se usa ninguno acá: una forma que no entra en ninguna chapa
    o que parece un rótulo se sigue importando como hasta ahora, y qué
    hacer con ella lo resuelve quien revisa las piezas."""
    recortes: dict[str, str] = {}
    for disenio in agrupar_en_disenios(piezas, DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM):
        _, roles = _hojas_y_roles(disenio, formatos)
        recortes.update({rol.pieza_id: rol.motivo for rol in roles if rol.rol is Rol.CONTRAPIEZA})
    return recortes
```

por:

```python
        FRACCION_MINIMA_EN_HOJA,
        COLORES_DE_ROTULO,
        correcciones,
    )


def _roles(
    piezas: list[PiezaImportada], formatos: list[Plancha], correcciones: Mapping[str, Rol]
) -> dict[str, PiezaConRol]:
    """El rol que el análisis de `CART-511` le da a cada forma, con lo que
    marcó quien carga. De esos roles la carga usa dos:

    - `Rol.CONTRAPIEZA`, el recorte del agujero de otra pieza que se corta
      (el centro de una «O», el hueco de un aro): el lector la devuelve
      como agujero de esa pieza y además como pieza propia
      (`_clasificar_piezas_y_agujeros` en `dxf.py`), y anidarla contaría
      dos veces su área. Entra descartada.
    - `Rol.NO_VA`, lo que sacó quien carga. No se guarda.

    Con los demás no hace nada: una forma que no entra en ninguna chapa o
    que parece un rótulo se importa igual, y qué hacer con ella lo
    resuelve quien mira el dibujo o revisa las piezas."""
    roles: dict[str, PiezaConRol] = {}
    for disenio in agrupar_en_disenios(piezas, DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM):
        _, del_disenio = _hojas_y_roles(disenio, formatos, correcciones)
        roles.update({rol.pieza_id: rol for rol in del_disenio})
    return roles


_ROL_DE_UNA_CORRECCION = {"cortar": Rol.CORTAR, "no_va": Rol.NO_VA}


def _correcciones(texto: str | None) -> dict[str, Rol]:
    """Lo que marcó quien carga, como llega en el campo `correcciones`: un
    objeto JSON de `id` de forma a `cortar` o `no_va`
    (`docs/plan/2.1b-corregir-la-lectura/diseno.md §5.2`). Sin el campo,
    ninguna. Lo que no tiene esa forma da 400, diciendo qué."""
    if texto is None or not texto.strip():
        return {}
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Las correcciones no son un JSON válido ({error.msg})."
        ) from error
    if not isinstance(datos, dict):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Las correcciones tienen que ser un objeto: de nombre de forma a «cortar» o «no_va».",
        )
    correcciones = {}
    for forma, valor in datos.items():
        if not isinstance(valor, str) or valor not in _ROL_DE_UNA_CORRECCION:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"«{valor}» no es una corrección: para «{forma}» tiene que ser «cortar» o «no_va».",
            )
        correcciones[forma] = _ROL_DE_UNA_CORRECCION[valor]
    return correcciones
```

**Cambio 5 de 21.** Reemplazar:

```python
class _Lectura:
    """Una manera de leer un DXF: las piezas que salen, cuáles entran
    descartadas y los avisos. Es lo que se dibuja y lo que se guarda."""

    piezas: list[PiezaImportada]
    #: `id` de la pieza → por qué entra descartada.
    recortes: dict[str, str]
    advertencias: list[str]
```

por:

```python
class _Lectura:
    """Una manera de leer un DXF: las piezas que salen, cuáles entran
    descartadas, cuáles no van y los avisos. Es lo que se dibuja y lo que
    se guarda."""

    piezas: list[PiezaImportada]
    #: `id` de la pieza → por qué entra descartada.
    recortes: dict[str, str]
    #: Las que sacó quien carga: no se guardan.
    no_van: set[str]
    #: Las que marcó quien carga, se corten o no vayan.
    corregidas: set[str]
    advertencias: list[str]

    def estado(self, pieza_id: str) -> str:
        if pieza_id in self.no_van:
            return "no_va"
        return "descartada" if pieza_id in self.recortes else "se_corta"

    def motivo(self, pieza_id: str) -> str | None:
        if pieza_id in self.corregidas:
            return "lo marcó quien carga"
        return self.recortes.get(pieza_id)
```

**Cambio 6 de 21.** Después de este bloque, que queda igual:

```python
    avisos: list[str],
```

agregar:

```python
    correcciones: Mapping[str, Rol],
```

**Cambio 7 de 21.** Reemplazar:

```python
    Entran descartados siempre: son huecos por cómo se armaron, y el
    análisis, que pide el color de la madre o que no sea un rectángulo
    que no entra, a veces no los reconoce (revisión de la rama). Si el
    análisis también los reconoce, queda su motivo."""
    recortes = {**(huecos_de_uniones or {}), **_recortes_de_huecos(piezas, formatos)}
    if recortes:
        avisos = [
```

por:

```python
    Entran descartados siempre: son huecos por cómo se armaron, y el
    análisis, que pide el color de la madre o que no sea un rectángulo
    que no entra, a veces no los reconoce (revisión de la rama de 2.1a).
    Si el análisis también los reconoce, queda su motivo.

    Lo que marcó quien carga manda también sobre eso: un hueco forzado a
    cortar no entra descartado."""
    roles = _roles(piezas, formatos, correcciones)
    corregidas = {pieza_id for pieza_id, rol in roles.items() if rol.corregida}
    no_van = {pieza_id for pieza_id, rol in roles.items() if rol.rol is Rol.NO_VA}
    recortes = {
        **{hueco: motivo for hueco, motivo in (huecos_de_uniones or {}).items() if hueco not in corregidas},
        **{pieza_id: rol.motivo for pieza_id, rol in roles.items() if rol.rol is Rol.CONTRAPIEZA},
    }
    if recortes:
        avisos = [
```

**Cambio 8 de 21.** Reemplazar:

```python
            "y entran descartadas: no se cortan ni se anidan. Si alguna se corta aparte, tocá «Restaurar».",
        ]
    return _Lectura(piezas=piezas, recortes=recortes, advertencias=avisos)


def _leer(
    ruta: Path, escala_a_mm: Decimal, tamano_maximo_agujero_mm: Decimal | None, formatos: list[Plancha]
) -> _LecturasDeUnDXF:
    """Parsea el archivo y arma sus dos lecturas: tal como viene, y con
    las formas que se pisan unidas (`uniones.py`). Las usan la ruta que
    muestra la lectura y la que carga, así que lo que se ve es lo que se
    guarda. Un archivo o una escala que no sirven dan 400."""
    tamano = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT if tamano_maximo_agujero_mm is None else tamano_maximo_agujero_mm
    try:
```

por:

```python
            "y entran descartadas: no se cortan ni se anidan. Si alguna se corta aparte, tocá «Restaurar».",
        ]
    if no_van:
        avisos = [*avisos, f"{len(no_van)} forma(s) no van: las marcaste en el dibujo, y no se cargan."]
    return _Lectura(piezas=piezas, recortes=recortes, no_van=no_van, corregidas=corregidas, advertencias=avisos)


def _leer(
    ruta: Path,
    escala_a_mm: Decimal,
    tamano_maximo_agujero_mm: Decimal | None,
    formatos: list[Plancha],
    correcciones: Mapping[str, Rol],
) -> _LecturasDeUnDXF:
    """Parsea el archivo y arma sus dos lecturas: tal como viene, y con
    las formas que se pisan unidas (`uniones.py`). Las usan la ruta que
    muestra la lectura y la que carga, así que lo que se ve es lo que se
    guarda. Un archivo o una escala que no sirven dan 400.

    `correcciones` se aplica a las dos lecturas. Cada una ignora las que
    nombran una forma que no tiene (el hueco de una pieza unida no existe
    en la lectura sin unir); una que no está en ninguna de las dos da 400."""
    tamano = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT if tamano_maximo_agujero_mm is None else tamano_maximo_agujero_mm
    try:
```

**Cambio 9 de 21.** Reemplazar:

```python
        resultado.piezas, DISTANCIA_PARA_TOCARSE_MM, AREA_MINIMA_PARA_PISARSE_MM2, tamano
    )
    avisos = list(resultado.advertencias)
    if not uniones:
        return _LecturasDeUnDXF(resultado, _lectura(resultado.piezas, formatos, avisos), None, 0)

    se_pisan = sum(len(union.lineas) for union in uniones)
```

por:

```python
        resultado.piezas, DISTANCIA_PARA_TOCARSE_MM, AREA_MINIMA_PARA_PISARSE_MM2, tamano
    )
    ajenas = sorted(set(correcciones) - {p.id for p in resultado.piezas} - {p.id for p in unidas})
    if ajenas:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Las correcciones nombran formas que no están en este archivo: {', '.join(ajenas)}.",
        )
    avisos = list(resultado.advertencias)
    if not uniones:
        return _LecturasDeUnDXF(resultado, _lectura(resultado.piezas, formatos, avisos, correcciones), None, 0)

    se_pisan = sum(len(union.lineas) for union in uniones)
```

**Cambio 10 de 21.** Reemplazar:

```python
            *avisos,
            f"Hay {se_pisan} formas que se pisan entre sí, sin unir. Si son franjas de una misma pieza, "
            "marcá «Unir las formas que se pisan».",
        ],
    )
    unida = _lectura(
```

por:

```python
            *avisos,
            f"Hay {se_pisan} formas que se pisan entre sí, sin unir. Si son franjas de una misma pieza, "
            "se unen con la casilla «Unir las formas que se pisan», al ver cómo se lee.",
        ],
        correcciones,
    )
    unida = _lectura(
```

**Cambio 11 de 21.** Después de este bloque, que queda igual:

```python
        [*avisos, f"{se_pisan} formas que se pisaban quedaron unidas en {len(uniones)} pieza(s)."],
```

agregar:

```python
        correcciones,
```

**Cambio 12 de 21.** Reemplazar:

```python
                contorno_mm=anillo_para_dibujar(pieza.contorno_mm, tolerancia),
                agujeros_mm=[anillo_para_dibujar(agujero, tolerancia) for agujero in pieza.agujeros_mm],
                descartada=pieza.id in lectura.recortes,
                motivo=lectura.recortes.get(pieza.id),
            )
            for pieza in lectura.piezas
        ],
        a_cortar=len(lectura.piezas) - len(lectura.recortes),
        descartadas=len(lectura.recortes),
        advertencias=lectura.advertencias,
    )
```

por:

```python
                contorno_mm=anillo_para_dibujar(pieza.contorno_mm, tolerancia),
                agujeros_mm=[anillo_para_dibujar(agujero, tolerancia) for agujero in pieza.agujeros_mm],
                estado=lectura.estado(pieza.id),
                corregida=pieza.id in lectura.corregidas,
                motivo=lectura.motivo(pieza.id),
            )
            for pieza in lectura.piezas
        ],
        a_cortar=len(lectura.piezas) - len(lectura.recortes) - len(lectura.no_van),
        descartadas=len(lectura.recortes),
        no_van=len(lectura.no_van),
        advertencias=lectura.advertencias,
    )
```

**Cambio 13 de 21.** Después de este bloque, que queda igual:

```python
async def leer_dxf(
    trabajo_id: int,
    archivo: UploadFile = File(...),
    escala_a_mm: Decimal = Form(...),
    tamano_maximo_agujero_mm: Decimal | None = Form(None),
```

agregar:

```python
    correcciones: str | None = Form(None),
```

**Cambio 14 de 21.** Reemplazar:

```python
    pisan, también la lectura con esas formas unidas: la pantalla cambia
    de una a otra sin volver a mandar el archivo. Cargar es otro pedido,
    `POST /trabajos/{id}/dxf`, con `unir` según lo que se eligió."""
    _trabajo_o_404(sesion, trabajo_id)
    sufijo = Path(archivo.filename or "trabajo.dxf").suffix or ".dxf"
    with tempfile.TemporaryDirectory() as carpeta:
```

por:

```python
    pisan, también la lectura con esas formas unidas: la pantalla cambia
    de una a otra sin volver a mandar el archivo. Cargar es otro pedido,
    `POST /trabajos/{id}/dxf`, con `unir` según lo que se eligió.

    `correcciones` es lo que quien carga marcó sobre el dibujo
    (`_correcciones`). La pantalla vuelve a pedir la lectura después de
    cada clic, con la lista entera, y manda esa misma lista al cargar."""
    _trabajo_o_404(sesion, trabajo_id)
    marcadas = _correcciones(correcciones)
    sufijo = Path(archivo.filename or "trabajo.dxf").suffix or ".dxf"
    with tempfile.TemporaryDirectory() as carpeta:
```

**Cambio 15 de 21.** Reemplazar:

```python
        ruta = Path(carpeta) / f"trabajo-{trabajo_id}{sufijo}"
        ruta.write_bytes(await archivo.read())
        lecturas = _leer(ruta, escala_a_mm, tamano_maximo_agujero_mm, _formatos_del_catalogo(sesion))
    return LecturaDXFLeer(
        contornos_no_cerrados=len(lecturas.resultado.contornos_no_cerrados),
```

por:

```python
        ruta = Path(carpeta) / f"trabajo-{trabajo_id}{sufijo}"
        ruta.write_bytes(await archivo.read())
        lecturas = _leer(ruta, escala_a_mm, tamano_maximo_agujero_mm, _formatos_del_catalogo(sesion), marcadas)
    return LecturaDXFLeer(
        contornos_no_cerrados=len(lecturas.resultado.contornos_no_cerrados),
```

**Cambio 16 de 21.** Después de este bloque, que queda igual:

```python
    unir: bool = Form(False),
```

agregar:

```python
    correcciones: str | None = Form(None),
```

**Cambio 17 de 21.** Reemplazar:

```python
    `parsear_dxf`: nunca se asume la escala del header del archivo.

    Se guardan todas las formas que devuelve el parser. Las que son el
    recorte del hueco de otra pieza entran descartadas, con un aviso
    (`_recortes_de_huecos`).

    Con `unir`, las formas que se pisan entran como una sola pieza
    (`uniones.py`). Es lo que eligió quien carga después de ver la
    lectura (`POST /trabajos/{id}/dxf/lectura`); sin eso no se une nada.

    Volver a subir un archivo (para corregir la escala o el propio DXF)
```

por:

```python
    `parsear_dxf`: nunca se asume la escala del header del archivo.

    Se guardan todas las formas que devuelve el parser, menos las que
    quien carga marcó como que no van. Las que son el recorte del hueco
    de otra pieza entran descartadas, con un aviso (`_roles`).

    Con `unir`, las formas que se pisan entran como una sola pieza
    (`uniones.py`). Es lo que eligió quien carga después de ver la
    lectura (`POST /trabajos/{id}/dxf/lectura`); sin eso no se une nada.
    `correcciones` es lo que marcó sobre ese dibujo (`_correcciones`).

    Volver a subir un archivo (para corregir la escala o el propio DXF)
```

**Cambio 18 de 21.** Después de este bloque, que queda igual:

```python
    """
    trabajo = _trabajo_o_404(sesion, trabajo_id)
```

agregar:

```python
    marcadas = _correcciones(correcciones)
```

**Cambio 19 de 21.** Reemplazar:

```python
    ruta_guardada.write_bytes(contenido)

    lecturas = _leer(ruta_guardada, escala_a_mm, tamano_maximo_agujero_mm, _formatos_del_catalogo(sesion))
    lectura = lecturas.elegida(unir)
```

por:

```python
    ruta_guardada.write_bytes(contenido)

    lecturas = _leer(ruta_guardada, escala_a_mm, tamano_maximo_agujero_mm, _formatos_del_catalogo(sesion), marcadas)
    lectura = lecturas.elegida(unir)
```

**Cambio 20 de 21.** Reemplazar:

```python
    sesion.flush()

    for pieza_importada in lectura.piezas:
        pieza = _pieza_orm_desde_importada(trabajo_id, pieza_importada)
        # Descartada y no omitida: queda a la vista, y si en este dibujo
```

por:

```python
    sesion.flush()

    a_guardar = [p for p in lectura.piezas if p.id not in lectura.no_van]
    for pieza_importada in a_guardar:
        pieza = _pieza_orm_desde_importada(trabajo_id, pieza_importada)
        # Descartada y no omitida: queda a la vista, y si en este dibujo
```

**Cambio 21 de 21.** Reemplazar:

```python
    return ImportacionDXFLeer(
        trabajo=TrabajoLeer.model_validate(trabajo),
        piezas_creadas=len(lectura.piezas),
        contornos_no_cerrados=len(lecturas.resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=lecturas.resultado.lineas_duplicadas_descartadas,
```

por:

```python
    return ImportacionDXFLeer(
        trabajo=TrabajoLeer.model_validate(trabajo),
        piezas_creadas=len(a_guardar),
        contornos_no_cerrados=len(lecturas.resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=lecturas.resultado.lineas_duplicadas_descartadas,
```

- [x] **Step 5: El detalle del dibujo, y su fila del registro**

En `backend/app/services/ingesta/dibujo.py`:

**El cambio.** Reemplazar:

```python
#: `PAR-52`. Cuánto se puede apartar del original un contorno dibujado,
#: como fracción del lado mayor del dibujo.
DETALLE_DEL_DIBUJO = Decimal(1) / Decimal(4000)

Anillo = list[tuple[Decimal, Decimal]]
```

por:

```python
#: `PAR-52`. Cuánto se puede apartar del original un contorno dibujado,
#: como fracción del lado mayor del dibujo. Alcanza para acercar el
#: dibujo hasta `PAR-53` sin que las curvas se vean facetadas.
DETALLE_DEL_DIBUJO = Decimal(1) / Decimal(20000)

Anillo = list[tuple[Decimal, Decimal]]
```

En `docs/REGISTRO.md`, en la fila de `PAR-52`: el valor pasa de `1/4000` a `1/20000`, la fuente de `historico/2.1a-lectura-con-imagen/diseno.md` a `plan/2.1b-corregir-la-lectura/diseno.md`, y el texto de la última columna pasa a decir:

```markdown
🟡 provisorio — 1/4000 desde el 2026-10-12; pasó a 1/20000 cuando el dibujo se pudo acercar (2.1b), en `backend/app/services/ingesta/dibujo.py`. Con este valor el dibujo de `Complejo.dxf` (7,76 m de lado) se aparta a lo sumo 0,39 mm del original, y acercado `PAR-53` veces eso es un píxel. Lo que pesa cada lectura está medido en la Tarea 7 de `plan/2.1b-corregir-la-lectura/plan.md`
```

- [x] **Step 6: Correr los tests y verlos pasar**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/api/test_rutas_trabajos.py`
Expected: `51 passed`.

Y el backend entero: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest"`
Expected: `484 passed`.

En este punto la pantalla de `main` deja de mostrar bien la lectura, porque todavía lee `descartada`: la arregla la Tarea 5. Por eso las Tareas 2 a 6 van en el mismo PR.

- [x] **Step 7: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/app/api/esquemas_trabajos.py backend/app/api/rutas_trabajos.py backend/app/services/ingesta/dibujo.py backend/tests/api/test_rutas_trabajos.py docs/REGISTRO.md
git commit -m "feat(ingesta): la lectura y la carga reciben correcciones, y lo que no va no se carga (2.1b)"
```

---

### Task 3: El lector: los agujeros de lo que no va pasan a ser formas

El lector decide si un contorno es pieza o agujero por cuántos lo encierran: con una cantidad par es pieza; con una impar es agujero, y además pieza si mide más de 25 mm. Un punto de 20 mm adentro de un contorno es, entonces, solo su agujero: al sacar el contorno se perdería con él. En el logo de la muestra son los dos puntos de la leyenda (`diseno.md §2`).

**Files:**
- Modify: `backend/app/services/ingesta/dxf.py` (`_clasificar_piezas_y_agujeros`, `_id` nuevo, `_pieza_desde_clasificacion`, `parsear_dxf`)
- Modify: `backend/app/api/rutas_trabajos.py` (`_leer`)
- Test: `backend/tests/services/ingesta/test_dxf.py`
- Test: `backend/tests/api/test_rutas_trabajos.py`

**Interfaces:**
- Consumes: `_leer(..., correcciones: Mapping[str, Rol])` (Tarea 2).
- Produces: `parsear_dxf(ruta, escala_a_mm, tamano_maximo_agujero_mm=..., *, marcadas: Collection[str] = (), no_van: Collection[str] = ())`. Las dos colecciones son `id` de formas (`<nombre del archivo>-<número>`). Un contorno de `marcadas` sale siempre como pieza. Los agujeros de un contorno de `no_van` salen, además, como piezas. Un `id` que no es de un contorno del archivo no hace nada. Sin las dos, el resultado es el de hoy.

- [x] **Step 1: Agregar los tests del lector**

En `backend/tests/services/ingesta/test_dxf.py`:

**El cambio.** Después de este bloque, que queda igual:

```python
    assert len(resultado.piezas[0].agujeros_mm) == 1
```

agregar:

```python
# --- Lo que marcó quien carga (2.1b) -------------------------------------
#
# `docs/plan/2.1b-corregir-la-lectura/diseno.md §5.1`. Un agujero chico no
# es una forma aparte: es solo el hueco de la que lo encierra. Si esa no
# va, el agujero se quedaría sin madre y se perdería con ella.


def _dos_contornos_con_un_punto(msp):
    """Dos contornos de 200, cada uno con un punto de 10 adentro: tan
    chico que el lector lo toma por un agujero, y nada más."""
    for x in (0, 300):
        msp.add_lwpolyline([(x, 0), (x + 200, 0), (x + 200, 200), (x, 200)], close=True)
        msp.add_lwpolyline([(x + 90, 90), (x + 100, 90), (x + 100, 100), (x + 90, 100)], close=True)


def _por_id(resultado) -> dict:
    return {pieza.id: pieza for pieza in resultado.piezas}


def test_un_punto_adentro_de_un_contorno_es_solo_su_agujero(tmp_path):
    ruta = _guardar_dxf(tmp_path, "puntos.dxf", _dos_contornos_con_un_punto)

    piezas = _por_id(parsear_dxf(ruta, _ESCALA_IDENTIDAD))

    assert sorted(piezas) == ["puntos-0", "puntos-2"]
    assert len(piezas["puntos-0"].agujeros_mm) == 1


def test_los_agujeros_de_una_forma_que_no_va_pasan_a_ser_formas(tmp_path):
    ruta = _guardar_dxf(tmp_path, "puntos.dxf", _dos_contornos_con_un_punto)

    piezas = _por_id(parsear_dxf(ruta, _ESCALA_IDENTIDAD, no_van={"puntos-0"}))

    assert sorted(piezas) == ["puntos-0", "puntos-1", "puntos-2"], "solo el punto del contorno que no va"
    assert piezas["puntos-1"].ancho_mm == Decimal("10")
    assert piezas["puntos-1"].contenida_en_id == "puntos-0"


def test_la_forma_que_no_va_se_sigue_dibujando_con_su_agujero(tmp_path):
    ruta = _guardar_dxf(tmp_path, "puntos.dxf", _dos_contornos_con_un_punto)

    piezas = _por_id(parsear_dxf(ruta, _ESCALA_IDENTIDAD, no_van={"puntos-0"}))

    assert len(piezas["puntos-0"].agujeros_mm) == 1


def test_una_forma_marcada_es_siempre_una_forma_aunque_sea_un_agujero_chico(tmp_path):
    # Quien carga marcó el punto cuando era una forma (su contorno no
    # iba) y después volvió a poner el contorno: el punto no desaparece
    # del dibujo con su marca puesta.
    ruta = _guardar_dxf(tmp_path, "puntos.dxf", _dos_contornos_con_un_punto)

    piezas = _por_id(parsear_dxf(ruta, _ESCALA_IDENTIDAD, marcadas={"puntos-1"}))

    assert sorted(piezas) == ["puntos-0", "puntos-1", "puntos-2"]
    assert len(piezas["puntos-0"].agujeros_mm) == 1, "sigue siendo, además, el agujero de su contorno"


def test_marcar_una_forma_que_no_es_de_este_archivo_no_cambia_nada(tmp_path):
    # La pieza unida y sus huecos (`uniones.py`) tienen nombres que el
    # lector no conoce: no son contornos del archivo.
    ruta = _guardar_dxf(tmp_path, "puntos.dxf", _dos_contornos_con_un_punto)

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD, marcadas={"puntos-0/unida", "otro-1"}, no_van={"puntos-0/unida"})

    assert sorted(_por_id(resultado)) == ["puntos-0", "puntos-2"]
```

- [x] **Step 2: Agregar los tests de las rutas**

En `backend/tests/api/test_rutas_trabajos.py`:

**El cambio.** Después de este bloque, que queda igual:

```python
    assert _totales(cuerpo["sin_unir"]) == _totales(antes["sin_unir"])
```

agregar:

```python
def _leyenda_con_un_punto(msp):
    """Un contorno de 900 que rodea una letra de 500 y un punto de 20. El
    punto es tan chico que el lector lo toma por un agujero del contorno,
    no por una forma: sin corregir no aparece en la lectura."""
    _octogono(msp, 0, 0, 900)
    _octogono(msp, 100, 200, 500)
    _octogono(msp, 700, 200, 20)


def _trabajo_con_la_leyenda(cliente, tmp_path):
    """El trabajo, el DXF y el nombre del contorno."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "leyenda.dxf", _leyenda_con_un_punto)
    formas = _por_ancho(_ver_lectura(cliente, trabajo["id"], contenido).json()["sin_unir"]["formas"])
    assert sorted(formas) == [500, 900], "el punto no es una forma hasta que se saca el contorno"
    return trabajo, contenido, formas[900]["id_origen"]


def test_al_sacar_un_contorno_sus_agujeros_chicos_pasan_a_cortarse(cliente, tmp_path):
    trabajo, contenido, contorno = _trabajo_con_la_leyenda(cliente, tmp_path)

    lectura = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={contorno: "no_va"}).json()["sin_unir"]

    formas = _por_ancho(lectura["formas"])
    assert [formas[ancho]["estado"] for ancho in (900, 500, 20)] == ["no_va", "se_corta", "se_corta"]
    assert _totales(lectura) == (2, 0, 1)


def test_cargar_sin_el_contorno_guarda_el_punto(cliente, tmp_path):
    trabajo, contenido, contorno = _trabajo_con_la_leyenda(cliente, tmp_path)

    respuesta = _subir(cliente, trabajo["id"], contenido, correcciones=json.dumps({contorno: "no_va"}))

    assert respuesta.status_code == 200, respuesta.text
    piezas = {round(Decimal(p["ancho_mm"])): p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()}
    assert sorted(piezas) == [20, 500]
    assert not piezas[20]["descartada"]


def test_un_punto_marcado_sigue_a_la_vista_aunque_vuelva_su_contorno(cliente, tmp_path):
    """Quien carga saca el contorno, saca también el punto, y después se
    arrepiente del contorno. El punto vuelve a ser su agujero, pero la
    marca sigue puesta y se tiene que poder sacar: si no fuera una forma,
    el pedido daría 400 por nombrar una que no existe."""
    trabajo, contenido, contorno = _trabajo_con_la_leyenda(cliente, tmp_path)
    sin_contorno = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={contorno: "no_va"}).json()
    punto = _por_ancho(sin_contorno["sin_unir"]["formas"])[20]["id_origen"]

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={punto: "no_va"})

    assert respuesta.status_code == 200, respuesta.text
    formas = _por_ancho(respuesta.json()["sin_unir"]["formas"])
    assert formas[20]["estado"] == "no_va" and formas[20]["corregida"] is True
    assert formas[900]["estado"] == "se_corta"
```

- [x] **Step 3: Correr los tests y verlos fallar**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/services/ingesta/test_dxf.py tests/api/test_rutas_trabajos.py`
Expected: `7 failed, 72 passed`. Los cuatro del lector fallan con `TypeError: parsear_dxf() got an unexpected keyword argument 'no_van'` (o `'marcadas'`); los tres de las rutas, porque el punto no aparece (`KeyError: 20`, o `assert [500] == [20, 500]` en la carga):

- `test_los_agujeros_de_una_forma_que_no_va_pasan_a_ser_formas`
- `test_la_forma_que_no_va_se_sigue_dibujando_con_su_agujero`
- `test_una_forma_marcada_es_siempre_una_forma_aunque_sea_un_agujero_chico`
- `test_marcar_una_forma_que_no_es_de_este_archivo_no_cambia_nada`
- `test_al_sacar_un_contorno_sus_agujeros_chicos_pasan_a_cortarse`
- `test_cargar_sin_el_contorno_guarda_el_punto`
- `test_un_punto_marcado_sigue_a_la_vista_aunque_vuelva_su_contorno`

`test_un_punto_adentro_de_un_contorno_es_solo_su_agujero` pasa desde ya: fija lo que el lector hace hoy, que es lo que no tiene que cambiar.

- [x] **Step 4: Cambiar el lector**

En `backend/app/services/ingesta/dxf.py`:

**Cambio 1 de 10.** Después de este bloque, que queda igual:

```python
from collections import Counter
```

agregar:

```python
from collections.abc import Collection
```

**Cambio 2 de 10.** Después de este bloque, que queda igual:

```python
    tamano_maximo_agujero_mm: Decimal | None,
```

agregar:

```python
    marcados: Collection[int] = (),
    no_van: Collection[int] = (),
```

**Cambio 3 de 10.** Reemplazar:

```python
    aparece como su propia pieza en la lista de anidado — ninguna de
    las dos cosas se pierde. `None` desactiva el umbral: nada se
    promueve, solo para tests que prueban la clasificación en sí."""
    n = len(contornos)
    bounds = [c.poligono.bounds for c in contornos]
```

por:

```python
    aparece como su propia pieza en la lista de anidado — ninguna de
    las dos cosas se pierde. `None` desactiva el umbral: nada se
    promueve, solo para tests que prueban la clasificación en sí.

    **Lo que marcó quien carga también promueve**
    (`docs/plan/2.1b-corregir-la-lectura/diseno.md §5.1`), por el
    `indice` del contorno. Uno de `marcados` es siempre pieza propia: si
    no, su marca nombraría una forma que no está. Y los agujeros de uno
    de `no_van` también: un agujero es el hueco de algo que se corta, y
    su padre ya no va. Sin esto, el punto de una leyenda rodeada por un
    contorno (un agujero de 20 mm) se perdería junto con el contorno.
    El que no va sigue saliendo con sus agujeros, para dibujarlo."""
    n = len(contornos)
    bounds = [c.poligono.bounds for c in contornos]
```

**Cambio 4 de 10.** Reemplazar:

```python
        return ancho > float(tamano_maximo_agujero_mm) or alto > float(tamano_maximo_agujero_mm)

    es_pieza_propia = [nivel[i] % 2 == 0 or _demasiado_grande_para_agujero(i) for i in range(n)]

    resultado = []
```

por:

```python
        return ancho > float(tamano_maximo_agujero_mm) or alto > float(tamano_maximo_agujero_mm)

    def _su_padre_no_va(i: int) -> bool:
        padre = padre_inmediato[i]
        return padre is not None and contornos[padre].indice in no_van

    es_pieza_propia = [
        nivel[i] % 2 == 0
        or _demasiado_grande_para_agujero(i)
        or contornos[i].indice in marcados
        or _su_padre_no_va(i)
        for i in range(n)
    ]

    resultado = []
```

**Cambio 5 de 10.** Después de este bloque, que queda igual:

```python
    return resultado
```

agregar:

```python
def _id(ruta: str | Path, contorno: _ContornoValido) -> str:
    """El nombre de un contorno: el del archivo y su número de orden. Es
    el `id` de su pieza, y el que usa quien carga para marcarlo."""
    return f"{Path(ruta).stem}-{contorno.indice}"
```

**Cambio 6 de 10.** Reemplazar:

```python
    minx, miny, maxx, maxy = pieza.poligono.bounds
    return PiezaImportada(
        id=f"{Path(ruta).stem}-{pieza.indice}",
        capa=pieza.capa,
        ancho_mm=Decimal(str(maxx - minx)),
```

por:

```python
    minx, miny, maxx, maxy = pieza.poligono.bounds
    return PiezaImportada(
        id=_id(ruta, pieza),
        capa=pieza.capa,
        ancho_mm=Decimal(str(maxx - minx)),
```

**Cambio 7 de 10.** Reemplazar:

```python
        contorno_mm=pieza.puntos,
        agujeros_mm=[a.puntos for a in agujeros],
        contenida_en_id=f"{Path(ruta).stem}-{contenedora.indice}" if contenedora is not None else None,
        color_aci=pieza.color,
    )
```

por:

```python
        contorno_mm=pieza.puntos,
        agujeros_mm=[a.puntos for a in agujeros],
        contenida_en_id=_id(ruta, contenedora) if contenedora is not None else None,
        color_aci=pieza.color,
    )
```

**Cambio 8 de 10.** Después de este bloque, que queda igual:

```python
    tamano_maximo_agujero_mm: Decimal | None = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT,
```

agregar:

```python
    *,
    marcadas: Collection[str] = (),
    no_van: Collection[str] = (),
```

**Cambio 9 de 10.** Después de este bloque, que queda igual:

```python
    de `_clasificar_piezas_y_agujeros`.
```

agregar:

```python
    `marcadas` y `no_van` son los `id` de las formas que quien carga
    marcó sobre el dibujo, y de esas, las que sacó. Cambian qué agujeros
    salen además como piezas (mismo docstring). Un `id` que no es de un
    contorno de este archivo no hace nada.
```

**Cambio 10 de 10.** Reemplazar:

```python
        contornos_validos.append(_ContornoValido(poligono, puntos, trazo.capa, trazo.indice, trazo.color))

    piezas = [
        _pieza_desde_clasificacion(ruta, pieza, agujeros, contenedora)
        for pieza, agujeros, contenedora in _clasificar_piezas_y_agujeros(contornos_validos, tamano_maximo_agujero_mm)
    ]
```

por:

```python
        contornos_validos.append(_ContornoValido(poligono, puntos, trazo.capa, trazo.indice, trazo.color))

    def _indices(ids: Collection[str]) -> set[int]:
        return {contorno.indice for contorno in contornos_validos if _id(ruta, contorno) in ids}

    piezas = [
        _pieza_desde_clasificacion(ruta, pieza, agujeros, contenedora)
        for pieza, agujeros, contenedora in _clasificar_piezas_y_agujeros(
            contornos_validos, tamano_maximo_agujero_mm, _indices(marcadas), _indices(no_van)
        )
    ]
```

- [x] **Step 5: Pasarle la lista desde las rutas**

En `backend/app/api/rutas_trabajos.py`:

**El cambio.** Reemplazar:

```python
    tamano = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT if tamano_maximo_agujero_mm is None else tamano_maximo_agujero_mm
    try:
        resultado = parsear_dxf(ruta, escala_a_mm, tamano)
    except ArchivoDXFInvalido as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
```

por:

```python
    tamano = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT if tamano_maximo_agujero_mm is None else tamano_maximo_agujero_mm
    try:
        # Lo marcado es siempre una forma, y los agujeros de una que no
        # va también: se quedaron sin la pieza de la que eran el hueco.
        resultado = parsear_dxf(
            ruta,
            escala_a_mm,
            tamano,
            marcadas=set(correcciones),
            no_van={id_forma for id_forma, rol in correcciones.items() if rol is Rol.NO_VA},
        )
    except ArchivoDXFInvalido as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
```

- [x] **Step 6: Correr los tests y verlos pasar**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/services/ingesta/test_dxf.py tests/api/test_rutas_trabajos.py`
Expected: `79 passed`.

Y el backend entero: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest"`
Expected: `492 passed`.

- [x] **Step 7: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/app/services/ingesta/dxf.py backend/app/api/rutas_trabajos.py backend/tests/services/ingesta/test_dxf.py backend/tests/api/test_rutas_trabajos.py
git commit -m "feat(ingesta): los agujeros de una forma que no va pasan a ser formas (2.1b)"
```

---

### Task 4: Lo que no va no se une ni es el hueco de nadie

Dos cosas más que salen de «una forma que no va no es madre de nadie» (`diseno.md §5.1`). La unión de las formas que se pisan se arma sin lo que no va: si no, la casilla vuelve a meter en una sola mancha los contornos que se sacaron. Y una forma que no va deja de ser el agujero de la pieza que la tiene adentro: en el logo, la mitad repetida del palo de la «T» cae adentro de la letra, y el lector la toma por un agujero.

**Files:**
- Modify: `backend/app/services/ingesta/analisis.py` (`sin_los_huecos_de_lo_que_no_va`, nueva, al final)
- Modify: `backend/app/api/rutas_trabajos.py` (`_leer`)
- Test: `backend/tests/services/ingesta/test_analisis.py` (al final)
- Test: `backend/tests/api/test_rutas_trabajos.py`

**Interfaces:**
- Consumes: `_leer` con las correcciones y `parsear_dxf(..., marcadas=, no_van=)` (Tareas 2 y 3).
- Produces: `sin_los_huecos_de_lo_que_no_va(piezas: list[PiezaImportada], no_van: Collection[str]) -> list[PiezaImportada]`: las mismas piezas, y a las que tenían como agujero el contorno de una forma de `no_van` se lo saca y les recalcula `area_real_mm2`. En la lectura, lo que no va queda afuera de la unión y sigue figurando en la lectura unida con su estado. Una corrección cuyo nombre tiene `/` y cuya primera parte es una forma del archivo no da 400 aunque esa pieza unida no exista.

- [x] **Step 1: Agregar los tests del análisis**

En `backend/tests/services/ingesta/test_analisis.py`:

**Cambio 1 de 2.** Después de este bloque, que queda igual:

```python
    detectar_hojas,
```

agregar:

```python
    sin_los_huecos_de_lo_que_no_va,
```

**Cambio 2 de 2.** Después de este bloque, que queda igual:

```python
    assert _roles_corregidos(piezas, {"otra": Rol.NO_VA}) == _roles_corregidos(piezas, {})
```

agregar:

```python
def _letra_con_su_centro() -> list[PiezaImportada]:
    """Una letra de 100 con un centro de 20, que es su agujero y además
    una forma aparte: así lo arma el lector."""
    centro = _rectangulo("centro", 40, 40, 20, 20, contenida_en_id="letra")
    letra = replace(
        _rectangulo("letra", 0, 0, 100, 100), agujeros_mm=[centro.contorno_mm], area_real_mm2=Decimal(100 * 100 - 20 * 20)
    )
    return [letra, centro]


def test_una_pieza_pierde_el_agujero_que_era_una_forma_que_no_va():
    # La mitad de una letra dibujada dos veces cae adentro de la letra, y
    # el lector la toma por un agujero. Sacándola, la letra queda llena.
    letra, centro = sin_los_huecos_de_lo_que_no_va(_letra_con_su_centro(), {"centro"})

    assert letra.agujeros_mm == []
    assert letra.area_real_mm2 == Decimal(100 * 100)
    assert centro.contorno_mm == _letra_con_su_centro()[1].contorno_mm, "la forma que no va no cambia"


def test_una_pieza_conserva_los_agujeros_de_las_formas_que_siguen():
    piezas = _letra_con_su_centro()

    assert sin_los_huecos_de_lo_que_no_va(piezas, set()) == piezas
    assert sin_los_huecos_de_lo_que_no_va(piezas, {"letra", "otra"}) == piezas, "sacar la letra no le saca su agujero"
```

- [x] **Step 2: Agregar los tests de las rutas**

En `backend/tests/api/test_rutas_trabajos.py`:

**El cambio.** Después de este bloque, que queda igual:

```python
    assert _totales(cuerpo["sin_unir"]) == _totales(antes["sin_unir"])
```

agregar:

```python
def _tres_formas_en_fila(msp):
    """Tres octógonos de 600, cada uno montado 100 mm sobre el anterior:
    el primero se pisa con el segundo y el segundo con el tercero."""
    for x in (0, 500, 1000):
        _octogono(msp, x, 0, 600)


def _trabajo_con_las_tres_formas(cliente, tmp_path):
    """El trabajo, el DXF y los nombres de las formas, de izquierda a derecha."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "fila.dxf", _tres_formas_en_fila)
    antes = _ver_lectura(cliente, trabajo["id"], contenido).json()
    assert antes["formas_que_se_pisan"] == 3 and _totales(antes["unida"]) == (1, 0, 0)
    en_fila = sorted(antes["sin_unir"]["formas"], key=lambda f: min(x for x, _ in f["contorno_mm"]))
    return trabajo, contenido, [f["id_origen"] for f in en_fila]


def test_una_forma_que_no_va_no_se_une_con_las_que_pisa(cliente, tmp_path):
    """Lo que se sacó no es parte del diseño: la unión se arma sin eso, y
    la forma sigue a la vista en la lectura unida, para poder devolverla."""
    trabajo, contenido, (_, _, tercera) = _trabajo_con_las_tres_formas(cliente, tmp_path)

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={tercera: "no_va"}).json()

    assert cuerpo["formas_que_se_pisan"] == 2
    assert _totales(cuerpo["unida"]) == (1, 0, 1)
    unida = next(f for f in cuerpo["unida"]["formas"] if f["id_origen"].endswith("/unida"))
    assert round(max(x for x, _ in unida["contorno_mm"])) == 1100, "la pieza unida llega hasta la segunda forma"
    assert next(f for f in cuerpo["unida"]["formas"] if f["id_origen"] == tercera)["estado"] == "no_va"


def test_si_al_sacar_una_forma_ya_nada_se_pisa_no_hay_nada_que_unir(cliente, tmp_path):
    trabajo, contenido, (_, segunda, _) = _trabajo_con_las_tres_formas(cliente, tmp_path)

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={segunda: "no_va"}).json()

    assert cuerpo["formas_que_se_pisan"] == 0 and cuerpo["unida"] is None
    assert not any("se pisan" in aviso for aviso in cuerpo["sin_unir"]["advertencias"])
    assert _totales(cuerpo["sin_unir"]) == (2, 0, 1)


def test_la_marca_de_una_pieza_unida_que_ya_no_se_arma_queda_sin_efecto(cliente, tmp_path):
    """Quien carga saca la pieza unida y después, mirando la lectura sin
    unir, saca una de sus formas: la unión que queda es otra, o ninguna, y
    la primera marca nombra una pieza que ya no está. No es un error."""
    trabajo, contenido, (_, segunda, _) = _trabajo_con_las_tres_formas(cliente, tmp_path)
    antes = _ver_lectura(cliente, trabajo["id"], contenido).json()
    unida = next(f["id_origen"] for f in antes["unida"]["formas"] if f["id_origen"].endswith("/unida"))

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={unida: "no_va", segunda: "no_va"})

    assert respuesta.status_code == 200, respuesta.text
    assert _totales(respuesta.json()["sin_unir"]) == (2, 0, 1)


def test_una_forma_que_no_va_no_es_el_hueco_de_nadie(cliente, tmp_path):
    """Como el palo de la «T» del logo de la muestra: su mitad de abajo
    está dibujada otra vez, adentro de la letra, y el lector la toma por un
    agujero. Sacándola, la letra queda llena."""
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)
    antes = _por_ancho(_ver_lectura(cliente, trabajo["id"], contenido).json()["sin_unir"]["formas"])
    assert len(antes[500]["agujeros_mm"]) == 1

    lectura = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={ids[200]: "no_va"}).json()["sin_unir"]

    formas = _por_ancho(lectura["formas"])
    assert formas[200]["estado"] == "no_va"
    assert formas[500]["agujeros_mm"] == []
    assert len(formas[900]["agujeros_mm"]) == 1, "el contorno sigue con el suyo"


def test_cargar_sin_una_forma_que_era_un_hueco_guarda_la_pieza_llena(cliente, tmp_path):
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)

    respuesta = _subir(
        cliente, trabajo["id"], contenido, correcciones=json.dumps({ids[900]: "no_va", ids[200]: "no_va"})
    )

    assert respuesta.status_code == 200, respuesta.text
    (letra,) = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert round(Decimal(letra["ancho_mm"])) == 500
    assert letra["agujeros_mm"] == []


def test_un_hueco_de_la_pieza_unida_que_no_va_deja_de_ser_un_hueco(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)
    antes = _ver_lectura(cliente, trabajo["id"], contenido).json()["unida"]
    hueco = next(f["id_origen"] for f in antes["formas"] if f["id_origen"].endswith("/hueco1"))

    unida = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={hueco: "no_va"}).json()["unida"]

    pieza = next(f for f in unida["formas"] if f["id_origen"].endswith("/unida"))
    assert len(pieza["agujeros_mm"]) == 1, "tenía dos"
    assert _totales(unida) == (1, 1, 1)
```

- [x] **Step 3: Correr los tests y verlos fallar**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/services/ingesta/test_analisis.py`
Expected: `1 error`, con `ImportError: cannot import name 'sin_los_huecos_de_lo_que_no_va'`. El archivo entero no llega a correr.

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/api/test_rutas_trabajos.py`
Expected: `5 failed, 55 passed`:

- `test_una_forma_que_no_va_no_se_une_con_las_que_pisa`
- `test_si_al_sacar_una_forma_ya_nada_se_pisa_no_hay_nada_que_unir`
- `test_una_forma_que_no_va_no_es_el_hueco_de_nadie`
- `test_cargar_sin_una_forma_que_era_un_hueco_guarda_la_pieza_llena`
- `test_un_hueco_de_la_pieza_unida_que_no_va_deja_de_ser_un_hueco`

`test_la_marca_de_una_pieza_unida_que_ya_no_se_arma_queda_sin_efecto` pasa desde ya, porque hoy la unión se arma con todo y esa pieza unida sigue existiendo. Lo pone a prueba el Step 5: sin la parte que acepta los nombres con `/`, ese test da 400. Se vio fallar así en el ensayo.

- [x] **Step 4: La función que saca los huecos**

En `backend/app/services/ingesta/analisis.py`:

**Cambio 1 de 2.** Reemplazar:

```python
import enum
import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
```

por:

```python
import enum
import math
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
```

**Cambio 2 de 2.** Después de este bloque, que queda igual:

```python
    return [rol_de[r.pieza_id] for r in roles]
```

agregar:

```python
def sin_los_huecos_de_lo_que_no_va(piezas: list[PiezaImportada], no_van: Collection[str]) -> list[PiezaImportada]:
    """Las piezas, sin los agujeros que eran el contorno de una forma que
    quien carga sacó (`Rol.NO_VA`). Una forma que no va no es el hueco de
    nadie: la pieza que la tenía adentro queda llena ahí
    (`docs/plan/2.1b-corregir-la-lectura/diseno.md §5.1`).

    El lector toma por agujero a todo contorno que cae adentro de otro
    (`_clasificar_piezas_y_agujeros` en `dxf.py`), y no siempre lo es: en
    el logo de la muestra, la mitad de abajo del palo de la «T» está
    dibujada otra vez, adentro de la letra. Sirve igual para los huecos
    de una pieza unida (`uniones.py`), que también son formas aparte.

    Una pieza que no tenía ninguno de esos agujeros sale como entró."""
    fuera = {tuple(pieza.contorno_mm) for pieza in piezas if pieza.id in no_van}
    resultado = []
    for pieza in piezas:
        quedan = [agujero for agujero in pieza.agujeros_mm if tuple(agujero) not in fuera]
        if len(quedan) != len(pieza.agujeros_mm):
            llena = Polygon(
                [(float(x), float(y)) for x, y in pieza.contorno_mm],
                [[(float(x), float(y)) for x, y in agujero] for agujero in quedan],
            )
            pieza = replace(pieza, agujeros_mm=quedan, area_real_mm2=Decimal(str(llena.area)))
        resultado.append(pieza)
    return resultado
```

- [x] **Step 5: Usarla en la lectura, y unir sin lo que no va**

En `backend/app/api/rutas_trabajos.py`:

**Cambio 1 de 3.** Después de este bloque, que queda igual:

```python
    detectar_hojas,
```

agregar:

```python
    sin_los_huecos_de_lo_que_no_va,
```

**Cambio 2 de 3.** Reemplazar:

```python
    `correcciones` se aplica a las dos lecturas. Cada una ignora las que
    nombran una forma que no tiene (el hueco de una pieza unida no existe
    en la lectura sin unir); una que no está en ninguna de las dos da 400."""
    tamano = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT if tamano_maximo_agujero_mm is None else tamano_maximo_agujero_mm
    try:
        # Lo marcado es siempre una forma, y los agujeros de una que no
        # va también: se quedaron sin la pieza de la que eran el hueco.
        resultado = parsear_dxf(
            ruta,
            escala_a_mm,
            tamano,
            marcadas=set(correcciones),
            no_van={id_forma for id_forma, rol in correcciones.items() if rol is Rol.NO_VA},
        )
    except ArchivoDXFInvalido as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    unidas, uniones = unir_formas_que_se_pisan(
        resultado.piezas, DISTANCIA_PARA_TOCARSE_MM, AREA_MINIMA_PARA_PISARSE_MM2, tamano
    )
    ajenas = sorted(set(correcciones) - {p.id for p in resultado.piezas} - {p.id for p in unidas})
    if ajenas:
        raise HTTPException(
```

por:

```python
    `correcciones` se aplica a las dos lecturas. Cada una ignora las que
    nombran una forma que no tiene (el hueco de una pieza unida no existe
    en la lectura sin unir); una que no es de este archivo da 400. Lo que
    no va queda afuera de la unión, no es el hueco de ninguna pieza, y
    sus propios agujeros pasan a ser formas."""
    tamano = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT if tamano_maximo_agujero_mm is None else tamano_maximo_agujero_mm
    no_van = {id_forma for id_forma, rol in correcciones.items() if rol is Rol.NO_VA}
    try:
        # Lo marcado es siempre una forma, y los agujeros de una que no
        # va también: se quedaron sin la pieza de la que eran el hueco.
        resultado = parsear_dxf(ruta, escala_a_mm, tamano, marcadas=set(correcciones), no_van=no_van)
    except ArchivoDXFInvalido as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    # Lo que no va no es parte del diseño: no es el hueco de nadie ni se
    # une con nada. Pasa a la lectura unida como está, para verlo ahí y
    # poder sacarle la marca.
    piezas = sin_los_huecos_de_lo_que_no_va(resultado.piezas, no_van)
    unidas, uniones = unir_formas_que_se_pisan(
        [p for p in piezas if p.id not in no_van],
        DISTANCIA_PARA_TOCARSE_MM,
        AREA_MINIMA_PARA_PISARSE_MM2,
        tamano,
    )
    unidas = sin_los_huecos_de_lo_que_no_va([*unidas, *(p for p in piezas if p.id in no_van)], no_van)
    del_archivo = {p.id for p in piezas}
    # Una pieza unida o un hueco suyo (`…/unida`, `…/hueco2`) puede no
    # estar ahora: sacar una de sus formas cambia qué se une. Su marca
    # queda sin efecto hasta que la pieza vuelva; no es un error.
    ajenas = sorted(
        id_forma
        for id_forma in set(correcciones) - del_archivo - {p.id for p in unidas}
        if "/" not in id_forma or id_forma.split("/")[0] not in del_archivo
    )
    if ajenas:
        raise HTTPException(
```

**Cambio 3 de 3.** Reemplazar:

```python
    avisos = list(resultado.advertencias)
    if not uniones:
        return _LecturasDeUnDXF(resultado, _lectura(resultado.piezas, formatos, avisos, correcciones), None, 0)

    se_pisan = sum(len(union.lineas) for union in uniones)
    sin_unir = _lectura(
        resultado.piezas,
        formatos,
        [
```

por:

```python
    avisos = list(resultado.advertencias)
    if not uniones:
        return _LecturasDeUnDXF(resultado, _lectura(piezas, formatos, avisos, correcciones), None, 0)

    se_pisan = sum(len(union.lineas) for union in uniones)
    sin_unir = _lectura(
        piezas,
        formatos,
        [
```

- [x] **Step 6: Correr los tests y verlos pasar**

Run: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest" tests/services/ingesta/test_analisis.py tests/api/test_rutas_trabajos.py`
Expected: `115 passed`.

Y el backend entero: `cd backend && CARTELERIA_DATOS="D:/temp/carteleria-datos" python -m pytest -q --basetemp="D:/temp/carteleria-pytest"`
Expected: `500 passed`.

- [x] **Step 7: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/app/services/ingesta/analisis.py backend/app/api/rutas_trabajos.py backend/tests/services/ingesta/test_analisis.py backend/tests/api/test_rutas_trabajos.py
git commit -m "feat(ingesta): lo que no va no se une ni es el hueco de nadie (2.1b)"
```

---

### Task 5: La pantalla: las cuentas y los tres estados

Todo lo que la pantalla decide es una cuenta que se prueba sola, sin navegador: qué pasa con una forma cuando se la toca, en qué orden se dibujan, qué dice el resumen, y cómo cambia lo que se ve al acercar y al mover. El panel pasa a dibujar los tres estados; todavía no se puede tocar nada.

**Files:**
- Modify: `frontend/src/api/piezasYgrupos.ts` (`FormaLeida`, `Lectura`, `Correcciones`)
- Modify: `frontend/src/components/LecturaDxf/dibujo.ts`
- Modify: `frontend/src/components/LecturaDxf/LecturaPanel.tsx`
- Modify: `docs/REGISTRO.md` (alta de `PAR-53`)
- Test: `frontend/src/components/LecturaDxf/dibujo.test.ts`

**Interfaces:**
- Consumes: la respuesta de la lectura con `estado`, `corregida` y `no_van` (Tarea 2).
- Produces, en `piezasYgrupos.ts`: `FormaLeida.estado: "se_corta" | "descartada" | "no_va"`, `FormaLeida.corregida: boolean` (ya no `descartada`), `Lectura.no_van: number`, y `type Correcciones = Record<string, "cortar" | "no_va">`.
- Produces, en `dibujo.ts`:
  - `resumenDeLectura(lectura: Pick<Lectura, "a_cortar" | "descartadas" | "no_van">): string`
  - `sePuedeCargar(lectura: Pick<Lectura, "a_cortar">): boolean`
  - `nombreCorto(idOrigen: string): string`
  - `alTocar(correcciones: Correcciones, forma: Pick<FormaLeida, "id_origen" | "estado">): Correcciones`
  - `sinCorreccion(correcciones: Correcciones, idOrigen: string): Correcciones`
  - `enOrdenDeDibujo(formas: FormaLeida[]): FormaLeida[]`
  - `descripcion(forma: FormaLeida): string`
  - `AUMENTO_MAXIMO = 20`, `interface Vista { x; y; ancho; alto }`, `vistaEntera(caja: Caja): Vista`
  - `acercar(vista: Vista, entera: Vista, factor: number, x: number, y: number): Vista`, que devuelve el mismo objeto `entera` cuando ya no hay nada que alejar
  - `mover(vista: Vista, entera: Vista, dx: number, dy: number): Vista`
  - `fueUnClic(dxPx: number, dyPx: number): boolean`

- [x] **Step 1: Cambiar y agregar los tests**

Cambian los ayudantes de arriba y los tests del resumen, que ahora llevan `estado` y `no_van`, y se agrega casi todo lo demás. `frontend/src/components/LecturaDxf/dibujo.test.ts` queda entero así:

```ts
import { describe, expect, it } from "vitest";
import type { FormaLeida } from "../../api/piezasYgrupos";
import {
  AUMENTO_MAXIMO,
  acercar,
  alTocar,
  cajaDelDibujo,
  descripcion,
  enOrdenDeDibujo,
  esLaLecturaDe,
  fueUnClic,
  mover,
  nombreCorto,
  resumenDeLectura,
  sePuedeCargar,
  sinCorreccion,
  trazo,
  vistaEntera,
} from "./dibujo";

function forma(contorno: number[][], agujeros: number[][][] = [], extra: Partial<FormaLeida> = {}): FormaLeida {
  return {
    id_origen: "f",
    contorno_mm: contorno,
    agujeros_mm: agujeros,
    estado: "se_corta",
    corregida: false,
    motivo: null,
    ...extra,
  };
}

/** Un cuadrado de `lado` con su esquina de abajo a la izquierda en (x, y). */
function cuadradoDe(lado: number, x = 0, y = 0, extra: Partial<FormaLeida> = {}): FormaLeida {
  return forma([[x, y], [x + lado, y], [x + lado, y + lado], [x, y + lado], [x, y]], [], extra);
}

// Un cuadrado de 100 lejos del origen, como viene de un DXF.
const cuadrado = forma([[500, 200], [600, 200], [600, 300], [500, 300], [500, 200]]);

describe("cajaDelDibujo", () => {
  it("abarca todas las formas", () => {
    const otra = forma([[0, 0], [50, 0], [50, 20], [0, 0]]);
    expect(cajaDelDibujo([cuadrado, otra])).toEqual({ minX: 0, minY: 0, ancho: 600, alto: 300 });
  });

  it("sin formas no devuelve una caja de lado cero, que no dibuja nada", () => {
    expect(cajaDelDibujo([])).toEqual({ minX: 0, minY: 0, ancho: 1, alto: 1 });
  });

  it("una forma sin alto tampoco deja la caja en cero", () => {
    expect(cajaDelDibujo([forma([[0, 5], [10, 5], [0, 5]])]).alto).toBe(1);
  });
});

describe("trazo", () => {
  const caja = cajaDelDibujo([cuadrado]);

  it("mide desde la esquina de la caja y da vuelta la Y", () => {
    // El punto de abajo a la izquierda del DXF (500, 200) queda abajo a
    // la izquierda en la pantalla: x = 0, y = el alto de la caja.
    expect(trazo(cuadrado, caja)).toBe("M0 100 L100 100 L100 0 L0 0 L0 100 Z");
  });

  it("lo de arriba en el DXF queda arriba en la pantalla", () => {
    // Una «M» apoyada en y = 0, con sus dos puntas arriba (y = 10).
    const eme = forma([[0, 0], [0, 10], [5, 4], [10, 10], [10, 0], [0, 0]]);
    const puntas = trazo(eme, cajaDelDibujo([eme])).match(/L0 0|L10 0/g);
    expect(puntas).toEqual(["L0 0", "L10 0"]);
  });

  it("suma cada hueco como otro tramo cerrado", () => {
    const conHueco = forma(cuadrado.contorno_mm, [[[520, 220], [540, 220], [540, 240], [520, 220]]]);
    expect(trazo(conHueco, caja)).toBe(
      "M0 100 L100 100 L100 0 L0 0 L0 100 Z M20 80 L40 80 L40 60 L20 80 Z",
    );
  });

  it("redondea a centésimas de milímetro", () => {
    const fina = forma([[0, 0], [1.23456, 0], [1.23456, 1], [0, 0]]);
    expect(trazo(fina, { minX: 0, minY: 0, ancho: 2, alto: 1 })).toBe("M0 1 L1.23 1 L1.23 0 L0 1 Z");
  });

  it("ignora un anillo que no llega a ser una forma", () => {
    expect(trazo(forma([[0, 0], [1, 1]]), caja)).toBe("");
  });
});

describe("resumenDeLectura", () => {
  it("cuenta lo que se corta y lo que entra descartado", () => {
    expect(resumenDeLectura({ a_cortar: 24, descartadas: 34, no_van: 0 })).toBe(
      "24 piezas a cortar · 34 entran descartadas",
    );
  });

  it("habla en singular cuando es una", () => {
    expect(resumenDeLectura({ a_cortar: 1, descartadas: 1, no_van: 1 })).toBe(
      "1 pieza a cortar · 1 entra descartada · 1 no va",
    );
  });

  it("no nombra las descartadas si no hay", () => {
    expect(resumenDeLectura({ a_cortar: 12, descartadas: 0, no_van: 0 })).toBe("12 piezas a cortar");
  });

  it("suma las que no van", () => {
    expect(resumenDeLectura({ a_cortar: 17, descartadas: 2, no_van: 15 })).toBe(
      "17 piezas a cortar · 2 entran descartadas · 15 no van",
    );
  });
});

describe("sePuedeCargar", () => {
  it("no, si no queda nada para cortar: cargar eso borraría las piezas del trabajo", () => {
    expect(sePuedeCargar({ a_cortar: 0 })).toBe(false);
  });

  it("sí, con una sola pieza a cortar", () => {
    expect(sePuedeCargar({ a_cortar: 1 })).toBe(true);
  });
});

describe("nombreCorto", () => {
  it("es el número de la forma, sin el nombre del archivo", () => {
    expect(nombreCorto("trabajo-1-497")).toBe("497");
  });

  it("conserva lo que sigue a la barra: la pieza unida y sus huecos", () => {
    expect(nombreCorto("trabajo-1-39/unida")).toBe("39/unida");
    expect(nombreCorto("trabajo-12-39/hueco7")).toBe("39/hueco7");
  });

  it("deja igual un nombre sin guiones", () => {
    expect(nombreCorto("suelta")).toBe("suelta");
  });
});

describe("alTocar", () => {
  it("una forma que se corta pasa a «no va»", () => {
    expect(alTocar({}, { id_origen: "a", estado: "se_corta" })).toEqual({ a: "no_va" });
  });

  it("una que entra descartada pasa a «se corta»", () => {
    expect(alTocar({}, { id_origen: "a", estado: "descartada" })).toEqual({ a: "cortar" });
  });

  it("una que ya se forzó a cortar pasa a «no va»: es como se saca un recorte que no era un hueco", () => {
    expect(alTocar({ a: "cortar" }, { id_origen: "a", estado: "se_corta" })).toEqual({ a: "no_va" });
  });

  it("una que ya se sacó vuelve a lo que decida el sistema: se le saca la corrección", () => {
    expect(alTocar({ a: "no_va", b: "cortar" }, { id_origen: "a", estado: "no_va" })).toEqual({ b: "cortar" });
  });

  it("tres clics sobre una descartada dan toda la vuelta: se corta, no va, y como la leyó el sistema", () => {
    const uno = alTocar({}, { id_origen: "a", estado: "descartada" });
    const dos = alTocar(uno, { id_origen: "a", estado: "se_corta" });
    const tres = alTocar(dos, { id_origen: "a", estado: "no_va" });
    expect([uno, dos, tres]).toEqual([{ a: "cortar" }, { a: "no_va" }, {}]);
  });

  it("no cambia la lista que recibe", () => {
    const antes = { a: "no_va" as const };
    alTocar(antes, { id_origen: "b", estado: "se_corta" });
    expect(antes).toEqual({ a: "no_va" });
  });
});

describe("sinCorreccion", () => {
  it("saca una y deja las demás", () => {
    expect(sinCorreccion({ a: "no_va", b: "cortar" }, "b")).toEqual({ a: "no_va" });
  });

  it("no hace nada si esa forma no estaba corregida", () => {
    expect(sinCorreccion({ a: "no_va" }, "z")).toEqual({ a: "no_va" });
  });
});

describe("enOrdenDeDibujo", () => {
  it("pone la más grande primero y la más chica al final, que es la que queda arriba y recibe el clic", () => {
    const formas = [cuadradoDe(10, 0, 0, { id_origen: "chica" }), cuadradoDe(100, 0, 0, { id_origen: "grande" })];
    expect(enOrdenDeDibujo(formas).map((f) => f.id_origen)).toEqual(["grande", "chica"]);
  });

  it("lo que no va queda al fondo aunque sea chico: no tapa lo que se corta ni recibe el clic que era para eso", () => {
    const formas = [
      cuadradoDe(100, 0, 0, { id_origen: "letra" }),
      cuadradoDe(40, 0, 0, { id_origen: "mitad repetida", estado: "no_va" }),
      cuadradoDe(10, 0, 0, { id_origen: "centro", estado: "descartada" }),
    ];
    expect(enOrdenDeDibujo(formas).map((f) => f.id_origen)).toEqual(["mitad repetida", "letra", "centro"]);
  });

  it("de dos formas en el mismo lugar, la que se sacó deja a la vista a la otra", () => {
    // El contorno de la leyenda y la chapa dibujada del logo de la muestra.
    const chapa = cuadradoDe(1000, 0, 0, { id_origen: "chapa", estado: "no_va" });
    const contorno = cuadradoDe(1000, 0, 0, { id_origen: "contorno" });
    expect(enOrdenDeDibujo([contorno, chapa]).map((f) => f.id_origen)).toEqual(["chapa", "contorno"]);
    expect(enOrdenDeDibujo([chapa, contorno]).map((f) => f.id_origen)).toEqual(["chapa", "contorno"]);
  });

  it("entre las que no van también va primero la más grande", () => {
    const formas = [
      cuadradoDe(10, 0, 0, { id_origen: "chica", estado: "no_va" }),
      cuadradoDe(100, 0, 0, { id_origen: "grande", estado: "no_va" }),
    ];
    expect(enOrdenDeDibujo(formas).map((f) => f.id_origen)).toEqual(["grande", "chica"]);
  });

  it("no cambia la lista que recibe", () => {
    const formas = [cuadradoDe(10, 0, 0, { id_origen: "chica" }), cuadradoDe(100, 0, 0, { id_origen: "grande" })];
    enOrdenDeDibujo(formas);
    expect(formas[0].id_origen).toBe("chica");
  });
});

describe("descripcion", () => {
  it("dice el nombre corto, la medida y el estado", () => {
    expect(descripcion(cuadradoDe(100, 500, 200, { id_origen: "trabajo-1-7" }))).toBe("7 · 100 × 100 mm · se corta");
  });

  it("suma el motivo cuando lo hay", () => {
    const recorte = cuadradoDe(20, 0, 0, { id_origen: "trabajo-1-8", estado: "descartada", motivo: "recorte del agujero de trabajo-1-7" });
    expect(descripcion(recorte)).toBe("8 · 20 × 20 mm · entra descartada: recorte del agujero de trabajo-1-7");
  });

  it("nombra lo que no va", () => {
    const fuera = cuadradoDe(20, 0, 0, { id_origen: "trabajo-1-9", estado: "no_va", motivo: "lo marcó quien carga" });
    expect(descripcion(fuera)).toBe("9 · 20 × 20 mm · no va: lo marcó quien carga");
  });
});

describe("la vista del dibujo", () => {
  // Un dibujo de 1000 × 500: la vista entera le deja un margen del 2 % del lado mayor.
  const entera = vistaEntera({ minX: 0, minY: 0, ancho: 1000, alto: 500 });

  it("la vista entera abarca el dibujo con un margen", () => {
    expect(entera).toEqual({ x: -20, y: -20, ancho: 1040, alto: 540 });
  });

  it("acercar al doble deja quieto el punto sobre el que está el puntero", () => {
    const vista = acercar(entera, entera, 2, 500, 250);
    expect(vista.ancho).toBe(520);
    expect(vista.alto).toBe(270);
    // (500, 250) estaba en el medio de la vista y sigue en el medio.
    expect(vista.x + vista.ancho / 2).toBeCloseTo(500);
    expect(vista.y + vista.alto / 2).toBeCloseTo(250);
  });

  it("no acerca más que el aumento máximo", () => {
    const vista = acercar(entera, entera, 1000, 500, 250);
    expect(vista.ancho).toBeCloseTo(entera.ancho / AUMENTO_MAXIMO);
  });

  it("alejar nunca muestra más que el dibujo entero", () => {
    const cerca = acercar(entera, entera, 4, 100, 100);
    expect(acercar(cerca, entera, 1 / 100, 100, 100)).toEqual(entera);
  });

  it("acercar sobre un borde no se sale del dibujo", () => {
    const vista = acercar(entera, entera, 2, -20, -20);
    expect(vista.x).toBe(-20);
    expect(vista.y).toBe(-20);
  });

  it("mover corre la vista en contra del arrastre: el dibujo sigue a la mano", () => {
    const cerca = acercar(entera, entera, 2, 500, 250);
    const movida = mover(cerca, entera, 100, -50);
    expect(movida.x).toBeCloseTo(cerca.x - 100);
    expect(movida.y).toBeCloseTo(cerca.y + 50);
  });

  it("mover no se sale del dibujo", () => {
    const cerca = acercar(entera, entera, 2, 500, 250);
    const movida = mover(cerca, entera, 100000, 100000);
    expect(movida.x).toBe(entera.x);
    expect(movida.y).toBe(entera.y);
  });

  it("con el dibujo entero a la vista no hay hacia dónde mover", () => {
    expect(mover(entera, entera, 300, 300)).toEqual(entera);
  });
});

describe("fueUnClic", () => {
  it("soltar donde se apretó es un clic", () => {
    expect(fueUnClic(0, 0)).toBe(true);
    expect(fueUnClic(2, -2)).toBe(true);
  });

  it("soltar después de arrastrar no: se estaba moviendo el dibujo", () => {
    expect(fueUnClic(12, 0)).toBe(false);
    expect(fueUnClic(0, -9)).toBe(false);
  });
});

describe("esLaLecturaDe", () => {
  const archivo = new File(["x"], "aro.dxf");
  const lectura = { archivo, escala: "100" };

  it("vale mientras no cambien el archivo ni la escala", () => {
    expect(esLaLecturaDe(lectura, archivo, "100")).toBe(true);
  });

  it("deja de valer si cambia la escala: lo que se ve ya no es lo que se cargaría", () => {
    expect(esLaLecturaDe(lectura, archivo, "10")).toBe(false);
  });

  it("deja de valer si la escala que hay escrita no sirve", () => {
    expect(esLaLecturaDe(lectura, archivo, null)).toBe(false);
  });

  it("deja de valer si se elige otro archivo, aunque se llame igual", () => {
    expect(esLaLecturaDe(lectura, new File(["y"], "aro.dxf"), "100")).toBe(false);
  });

  it("sin lectura no hay nada que valga", () => {
    expect(esLaLecturaDe(null, archivo, "100")).toBe(false);
  });
});
```

- [x] **Step 2: Correr los tests y verlos fallar**

Run: `cd frontend && npx vitest run src/components/LecturaDxf`
Expected: `FAIL  src/components/LecturaDxf/dibujo.test.ts`, con `TypeError: vistaEntera is not a function`, y `Test Files  1 failed (1)`. El bloque de la vista arma su caja antes de cada test, así que el archivo entero no llega a correr: falta todo lo que importa.

- [x] **Step 3: Los tipos**

En `frontend/src/api/piezasYgrupos.ts`:

**Cambio 1 de 2.** Reemplazar:

```ts
  contorno_mm: number[][];
  agujeros_mm: number[][][];
  descartada: boolean;
  /** Por qué entra descartada; `null` si se corta. */
  motivo: string | null;
}
```

por:

```ts
  contorno_mm: number[][];
  agujeros_mm: number[][][];
  /** `se_corta`: se carga y se anida. `descartada`: se carga atenuada, sin
   * cortarse (el recorte de un hueco). `no_va`: la sacó quien carga, y no
   * se carga. */
  estado: "se_corta" | "descartada" | "no_va";
  /** El estado no salió de una regla: lo marcó quien carga. */
  corregida: boolean;
  /** Por qué entra descartada o no va; `null` si se corta sin que nadie
   * lo haya marcado. */
  motivo: string | null;
}
```

**Cambio 2 de 2.** Reemplazar:

```ts
  a_cortar: number;
  descartadas: number;
  advertencias: string[];
}

/** Cómo se leería un DXF. `unida` viene solo si hay formas que se pisan. */
```

por:

```ts
  a_cortar: number;
  descartadas: number;
  no_van: number;
  advertencias: string[];
}

/** Lo que quien carga marcó sobre el dibujo: de nombre de forma
 * (`id_origen`) a lo que tiene que pasar con ella. */
export type Correcciones = Record<string, "cortar" | "no_va">;

/** Cómo se leería un DXF. `unida` viene solo si hay formas que se pisan. */
```

- [x] **Step 4: Las cuentas**

De lo que había quedan igual `Caja`, `cajaDelDibujo`, `trazo` y, al final, `esLaLecturaDe`. `frontend/src/components/LecturaDxf/dibujo.ts` queda entero así:

```ts
// Cuentas puras del dibujo de una lectura (cómo leyó el sistema un DXF,
// antes de cargarlo). Sin React: se prueban solas.

import type { Correcciones, FormaLeida, Lectura } from "../../api/piezasYgrupos";

export interface Caja {
  minX: number;
  minY: number;
  ancho: number;
  alto: number;
}

/**
 * La caja que contiene a todas las formas, en mm del dibujo.
 *
 * Sin formas, o con una sola línea sin ancho, devuelve una caja de al
 * menos 1 × 1: un `viewBox` de lado cero no dibuja nada.
 */
export function cajaDelDibujo(formas: FormaLeida[]): Caja {
  const puntos = formas.flatMap((forma) => forma.contorno_mm);
  if (puntos.length === 0) return { minX: 0, minY: 0, ancho: 1, alto: 1 };
  const xs = puntos.map(([x]) => x);
  const ys = puntos.map(([, y]) => y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  return { minX, minY, ancho: Math.max(Math.max(...xs) - minX, 1), alto: Math.max(Math.max(...ys) - minY, 1) };
}

const centesimas = (valor: number) => Math.round(valor * 100) / 100;

/**
 * El `d` de un `<path>` con el contorno de la forma y sus huecos,
 * medido desde la esquina de arriba a la izquierda de la caja.
 *
 * La Y se da vuelta: en el DXF crece hacia arriba y en la pantalla,
 * hacia abajo. Sin eso el dibujo sale cabeza abajo. Con
 * `fillRule="evenodd"` los huecos quedan vacíos.
 */
export function trazo(forma: FormaLeida, caja: Caja): string {
  const arriba = caja.minY + caja.alto;
  return [forma.contorno_mm, ...forma.agujeros_mm]
    .filter((anillo) => anillo.length > 2)
    .map(
      (anillo) =>
        anillo
          .map(([x, y], i) => `${i === 0 ? "M" : "L"}${centesimas(x - caja.minX)} ${centesimas(arriba - y)}`)
          .join(" ") + " Z",
    )
    .join(" ");
}

/** «17 piezas a cortar · 2 entran descartadas · 15 no van». Lo que vale
 * cero no se nombra, salvo las piezas a cortar. */
export function resumenDeLectura(lectura: Pick<Lectura, "a_cortar" | "descartadas" | "no_van">): string {
  const partes = [lectura.a_cortar === 1 ? "1 pieza a cortar" : `${lectura.a_cortar} piezas a cortar`];
  if (lectura.descartadas > 0) {
    partes.push(lectura.descartadas === 1 ? "1 entra descartada" : `${lectura.descartadas} entran descartadas`);
  }
  if (lectura.no_van > 0) partes.push(lectura.no_van === 1 ? "1 no va" : `${lectura.no_van} no van`);
  return partes.join(" · ");
}

/** Sin nada para cortar no se carga: cargar reemplaza las piezas del
 * trabajo, y eso lo dejaría vacío. */
export function sePuedeCargar(lectura: Pick<Lectura, "a_cortar">): boolean {
  return lectura.a_cortar > 0;
}

/**
 * El nombre de una forma como se muestra: su número en el archivo, sin
 * el nombre del archivo. «trabajo-1-497» es «497»; lo que sigue a una
 * barra se conserva («39/unida», «39/hueco7»).
 */
export function nombreCorto(idOrigen: string): string {
  const [base, ...resto] = idOrigen.split("/");
  return [base.split("-").pop(), ...resto].join("/");
}

/**
 * La lista de correcciones después de tocar una forma.
 *
 * Tocar una forma sin corregir la fuerza a lo contrario de lo que se ve:
 * la que se corta pasa a «no va»; la que no se corta, a «cortar». Otro
 * clic sobre la que se forzó a cortar la saca («no va»): es el camino
 * para un recorte que no era un hueco, como la mitad de una letra
 * dibujada dos veces. Tocar una que se sacó le quita la corrección, y
 * vuelve a decidir el sistema.
 */
export function alTocar(correcciones: Correcciones, forma: Pick<FormaLeida, "id_origen" | "estado">): Correcciones {
  const marca = correcciones[forma.id_origen];
  if (marca === "no_va") return sinCorreccion(correcciones, forma.id_origen);
  if (marca === "cortar") return { ...correcciones, [forma.id_origen]: "no_va" };
  return { ...correcciones, [forma.id_origen]: forma.estado === "se_corta" ? "no_va" : "cortar" };
}

/** La lista sin la corrección de esa forma. */
export function sinCorreccion(correcciones: Correcciones, idOrigen: string): Correcciones {
  return Object.fromEntries(Object.entries(correcciones).filter(([id]) => id !== idOrigen));
}

function medida(forma: FormaLeida): { ancho: number; alto: number } {
  const { ancho, alto } = cajaDelDibujo([forma]);
  return { ancho, alto };
}

/**
 * Las formas en el orden en que hay que dibujarlas; la última queda
 * arriba y recibe el clic.
 *
 * Primero, al fondo, las que no van: así el rayado no tapa lo que se
 * corta, y de dos formas dibujadas en el mismo lugar (una chapa sobre
 * un contorno) la que se sacó deja a la otra a la vista y a mano.
 * Dentro de cada grupo, de la más grande a la más chica: se puede tocar
 * una letra que está adentro de un contorno.
 */
export function enOrdenDeDibujo(formas: FormaLeida[]): FormaLeida[] {
  const area = (forma: FormaLeida) => {
    const { ancho, alto } = medida(forma);
    return ancho * alto;
  };
  const alFondo = (forma: FormaLeida) => (forma.estado === "no_va" ? 0 : 1);
  return [...formas].sort((a, b) => alFondo(a) - alFondo(b) || area(b) - area(a));
}

const ESTADO_EN_PALABRAS = { se_corta: "se corta", descartada: "entra descartada", no_va: "no va" };

/** Lo que se lee al pasar el mouse por una forma: «497 · 1203 × 506 mm ·
 * no va: lo marcó quien carga». */
export function descripcion(forma: FormaLeida): string {
  const { ancho, alto } = medida(forma);
  const estado = ESTADO_EN_PALABRAS[forma.estado] + (forma.motivo ? `: ${forma.motivo}` : "");
  return `${nombreCorto(forma.id_origen)} · ${Math.round(ancho)} × ${Math.round(alto)} mm · ${estado}`;
}

// --- Acercar y mover ---------------------------------------------------------
//
// La vista es el recuadro del dibujo que se ve, en las mismas unidades que
// `trazo`: milímetros desde la esquina de arriba a la izquierda de la caja.

/** `PAR-53`. Cuánto se puede acercar el dibujo. Es donde el detalle con
 * que viaja (`PAR-52`) llega a un píxel de error. */
export const AUMENTO_MAXIMO = 20;

export interface Vista {
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

/** El dibujo entero, con un margen del 2 % de su lado mayor. */
export function vistaEntera(caja: Caja): Vista {
  const margen = Math.max(caja.ancho, caja.alto) * 0.02;
  return { x: -margen, y: -margen, ancho: caja.ancho + 2 * margen, alto: caja.alto + 2 * margen };
}

const entre = (valor: number, minimo: number, maximo: number) => Math.min(Math.max(valor, minimo), maximo);

function adentro(vista: Vista, entera: Vista): Vista {
  return {
    ...vista,
    x: entre(vista.x, entera.x, entera.x + entera.ancho - vista.ancho),
    y: entre(vista.y, entera.y, entera.y + entera.alto - vista.alto),
  };
}

/**
 * La vista acercada `factor` veces (menos de 1 aleja), dejando quieto el
 * punto (x, y) del dibujo, que es donde está el puntero. No acerca más
 * que `AUMENTO_MAXIMO` ni muestra más que el dibujo entero.
 */
export function acercar(vista: Vista, entera: Vista, factor: number, x: number, y: number): Vista {
  const ancho = entre(vista.ancho / factor, entera.ancho / AUMENTO_MAXIMO, entera.ancho);
  if (ancho === entera.ancho) return entera;
  const alto = (ancho * entera.alto) / entera.ancho;
  const queda = ancho / vista.ancho;
  return adentro({ x: x - (x - vista.x) * queda, y: y - (y - vista.y) * queda, ancho, alto }, entera);
}

/**
 * La vista corrida al arrastrar (dx, dy) milímetros del dibujo: el
 * dibujo sigue a la mano, así que la vista va para el otro lado. No se
 * sale del dibujo entero.
 */
export function mover(vista: Vista, entera: Vista, dx: number, dy: number): Vista {
  return adentro({ ...vista, x: vista.x - dx, y: vista.y - dy }, entera);
}

/** Soltar a menos de 4 píxeles de donde se apretó es un clic; más lejos,
 * se estaba arrastrando el dibujo. */
export function fueUnClic(dxPx: number, dyPx: number): boolean {
  return Math.hypot(dxPx, dyPx) < 4;
}

/**
 * Si la lectura que se pidió es la del archivo y la escala que hay
 * ahora en pantalla. Cambiar cualquiera de los dos la deja vieja: lo
 * que se ve ya no es lo que se cargaría.
 */
export function esLaLecturaDe(
  lectura: { archivo: File; escala: string } | null,
  archivo: File | null,
  escala: string | null,
): boolean {
  return lectura !== null && lectura.archivo === archivo && lectura.escala === escala;
}
```

- [x] **Step 5: El panel, con tres estados**

`frontend/src/components/LecturaDxf/LecturaPanel.tsx` queda entero así:

```tsx
import Banner from "../Banner";
import type { FormaLeida, LecturaDxf } from "../../api/piezasYgrupos";
import {
  cajaDelDibujo,
  descripcion,
  enOrdenDeDibujo,
  resumenDeLectura,
  sePuedeCargar,
  trazo,
  vistaEntera,
} from "./dibujo";

interface LecturaPanelProps {
  lectura: LecturaDxf;
  unir: boolean;
  alCambiarUnir: (unir: boolean) => void;
  alCargar: () => void;
  alCancelar: () => void;
  cargando: boolean;
  /** Cuántas piezas tiene hoy el trabajo: cargar las reemplaza. */
  piezasQueReemplaza: number;
}

const TINTA = "#2B2420";
const CORTE = "#2E8074";
const CONFLICTO = "#C4432A";
const RAYADO = "lectura-rayado-no-va";

/** Cómo se pinta una forma según su estado. Lo que marcó quien carga
 * lleva el borde más grueso, para distinguirlo de lo que decidió el
 * sistema. */
function pintura(forma: FormaLeida) {
  const strokeWidth = forma.corregida ? 2.5 : 1;
  if (forma.estado === "se_corta") return { fill: CORTE, fillOpacity: 0.45, stroke: TINTA, strokeWidth };
  if (forma.estado === "no_va") return { fill: `url(#${RAYADO})`, stroke: CONFLICTO, strokeWidth };
  return { fill: "none", stroke: TINTA, strokeOpacity: 0.55, strokeDasharray: "4 3", strokeWidth };
}

/**
 * Cómo leyó el sistema un DXF, antes de cargarlo: lo que se corta,
 * pintado; lo que entra descartado, en línea de puntos; lo que no va,
 * rayado en rojo. El relleno es semitransparente a propósito: donde dos
 * piezas se pisan se ve más oscuro, y un dibujo mal leído salta a la
 * vista.
 */
export default function LecturaPanel({
  lectura,
  unir,
  alCambiarUnir,
  alCargar,
  alCancelar,
  cargando,
  piezasQueReemplaza,
}: LecturaPanelProps) {
  const leida = unir && lectura.unida ? lectura.unida : lectura.sin_unir;
  const caja = cajaDelDibujo(leida.formas);
  const vista = vistaEntera(caja);
  const dibujadas = enOrdenDeDibujo(leida.formas).map((forma) => ({ forma, d: trazo(forma, caja) }));
  // `enOrdenDeDibujo` ya las trae así: primero las que no van.
  const alFondo = dibujadas.filter(({ forma }) => forma.estado === "no_va");
  const enJuego = dibujadas.filter(({ forma }) => forma.estado !== "no_va");
  // El rayado se mide contra lo que se ve, no en milímetros: así las
  // rayas quedan igual de separadas en un cartel de 10 m que en una
  // letra de 10 cm.
  const paso = vista.ancho / 90;

  const dibujar = ({ forma, d }: { forma: FormaLeida; d: string }) => (
    <path key={forma.id_origen} d={d} fillRule="evenodd" vectorEffect="non-scaling-stroke" {...pintura(forma)}>
      <title>{descripcion(forma)}</title>
    </path>
  );

  return (
    <div className="border border-line rounded p-3 mb-4">
      <h2 className="font-semibold mb-2">Así se lee</h2>
      {leida.formas.length === 0 ? (
        <p className="text-sm mb-2">No hay ninguna forma cerrada para dibujar.</p>
      ) : (
        <svg
          viewBox={`${vista.x} ${vista.y} ${vista.ancho} ${vista.alto}`}
          className="w-full border border-line rounded bg-white"
          style={{ maxHeight: "60vh" }}
        >
          <defs>
            <pattern id={RAYADO} patternUnits="userSpaceOnUse" width={paso} height={paso} patternTransform="rotate(45)">
              <line x1={0} y1={0} x2={0} y2={paso} stroke={CONFLICTO} strokeWidth={paso * 0.3} />
            </pattern>
          </defs>
          {alFondo.map(dibujar)}
          {/* El relleno de lo que se corta deja ver lo de abajo, para que
              se note donde dos piezas se pisan. El rayado de lo que no va
              no tiene que verse a través: parecería que esa pieza tampoco
              va. Se lo tapa con blanco, antes de pintar ninguna pieza. */}
          {alFondo.length > 0 &&
            enJuego
              .filter(({ forma }) => forma.estado === "se_corta")
              .map(({ forma, d }) => (
                <path key={`fondo de ${forma.id_origen}`} d={d} fillRule="evenodd" fill="#FFFFFF" pointerEvents="none" />
              ))}
          {enJuego.map(dibujar)}
        </svg>
      )}
      <p className="text-xs mt-1 mb-2">
        Pintado: se corta · Punteado: entra descartada · Rayado rojo: no va. En blanco, los huecos.
      </p>

      <p className="text-sm font-semibold mb-2">{resumenDeLectura(leida)}</p>

      {leida.advertencias.length > 0 && (
        <div className="mb-2">
          <Banner variante="aviso">
            <ul className="list-disc pl-4">
              {leida.advertencias.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          </Banner>
        </div>
      )}

      {lectura.unida && (
        <label className="flex items-center gap-2 text-sm mb-2">
          <input type="checkbox" checked={unir} onChange={(evento) => alCambiarUnir(evento.target.checked)} />
          Unir las formas que se pisan
        </label>
      )}

      {piezasQueReemplaza > 0 && (
        <p className="text-sm mb-2">
          Cargar reemplaza {piezasQueReemplaza === 1 ? "la pieza" : `las ${piezasQueReemplaza} piezas`} que ya tiene
          este trabajo.
        </p>
      )}

      {!sePuedeCargar(leida) && (
        <p className="text-sm text-conflict mb-2">No queda ninguna forma para cortar: así no hay nada que cargar.</p>
      )}

      <div className="flex gap-2">
        <button
          className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
          disabled={cargando || !sePuedeCargar(leida)}
          onClick={alCargar}
        >
          {cargando ? "Cargando…" : "Cargar"}
        </button>
        <button
          className="border border-line rounded px-3 py-1 text-sm hover:bg-line/40"
          disabled={cargando}
          onClick={alCancelar}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
```

- [x] **Step 6: La fila nueva del registro**

En `docs/REGISTRO.md`, después de la fila de `PAR-52`:

```markdown
| **PAR-53** | Cuánto se puede acercar el dibujo de la lectura | 20 | aumentos | Sistema | Config | `plan/2.1b-corregir-la-lectura/diseno.md` | 🟡 provisorio — propuesto el 2026-10-12, en `frontend/src/components/LecturaDxf/dibujo.ts`. Es donde lo que se aparta el dibujo con `PAR-52` llega a un píxel |
```

- [x] **Step 7: Correr los tests y verlos pasar**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `Tests  88 passed (88)`.

- [x] **Step 8: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add frontend/src/api/piezasYgrupos.ts frontend/src/components/LecturaDxf docs/REGISTRO.md
git commit -m "feat(frontend): la lectura con tres estados, y las cuentas para corregirla (2.1b)"
```

---

### Task 6: La pantalla: corregir con clics, acercar y mover

**Files:**
- Create: `frontend/src/api/piezasYgrupos.test.ts`
- Modify: `frontend/src/api/piezasYgrupos.ts` (`subirDxf`, `leerDxf`)
- Modify: `frontend/src/hooks/usePiezas.ts` (`useSubirDxf`, `useLeerDxf`)
- Modify: `frontend/src/components/LecturaDxf/dibujo.ts` (`correccionesALaVista`, `turnos`)
- Modify: `frontend/src/components/LecturaDxf/LecturaPanel.tsx`
- Modify: `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`
- Test: `frontend/src/components/LecturaDxf/dibujo.test.ts`

**Interfaces:**
- Consumes: el campo `correcciones` de los dos pedidos (Tarea 2) y todo lo que la Tarea 5 dejó en `dibujo.ts` y en `piezasYgrupos.ts`.
- Produces: `leerDxf(trabajoId: number, archivo: File, escalaAMm: string, correcciones: Correcciones)` y `subirDxf(trabajoId: number, archivo: File, escalaAMm: string, unir: boolean, correcciones: Correcciones)`; las dos mandan la lista como texto JSON en el campo `correcciones`, también cuando está vacía. `useLeerDxf` y `useSubirDxf` reciben `correcciones` junto con lo que ya recibían. En `dibujo.ts`: `correccionesALaVista(correcciones: Correcciones, formas: Pick<FormaLeida, "id_origen">[]): { id: string; texto: string }[]` y `turnos(): { nuevo: () => number; esElUltimo: (turno: number) => boolean }`. `LecturaPanel` suma tres propiedades: `correcciones: Correcciones`, `alCorregir: (correcciones: Correcciones) => void` y `leyendo: boolean`.

- [x] **Step 1: Los tests de los dos pedidos**

`frontend/src/api/piezasYgrupos.test.ts`, nuevo:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { leerDxf, subirDxf } from "./piezasYgrupos";

const archivo = new File(["0"], "logo.dxf");

/** Reemplaza `fetch` por uno que responde bien, y lo devuelve para mirar
 * qué se le pidió. */
function fetchQueResponde() {
  const falso = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
  vi.stubGlobal("fetch", falso);
  return falso;
}

/** A dónde fue el único pedido, y el formulario que llevó. */
function pedidoDe(falso: ReturnType<typeof fetchQueResponde>): { url: string; campos: FormData } {
  const [url, opciones] = falso.mock.calls[0];
  return { url, campos: opciones.body };
}

const correccionesDe = (campos: FormData) => JSON.parse(campos.get("correcciones") as string);

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("leerDxf", () => {
  it("manda las correcciones como JSON en un campo del formulario", async () => {
    const falso = fetchQueResponde();

    await leerDxf(7, archivo, "100", { "logo-497": "no_va", "logo-519": "cortar" });

    const { url, campos } = pedidoDe(falso);
    expect(url).toMatch(/\/trabajos\/7\/dxf\/lectura$/);
    expect(campos.get("escala_a_mm")).toBe("100");
    expect(correccionesDe(campos)).toEqual({ "logo-497": "no_va", "logo-519": "cortar" });
  });

  it("sin correcciones manda la lista vacía, que el servidor lee como «ninguna»", async () => {
    const falso = fetchQueResponde();

    await leerDxf(7, archivo, "100", {});

    expect(correccionesDe(pedidoDe(falso).campos)).toEqual({});
  });
});

describe("subirDxf", () => {
  it("manda la misma lista que la lectura, junto con la unión: se carga lo que se vio", async () => {
    const falso = fetchQueResponde();

    await subirDxf(7, archivo, "100", true, { "logo-497": "no_va" });

    const { url, campos } = pedidoDe(falso);
    expect(url).toMatch(/\/trabajos\/7\/dxf$/);
    expect(campos.get("unir")).toBe("true");
    expect(correccionesDe(campos)).toEqual({ "logo-497": "no_va" });
  });
});
```

- [x] **Step 2: Los tests de la lista y de los turnos**

En `frontend/src/components/LecturaDxf/dibujo.test.ts`:

**Cambio 1 de 3.** Después de este bloque, que queda igual:

```ts
  cajaDelDibujo,
```

agregar:

```ts
  correccionesALaVista,
```

**Cambio 2 de 3.** Después de este bloque, que queda igual:

```ts
  trazo,
```

agregar:

```ts
  turnos,
```

**Cambio 3 de 3.** Después de este bloque, que queda igual:

```ts
    expect(fueUnClic(0, -9)).toBe(false);
  });
});
```

agregar:

```ts
describe("correccionesALaVista", () => {
  const formas = [cuadradoDe(100, 0, 0, { id_origen: "logo-497" }), cuadradoDe(10, 0, 0, { id_origen: "logo-519" })];

  it("nombra cada una por su número y por lo que se le marcó", () => {
    expect(correccionesALaVista({ "logo-497": "no_va", "logo-519": "cortar" }, formas)).toEqual([
      { id: "logo-497", texto: "497 no va" },
      { id: "logo-519", texto: "519 se corta" },
    ]);
  });

  it("no lista la de una forma que esta lectura no tiene: es de la otra, la unida o la sin unir", () => {
    expect(correccionesALaVista({ "logo-39/unida": "no_va", "logo-497": "no_va" }, formas)).toEqual([
      { id: "logo-497", texto: "497 no va" },
    ]);
  });

  it("sin correcciones no hay nada que listar", () => {
    expect(correccionesALaVista({}, formas)).toEqual([]);
  });
});

describe("turnos", () => {
  it("vale la respuesta del último pedido, no la de uno anterior que llega tarde", () => {
    const pedidos = turnos();
    const primero = pedidos.nuevo();
    const segundo = pedidos.nuevo();
    expect(pedidos.esElUltimo(primero)).toBe(false);
    expect(pedidos.esElUltimo(segundo)).toBe(true);
  });

  it("abrir un turno sin pedir nada deja sin valor al que estaba en camino: es lo que hace cancelar", () => {
    const pedidos = turnos();
    const enCamino = pedidos.nuevo();
    expect(pedidos.esElUltimo(enCamino)).toBe(true);
    pedidos.nuevo();
    expect(pedidos.esElUltimo(enCamino)).toBe(false);
  });

  it("cada cuenta es aparte", () => {
    const unos = turnos();
    const otros = turnos();
    const turno = unos.nuevo();
    otros.nuevo();
    otros.nuevo();
    expect(unos.esElUltimo(turno)).toBe(true);
  });
});
```

- [x] **Step 3: Correr los tests y verlos fallar**

Run: `cd frontend && npm test`
Expected: `Tests  9 failed | 88 passed (97)`. Los tres de `piezasYgrupos.test.ts` fallan con `expected null to deeply equal …`, porque el campo no viaja; los tres de `correccionesALaVista` y los tres de `turnos`, con `… is not a function`.

No correr `npm run build` acá: los tests llaman a los dos pedidos con un argumento que todavía no tienen, y `tsc` lo marca. Es lo esperado.

- [x] **Step 4: La lista en los dos pedidos**

En `frontend/src/api/piezasYgrupos.ts`:

**Cambio 1 de 3.** Reemplazar:

```ts
}

/** `unir`: cargar con las formas que se pisan vueltas una sola pieza,
 * como se vio en la lectura (`leerDxf`). */
export function subirDxf(trabajoId: number, archivo: File, escalaAMm: string, unir: boolean): Promise<{
  trabajo: unknown;
  piezas_creadas: number;
```

por:

```ts
}

/** `unir`: cargar con las formas que se pisan vueltas una sola pieza.
 * `correcciones`: lo que se marcó sobre el dibujo. Los dos tienen que
 * ser los de la lectura que se vio (`leerDxf`): se carga lo que se vio. */
export function subirDxf(
  trabajoId: number,
  archivo: File,
  escalaAMm: string,
  unir: boolean,
  correcciones: Correcciones,
): Promise<{
  trabajo: unknown;
  piezas_creadas: number;
```

**Cambio 2 de 3.** Después de este bloque, que queda igual:

```ts
  formData.append("unir", unir ? "true" : "false");
```

agregar:

```ts
  formData.append("correcciones", JSON.stringify(correcciones));
```

**Cambio 3 de 3.** Reemplazar:

```ts
}

/** Lee el archivo sin guardar nada: es lo que se dibuja antes de cargar. */
export function leerDxf(trabajoId: number, archivo: File, escalaAMm: string): Promise<LecturaDxf> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  return apiPostForm(`/trabajos/${trabajoId}/dxf/lectura`, formData);
}
```

por:

```ts
}

/** Lee el archivo sin guardar nada: es lo que se dibuja antes de cargar.
 * Con `correcciones`, el servidor fuerza lo marcado y vuelve a decidir
 * lo demás. */
export function leerDxf(
  trabajoId: number,
  archivo: File,
  escalaAMm: string,
  correcciones: Correcciones,
): Promise<LecturaDxf> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  formData.append("correcciones", JSON.stringify(correcciones));
  return apiPostForm(`/trabajos/${trabajoId}/dxf/lectura`, formData);
}
```

En `frontend/src/hooks/usePiezas.ts`:

**Cambio 1 de 3.** Después de este bloque, que queda igual:

```ts
  subirDxf,
```

agregar:

```ts
  type Correcciones,
```

**Cambio 2 de 3.** Reemplazar:

```ts
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ archivo, escalaAMm, unir }: { archivo: File; escalaAMm: string; unir: boolean }) =>
      subirDxf(trabajoId, archivo, escalaAMm, unir),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
```

por:

```ts
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      archivo,
      escalaAMm,
      unir,
      correcciones,
    }: {
      archivo: File;
      escalaAMm: string;
      unir: boolean;
      correcciones: Correcciones;
    }) => subirDxf(trabajoId, archivo, escalaAMm, unir, correcciones),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
```

**Cambio 3 de 3.** Reemplazar:

```ts
export function useLeerDxf(trabajoId: number) {
  return useMutation({
    mutationFn: ({ archivo, escalaAMm }: { archivo: File; escalaAMm: string }) =>
      leerDxf(trabajoId, archivo, escalaAMm),
  });
}
```

por:

```ts
export function useLeerDxf(trabajoId: number) {
  return useMutation({
    mutationFn: ({
      archivo,
      escalaAMm,
      correcciones,
    }: {
      archivo: File;
      escalaAMm: string;
      correcciones: Correcciones;
    }) => leerDxf(trabajoId, archivo, escalaAMm, correcciones),
  });
}
```

- [x] **Step 5: La lista a la vista y los turnos**

En `frontend/src/components/LecturaDxf/dibujo.ts`:

**El cambio.** Después de este bloque, que queda igual:

```ts
  return Object.fromEntries(Object.entries(correcciones).filter(([id]) => id !== idOrigen));
```

agregar:

```ts
}

const MARCA_EN_PALABRAS = { cortar: "se corta", no_va: "no va" };

/**
 * Las correcciones como se listan debajo del dibujo: «497 no va»,
 * «519 se corta». Solo las de formas que están en la lectura que se ve:
 * la pieza unida no existe en la lectura sin unir, y nombrarla ahí no
 * diría nada. Su corrección no se pierde, vuelve al cambiar de lectura.
 */
export function correccionesALaVista(
  correcciones: Correcciones,
  formas: Pick<FormaLeida, "id_origen">[],
): { id: string; texto: string }[] {
  const aLaVista = new Set(formas.map((forma) => forma.id_origen));
  return Object.entries(correcciones)
    .filter(([id]) => aLaVista.has(id))
    .map(([id, marca]) => ({ id, texto: `${nombreCorto(id)} ${MARCA_EN_PALABRAS[marca]}` }));
}

/**
 * La cuenta de los pedidos que se pisan. Cada clic sobre el dibujo pide
 * la lectura de nuevo, y las respuestas pueden llegar en otro orden:
 * solo vale la del último turno. Abrir un turno sin pedir nada (al
 * cancelar, al leer otro archivo) deja sin valor al que estaba en camino.
 */
export function turnos(): { nuevo: () => number; esElUltimo: (turno: number) => boolean } {
  let ultimo = 0;
  return { nuevo: () => ++ultimo, esElUltimo: (turno) => turno === ultimo };
```

- [x] **Step 6: El panel, que ahora se toca**

`frontend/src/components/LecturaDxf/LecturaPanel.tsx` queda entero así:

```tsx
import { useEffect, useMemo, useRef, useState } from "react";
import Banner from "../Banner";
import type { Correcciones, FormaLeida, LecturaDxf } from "../../api/piezasYgrupos";
import {
  AUMENTO_MAXIMO,
  acercar,
  alTocar,
  cajaDelDibujo,
  correccionesALaVista,
  descripcion,
  enOrdenDeDibujo,
  fueUnClic,
  mover,
  resumenDeLectura,
  sePuedeCargar,
  sinCorreccion,
  trazo,
  vistaEntera,
  type Vista,
} from "./dibujo";

interface LecturaPanelProps {
  lectura: LecturaDxf;
  unir: boolean;
  alCambiarUnir: (unir: boolean) => void;
  /** Lo que se marcó sobre el dibujo. */
  correcciones: Correcciones;
  /** La lista nueva, cada vez que se toca una forma o se saca una
   * corrección. Quien la recibe pide la lectura de nuevo. */
  alCorregir: (correcciones: Correcciones) => void;
  /** Se pidió la lectura de nuevo y todavía no llegó: lo que se ve es
   * la anterior. */
  leyendo: boolean;
  alCargar: () => void;
  alCancelar: () => void;
  cargando: boolean;
  /** Cuántas piezas tiene hoy el trabajo: cargar las reemplaza. */
  piezasQueReemplaza: number;
}

const TINTA = "#2B2420";
const CORTE = "#2E8074";
const CONFLICTO = "#C4432A";
const RAYADO = "lectura-rayado-no-va";
// Cuánto acerca cada muesca de la rueda y cada toque de los botones.
const PASO_DE_RUEDA = 1.25;
const PASO_DE_BOTON = 1.6;

/** Cómo se pinta una forma según su estado. Lo que marcó quien carga
 * lleva el borde más grueso, para distinguirlo de lo que decidió el
 * sistema. Las que no tienen relleno también reciben el clic en todo su
 * cuerpo, no solo en la línea. */
function pintura(forma: FormaLeida) {
  const strokeWidth = forma.corregida ? 2.5 : 1;
  if (forma.estado === "se_corta") return { fill: CORTE, fillOpacity: 0.45, stroke: TINTA, strokeWidth };
  if (forma.estado === "no_va") return { fill: `url(#${RAYADO})`, stroke: CONFLICTO, strokeWidth };
  return {
    fill: "none",
    pointerEvents: "all" as const,
    stroke: TINTA,
    strokeOpacity: 0.55,
    strokeDasharray: "4 3",
    strokeWidth,
  };
}

/**
 * Cómo leyó el sistema un DXF, antes de cargarlo, y dónde se lo corrige:
 * lo que se corta, pintado; lo que entra descartado, en línea de puntos;
 * lo que no va, rayado en rojo. Un clic sobre una forma la corrige
 * (`alTocar`). El relleno es semitransparente a propósito: donde dos
 * piezas se pisan se ve más oscuro, y un dibujo mal leído salta a la
 * vista.
 */
export default function LecturaPanel({
  lectura,
  unir,
  alCambiarUnir,
  correcciones,
  alCorregir,
  leyendo,
  alCargar,
  alCancelar,
  cargando,
  piezasQueReemplaza,
}: LecturaPanelProps) {
  const leida = unir && lectura.unida ? lectura.unida : lectura.sin_unir;
  // Mover el dibujo vuelve a pintar el panel con cada píxel del puntero:
  // los trazos, que son lo caro, se arman una vez por lectura.
  const { entera, alFondo, enJuego } = useMemo(() => {
    const caja = cajaDelDibujo(leida.formas);
    const dibujadas = enOrdenDeDibujo(leida.formas).map((forma) => ({ forma, d: trazo(forma, caja) }));
    return {
      entera: vistaEntera(caja),
      // `enOrdenDeDibujo` ya las trae así: primero las que no van.
      alFondo: dibujadas.filter(({ forma }) => forma.estado === "no_va"),
      enJuego: dibujadas.filter(({ forma }) => forma.estado !== "no_va"),
    };
  }, [leida]);
  // `null`: se ve el dibujo entero.
  const [acercada, setAcercada] = useState<Vista | null>(null);
  const vista = acercada ?? entera;
  const hayDibujo = leida.formas.length > 0;
  // El rayado se mide contra lo que se ve, no en milímetros: así las
  // rayas quedan igual de separadas en un cartel de 10 m que en una
  // letra de 10 cm, y con cualquier acercamiento.
  const paso = vista.ancho / 90;

  const svgRef = useRef<SVGSVGElement | null>(null);
  // Dónde se apretó, con qué vista y sobre qué forma: al soltar se sabe
  // si fue un clic o se estuvo moviendo el dibujo.
  const apretado = useRef<{ x: number; y: number; vista: Vista; id: string | null; seMovio: boolean } | null>(null);
  // El listener de la rueda es nativo y se registra una vez (ver el
  // efecto): este ref le da siempre la vista de ahora.
  const paraLaRueda = useRef({ vista, entera });
  paraLaRueda.current = { vista, entera };

  const ver = (nueva: Vista, completa: Vista) => setAcercada(nueva === completa ? null : nueva);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const alGirarRueda = (evento: WheelEvent) => {
      const { vista, entera } = paraLaRueda.current;
      const aPantalla = svg.getScreenCTM();
      if (!aPantalla) return;
      const puntero = new DOMPoint(evento.clientX, evento.clientY).matrixTransform(aPantalla.inverse());
      const nueva = acercar(vista, entera, evento.deltaY < 0 ? PASO_DE_RUEDA : 1 / PASO_DE_RUEDA, puntero.x, puntero.y);
      // Con el dibujo entero a la vista, alejar no cambia nada: ahí la
      // rueda mueve la página, como en cualquier otro lado.
      if (nueva === entera && vista === entera) return;
      evento.preventDefault();
      ver(nueva, entera);
    };

    // `passive: false` explícito: React registra `wheel` como pasivo, y
    // ahí `preventDefault()` no hace nada. Mismo motivo que en
    // `PlanoEditor`.
    svg.addEventListener("wheel", alGirarRueda, { passive: false });
    return () => svg.removeEventListener("wheel", alGirarRueda);
  }, [hayDibujo]);

  function alApretar(evento: React.PointerEvent<SVGSVGElement>) {
    if (evento.button !== 0) return;
    const tocada = (evento.target as Element).closest("path[data-id]");
    apretado.current = {
      x: evento.clientX,
      y: evento.clientY,
      vista,
      id: tocada?.getAttribute("data-id") ?? null,
      seMovio: false,
    };
    // Si el puntero sale del dibujo mientras se arrastra, se sigue
    // moviendo, y soltar afuera también termina el arrastre.
    evento.currentTarget.setPointerCapture(evento.pointerId);
  }

  function alMoverElPuntero(evento: React.PointerEvent<SVGSVGElement>) {
    const inicio = apretado.current;
    if (!inicio) return;
    const dx = evento.clientX - inicio.x;
    const dy = evento.clientY - inicio.y;
    // Pasada la holgura ya es un arrastre, aunque el puntero vuelva.
    if (!inicio.seMovio && fueUnClic(dx, dy)) return;
    inicio.seMovio = true;
    const aPantalla = evento.currentTarget.getScreenCTM();
    // Sin acercar no hay hacia dónde mover.
    if (!aPantalla || inicio.vista === entera) return;
    // `aPantalla.a`: cuántos píxeles ocupa un milímetro del dibujo.
    ver(mover(inicio.vista, entera, dx / aPantalla.a, dy / aPantalla.a), entera);
  }

  function alSoltar() {
    const inicio = apretado.current;
    apretado.current = null;
    if (!inicio || inicio.seMovio || inicio.id === null) return;
    const forma = leida.formas.find((candidata) => candidata.id_origen === inicio.id);
    if (forma) alCorregir(alTocar(correcciones, forma));
  }

  function acercarAlCentro(factor: number) {
    ver(acercar(vista, entera, factor, vista.x + vista.ancho / 2, vista.y + vista.alto / 2), entera);
  }

  const marcadas = correccionesALaVista(correcciones, leida.formas);
  const dibujar = ({ forma, d }: { forma: FormaLeida; d: string }) => (
    <path
      key={forma.id_origen}
      data-id={forma.id_origen}
      d={d}
      fillRule="evenodd"
      vectorEffect="non-scaling-stroke"
      style={{ cursor: "pointer" }}
      {...pintura(forma)}
    >
      <title>{descripcion(forma)}</title>
    </path>
  );
  const boton = "border border-line rounded px-2 py-0.5 text-sm hover:bg-line/40 disabled:opacity-50";

  return (
    <div className="border border-line rounded p-3 mb-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="font-semibold">Así se lee</h2>
        {hayDibujo && (
          <div className="flex gap-1">
            <button
              className={boton}
              title="Acercar"
              disabled={vista.ancho <= entera.ancho / AUMENTO_MAXIMO}
              onClick={() => acercarAlCentro(PASO_DE_BOTON)}
            >
              +
            </button>
            <button
              className={boton}
              title="Alejar"
              disabled={acercada === null}
              onClick={() => acercarAlCentro(1 / PASO_DE_BOTON)}
            >
              −
            </button>
            <button className={boton} disabled={acercada === null} onClick={() => setAcercada(null)}>
              Ver todo
            </button>
          </div>
        )}
      </div>
      {!hayDibujo ? (
        <p className="text-sm mb-2">No hay ninguna forma cerrada para dibujar.</p>
      ) : (
        <svg
          ref={svgRef}
          viewBox={`${vista.x} ${vista.y} ${vista.ancho} ${vista.alto}`}
          className="w-full border border-line rounded bg-white select-none"
          style={{ maxHeight: "60vh", opacity: leyendo ? 0.5 : 1, cursor: acercada ? "grab" : undefined }}
          onPointerDown={alApretar}
          onPointerMove={alMoverElPuntero}
          onPointerUp={alSoltar}
          onPointerCancel={() => {
            apretado.current = null;
          }}
        >
          <defs>
            <pattern id={RAYADO} patternUnits="userSpaceOnUse" width={paso} height={paso} patternTransform="rotate(45)">
              <line x1={0} y1={0} x2={0} y2={paso} stroke={CONFLICTO} strokeWidth={paso * 0.3} />
            </pattern>
          </defs>
          {alFondo.map(dibujar)}
          {/* El relleno de lo que se corta deja ver lo de abajo, para que
              se note donde dos piezas se pisan. El rayado de lo que no va
              no tiene que verse a través: parecería que esa pieza tampoco
              va. Se lo tapa con blanco, antes de pintar ninguna pieza. */}
          {alFondo.length > 0 &&
            enJuego
              .filter(({ forma }) => forma.estado === "se_corta")
              .map(({ forma, d }) => (
                <path key={`fondo de ${forma.id_origen}`} d={d} fillRule="evenodd" fill="#FFFFFF" pointerEvents="none" />
              ))}
          {enJuego.map(dibujar)}
        </svg>
      )}
      <p className="text-xs mt-1">
        Pintado: se corta · Punteado: entra descartada · Rayado rojo: no va. En blanco, los huecos.
      </p>
      <p className="text-xs mb-2">
        Clic en una forma para corregirla: la que se corta pasa a «no va», y con otro clic vuelve. La descartada pasa
        primero a «se corta». Rueda para acercar, arrastrar para mover.
        {leyendo && " Leyendo de nuevo…"}
      </p>

      <p className="text-sm font-semibold mb-2">{resumenDeLectura(leida)}</p>

      {marcadas.length > 0 && (
        <div className="flex flex-wrap items-center gap-1 text-sm mb-2">
          <span>Tus correcciones:</span>
          {marcadas.map(({ id, texto }) => (
            <span key={id} className="border border-line rounded px-2 py-0.5 text-xs font-mono">
              {texto}{" "}
              <button
                title="Sacar esta corrección"
                aria-label={`Sacar la corrección «${texto}»`}
                onClick={() => alCorregir(sinCorreccion(correcciones, id))}
              >
                ✕
              </button>
            </span>
          ))}
          {/* Saca también las de la otra lectura (unida o sin unir), que acá no se listan. */}
          <button className="underline text-xs ml-1" onClick={() => alCorregir({})}>
            Quitar todas
          </button>
        </div>
      )}

      {leida.advertencias.length > 0 && (
        <div className="mb-2">
          <Banner variante="aviso">
            <ul className="list-disc pl-4">
              {leida.advertencias.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          </Banner>
        </div>
      )}

      {lectura.unida && (
        <label className="flex items-center gap-2 text-sm mb-2">
          <input type="checkbox" checked={unir} onChange={(evento) => alCambiarUnir(evento.target.checked)} />
          Unir las formas que se pisan
        </label>
      )}

      {piezasQueReemplaza > 0 && (
        <p className="text-sm mb-2">
          Cargar reemplaza {piezasQueReemplaza === 1 ? "la pieza" : `las ${piezasQueReemplaza} piezas`} que ya tiene
          este trabajo.
        </p>
      )}

      {!sePuedeCargar(leida) && (
        <p className="text-sm text-conflict mb-2">No queda ninguna forma para cortar: así no hay nada que cargar.</p>
      )}

      <div className="flex gap-2">
        <button
          className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
          disabled={cargando || leyendo || !sePuedeCargar(leida)}
          onClick={alCargar}
        >
          {cargando ? "Cargando…" : "Cargar"}
        </button>
        <button
          className="border border-line rounded px-3 py-1 text-sm hover:bg-line/40"
          disabled={cargando}
          onClick={alCancelar}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
```

- [x] **Step 7: La pestaña Piezas guarda la lista y vuelve a pedir la lectura**

En `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`:

**Cambio 1 de 5.** Reemplazar:

```tsx
import SeccionarPanel from "../../components/Seccionado/SeccionarPanel";
import LecturaPanel from "../../components/LecturaDxf/LecturaPanel";
import { esLaLecturaDe } from "../../components/LecturaDxf/dibujo";
import { originalesASeccionar, porQueSeccionar } from "../../components/Seccionado/geometria";
import { ApiError } from "../../api/client";
import type { LecturaDxf, Pieza } from "../../api/piezasYgrupos";
import { escalaParaCargar } from "./cargaDxf";
```

por:

```tsx
import SeccionarPanel from "../../components/Seccionado/SeccionarPanel";
import LecturaPanel from "../../components/LecturaDxf/LecturaPanel";
import { esLaLecturaDe, turnos } from "../../components/LecturaDxf/dibujo";
import { originalesASeccionar, porQueSeccionar } from "../../components/Seccionado/geometria";
import { ApiError } from "../../api/client";
import type { Correcciones, LecturaDxf, Pieza } from "../../api/piezasYgrupos";
import { escalaParaCargar } from "./cargaDxf";
```

**Cambio 2 de 5.** Reemplazar:

```tsx
  const [archivoActual, setArchivoActual] = useState<File | null>(null);
  const escala = escalaParaCargar(escalaAMm);
  // Cómo leyó el servidor el archivo, con qué archivo y escala se pidió.
  // Nada se guarda hasta «Cargar»; si después cambia el archivo o la
  // escala, esta lectura queda vieja y el panel se cierra solo.
  const [lectura, setLectura] = useState<{ datos: LecturaDxf; archivo: File; escala: string } | null>(null);
  const [unir, setUnir] = useState(false);
  const lecturaVigente = esLaLecturaDe(lectura, archivoActual, escala) ? lectura : null;

  const noSePudoSubir = "No se pudo subir el archivo. Si lo modificaste después de elegirlo, volvé a elegirlo.";

  async function alVerLectura() {
    if (!archivoActual || escala === null) return;
    setError(null);
    setAvisos([]);
    setLectura(null);
    // La unión nunca viene elegida de antes: se decide mirando este dibujo.
    setUnir(false);
    try {
      const datos = await leerDxf.mutateAsync({ archivo: archivoActual, escalaAMm: escala });
      setLectura({ datos, archivo: archivoActual, escala });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : noSePudoSubir);
    }
  }
```

por:

```tsx
  const [archivoActual, setArchivoActual] = useState<File | null>(null);
  const escala = escalaParaCargar(escalaAMm);
  // Cómo leyó el servidor el archivo, con qué archivo, escala y
  // correcciones se pidió. Nada se guarda hasta «Cargar»; si después
  // cambia el archivo o la escala, esta lectura queda vieja y el panel
  // se cierra solo.
  const [lectura, setLectura] = useState<{
    datos: LecturaDxf;
    archivo: File;
    escala: string;
    correcciones: Correcciones;
  } | null>(null);
  const [unir, setUnir] = useState(false);
  // Lo último que se marcó sobre el dibujo. Mientras llega la lectura que
  // lo aplica va un paso adelante de `lectura.correcciones`, que es lo
  // que se está viendo, y lo que se carga.
  const [correcciones, setCorrecciones] = useState<Correcciones>({});
  // Cada clic pide la lectura de nuevo: solo vale la última respuesta.
  const [pedidos] = useState(turnos);
  const lecturaVigente = esLaLecturaDe(lectura, archivoActual, escala) ? lectura : null;

  const noSePudoSubir = "No se pudo subir el archivo. Si lo modificaste después de elegirlo, volvé a elegirlo.";

  /** Pide la lectura con las correcciones `pedidas`. `aLaVista` son las
   * de la lectura que se está viendo: si el pedido falla, se sigue viendo
   * esa, y la lista vuelve a ser la suya. */
  async function leer(archivo: File, escalaPedida: string, pedidas: Correcciones, aLaVista: Correcciones) {
    const turno = pedidos.nuevo();
    setError(null);
    setCorrecciones(pedidas);
    try {
      const datos = await leerDxf.mutateAsync({ archivo, escalaAMm: escalaPedida, correcciones: pedidas });
      if (!pedidos.esElUltimo(turno)) return;
      setLectura({ datos, archivo, escala: escalaPedida, correcciones: pedidas });
    } catch (e) {
      if (!pedidos.esElUltimo(turno)) return;
      setCorrecciones(aLaVista);
      setError(e instanceof ApiError ? e.message : noSePudoSubir);
    }
  }

  function alVerLectura() {
    if (!archivoActual || escala === null) return;
    setAvisos([]);
    setLectura(null);
    // Ni la unión ni las correcciones vienen de antes: se deciden
    // mirando este dibujo.
    setUnir(false);
    void leer(archivoActual, escala, {}, {});
  }

  function alCorregir(nuevas: Correcciones) {
    if (!lecturaVigente) return;
    void leer(lecturaVigente.archivo, lecturaVigente.escala, nuevas, lecturaVigente.correcciones);
  }

  /** Cierra el panel. El turno nuevo deja sin valor a la lectura que
   * estuviera en camino: si no, al llegar lo abriría de nuevo. */
  function cerrarLectura() {
    pedidos.nuevo();
    setLectura(null);
    setCorrecciones({});
  }
```

**Cambio 3 de 5.** Reemplazar:

```tsx
        escalaAMm: lecturaVigente.escala,
        unir: unir && lecturaVigente.datos.unida !== null,
      });
      setLectura(null);
      setAvisos([
        `${resultado.piezas_creadas} pieza(s) importada(s).`,
```

por:

```tsx
        escalaAMm: lecturaVigente.escala,
        unir: unir && lecturaVigente.datos.unida !== null,
        correcciones: lecturaVigente.correcciones,
      });
      cerrarLectura();
      setAvisos([
        `${resultado.piezas_creadas} pieza(s) importada(s).`,
```

**Cambio 4 de 5.** Reemplazar:

```tsx
              className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
              disabled={escala === null || leerDxf.isPending}
              onClick={() => void alVerLectura()}
            >
              {leerDxf.isPending
```

por:

```tsx
              className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
              disabled={escala === null || leerDxf.isPending}
              onClick={alVerLectura}
            >
              {leerDxf.isPending
```

**Cambio 5 de 5.** Reemplazar:

```tsx
          unir={unir}
          alCambiarUnir={setUnir}
          alCargar={() => void alCargar()}
          alCancelar={() => setLectura(null)}
          cargando={subirDxf.isPending}
          piezasQueReemplaza={piezas?.length ?? 0}
```

por:

```tsx
          unir={unir}
          alCambiarUnir={setUnir}
          correcciones={correcciones}
          alCorregir={alCorregir}
          leyendo={leerDxf.isPending}
          alCargar={() => void alCargar()}
          alCancelar={cerrarLectura}
          cargando={subirDxf.isPending}
          piezasQueReemplaza={piezas?.length ?? 0}
```

- [x] **Step 8: Correr los tests y verlos pasar**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `Tests  97 passed (97)`.

- [x] **Step 9: Recorrer la pantalla con clics de verdad**

Lo que no cubre ninguna prueba automática: que el clic llegue a la forma, la rueda, el arrastre, y que lo que se carga sea lo que se ve. Se hace con un Chrome sin ventana contra una **copia** de la base. Antes, mirar que nadie escuche en 8000, 5173 ni 9223.

Si `backend/local/herramientas-2.1b-2026-10-12/logo-awaduct.dxf` no está, armarlo (lee la muestra del respaldo, no la toca):

```bash
cd backend && PYTHONPATH=. python local/herramientas-2.1b-2026-10-12/armar_logo_dxf.py
```

Expected: `formas del logo en la muestra: 34 | en el archivo nuevo: 35`. Son 35 porque, sin el fondo que lo rodea en la muestra, el lector lee el logo de otra manera (`diseno.md §2`).

Después, en tres terminales, con todo lo temporal en D::

```bash
mkdir -p D:/temp/2.1b-pantalla && cp backend/local/carteleria.db D:/temp/2.1b-pantalla/
cd backend && CARTELERIA_DATOS="D:/temp/2.1b-pantalla" python -m uvicorn app.api.app:app --port 8000
```

```bash
cd frontend && npx vite
```

```bash
"C:/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --remote-debugging-port=9223 --user-data-dir="D:/temp/2.1b-chrome" --no-first-run --disable-gpu --window-size=1500,1100 about:blank
```

Y el recorrido:

```bash
mkdir -p D:/temp/2.1b-capturas
node backend/local/herramientas-2.1b-2026-10-12/ver_correcciones.mjs D:/temp/2.1b-capturas "D:/User/Desktop/proyectos/cartelería/backend/local/herramientas-2.1b-2026-10-12/logo-awaduct.dxf" 9223
```

Expected: cada renglón dice `ok:` y termina en `Sin errores de consola.` Lo que comprueba:

1. Sin tocar nada: `12 piezas a cortar · 23 entran descartadas`, 35 formas en el dibujo, ninguna corrección listada.
2. Un clic sobre el contorno de la palabra pide la lectura una vez, lo deja rayado y con borde grueso, y figura abajo. «Quitar todas» vuelve a la lectura del sistema.
3. Los nueve clics del `diseno.md §2`, con lo que dice el resumen después de cada uno. Al final: `21 piezas a cortar · 8 entran descartadas · 8 no van`, las cinco formas de la palabra y los dos puntos de la leyenda pintados, la «T» sin agujero, y la casilla de unir ya no está porque nada se pisa.
4. Una mitad repetida que se sacó queda detrás de su letra y no se puede tocar; la ✕ de la lista la devuelve. Un clic sobre el borde del contorno, que no va, le saca la corrección.
5. Seis muescas de rueda acercan 1,25⁶ veces dejando quieto el punto bajo el puntero; arrastrar mueve y no cuenta como clic; no acerca más de 20 veces; «Ver todo» vuelve al dibujo entero.
6. «Cargar» guarda 29 piezas: 21 para cortar y 8 atenuadas. El aviso dice que 8 formas no se cargaron.

Mirar las cinco capturas de `D:/temp/2.1b-capturas`. La 3 tiene que mostrar la palabra y la leyenda pintadas, limpias, sobre el fondo rayado.

Al terminar, cerrar los tres procesos: son los de esta prueba, no los de Enzo.

- [x] **Step 10: Mostrarle las capturas a Enzo y, con su ok, commitear**

```bash
git add frontend/src/api/piezasYgrupos.ts frontend/src/api/piezasYgrupos.test.ts frontend/src/hooks/usePiezas.ts frontend/src/components/LecturaDxf frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx
git commit -m "feat(frontend): corregir la lectura con clics, acercar y mover el dibujo (2.1b)"
```

---

### Task 7: Medir con los archivos reales y documentar

**Files:**
- Modify: `docs/plan/2.1b-corregir-la-lectura/diseno.md`, `docs/BITACORA.md`

**Interfaces:**
- Consumes: los dos pedidos con correcciones (Tareas 2 a 4).
- Produces: nada que use otra tarea.

- [x] **Step 1: Los nueve clics sobre el logo, por los pedidos de verdad**

Contra una copia de la base, que es de donde sale el catálogo de chapas:

```bash
mkdir -p D:/temp/2.1b-logo && cp backend/local/carteleria.db D:/temp/2.1b-logo/
cd backend && CARTELERIA_DATOS="D:/temp/2.1b-logo" PYTHONPATH=. python local/herramientas-2.1b-2026-10-12/clics_del_logo.py
```

Expected, medido el 2026-10-13 con este mismo código:

```text
sin tocar nada: 12 a cortar, 23 descartadas, 0 no van
clic  1: la 497 (se_corta) -> no_va: 12 a cortar, 22 descartadas, 1 no van
clic  2: la 527 (se_corta) -> no_va: 26 a cortar, 9 descartadas, 2 no van
clic  3: la 533 (se_corta) -> no_va: 25 a cortar, 9 descartadas, 3 no van
clic  4: la 528 (se_corta) -> no_va: 24 a cortar, 9 descartadas, 4 no van
clic  5: la 529 (se_corta) -> no_va: 23 a cortar, 9 descartadas, 5 no van
clic  6: la 530 (se_corta) -> no_va: 22 a cortar, 9 descartadas, 6 no van
clic  7: la 531 (se_corta) -> no_va: 21 a cortar, 9 descartadas, 7 no van
clic  8: la 532 (descartada) -> cortar: 22 a cortar, 8 descartadas, 7 no van
clic  9: la 532 (se_corta) -> no_va: 21 a cortar, 8 descartadas, 8 no van
```

Cada renglón sigue con lo que sobra y lo que falta respecto de lo que dijo Enzo; el último termina en `de más: [] | faltan: []`. Y al final:

```text
  queda como dijo Enzo: True
  piezas a cortar con agujeros (cuántos): {498: 1, 501: 1, 503: 1, 508: 1, 513: 1, 515: 1, 522: 1, 524: 1}
  con la casilla de unir: se pisan 0; unida: no hay

cargado: 21 piezas para cortar, 8 descartadas [499, 517, 518, 519, 520, 521, 523, 525]
  lo cargado es lo que se vio: True
```

La «T» (526) no figura entre las piezas con agujeros: es el criterio de éxito del `diseno.md §1`. Los números son los de la muestra; en el archivo del logo solo, cada forma lleva ese número menos 497.

- [x] **Step 2: Los DXF reales, sin correcciones, se leen igual que antes**

Con el guion de 2.1a, que usa el mismo pedido que la pantalla:

```bash
cd backend
R=local/respaldo-2026-10-08-antes-de-borrar-trabajos/archivos
CARTELERIA_DATOS="D:/temp/2.1b-logo" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/Complejo.dxf" 100
CARTELERIA_DATOS="D:/temp/2.1b-logo" python scripts/leer_un_dxf.py "$R/trabajo-10.dxf" 100
CARTELERIA_DATOS="D:/temp/2.1b-logo" python scripts/leer_un_dxf.py "$R/trabajo-4.dxf" 100
CARTELERIA_DATOS="D:/temp/2.1b-logo" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/strat.dxf" 1
CARTELERIA_DATOS="D:/temp/2.1b-logo" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/carrusel.dxf" 1
CARTELERIA_DATOS="D:/temp/2.1b-logo" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/esqueletos.dxf" 1
CARTELERIA_DATOS="D:/temp/2.1b-logo" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/repisas.dxf" 1
```

Expected, medido el 2026-10-13 con este mismo código. Las cantidades son las de la Tarea 7 del plan de 2.1a; lo que cambia es lo que pesa la respuesta, por el detalle nuevo del dibujo:

| Archivo | Formas | Se pisan | Sin unir: a cortar / descartadas | Unida: a cortar / descartadas | Pesa la respuesta |
|---|---|---|---|---|---|
| `Complejo.dxf` | 40 | 8 | 26 / 14 | 24 / 34 | 0,3 MB |
| `trabajo-10.dxf` (el `Complejo.dxf` anterior) | 162 | 8 | 105 / 57 | 103 / 77 | 0,5 MB |
| `trabajo-4.dxf` (`Muestra Vectores.dxf`) | 2.154 | 39 | 1.786 / 368 | 1.778 / 370 | 3,8 MB |
| `strat.dxf` | 120 | 13 | 107 / 13 | 105 / 7 | 0,3 MB |
| `carrusel.dxf` | 35 | 0 | 35 / 0 | — | 0,1 MB |
| `esqueletos.dxf` | 15 | 0 | 13 / 2 | — | 0,1 MB |
| `repisas.dxf` | 12 | 0 | 12 / 0 | — | menos de 0,1 MB |

En `Complejo.dxf`, la unida tiene que mostrar `trabajo-1-39/unida: 4610 x 4610 mm, 4.30 m2, 25 huecos`.

Si una cantidad no coincide, parar y mirar por qué antes de seguir: es la única comprobación de que el lector, sin correcciones, no cambió.

- [x] **Step 3: Actualizar el diseño**

En `docs/plan/2.1b-corregir-la-lectura/diseno.md`, la línea de estado pasa a decir, con la fecha del día:

```markdown
> **Estado:** **construido el AAAA-MM-DD, en la rama `feat/corregir-la-lectura`, a la espera de que Enzo lo fusione.** Lo que el código precisó del diseño está al principio de [`plan.md`](plan.md), y lo que corrigió el ensayo, en el §8.
```

Y en la última fila de la tabla del §7 («El dibujo pesa más»), el efecto pasa a decir lo que dio el Step 2:

```markdown
Con `PAR-52` en 1/20000, la respuesta de `Complejo.dxf`, que trae sus dos lecturas, pesa 0,3 MB; la de `Muestra Vectores.dxf`, 3,8 MB en vez de 2,3
```

- [x] **Step 4: Escribir la entrada de la bitácora**

En `docs/BITACORA.md`, arriba de la entrada más nueva, con la fecha del día en que se termina:

```markdown
## AAAA-MM-DD — Corregir a mano la lectura del DXF (2.1b): clics sobre el dibujo, acercar y mover

Sub-proyecto [`plan/2.1b-corregir-la-lectura/`](plan/2.1b-corregir-la-lectura/diseno.md). Rama `feat/corregir-la-lectura`.

### Qué se hizo

- **El dibujo de «Así se lee» ahora se corrige con clics.** Una forma que se corta pasa a «no va»; una descartada pasa a «se corta» y, con otro clic, a «no va». Lo que no va no se carga. Cada corrección figura debajo del dibujo, con una ✕ que la saca.
- **El servidor vuelve a leer en cada clic,** con el archivo y la lista de correcciones. Lo marcado manda, y lo demás se acomoda solo: sacar un contorno pone a cortar las letras que encierra.
- **Lo que no va no es madre ni hueco de nadie, ni se une.** Sus agujeros chicos pasan a ser formas, la pieza que lo tenía adentro queda llena, y la casilla de unir no lo junta con nada.
- **El dibujo se acerca y se mueve:** rueda, arrastre, tres botones, hasta 20 aumentos.
- El logo «AWADUCT / PERFECTO ETERNO» de la muestra, solo en un archivo, queda como dijo Enzo con nueve clics: 21 piezas a cortar.
- Backend 500 tests en verde (467 antes), frontend 97 (56 antes).

### Qué se decidió

- **Dos opciones por forma, «se corta» y «no va», y un solo gesto.** El clic da toda la vuelta: lo contrario de lo que se ve, después «no va», después como lo leyó el sistema (Enzo, 2026-10-13).
- **Lo que no va se dibuja al fondo.** Con el rayado encima de lo que se corta, media palabra parecía que no iba (Enzo, 2026-10-13).
- **El código se ensayó entero antes de escribir el plan,** contra un DXF con el logo solo y en un navegador. Ahí apareció que la palabra del logo son cinco formas y no una, y tres reglas que el diseño no tenía (`diseno.md §8`).

### Cambios en el registro

`PAR-52` pasa de 1/4000 a 1/20000. Alta de `PAR-53`.

### Pendiente

- **El lector decide pieza o agujero por cuántos contornos encierran a la forma.** El mismo dibujo se lee distinto solo que junto a otros. La corrección a mano lo resuelve en cada caso; cambiar esa regla quedó afuera.
- Al sacar una placa con tornillos, cada tornillo aparece como una forma a cortar y hay que sacarlo también. Marcar de a muchas con un recuadro quedó anotado.
- Girar una pieza con ángulo libre en el anidado automático (pedido de Enzo del 2026-10-12): es del motor.
- Las miniaturas de la tabla de Piezas siguen dadas vuelta.
```

- [x] **Step 5: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add docs/plan/2.1b-corregir-la-lectura/diseno.md docs/BITACORA.md
git commit -m "docs: corregir la lectura (2.1b) construida y medida"
```

- [x] **Step 6: Con el ok de Enzo, subir la rama y abrir el PR**

Subir es publicar: no se hace sin que lo pida.

```bash
git push -u origin feat/corregir-la-lectura
gh pr create --base main --title "feat(ingesta): corregir a mano la lectura del DXF, con clics sobre el dibujo (2.1b)" --body "Diseño y plan en docs/plan/2.1b-corregir-la-lectura/.

- En «Así se lee», un clic sobre una forma la pasa a «no va» o a «se corta». Lo que no va no se carga.
- El servidor vuelve a leer en cada clic con la lista de correcciones: lo marcado manda y lo demás se acomoda.
- Lo que no va no es madre ni hueco de nadie, ni se une con nada.
- El dibujo se acerca y se mueve.

Backend 500 tests, frontend 97. Medido sobre los DXF reales y recorrido en un navegador: Tareas 6 y 7 del plan."
```

Fusionar es de Enzo: `gh pr merge <n> --merge`, con dos guiones.

---

### Task 8: Cerrar, después de que Enzo fusione

**Files:**
- Move: `docs/plan/2.1b-corregir-la-lectura/` → `docs/historico/2.1b-corregir-la-lectura/`
- Modify: `docs/plan/PLAN-MAESTRO.md`, `docs/MAPA-DEL-PROYECTO.md`, `docs/REGISTRO.md`, `docs/BITACORA.md`

- [x] **Step 1: Pasar la carpeta a `historico/`**

`CONVENCIONES.md §8 bis`: un sub-proyecto terminado pasa entero a `docs/historico/`, en el commit que lo cierra.

```bash
git switch main && git pull --rebase origin main
git mv docs/plan/2.1b-corregir-la-lectura docs/historico/2.1b-corregir-la-lectura
grep -rn "2.1b-corregir-la-lectura" docs backend frontend/src --include=*.md --include=*.py --include=*.ts --include=*.tsx
```

Corregir cada ruta que devuelva el `grep`: dentro de la carpeta movida, `../PLAN-MAESTRO.md` pasa a `../../plan/PLAN-MAESTRO.md` y `../../historico/` a `../`; en el plan maestro, `2.1b-corregir-la-lectura/diseno.md` pasa a `../historico/2.1b-corregir-la-lectura/diseno.md`; en el registro, los comentarios del código y la bitácora, `docs/plan/` y `plan/` pasan a `docs/historico/` e `historico/`.

- [x] **Step 2: Dejar el estado y los pendientes en el plan maestro**

En `diseno.md` y `plan.md` (ya en `historico/`), la línea de estado pasa a «**cerrado el AAAA-MM-DD**», con el número del PR.

En `docs/plan/PLAN-MAESTRO.md §7`:

- En la fila de 2.1, «y **2.1b**, corregir la lectura a mano con clics sobre el dibujo, con diseño en» pasa a «construida el AAAA-MM-DD:», con la ruta nueva.
- De la tabla «Pendientes de la lectura con imagen» salen las dos filas que esto resolvió: «Corregir a mano la lectura…» y «Acercar y mover el dibujo…». De la primera queda viva una parte, que pasa a la tabla nueva: la casilla de unir sigue valiendo para el archivo entero.
- Después de esa tabla:

```markdown
**Pendientes de corregir la lectura a mano.** Se cerró el AAAA-MM-DD y su carpeta pasó a [`historico/2.1b-corregir-la-lectura/`](../historico/2.1b-corregir-la-lectura/). Esto es lo que quedó vivo y se sigue desde acá.

| Pendiente | De dónde sale | Depende de |
|---|---|---|
| El lector decide pieza o agujero por cuántos contornos encierran a la forma: el mismo dibujo se lee distinto solo que junto a otros | §2 y §7 de su diseño | — |
| Elegir qué grupo de formas se une: la casilla vale para el archivo entero | §3 de su diseño | Que aparezca un diseño que lo pida |
| Marcar de a muchas formas con un recuadro. Al sacar una placa con tornillos hay que sacar cada tornillo | §3 y §7 de su diseño | Que haga falta |
| Recordar las correcciones de una carga a la otra | §3 de su diseño | — |
| Corregir la lectura en la importación de varios diseños (`/importaciones/dxf/...`) | §3 de su diseño | Carril B, B2 y B4 |
```

En `docs/MAPA-DEL-PROYECTO.md §1`, en la fila «Importación de DXF»: a «Qué hay» se le suma «Corregir la lectura con clics sobre el dibujo, y acercarlo y moverlo (2.1b)».

- [x] **Step 3: Mostrárselo a Enzo y, con su ok, commitear y subir**

```bash
git add -A docs backend/app backend/tests frontend/src
git status --short
git commit -m "docs: corregir la lectura cerrada, su carpeta pasa a historico"
git push origin main
```

Antes del commit, mirar el `git status`: no tiene que figurar `Presupuesto_Cliente_Carteleria.docx`.

---

## Desvíos respecto de este plan (2026-10-13)

**En la ejecución.**

- **Cómo se aplicó cada tarea.** Los archivos no se tipearon: se copiaron del repo del ensayo, del que salió este plan (`git -C .superpowers/ensayo-2.1b show Tn-codigo:<ruta>`), y se comprobó que quedaran en CRLF. Cada tarea falló y pasó con los mismos números que dice el plan.
- **Tarea 5, Step 6.** La fila de `PAR-53` quedó al final de su tabla del registro: la de `PAR-52` era la última.
- **Tarea 7.** Además de lo que pedía, se actualizó la línea de estado de este plan y se tildaron sus pasos.

**Lo que dejó la revisión de la rama.** Un revisor aparte leyó la rama entera: «se puede fusionar, con arreglos». Corrió las pruebas y, por su cuenta, 720 lecturas corregidas al azar sobre 120 dibujos: ningún error, y lo que muestra la lectura fue siempre lo que guarda la carga. Se arregló, cada cosa con una prueba que falló primero:

1. **Lo de adentro de una forma que no va no se leía como si ella no estuviera** (`dxf.py`, `_clasificar_piezas_y_agujeros`). Si la forma sacada estaba adentro de otra que se corta, lo que tenía adentro seguía colgando de ella: una placa con un marco dibujado alrededor de su ventana se cargaba llena, y la ventana, como pieza suelta. No había clic que lo arreglara. En el logo no pasa, porque los contornos que se sacan son los de más afuera. Ahora lo de adentro cuelga del contorno más chico que la rodea y sí va, como agujero suyo. Pruebas: `test_lo_de_adentro_de_una_forma_que_no_va_cuelga_de_la_que_la_rodea`, `test_si_la_que_la_rodea_tampoco_va_cuelga_de_la_primera_que_si`, `test_al_sacar_una_forma_lo_que_tenia_adentro_es_el_hueco_de_la_que_la_rodea` y `test_cargar_sin_el_marco_guarda_la_placa_con_su_ventana`.
2. **Los huecos de una pieza unida que no va seguían entrando descartados** (`rutas_trabajos.py`, `_leer`), con un motivo que ya no era cierto. Enzo decidió que se van con ella. Queda el que se haya marcado. Pruebas: `test_los_huecos_de_una_pieza_unida_que_no_va_se_van_con_ella` y `test_un_hueco_puesto_a_cortar_queda_aunque_su_pieza_unida_no_vaya`.
3. **Un doble clic rápido sobre una forma que no va la dejaba forzada a cortar** (`dibujo.ts`, `alTocar`). El segundo clic veía la lista ya sin la marca y el dibujo de antes. Ahora ese clic no hace nada, y el panel no vuelve a pedir la lectura si la lista no cambió. Prueba: la de `alTocar` que termina en «el dibujo es de antes del último clic».
4. **`turnos()` repetía a `crearTurnos()`,** que ya estaba en `Seccionado/turnos.ts` con sus pruebas. La pestaña Piezas usa esa; la de `dibujo.ts` y sus tres pruebas salieron.
5. **El diseño decía que cambiar la escala «borra las correcciones».** Cierra el panel, y si se vuelve a la escala de antes reaparecen, como la lectura. Se corrigió el texto (`diseno.md §5.3` y `§7`).

Backend 506 en verde después de los arreglos, frontend 95. Se volvió a medir: el logo da los mismos números en cada clic, en los dos órdenes en que se pueden tocar el contorno de la leyenda y la chapa dibujada; los siete DXF reales, sin correcciones, las mismas cantidades de la Tarea 7; y el recorrido en el navegador del Step 9 de la Tarea 6, entero y sin errores.

**Lo que señaló y no se tocó:**

- La parte de la pestaña Piezas que maneja los pedidos (vale la última respuesta, cancelar la descarta, se carga con la lista que se ve, si falla vuelve la lista) no tiene prueba en el repositorio: la cubre el recorrido en el navegador, que está afuera. Se puede pasar ese flujo a una función sin React y probarla con promesas falsas.
- Si la carga da 400, el DXF guardado del trabajo ya quedó pisado por el archivo nuevo. El orden es anterior a esta rama, y hoy nadie vuelve a leer ese archivo.
- Una corrección cuyo nombre tiene una barra se acepta con cualquier cosa después de la barra; alcanzaría con `/unida` y `/huecoN`.
- Con un touchpad, o con la rueda inclinada, el acercamiento salta: cada evento chico acerca 1,25 veces, y uno horizontal aleja.
- `cajaDelDibujo` usa `Math.min(...xs)` con todos los puntos de la lectura. Con el dibujo cinco veces más detallado queda menos margen en un archivo enorme. Estimado, no medido.
- Un JSON con miles de niveles en `correcciones` da 500; solo con un pedido armado a mano.
- `sin_los_huecos_de_lo_que_no_va` recorre todos los agujeros aunque no haya nada sacado.
- El motivo «lo marcó quien carga» le habla en tercera persona a quien está cargando.
- El servidor acepta cargar con todo sacado, y deja el trabajo sin piezas: lo impide la pantalla, no el pedido.
- Una hoja de chapa de catálogo marcada «no va» sigue contando como hoja para lo que tiene adentro. Es de los archivos con hojas armadas, que quedaron afuera (`diseno.md §3`).
- El dibujo no se maneja con teclado ni con pantalla táctil.
