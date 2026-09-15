# Frontend del cotizador — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Una SPA (React+Vite) que recorra el ciclo completo del cotizador — desde subir un DXF hasta el desglose de un presupuesto, incluyendo el ajuste manual de piezas sobre el plano — para una herramienta interna de un solo usuario, sin auth.

**Architecture:** `frontend/` nuevo, hermano de `backend/`. React Router organiza la navegación como `Trabajo` (contenedor: piezas/grupos/anidado/ajuste, una vez) → `Presupuesto` (N opciones de precio por trabajo, vía `duplicar`). React Query maneja todo el estado de servidor. Dos endpoints nuevos y chicos se agregan al backend (listar ejecuciones de un grupo, comparar formatos) — ambos envoltorios de código de dominio ya probado, sin tocar el modelo de datos.

**Tech Stack:** Vite, React 18, TypeScript, React Router, TanStack Query, Tailwind CSS, Vitest. Backend: FastAPI/SQLAlchemy ya existentes.

**Spec:** `docs/superpowers/specs/2026-09-15-frontend-cotizador-design.md`

## Global Constraints

- Paleta Tailwind (nunca decorativa, un rol fijo cada una): `paper #F5F1E8` (fondo), `ink #2B2420` (texto), `line #E3D9C6` (hairlines/grilla), `cut #2E8074` (geometría/corte), `bronze #C9922E` (dinero), `conflict #C4432A` (colocación inválida).
- Tipografía: `IBM Plex Sans` para todo el texto; `IBM Plex Mono` **solo** para valores numéricos reales (mm, ángulos, montos) en tablas/campos — nunca en etiquetas.
- Bordes: radio suave (8px por default en Tailwind config).
- Backend corre en `http://localhost:8000` (`uvicorn app.api.app:app --reload` desde `backend/`); frontend en `http://localhost:5173` (Vite default).
- Los campos `Decimal` del backend viajan como **string** en el JSON (confirmado en `backend/tests/api/test_rutas_nesting.py`, ej. `final["parametros"]["kerf_mm"] == "2"`) — los tipos TS los modelan como `string`, se convierten a `number` solo para render/matemática de UI, nunca se hace matemática de dinero en el cliente (todo cálculo real de costeo/totales lo hace el servidor).
- Todos los errores HTTP del backend traen `{"detail": "mensaje humano"}` — se muestran tal cual, nunca se inventa texto genérico.
- Sin suite de tests de componentes: se verifica corriendo la app contra la API local. Sí hay tests automatizados para: el endpoint backend nuevo (pytest, seguido el patrón de `backend/tests/api/`) y la conversión mm↔px/rotación del editor SVG (vitest, TDD real).

---

## File Structure

```
backend/app/api/
  esquemas_nesting.py       (modificar: + esquemas de comparación de formatos)
  rutas_nesting.py          (modificar: + GET /grupos/{id}/ejecuciones, + POST /grupos/{id}/comparar-formatos)
  app.py                    (modificar: + CORSMiddleware)
backend/tests/api/
  test_rutas_nesting.py     (modificar: + tests de los dos endpoints nuevos)

frontend/
  package.json, vite.config.ts, tsconfig.json, tailwind.config.ts, postcss.config.js, index.html
  src/
    main.tsx, App.tsx
    styles/index.css
    api/
      client.ts             (fetch wrapper + ApiError)
      client.test.ts
      trabajos.ts            (Trabajo, Pieza, GrupoDeCorte — CRUD)
      nesting.ts             (Ejecucion, Colocacion, anidar, comparar-formatos, costeo)
      catalogo.ts            (Material, Formato — solo lectura)
      presupuestos.ts        (Cliente, Presupuesto, LineaCosto, Totales, Desglose)
    hooks/
      useTrabajos.ts, usePiezas.ts, useGrupos.ts, useNesting.ts, useCatalogo.ts, usePresupuestos.ts
    routes/
      TrabajosLista.tsx
      TrabajoWorkspace/
        WorkspaceLayout.tsx
        PiezasTab.tsx
        GruposTab.tsx
        AnidadoTab.tsx
        AjusteTab.tsx
        CosteoTab.tsx
    components/
      Banner.tsx, EstadoBadge.tsx, PiezaMiniPreview.tsx
      PlanoEditor/
        PlanoEditor.tsx
        geometria.ts
        geometria.test.ts
```

---

## Task 1: CORS para el frontend local

**Files:**
- Modify: `backend/app/api/app.py`
- Test: `backend/tests/api/test_rutas_nesting.py` (agregar un test al final; reutiliza la fixture `cliente` ya existente)

**Interfaces:**
- Produces: la API acepta requests con header `Origin: http://localhost:5173` y responde con `access-control-allow-origin` en la respuesta — nada que otros tasks consuman directamente, es infraestructura.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_cors_permite_origen_del_frontend_local(cliente):
    respuesta = cliente.get("/trabajos", headers={"Origin": "http://localhost:5173"})
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"
```

Agregar al final de `backend/tests/api/test_rutas_nesting.py`.

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && pytest tests/api/test_rutas_nesting.py -k test_cors -v`
Expected: FAIL — `KeyError: 'access-control-allow-origin'` (el header no existe todavía).

- [ ] **Step 3: Agregar el middleware**

En `backend/app/api/app.py`, agregar el import y el middleware — el comentario explica por qué el origen es fijo, no una lista:

```python
from fastapi.middleware.cors import CORSMiddleware
```

Y después de crear `app = FastAPI(...)`:

```python
# Único origen permitido: el dev server de Vite del frontend interno
# (docs/superpowers/specs/2026-09-15-frontend-cotizador-design.md). No se
# amplía a "*" ni a una lista: esta API sigue sin autenticación y solo
# corre en localhost (ver el docstring de este módulo).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `cd backend && pytest tests/api/test_rutas_nesting.py -k test_cors -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/app.py backend/tests/api/test_rutas_nesting.py
git commit -m "feat(backend): habilitar CORS para el frontend local"
```

---

## Task 2: Listar el historial de ejecuciones de un grupo

**Files:**
- Modify: `backend/app/api/rutas_nesting.py`
- Test: `backend/tests/api/test_rutas_nesting.py`

**Interfaces:**
- Consumes: `EjecucionNesting` (modelo, ya existe), `EjecucionLeer` (esquema, ya existe en `esquemas_nesting.py`), `_grupo_o_404` (helper — **no existe en `rutas_nesting.py` todavía**, hay que importarlo desde `rutas_trabajos.py` igual que ya se hace con `_ejecucion_o_404`/`_trabajo_o_404` en ese mismo archivo).
- Produces: `GET /grupos/{grupo_id}/ejecuciones` → `list[EjecucionLeer]`, ordenada por `id` descendente (la más reciente primero) — la consume la pantalla de Anidado (Task 10) para el historial.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `backend/tests/api/test_rutas_nesting.py`, en la sección de "Anidado":

```python
def test_listar_ejecuciones_de_grupo_ordena_mas_reciente_primero(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    primera_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, primera_id)
    segunda_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, segunda_id)

    respuesta = cliente.get(f"/grupos/{grupo['id']}/ejecuciones")

    assert respuesta.status_code == 200
    ids = [e["id"] for e in respuesta.json()]
    assert ids == [segunda_id, primera_id]


def test_listar_ejecuciones_de_grupo_inexistente_da_404(cliente):
    assert cliente.get("/grupos/999/ejecuciones").status_code == 404
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && pytest tests/api/test_rutas_nesting.py -k test_listar_ejecuciones -v`
Expected: FAIL — 404 not found (la ruta no existe).

- [ ] **Step 3: Implementar la ruta**

En `backend/app/api/rutas_nesting.py`, agregar el import de `_grupo_o_404` junto al de `_grupo_o_404`/`_trabajo_o_404` que ya se importan de `rutas_trabajos`:

```python
from .rutas_trabajos import _grupo_o_404, _trabajo_o_404
```

Y agregar la ruta, cerca de `listar_colocaciones` (mismo patrón: 404 del padre, `select` ordenado):

```python
@router.get("/grupos/{grupo_id}/ejecuciones", response_model=list[EjecucionLeer])
def listar_ejecuciones(grupo_id: int, sesion: Session = Depends(obtener_sesion)) -> list[EjecucionNesting]:
    """Historial de anidados de un grupo — comparar aprovechamiento y
    planchas entre corridas (motor, parámetros) antes de marcar una
    definitiva. La más reciente primero."""
    _grupo_o_404(sesion, grupo_id)
    consulta = (
        select(EjecucionNesting)
        .where(EjecucionNesting.grupo_id == grupo_id)
        .order_by(EjecucionNesting.id.desc())
    )
    return list(sesion.execute(consulta).scalars().all())
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd backend && pytest tests/api/test_rutas_nesting.py -k test_listar_ejecuciones -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite de ese archivo para no haber roto nada**

Run: `cd backend && pytest tests/api/test_rutas_nesting.py -v`
Expected: todos PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/rutas_nesting.py backend/tests/api/test_rutas_nesting.py
git commit -m "feat(backend): listar historial de ejecuciones de un grupo de corte"
```

---

## Task 3: Comparar formatos antes de asignar material (`CART-205`)

**Files:**
- Modify: `backend/app/api/esquemas_nesting.py`
- Modify: `backend/app/api/rutas_nesting.py`
- Test: `backend/tests/api/test_rutas_nesting.py`

**Interfaces:**
- Consumes: `comparar_formatos`, `formato_recomendado`, `OpcionFormato` de `backend/app/services/nesting/comparador.py` (ya existen, probados); `Formato`/`Material` de `..modelos.catalogo`; `_datos_para_anidar` (mismo archivo, ya existe) como referencia de cómo se arma `ParametrosCorte` desde un material.
- Produces: `POST /grupos/{grupo_id}/comparar-formatos` con body `{"formato_ids": [1, 2]}` → `list[OpcionFormatoLeer]` (uno por `formato_id`, en el mismo orden pedido) — sin persistir nada. Lo consume la pantalla de Grupos (Task 9).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `backend/tests/api/test_rutas_nesting.py`, sección nueva al final:

```python
# --- Comparar formatos (CART-205) -----------------------------------------


def _grupo_con_piezas_sin_formato(cliente, tmp_path, *, ancho=100, alto=100) -> dict:
    """Un grupo con piezas asignadas pero SIN formato — el estado en el
    que corresponde comparar, antes de decidir un material."""
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    documento = ezdxf.new()
    documento.modelspace().add_lwpolyline(
        [(0, 0), (ancho, 0), (ancho, alto), (0, alto)], close=True
    )
    ruta = tmp_path / "pieza.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("pieza.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Sin material"}).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    return grupo


def test_comparar_formatos_devuelve_uno_por_formato_y_marca_el_mas_barato(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    _material_caro, formato_caro = _material_con_formato_y_parametros(cliente)
    material_barato = cliente.post("/materiales", json={"nombre": "MDF"}).json()
    formato_barato = cliente.post(
        f"/materiales/{material_barato['id']}/formatos",
        json={"ancho_mm": "1000", "alto_mm": "1000", "unidad_venta": "M2", "costo_unidad_venta": "10"},
    ).json()
    cliente.put(
        f"/materiales/{material_barato['id']}/parametros-corte",
        json={
            "kerf_mm": "2", "margen_borde_mm": "10", "separacion_piezas_mm": "5",
            "rotaciones_permitidas": "LIBRE_0_90",
        },
    )

    respuesta = cliente.post(
        f"/grupos/{grupo['id']}/comparar-formatos",
        json={"formato_ids": [formato_caro["id"], formato_barato["id"]]},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [op["formato_id"] for op in cuerpo] == [formato_caro["id"], formato_barato["id"]]
    assert cuerpo[0]["recomendado"] is False
    assert cuerpo[1]["recomendado"] is True
    assert Decimal(cuerpo[1]["costo_total"]) < Decimal(cuerpo[0]["costo_total"])

    # No persiste nada: el grupo sigue sin formato ni ejecuciones.
    assert cliente.get(f"/trabajos/{grupo['trabajo_id']}/grupos").json()[0]["formato_id"] is None
    assert cliente.get(f"/grupos/{grupo['id']}/ejecuciones").json() == []


def test_comparar_formatos_grupo_sin_piezas_da_400(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Vacío"}).json()
    _material, formato = _material_con_formato_y_parametros(cliente)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparar-formatos", json={"formato_ids": [formato["id"]]})

    assert respuesta.status_code == 400
    assert "piezas" in respuesta.json()["detail"]


def test_comparar_formatos_con_formato_inexistente_da_404(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparar-formatos", json={"formato_ids": [999]})

    assert respuesta.status_code == 404


def test_comparar_formatos_grupo_inexistente_da_404(cliente):
    assert cliente.post("/grupos/999/comparar-formatos", json={"formato_ids": [1]}).status_code == 404
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && pytest tests/api/test_rutas_nesting.py -k comparar_formatos -v`
Expected: FAIL — 404 not found en todos (la ruta no existe).

- [ ] **Step 3: Agregar los esquemas**

En `backend/app/api/esquemas_nesting.py`, al final:

```python
# --- Comparar formatos, sin comprometer el grupo (`CART-205`) -------------


class ComparacionFormatosCrear(BaseModel):
    formato_ids: list[int]


class OpcionFormatoLeer(BaseModel):
    formato_id: int
    formato_descripcion: str
    material_nombre: str
    planchas_usadas: int
    aprovechamiento_pct: Decimal
    costo_total: Decimal
    moneda: str
    recomendado: bool
```

- [ ] **Step 4: Implementar la ruta**

En `backend/app/api/rutas_nesting.py`, agregar los imports que faltan junto a los que ya están:

```python
from ..modelos.catalogo import Formato  # ya se importa en esquemas_nesting indirectamente; acá hace falta el modelo
from ..services.nesting.comparador import OpcionFormato, comparar_formatos, formato_recomendado
```

Y la ruta, después de `obtener_costeo` (usa las mismas piezas/parámetros que `_datos_para_anidar`, pero para VARIOS formatos candidatos en vez del `formato_id` ya asignado al grupo):

```python
@router.post("/grupos/{grupo_id}/comparar-formatos", response_model=list[OpcionFormatoLeer])
def comparar_formatos_de_grupo(
    grupo_id: int, datos: ComparacionFormatosCrear, sesion: Session = Depends(obtener_sesion)
) -> list[OpcionFormatoLeer]:
    """Compara las piezas de un grupo contra varios formatos candidatos
    SIN persistir nada — ni tocar `grupo.formato_id` ni crear una
    `EjecucionNesting`. Es el paso previo a elegir un material cuando
    se quiere ofrecer una variante más económica o en otro material
    (`docs/superpowers/specs/2026-09-15-frontend-cotizador-design.md §5.2`).
    """
    grupo = _grupo_o_404(sesion, grupo_id)
    piezas = [p for p in grupo.piezas if not p.descartada]
    if not piezas:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"El grupo «{grupo.nombre}» no tiene piezas para comparar.")
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
        if formato.costo_unidad_venta is None or formato.unidad_venta != "M2":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El formato «{formato.ancho_mm}×{formato.alto_mm}» no tiene un precio por plancha "
                f"calculable (se vende por «{formato.unidad_venta}», no por m²).",
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

    resultados = comparar_formatos(piezas_dominio, opciones, tope_planchas_advertencia=_TOPE_PLANCHAS_ADVERTENCIA)
    recomendado = formato_recomendado(resultados)

    return [
        OpcionFormatoLeer(
            formato_id=formato.id,
            formato_descripcion=f"{formato.ancho_mm}×{formato.alto_mm} mm",
            material_nombre=formato.material.nombre,
            planchas_usadas=resultado.resultado_anidado.planchas_usadas,
            aprovechamiento_pct=resultado.reporte_aprovechamiento.porcentaje_aprovechamiento,
            costo_total=resultado.costo_total,
            moneda=formato.moneda,
            recomendado=resultado is recomendado,
        )
        for formato, resultado in zip(formatos, resultados)
    ]
```

> Nota para quien implemente: `ComparacionFormatosCrear` y `OpcionFormatoLeer` se importan junto al resto de `esquemas_nesting` en el bloque de imports de arriba del archivo (agregarlos a la lista existente). Verificar el nombre exacto del campo de `ReporteAprovechamiento` (`porcentaje_aprovechamiento`) contra `backend/app/services/nesting/aprovechamiento.py` antes de asumirlo — es el mismo campo que ya usa `EjecucionLeer.aprovechamiento_pct` en este archivo.

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `cd backend && pytest tests/api/test_rutas_nesting.py -k comparar_formatos -v`
Expected: PASS

- [ ] **Step 6: Correr toda la suite de backend para no haber roto nada**

Run: `cd backend && pytest -v`
Expected: todos PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/esquemas_nesting.py backend/app/api/rutas_nesting.py backend/tests/api/test_rutas_nesting.py
git commit -m "feat(backend): comparar formatos candidatos antes de asignar material a un grupo (CART-205)"
```

---

## Task 4: Scaffold del frontend — Vite, React, Tailwind, identidad visual

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.ts`, `frontend/postcss.config.js`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/styles/index.css`
- Modify: `.gitignore` (raíz)

**Interfaces:**
- Produces: la app arranca con `npm run dev` en `http://localhost:5173`, con los tokens de color/tipografía de la spec disponibles como clases Tailwind (`bg-paper`, `text-ink`, `bg-cut`, `bg-bronze`, `bg-conflict`, `font-sans`, `font-mono`) — todas las tareas siguientes los usan.

- [ ] **Step 1: Crear `package.json`**

```json
{
  "name": "carteleria-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.26.0",
    "@tanstack/react-query": "^5.56.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 2: Crear `vite.config.ts`** (con `test` de Vitest ya incluido, para no reabrir este archivo en la Tarea 5)

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  test: { environment: "node" },
});
```

- [ ] **Step 3: Crear `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Crear `tailwind.config.ts`** con los tokens de la spec

```typescript
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F5F1E8",
        ink: "#2B2420",
        line: "#E3D9C6",
        cut: "#2E8074",
        bronze: "#C9922E",
        conflict: "#C4432A",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "8px",
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 5: Crear `postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 6: Crear `index.html`**

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cartelería — cotizador</title>
  </head>
  <body class="bg-paper text-ink">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Crear `src/styles/index.css`**

```css
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: "IBM Plex Sans", system-ui, sans-serif;
}
```

- [ ] **Step 8: Crear `src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./styles/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
```

- [ ] **Step 9: Crear `src/App.tsx`** (versión de esta tarea — la Tarea 6 la reemplaza por el router real)

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-paper text-ink p-8">
      <h1 className="text-2xl font-semibold">Cartelería — cotizador</h1>
      <p className="mt-2 text-sm">
        Herramienta interna.{" "}
        <span className="rounded px-2 py-1 bg-cut text-paper">corte</span>{" "}
        <span className="rounded px-2 py-1 bg-bronze text-paper">dinero</span>{" "}
        <span className="rounded px-2 py-1 bg-conflict text-paper">conflicto</span>
      </p>
      <p className="mt-2 font-mono text-sm">123.45 mm · $ 45.678,90</p>
    </div>
  );
}
```

- [ ] **Step 10: Instalar dependencias**

Run: `cd frontend && npm install`
Expected: instala sin errores.

- [ ] **Step 11: Agregar `dist` al `.gitignore` de la raíz**

En `.gitignore`, bajo la sección `# Node / frontend`, agregar una línea:

```
dist/
```

- [ ] **Step 12: Verificar en el navegador**

Run: `cd frontend && npm run dev`
Abrir `http://localhost:5173`: debe verse el título, los tres badges de color (verde azulado, ocre, rojo ladrillo) y la línea en `IBM Plex Mono` visiblemente distinta de la tipografía del resto del texto.

- [ ] **Step 13: Commit**

```bash
git add frontend .gitignore
git commit -m "feat(frontend): scaffold de Vite+React+TS+Tailwind con la identidad visual del cotizador"
```

---

## Task 5: Capa de API — cliente fetch y manejo de errores

**Files:**
- Create: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts`

**Interfaces:**
- Produces: `apiGet<T>(path)`, `apiPost<T>(path, body?)`, `apiPatch<T>(path, body)`, `apiDelete(path)`, `apiPostForm<T>(path, formData)`, y la clase `ApiError extends Error` con `.status: number` — todas las tareas de `api/*.ts` siguientes los usan como única forma de hablar con el backend.

- [ ] **Step 1: Escribir el test que falla**

```typescript
// frontend/src/api/client.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiGet, ApiError } from "./client";

describe("apiGet", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("devuelve el cuerpo parseado cuando la respuesta es 2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ id: 1, nombre: "Prueba" }),
      })
    );

    const resultado = await apiGet<{ id: number; nombre: string }>("/trabajos/1");

    expect(resultado).toEqual({ id: 1, nombre: "Prueba" });
  });

  it("lanza ApiError con el mensaje del backend cuando la respuesta no es 2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: "No existe el trabajo 999." }),
      })
    );

    await expect(apiGet("/trabajos/999")).rejects.toBeInstanceOf(ApiError);
    await expect(apiGet("/trabajos/999")).rejects.toThrow("No existe el trabajo 999.");
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run src/api/client.test.ts`
Expected: FAIL — no existe el módulo `./client`.

- [ ] **Step 3: Implementar `client.ts`**

```typescript
const BASE_URL = "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function manejarRespuesta<T>(respuesta: Response): Promise<T> {
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null);
    const mensaje =
      cuerpo && typeof cuerpo.detail === "string" ? cuerpo.detail : `Error ${respuesta.status}`;
    throw new ApiError(respuesta.status, mensaje);
  }
  if (respuesta.status === 204) {
    return undefined as T;
  }
  return respuesta.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`);
  return manejarRespuesta<T>(respuesta);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return manejarRespuesta<T>(respuesta);
}

export async function apiDelete(path: string): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
  return manejarRespuesta<void>(respuesta);
}

export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const respuesta = await fetch(`${BASE_URL}${path}`, { method: "POST", body: formData });
  return manejarRespuesta<T>(respuesta);
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `cd frontend && npx vitest run src/api/client.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat(frontend): cliente fetch tipado con manejo de errores del backend"
```

---

## Task 6: Trabajos — lista, alta y routing

**Files:**
- Create: `frontend/src/api/trabajos.ts`
- Create: `frontend/src/hooks/useTrabajos.ts`
- Create: `frontend/src/routes/TrabajosLista.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `apiGet`/`apiPost` de `../api/client` (Task 5).
- Produces: tipo `Trabajo`; `listarTrabajos()`, `obtenerTrabajo(id)`, `crearTrabajo(nombre)`; hooks `useTrabajos()`, `useTrabajo(id)`, `useCrearTrabajo()` — la Tarea 7 (`WorkspaceLayout`) consume `useTrabajo(id)` y el tipo `Trabajo`.

**Nota respecto a la spec:** `POST /trabajos` solo pide `nombre` — un `Trabajo` no tiene `cliente_id` (el cliente recién se asocia al crear el primer `Presupuesto`, Tarea 13). La spec §5 decía "alta de trabajo + cliente nuevo" de forma simplificada; el alta de cliente se hace en Costeo, no acá.

- [ ] **Step 1: Crear `api/trabajos.ts`**

```typescript
import { apiGet, apiPost } from "./client";

export interface Trabajo {
  id: number;
  nombre: string;
  archivo_origen: string | null;
  escala_a_mm: string | null;
  creado_en: string;
  actualizado_en: string;
}

export function listarTrabajos(): Promise<Trabajo[]> {
  return apiGet<Trabajo[]>("/trabajos");
}

export function obtenerTrabajo(trabajoId: number): Promise<Trabajo> {
  return apiGet<Trabajo>(`/trabajos/${trabajoId}`);
}

export function crearTrabajo(nombre: string): Promise<Trabajo> {
  return apiPost<Trabajo>("/trabajos", { nombre });
}
```

- [ ] **Step 2: Crear `hooks/useTrabajos.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { crearTrabajo, listarTrabajos, obtenerTrabajo } from "../api/trabajos";

export function useTrabajos() {
  return useQuery({ queryKey: ["trabajos"], queryFn: listarTrabajos });
}

export function useTrabajo(trabajoId: number) {
  return useQuery({
    queryKey: ["trabajo", trabajoId],
    queryFn: () => obtenerTrabajo(trabajoId),
  });
}

export function useCrearTrabajo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => crearTrabajo(nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["trabajos"] }),
  });
}
```

- [ ] **Step 3: Crear `routes/TrabajosLista.tsx`**

```tsx
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCrearTrabajo, useTrabajos } from "../hooks/useTrabajos";

export default function TrabajosLista() {
  const { data: trabajos, isLoading } = useTrabajos();
  const crearTrabajo = useCrearTrabajo();
  const [nombre, setNombre] = useState("");
  const navigate = useNavigate();

  async function alCrear(evento: FormEvent) {
    evento.preventDefault();
    if (!nombre.trim()) return;
    const trabajo = await crearTrabajo.mutateAsync(nombre.trim());
    setNombre("");
    navigate(`/trabajos/${trabajo.id}/piezas`);
  }

  return (
    <div className="min-h-screen bg-paper text-ink p-8">
      <h1 className="text-2xl font-semibold mb-6">Trabajos</h1>

      <form onSubmit={alCrear} className="flex gap-2 mb-8">
        <input
          className="border border-line rounded px-3 py-2 flex-1 bg-paper"
          placeholder="Nombre del trabajo (ej. «López — cartel luminoso»)"
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
        />
        <button
          type="submit"
          className="bg-cut text-paper rounded px-4 py-2 disabled:opacity-50"
          disabled={crearTrabajo.isPending}
        >
          Nuevo trabajo
        </button>
      </form>

      {isLoading ? (
        <p>Cargando...</p>
      ) : (
        <ul className="divide-y divide-line">
          {trabajos?.map((trabajo) => (
            <li key={trabajo.id} className="py-3">
              <Link to={`/trabajos/${trabajo.id}/piezas`} className="font-medium hover:text-cut">
                {trabajo.nombre}
              </Link>
              <span className="ml-3 text-sm font-mono text-ink/60">
                {new Date(trabajo.creado_en).toLocaleDateString("es-AR")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Reemplazar `App.tsx` con el router**

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import TrabajosLista from "./routes/TrabajosLista";

const router = createBrowserRouter([{ path: "/", element: <TrabajosLista /> }]);

export default function App() {
  return <RouterProvider router={router} />;
}
```

- [ ] **Step 5: Verificar en el navegador**

Con el backend corriendo (`cd backend && uvicorn app.api.app:app --reload`) y el frontend (`cd frontend && npm run dev`): crear un trabajo desde el formulario, confirmar que aparece en la lista con su fecha. El `Link` a `/trabajos/:id/piezas` puede dar una página en blanco todavía — esa ruta la agrega la Tarea 7.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/trabajos.ts frontend/src/hooks/useTrabajos.ts frontend/src/routes/TrabajosLista.tsx frontend/src/App.tsx
git commit -m "feat(frontend): lista y alta de trabajos"
```

---

## Task 7: Workspace del trabajo — riel lateral y routing anidado

**Files:**
- Create: `frontend/src/api/piezasYgrupos.ts` (piezas + grupos: lo mínimo que necesita el riel para los indicadores de etapa)
- Create: `frontend/src/hooks/usePiezas.ts`, `frontend/src/hooks/useGrupos.ts`
- Create: `frontend/src/routes/TrabajoWorkspace/WorkspaceLayout.tsx`
- Create: `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx` (placeholder mínimo — el contenido real es la Tarea 8)
- Create: `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`, `AnidadoTab.tsx`, `AjusteTab.tsx`, `CosteoTab.tsx` (cada uno con un `<p>` de marcador, reemplazados por las tareas correspondientes)
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `useTrabajo` (Task 6); `Trabajo` (Task 6).
- Produces: tipos `Pieza`, `GrupoDeCorte`; `listarPiezas(trabajoId)`, `listarGrupos(trabajoId)`; hooks `usePiezas(trabajoId)`, `useGrupos(trabajoId)` — la Tarea 8 y la Tarea 9 los extienden (no los reemplazan: agregan mutaciones al mismo archivo). El layout expone las rutas anidadas `/trabajos/:id/piezas|grupos|anidado|ajuste|costeo` vía `<Outlet />`.

> Las pantallas de Anidado (Tarea 10), Ajuste (Tarea 12) y Costeo (Tareas 13-14) se crean acá como marcadores mínimos **funcionales** (renderizan de verdad, solo que sin la lógica final) para que el routing completo se pueda probar de punta a punta en esta tarea — cada tarea posterior reemplaza el cuerpo del archivo correspondiente, no crea uno nuevo.

- [ ] **Step 1: Crear `api/piezasYgrupos.ts`**

```typescript
import { apiGet } from "./client";

export interface Pieza {
  id: number;
  trabajo_id: number;
  grupo_id: number | null;
  id_origen: string;
  cantidad: number;
  ancho_mm: string;
  alto_mm: string;
  contorno_mm: number[][];
  agujeros_mm: number[][][];
  descartada: boolean;
  contorno_recto: boolean;
}

export interface GrupoDeCorte {
  id: number;
  trabajo_id: number;
  nombre: string;
  formato_id: number | null;
  orden: number;
  parametros_usados: Record<string, string> | null;
}

export function listarPiezas(trabajoId: number): Promise<Pieza[]> {
  return apiGet<Pieza[]>(`/trabajos/${trabajoId}/piezas`);
}

export function listarGrupos(trabajoId: number): Promise<GrupoDeCorte[]> {
  return apiGet<GrupoDeCorte[]>(`/trabajos/${trabajoId}/grupos`);
}
```

- [ ] **Step 2: Crear `hooks/usePiezas.ts` y `hooks/useGrupos.ts`**

```typescript
// frontend/src/hooks/usePiezas.ts
import { useQuery } from "@tanstack/react-query";
import { listarPiezas } from "../api/piezasYgrupos";

export function usePiezas(trabajoId: number) {
  return useQuery({ queryKey: ["piezas", trabajoId], queryFn: () => listarPiezas(trabajoId) });
}
```

```typescript
// frontend/src/hooks/useGrupos.ts
import { useQuery } from "@tanstack/react-query";
import { listarGrupos } from "../api/piezasYgrupos";

export function useGrupos(trabajoId: number) {
  return useQuery({ queryKey: ["grupos", trabajoId], queryFn: () => listarGrupos(trabajoId) });
}
```

- [ ] **Step 3: Crear `WorkspaceLayout.tsx`** — el riel con los indicadores de etapa (`●`/`○` salen de si hay datos, no son decorativos)

```tsx
import { NavLink, Outlet, useParams } from "react-router-dom";
import { useTrabajo } from "../../hooks/useTrabajos";
import { usePiezas } from "../../hooks/usePiezas";
import { useGrupos } from "../../hooks/useGrupos";

const ETAPAS = [
  { path: "piezas", etiqueta: "Piezas" },
  { path: "grupos", etiqueta: "Grupos" },
  { path: "anidado", etiqueta: "Anidado" },
  { path: "ajuste", etiqueta: "Ajuste" },
  { path: "costeo", etiqueta: "Costeo" },
] as const;

export default function WorkspaceLayout() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: trabajo } = useTrabajo(id);
  const { data: piezas } = usePiezas(id);
  const { data: grupos } = useGrupos(id);

  const tieneDatos: Record<string, boolean> = {
    piezas: (piezas?.length ?? 0) > 0,
    grupos: (grupos?.length ?? 0) > 0,
    // Anidado, Ajuste y Costeo se afinan en las Tareas 10/12/13 cuando
    // exista el hook para consultar ejecuciones/presupuestos — hasta
    // entonces el punto queda vacío (nunca en falso positivo).
    anidado: false,
    ajuste: false,
    costeo: false,
  };

  return (
    <div className="min-h-screen bg-paper text-ink flex">
      <aside className="w-64 border-r border-line p-4">
        <h2 className="font-semibold mb-1">{trabajo?.nombre ?? "..."}</h2>
        <p className="text-xs text-ink/60 mb-4">Trabajo #{id}</p>
        <nav className="flex flex-col gap-1">
          {ETAPAS.map((etapa) => (
            <NavLink
              key={etapa.path}
              to={`/trabajos/${id}/${etapa.path}`}
              className={({ isActive }) =>
                `rounded px-3 py-2 text-sm ${isActive ? "bg-cut text-paper" : "hover:bg-line/40"}`
              }
            >
              <span className="mr-2">{tieneDatos[etapa.path] ? "●" : "○"}</span>
              {etapa.etiqueta}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Crear `PiezasTab.tsx`** (marcador funcional — reemplazado por la Tarea 8)

```tsx
export default function PiezasTab() {
  return <p>Piezas — pendiente (Tarea 8).</p>;
}
```

- [ ] **Step 5: Crear `GruposTab.tsx`, `AnidadoTab.tsx`, `AjusteTab.tsx`, `CosteoTab.tsx`** (mismo patrón que el Step 4, un componente por archivo con su propio mensaje: "Grupos — pendiente (Tarea 9).", "Anidado — pendiente (Tarea 10).", "Ajuste — pendiente (Tarea 12).", "Costeo — pendiente (Tareas 13-14).")

- [ ] **Step 6: Actualizar `App.tsx` con las rutas anidadas**

```tsx
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import TrabajosLista from "./routes/TrabajosLista";
import WorkspaceLayout from "./routes/TrabajoWorkspace/WorkspaceLayout";
import PiezasTab from "./routes/TrabajoWorkspace/PiezasTab";
import GruposTab from "./routes/TrabajoWorkspace/GruposTab";
import AnidadoTab from "./routes/TrabajoWorkspace/AnidadoTab";
import AjusteTab from "./routes/TrabajoWorkspace/AjusteTab";
import CosteoTab from "./routes/TrabajoWorkspace/CosteoTab";

const router = createBrowserRouter([
  { path: "/", element: <TrabajosLista /> },
  {
    path: "/trabajos/:trabajoId",
    element: <WorkspaceLayout />,
    children: [
      { index: true, element: <Navigate to="piezas" replace /> },
      { path: "piezas", element: <PiezasTab /> },
      { path: "grupos", element: <GruposTab /> },
      { path: "anidado", element: <AnidadoTab /> },
      { path: "ajuste", element: <AjusteTab /> },
      { path: "costeo", element: <CosteoTab /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
```

- [ ] **Step 7: Verificar en el navegador**

Crear un trabajo desde `/`, confirmar que navega a `/trabajos/:id/piezas` y se ve el riel lateral con el nombre del trabajo y los 5 puntos (todos `○` en un trabajo nuevo). Clickear cada pestaña y confirmar que cambia el contenido y el resaltado del ítem activo.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/piezasYgrupos.ts frontend/src/hooks/usePiezas.ts frontend/src/hooks/useGrupos.ts frontend/src/routes/TrabajoWorkspace frontend/src/App.tsx
git commit -m "feat(frontend): workspace del trabajo con riel de etapas y routing anidado"
```

---

## Task 8: Piezas — subir DXF, listar con preview, descartar

**Files:**
- Modify: `frontend/src/api/piezasYgrupos.ts` (agregar `subirDxf`, `descartarPieza`)
- Modify: `frontend/src/hooks/usePiezas.ts` (agregar mutaciones)
- Create: `frontend/src/components/PiezaMiniPreview.tsx`
- Create: `frontend/src/components/Banner.tsx`
- Rewrite: `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`

**Interfaces:**
- Consumes: `apiPostForm`, `apiPatch` (Task 5); `Pieza`, `usePiezas` (Task 7).
- Produces: `Banner` (mensaje + variante `error`/`aviso`, reusado en Tareas 10/12/13/14 para mostrar errores del backend); `PiezaMiniPreview` (reusado en la Tarea 12, el editor de plano).

- [ ] **Step 1: Agregar a `api/piezasYgrupos.ts`**

```typescript
export function subirDxf(trabajoId: number, archivo: File, escalaAMm: string): Promise<{
  trabajo: unknown;
  piezas_creadas: number;
  contornos_no_cerrados: number;
  lineas_duplicadas_descartadas: number;
  advertencias: string[];
}> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  return apiPostForm(`/trabajos/${trabajoId}/dxf`, formData);
}

export function descartarPieza(piezaId: number, descartada: boolean): Promise<Pieza> {
  return apiPatch<Pieza>(`/piezas/${piezaId}`, { descartada });
}
```

(Agregar `apiPatch, apiPostForm` al import existente de `./client` en este archivo.)

- [ ] **Step 2: Agregar mutaciones a `hooks/usePiezas.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { descartarPieza, listarPiezas, subirDxf } from "../api/piezasYgrupos";

export function usePiezas(trabajoId: number) {
  return useQuery({ queryKey: ["piezas", trabajoId], queryFn: () => listarPiezas(trabajoId) });
}

export function useSubirDxf(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ archivo, escalaAMm }: { archivo: File; escalaAMm: string }) =>
      subirDxf(trabajoId, archivo, escalaAMm),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}

export function useDescartarPieza(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ piezaId, descartada }: { piezaId: number; descartada: boolean }) =>
      descartarPieza(piezaId, descartada),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}
```

- [ ] **Step 3: Crear `components/Banner.tsx`**

```tsx
interface BannerProps {
  variante: "error" | "aviso";
  children: React.ReactNode;
}

export default function Banner({ variante, children }: BannerProps) {
  const color = variante === "error" ? "border-conflict text-conflict" : "border-bronze text-bronze";
  return <div className={`border rounded px-3 py-2 text-sm bg-paper ${color}`}>{children}</div>;
}
```

- [ ] **Step 4: Crear `components/PiezaMiniPreview.tsx`** — dibuja el `contorno_mm` a escala dentro de un `viewBox` fijo, sin depender de la escala real del trabajo (mini-preview, no el editor a escala real de la Tarea 12)

```tsx
interface PiezaMiniPreviewProps {
  contornoMm: number[][];
  anchoMm: string;
  altoMm: string;
}

const TAMANO_PX = 48;

export default function PiezaMiniPreview({ contornoMm, anchoMm, altoMm }: PiezaMiniPreviewProps) {
  const ancho = Number(anchoMm);
  const alto = Number(altoMm);
  const puntos = contornoMm.map(([x, y]) => `${x},${y}`).join(" ");

  return (
    <svg
      width={TAMANO_PX}
      height={TAMANO_PX}
      viewBox={`0 0 ${ancho || 1} ${alto || 1}`}
      className="border border-line rounded bg-paper"
    >
      <polygon points={puntos} fill="none" stroke="#2E8074" strokeWidth={Math.max(ancho, alto) / 40} />
    </svg>
  );
}
```

- [ ] **Step 5: Reescribir `PiezasTab.tsx`** — con la validación de extensión y el mensaje de `D-11`

```tsx
import { useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { usePiezas, useSubirDxf, useDescartarPieza } from "../../hooks/usePiezas";
import PiezaMiniPreview from "../../components/PiezaMiniPreview";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";

export default function PiezasTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: piezas, isLoading } = usePiezas(id);
  const subirDxf = useSubirDxf(id);
  const descartarPieza = useDescartarPieza(id);
  const [escalaAMm, setEscalaAMm] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const inputArchivo = useRef<HTMLInputElement>(null);

  async function alElegirArchivo() {
    const archivo = inputArchivo.current?.files?.[0];
    if (!archivo) return;
    setError(null);

    if (!archivo.name.toLowerCase().endsWith(".dxf")) {
      setError(
        `Este archivo es «${archivo.name.split(".").pop()}». Exportá el DXF desde Corel ` +
          "(Archivo → Exportar → DXF) y subí ese archivo."
      );
      if (inputArchivo.current) inputArchivo.current.value = "";
      return;
    }

    try {
      await subirDxf.mutateAsync({ archivo, escalaAMm });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo subir el archivo.");
    } finally {
      if (inputArchivo.current) inputArchivo.current.value = "";
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Piezas</h1>

      <div className="flex items-center gap-2 mb-4">
        <label className="text-sm">
          Escala a mm:{" "}
          <input
            className="border border-line rounded px-2 py-1 w-16 font-mono bg-paper"
            value={escalaAMm}
            onChange={(evento) => setEscalaAMm(evento.target.value)}
          />
        </label>
        <input ref={inputArchivo} type="file" accept=".dxf" onChange={alElegirArchivo} />
      </div>

      {error && (
        <div className="mb-4">
          <Banner variante="error">{error}</Banner>
        </div>
      )}

      {isLoading ? (
        <p>Cargando...</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b border-line">
              <th className="py-2">Contorno</th>
              <th>Origen</th>
              <th>Ancho</th>
              <th>Alto</th>
              <th>Cantidad</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {piezas?.map((pieza) => (
              <tr key={pieza.id} className={`border-b border-line ${pieza.descartada ? "opacity-40" : ""}`}>
                <td className="py-2">
                  <PiezaMiniPreview contornoMm={pieza.contorno_mm} anchoMm={pieza.ancho_mm} altoMm={pieza.alto_mm} />
                </td>
                <td>{pieza.id_origen}</td>
                <td className="font-mono">{pieza.ancho_mm} mm</td>
                <td className="font-mono">{pieza.alto_mm} mm</td>
                <td className="font-mono">{pieza.cantidad}</td>
                <td>
                  <button
                    className="text-xs underline"
                    onClick={() =>
                      descartarPieza.mutate({ piezaId: pieza.id, descartada: !pieza.descartada })
                    }
                  >
                    {pieza.descartada ? "Restaurar" : "Descartar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Verificar en el navegador**

Con el backend corriendo: intentar subir un archivo que no sea `.dxf` (ej. renombrar cualquier `.txt`) y confirmar el mensaje de error específico. Después subir un DXF real con `escala_a_mm=1` (por ejemplo `backend/modelos/repisas.dxf`, si existe localmente — no está en git, ver `docs/GUIA-PRUEBAS-LOCALES.md`) y confirmar que las piezas aparecen listadas con su mini-preview. Descartar una y confirmar que se atenúa visualmente.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/piezasYgrupos.ts frontend/src/hooks/usePiezas.ts frontend/src/components/PiezaMiniPreview.tsx frontend/src/components/Banner.tsx frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx
git commit -m "feat(frontend): subir DXF, listar piezas con preview y descartar"
```

---

## Task 9: Catálogo y Grupos — crear grupo, mover piezas, comparar formatos

**Files:**
- Create: `frontend/src/api/catalogo.ts`
- Create: `frontend/src/hooks/useCatalogo.ts`
- Modify: `frontend/src/api/piezasYgrupos.ts` (agregar `crearGrupo`, `asignarPiezaAGrupo`, `asignarFormatoAGrupo`, `compararFormatos`)
- Modify: `frontend/src/hooks/useGrupos.ts` (agregar mutaciones)
- Rewrite: `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`

**Interfaces:**
- Consumes: `apiGet`, `apiPost`, `apiPatch` (Task 5); `Pieza`, `GrupoDeCorte`, `usePiezas` (Tasks 7-8); `Banner` (Task 8).
- Produces: tipos `Material`, `Formato`; `listarMateriales()`, `listarFormatos(materialId)`; `crearGrupo`, `asignarPiezaAGrupo`, `asignarFormatoAGrupo`, `compararFormatos` — la Tarea 10 (Anidado) consume `GrupoDeCorte.formato_id` para saber si un grupo está listo para anidar.

- [ ] **Step 1: Crear `api/catalogo.ts`**

```typescript
import { apiGet } from "./client";

export interface Material {
  id: number;
  nombre: string;
}

export interface Formato {
  id: number;
  material_id: number;
  ancho_mm: string;
  alto_mm: string;
  moneda: string | null;
  costo_unidad_venta: string | null;
  unidad_venta: string | null;
}

export function listarMateriales(): Promise<Material[]> {
  return apiGet<Material[]>("/materiales");
}

export function listarFormatos(materialId: number): Promise<Formato[]> {
  return apiGet<Formato[]>(`/materiales/${materialId}/formatos`);
}
```

- [ ] **Step 2: Crear `hooks/useCatalogo.ts`**

```typescript
import { useQueries, useQuery } from "@tanstack/react-query";
import { listarFormatos, listarMateriales } from "../api/catalogo";

export function useMateriales() {
  return useQuery({ queryKey: ["materiales"], queryFn: listarMateriales });
}

/** Todos los formatos de todos los materiales, aplanados — el catálogo
 * es chico (~20 formatos, ver B-02 en REGISTRO.md), así que N+1
 * requests client-side es aceptable para esta herramienta interna. */
export function useTodosLosFormatos() {
  const { data: materiales } = useMateriales();
  const resultados = useQueries({
    queries: (materiales ?? []).map((material) => ({
      queryKey: ["formatos", material.id],
      queryFn: () => listarFormatos(material.id),
      enabled: !!materiales,
    })),
  });
  const formatos = resultados.flatMap((r) => r.data ?? []);
  const cargando = (materiales === undefined) || resultados.some((r) => r.isLoading);
  return { formatos, materiales: materiales ?? [], cargando };
}
```

- [ ] **Step 3: Agregar a `api/piezasYgrupos.ts`**

```typescript
export interface OpcionFormato {
  formato_id: number;
  formato_descripcion: string;
  material_nombre: string;
  planchas_usadas: number;
  aprovechamiento_pct: string;
  costo_total: string;
  moneda: string;
  recomendado: boolean;
}

export function crearGrupo(trabajoId: number, nombre: string): Promise<GrupoDeCorte> {
  return apiPost<GrupoDeCorte>(`/trabajos/${trabajoId}/grupos`, { nombre });
}

export function asignarPiezaAGrupo(piezaId: number, grupoId: number | null): Promise<Pieza> {
  return apiPatch<Pieza>(`/piezas/${piezaId}`, { grupo_id: grupoId });
}

export function asignarFormatoAGrupo(grupoId: number, formatoId: number): Promise<GrupoDeCorte> {
  return apiPatch<GrupoDeCorte>(`/grupos/${grupoId}`, { formato_id: formatoId });
}

export function compararFormatos(grupoId: number, formatoIds: number[]): Promise<OpcionFormato[]> {
  return apiPost<OpcionFormato[]>(`/grupos/${grupoId}/comparar-formatos`, { formato_ids: formatoIds });
}
```

(Agregar `apiGet` al import de `./client` si todavía no estaba.)

- [ ] **Step 4: Agregar mutaciones a `hooks/useGrupos.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  asignarFormatoAGrupo,
  asignarPiezaAGrupo,
  compararFormatos,
  crearGrupo,
  listarGrupos,
} from "../api/piezasYgrupos";

export function useGrupos(trabajoId: number) {
  return useQuery({ queryKey: ["grupos", trabajoId], queryFn: () => listarGrupos(trabajoId) });
}

export function useCrearGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => crearGrupo(trabajoId, nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grupos", trabajoId] }),
  });
}

export function useAsignarPiezaAGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ piezaId, grupoId }: { piezaId: number; grupoId: number | null }) =>
      asignarPiezaAGrupo(piezaId, grupoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}

export function useAsignarFormatoAGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ grupoId, formatoId }: { grupoId: number; formatoId: number }) =>
      asignarFormatoAGrupo(grupoId, formatoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grupos", trabajoId] }),
  });
}

export function useCompararFormatos() {
  return useMutation({
    mutationFn: ({ grupoId, formatoIds }: { grupoId: number; formatoIds: number[] }) =>
      compararFormatos(grupoId, formatoIds),
  });
}
```

- [ ] **Step 5: Reescribir `GruposTab.tsx`**

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { usePiezas } from "../../hooks/usePiezas";
import {
  useAsignarFormatoAGrupo,
  useAsignarPiezaAGrupo,
  useCompararFormatos,
  useCrearGrupo,
  useGrupos,
} from "../../hooks/useGrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import Banner from "../../components/Banner";
import type { OpcionFormato } from "../../api/piezasYgrupos";
import { ApiError } from "../../api/client";

export default function GruposTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: piezas } = usePiezas(id);
  const { data: grupos } = useGrupos(id);
  const { formatos, materiales } = useTodosLosFormatos();
  const crearGrupo = useCrearGrupo(id);
  const asignarPieza = useAsignarPiezaAGrupo(id);
  const asignarFormato = useAsignarFormatoAGrupo(id);
  const compararFormatos = useCompararFormatos();

  const [nombreNuevoGrupo, setNombreNuevoGrupo] = useState("");
  const [grupoComparando, setGrupoComparando] = useState<number | null>(null);
  const [candidatos, setCandidatos] = useState<number[]>([]);
  const [resultado, setResultado] = useState<OpcionFormato[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sinAsignar = piezas?.filter((p) => p.grupo_id === null && !p.descartada) ?? [];

  function nombreMaterial(materialId: number) {
    return materiales.find((m) => m.id === materialId)?.nombre ?? "?";
  }

  async function alComparar(grupoId: number) {
    setError(null);
    setResultado(null);
    try {
      const opciones = await compararFormatos.mutateAsync({ grupoId, formatoIds: candidatos });
      setResultado(opciones);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo comparar.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Grupos de corte</h1>

      <div className="flex gap-2 mb-6">
        <input
          className="border border-line rounded px-3 py-2 bg-paper"
          placeholder="Nombre del grupo (ej. «Chapa negra»)"
          value={nombreNuevoGrupo}
          onChange={(e) => setNombreNuevoGrupo(e.target.value)}
        />
        <button
          className="bg-cut text-paper rounded px-4 py-2"
          onClick={() => nombreNuevoGrupo.trim() && crearGrupo.mutate(nombreNuevoGrupo.trim())}
        >
          Nuevo grupo
        </button>
      </div>

      {sinAsignar.length > 0 && (
        <div className="mb-6">
          <h2 className="font-medium mb-2">Piezas sin asignar ({sinAsignar.length})</h2>
          <ul className="text-sm">
            {sinAsignar.map((pieza) => (
              <li key={pieza.id} className="flex items-center gap-2 py-1">
                <span>{pieza.id_origen}</span>
                <select
                  className="border border-line rounded px-2 py-1 bg-paper"
                  defaultValue=""
                  onChange={(e) =>
                    e.target.value &&
                    asignarPieza.mutate({ piezaId: pieza.id, grupoId: Number(e.target.value) })
                  }
                >
                  <option value="" disabled>
                    Mover a grupo...
                  </option>
                  {grupos?.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.nombre}
                    </option>
                  ))}
                </select>
              </li>
            ))}
          </ul>
        </div>
      )}

      {grupos?.map((grupo) => (
        <div key={grupo.id} className="border border-line rounded p-4 mb-4">
          <div className="flex justify-between items-center">
            <h3 className="font-medium">{grupo.nombre}</h3>
            <span className="text-sm font-mono">
              {grupo.formato_id ? `Formato #${grupo.formato_id}` : "Sin material"}
            </span>
          </div>

          <div className="mt-3">
            <button
              className="text-sm underline"
              onClick={() => {
                setGrupoComparando(grupo.id);
                setResultado(null);
                setCandidatos([]);
              }}
            >
              Comparar formatos
            </button>
          </div>

          {grupoComparando === grupo.id && (
            <div className="mt-3 border-t border-line pt-3">
              <p className="text-sm mb-2">Elegí 2 o más formatos candidatos:</p>
              <div className="flex flex-wrap gap-2 mb-3">
                {formatos.map((formato) => (
                  <label key={formato.id} className="text-xs flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={candidatos.includes(formato.id)}
                      onChange={(e) =>
                        setCandidatos((prev) =>
                          e.target.checked ? [...prev, formato.id] : prev.filter((id) => id !== formato.id)
                        )
                      }
                    />
                    {nombreMaterial(formato.material_id)} {formato.ancho_mm}×{formato.alto_mm}
                  </label>
                ))}
              </div>
              <button
                className="bg-cut text-paper rounded px-3 py-1 text-sm mb-3"
                disabled={candidatos.length < 2}
                onClick={() => alComparar(grupo.id)}
              >
                Comparar
              </button>

              {error && <Banner variante="error">{error}</Banner>}

              {resultado && (
                <table className="w-full text-sm mt-2">
                  <thead>
                    <tr className="text-left border-b border-line">
                      <th>Material</th>
                      <th>Formato</th>
                      <th>Planchas</th>
                      <th>Aprov.</th>
                      <th>Costo</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultado.map((opcion) => (
                      <tr
                        key={opcion.formato_id}
                        className={`border-b border-line ${opcion.recomendado ? "bg-bronze/10" : ""}`}
                      >
                        <td>{opcion.material_nombre}</td>
                        <td>{opcion.formato_descripcion}</td>
                        <td className="font-mono">{opcion.planchas_usadas}</td>
                        <td className="font-mono">{Number(opcion.aprovechamiento_pct).toFixed(1)}%</td>
                        <td className="font-mono">
                          {opcion.moneda} {Number(opcion.costo_total).toFixed(2)}
                        </td>
                        <td>
                          <button
                            className="text-xs underline"
                            onClick={() => {
                              asignarFormato.mutate({ grupoId: grupo.id, formatoId: opcion.formato_id });
                              setGrupoComparando(null);
                            }}
                          >
                            Usar este
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Verificar en el navegador**

Con al menos un material+formato ya cargados en el catálogo (via Swagger `/docs` si hace falta, `POST /materiales`, `POST /materiales/{id}/formatos`, `PUT /materiales/{id}/parametros-corte` — no hay pantalla de catálogo en este slice, ver spec §9): crear un grupo, mover una pieza sin asignar hacia él, comparar 2+ formatos candidatos y confirmar que la fila más barata queda resaltada y marcada como recomendada. Elegir uno y confirmar que el grupo pasa a mostrar el formato asignado.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/catalogo.ts frontend/src/hooks/useCatalogo.ts frontend/src/api/piezasYgrupos.ts frontend/src/hooks/useGrupos.ts frontend/src/routes/TrabajoWorkspace/GruposTab.tsx
git commit -m "feat(frontend): crear grupos, mover piezas y comparar formatos antes de asignar material"
```

---

## Task 10: Anidado — encolar, polling, historial, marcar definitiva

**Files:**
- Create: `frontend/src/api/nesting.ts`
- Create: `frontend/src/hooks/useNesting.ts`
- Create: `frontend/src/components/EstadoBadge.tsx`
- Rewrite: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`

**Interfaces:**
- Consumes: `apiGet`, `apiPost` (Task 5); `GrupoDeCorte`, `useGrupos` (Task 9); `Banner` (Task 8).
- Produces: tipo `Ejecucion`; `anidar(grupoId)`, `obtenerEjecucion(id)`, `listarEjecucionesDeGrupo(grupoId)`, `marcarDefinitiva(id)`; hooks `useAnidar`, `useEjecucion` (con polling), `useEjecucionesDeGrupo`, `useMarcarDefinitiva` — la Tarea 12 (Ajuste) consume `Ejecucion` y `useEjecucionesDeGrupo` para elegir sobre cuál ejecución editar.

- [ ] **Step 1: Crear `api/nesting.ts`**

```typescript
import { apiGet, apiPost } from "./client";

export interface Ejecucion {
  id: number;
  grupo_id: number;
  motor: string;
  estado: "encolada" | "corriendo" | "lista" | "cancelada" | "error";
  planchas_usadas: number | null;
  aprovechamiento_pct: string | null;
  milisegundos: number | null;
  mensajes: string[] | null;
  error: string | null;
  es_definitiva: boolean;
  creado_en: string;
}

export function anidar(grupoId: number): Promise<Ejecucion> {
  return apiPost<Ejecucion>(`/grupos/${grupoId}/anidar`, { motor: "rectpack" });
}

export function obtenerEjecucion(ejecucionId: number): Promise<Ejecucion> {
  return apiGet<Ejecucion>(`/ejecuciones/${ejecucionId}`);
}

export function listarEjecucionesDeGrupo(grupoId: number): Promise<Ejecucion[]> {
  return apiGet<Ejecucion[]>(`/grupos/${grupoId}/ejecuciones`);
}

export function marcarDefinitiva(ejecucionId: number): Promise<Ejecucion> {
  return apiPost<Ejecucion>(`/ejecuciones/${ejecucionId}/marcar-definitiva`);
}
```

- [ ] **Step 2: Crear `hooks/useNesting.ts`** — el polling es lo que valida esta tarea: se apaga solo al llegar a un estado terminal

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { anidar, listarEjecucionesDeGrupo, marcarDefinitiva, obtenerEjecucion, type Ejecucion } from "../api/nesting";

const ESTADOS_TERMINALES = new Set(["lista", "error", "cancelada"]);

export function useEjecucion(ejecucionId: number | null) {
  return useQuery({
    queryKey: ["ejecucion", ejecucionId],
    queryFn: () => obtenerEjecucion(ejecucionId as number),
    enabled: ejecucionId !== null,
    refetchInterval: (query) => {
      const datos = query.state.data as Ejecucion | undefined;
      return datos && ESTADOS_TERMINALES.has(datos.estado) ? false : 500;
    },
  });
}

export function useEjecucionesDeGrupo(grupoId: number) {
  return useQuery({
    queryKey: ["ejecuciones", grupoId],
    queryFn: () => listarEjecucionesDeGrupo(grupoId),
  });
}

export function useAnidar(grupoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => anidar(grupoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ejecuciones", grupoId] }),
  });
}

export function useMarcarDefinitiva(grupoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ejecucionId: number) => marcarDefinitiva(ejecucionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ejecuciones", grupoId] }),
  });
}
```

- [ ] **Step 3: Crear `components/EstadoBadge.tsx`**

```tsx
const COLOR: Record<string, string> = {
  encolada: "bg-line text-ink",
  corriendo: "bg-bronze text-paper",
  lista: "bg-cut text-paper",
  cancelada: "bg-line text-ink",
  error: "bg-conflict text-paper",
};

export default function EstadoBadge({ estado }: { estado: string }) {
  return <span className={`rounded px-2 py-0.5 text-xs font-mono ${COLOR[estado] ?? ""}`}>{estado}</span>;
}
```

- [ ] **Step 4: Reescribir `AnidadoTab.tsx`**

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGrupos } from "../../hooks/useGrupos";
import { useAnidar, useEjecucion, useEjecucionesDeGrupo, useMarcarDefinitiva } from "../../hooks/useNesting";
import EstadoBadge from "../../components/EstadoBadge";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";

function PanelDeGrupo({ grupoId, nombre }: { grupoId: number; nombre: string }) {
  const anidar = useAnidar(grupoId);
  const marcarDefinitiva = useMarcarDefinitiva(grupoId);
  const { data: historial } = useEjecucionesDeGrupo(grupoId);
  const [ejecucionEnCurso, setEjecucionEnCurso] = useState<number | null>(null);
  const { data: enCurso } = useEjecucion(ejecucionEnCurso);
  const [error, setError] = useState<string | null>(null);

  async function alAnidar() {
    setError(null);
    try {
      const ejecucion = await anidar.mutateAsync();
      setEjecucionEnCurso(ejecucion.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo anidar.");
    }
  }

  return (
    <div className="border border-line rounded p-4 mb-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-medium">{nombre}</h3>
        <button className="bg-cut text-paper rounded px-3 py-1 text-sm" onClick={alAnidar}>
          Anidar
        </button>
      </div>

      {error && <Banner variante="error">{error}</Banner>}
      {enCurso && (
        <p className="text-sm mb-2">
          Ejecución #{enCurso.id}: <EstadoBadge estado={enCurso.estado} />
          {enCurso.error && <span className="ml-2 text-conflict">{enCurso.error}</span>}
        </p>
      )}

      <table className="w-full text-sm mt-2">
        <thead>
          <tr className="text-left border-b border-line">
            <th>Ejecución</th>
            <th>Estado</th>
            <th>Planchas</th>
            <th>Aprov.</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {historial?.map((ejecucion) => (
            <tr key={ejecucion.id} className="border-b border-line">
              <td className="font-mono">#{ejecucion.id}</td>
              <td>
                <EstadoBadge estado={ejecucion.estado} />
              </td>
              <td className="font-mono">{ejecucion.planchas_usadas ?? "—"}</td>
              <td className="font-mono">
                {ejecucion.aprovechamiento_pct ? `${Number(ejecucion.aprovechamiento_pct).toFixed(1)}%` : "—"}
              </td>
              <td>
                {ejecucion.estado === "lista" && !ejecucion.es_definitiva && (
                  <button className="text-xs underline" onClick={() => marcarDefinitiva.mutate(ejecucion.id)}>
                    Marcar definitiva
                  </button>
                )}
                {ejecucion.es_definitiva && <span className="text-xs text-bronze">definitiva</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AnidadoTab() {
  const { trabajoId } = useParams();
  const { data: grupos } = useGrupos(Number(trabajoId));

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Anidado</h1>
      {grupos?.map((grupo) => (
        <PanelDeGrupo key={grupo.id} grupoId={grupo.id} nombre={grupo.nombre} />
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Verificar en el navegador**

Con un grupo que ya tiene formato asignado y piezas (Tareas 8-9): apretar "Anidar", ver el badge pasar de `encolada` a `lista` sin recargar la página, y que aparece en el historial. Anidar una segunda vez y marcar esa como definitiva; confirmar que la anterior deja de mostrar el botón y la nueva muestra "definitiva".

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/nesting.ts frontend/src/hooks/useNesting.ts frontend/src/components/EstadoBadge.tsx frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx
git commit -m "feat(frontend): anidar con polling de estado, historial de ejecuciones y marcar definitiva"
```

---

## Task 11: Geometría del editor de plano — mm↔px y rotación (TDD)

**Files:**
- Create: `frontend/src/components/PlanoEditor/geometria.ts`
- Test: `frontend/src/components/PlanoEditor/geometria.test.ts`

**Interfaces:**
- Produces: `mmAPx(mm, escala)`, `pxAMm(px, escala)`, `rotarPunto(punto, centro, anguloGrados)` — los consume `PlanoEditor.tsx` (Task 12) para dibujar y arrastrar piezas.

- [ ] **Step 1: Escribir los tests que fallan**

```typescript
// frontend/src/components/PlanoEditor/geometria.test.ts
import { describe, expect, it } from "vitest";
import { mmAPx, pxAMm, rotarPunto } from "./geometria";

describe("mmAPx / pxAMm", () => {
  it("convierte mm a píxeles según la escala", () => {
    expect(mmAPx(100, 0.5)).toBe(50);
  });

  it("es la inversa de pxAMm", () => {
    const mm = 123.4;
    const escala = 0.3;
    expect(pxAMm(mmAPx(mm, escala), escala)).toBeCloseTo(mm, 6);
  });
});

describe("rotarPunto", () => {
  it("rota 90 grados un punto a la derecha del centro hacia arriba", () => {
    const resultado = rotarPunto({ x: 10, y: 0 }, { x: 0, y: 0 }, 90);
    expect(resultado.x).toBeCloseTo(0, 6);
    expect(resultado.y).toBeCloseTo(10, 6);
  });

  it("con 0 grados devuelve el mismo punto", () => {
    const resultado = rotarPunto({ x: 3, y: 4 }, { x: 1, y: 1 }, 0);
    expect(resultado.x).toBeCloseTo(3, 6);
    expect(resultado.y).toBeCloseTo(4, 6);
  });

  it("rota alrededor de un centro que no es el origen", () => {
    const resultado = rotarPunto({ x: 10, y: 10 }, { x: 10, y: 0 }, 90);
    expect(resultado.x).toBeCloseTo(0, 6);
    expect(resultado.y).toBeCloseTo(0, 6);
  });
});
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd frontend && npx vitest run src/components/PlanoEditor/geometria.test.ts`
Expected: FAIL — no existe el módulo `./geometria`.

- [ ] **Step 3: Implementar `geometria.ts`**

```typescript
export interface Punto {
  x: number;
  y: number;
}

export function mmAPx(mm: number, escalaPxPorMm: number): number {
  return mm * escalaPxPorMm;
}

export function pxAMm(px: number, escalaPxPorMm: number): number {
  return px / escalaPxPorMm;
}

/** Rota `punto` alrededor de `centro` por `anguloGrados`, sentido
 * antihorario (convención matemática estándar; el SVG invierte Y en
 * pantalla, pero esta función trabaja en el espacio mm, no en píxeles
 * de pantalla — la inversión de eje la maneja quien dibuja). */
export function rotarPunto(punto: Punto, centro: Punto, anguloGrados: number): Punto {
  const radianes = (anguloGrados * Math.PI) / 180;
  const coseno = Math.cos(radianes);
  const seno = Math.sin(radianes);
  const dx = punto.x - centro.x;
  const dy = punto.y - centro.y;
  return {
    x: centro.x + dx * coseno - dy * seno,
    y: centro.y + dx * seno + dy * coseno,
  };
}
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd frontend && npx vitest run src/components/PlanoEditor/geometria.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PlanoEditor/geometria.ts frontend/src/components/PlanoEditor/geometria.test.ts
git commit -m "feat(frontend): conversion mm/px y rotacion para el editor de plano, con tests"
```

---

## Task 12: Editor de plano — arrastrar, rotar, conflicto, exportar

**Files:**
- Modify: `frontend/src/api/nesting.ts` (agregar `Colocacion`, `listarColocaciones`, `ajustarColocacion`, helpers de URL de plano/DXF)
- Modify: `frontend/src/hooks/useNesting.ts` (agregar `useColocaciones`, `useAjustarColocacion`)
- Modify: `frontend/src/api/catalogo.ts` (agregar `obtenerFormato` — las medidas reales de la plancha salen del catálogo, no de un valor de prueba: `GET /formatos/{id}` ya existe en `rutas_catalogo.py`, solo faltaba una función tipada en el frontend)
- Modify: `frontend/src/hooks/useCatalogo.ts` (agregar `useFormato`)
- Create: `frontend/src/components/PlanoEditor/PlanoEditor.tsx`
- Rewrite: `frontend/src/routes/TrabajoWorkspace/AjusteTab.tsx`

**Interfaces:**
- Consumes: `mmAPx`, `pxAMm`, `rotarPunto` (Task 11); `Pieza`, `usePiezas` (Tasks 7-8); `Ejecucion`, `useEjecucionesDeGrupo` (Task 10); `Banner` (Task 8); `Formato` (Task 9, ya tipado en `api/catalogo.ts`).
- Produces: `PlanoEditor` — componente autocontenido, no lo consume ninguna tarea posterior. `obtenerFormato`/`useFormato` quedan disponibles para cualquier pantalla futura que necesite las medidas reales de una plancha por su `formato_id`.

- [ ] **Step 1: Agregar a `api/nesting.ts`**

```typescript
export interface Colocacion {
  id: number;
  pieza_id: number;
  instancia: number;
  plancha_indice: number;
  centro_x_mm: string;
  centro_y_mm: string;
  angulo_grados: string;
  movida_a_mano: boolean;
}

export interface ColocacionAjustada extends Colocacion {
  valida: boolean;
  motivo: string | null;
}

export function listarColocaciones(ejecucionId: number): Promise<Colocacion[]> {
  return apiGet<Colocacion[]>(`/ejecuciones/${ejecucionId}/colocaciones`);
}

export function ajustarColocacion(
  colocacionId: number,
  datos: { centro_x_mm?: number; centro_y_mm?: number; angulo_grados?: number }
): Promise<ColocacionAjustada> {
  return apiPatch<ColocacionAjustada>(`/colocaciones/${colocacionId}`, datos);
}

export function urlPlano(ejecucionId: number, plancha: number): string {
  return `http://localhost:8000/ejecuciones/${ejecucionId}/plano?plancha=${plancha}`;
}

export function urlDxf(ejecucionId: number, plancha: number): string {
  return `http://localhost:8000/ejecuciones/${ejecucionId}/dxf?plancha=${plancha}`;
}
```

(Agregar `apiPatch` al import de `./client` en este archivo.)

- [ ] **Step 2: Agregar a `hooks/useNesting.ts`**

```typescript
import { ajustarColocacion, listarColocaciones } from "../api/nesting";

export function useColocaciones(ejecucionId: number | null) {
  return useQuery({
    queryKey: ["colocaciones", ejecucionId],
    queryFn: () => listarColocaciones(ejecucionId as number),
    enabled: ejecucionId !== null,
  });
}

export function useAjustarColocacion(ejecucionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      colocacionId,
      datos,
    }: {
      colocacionId: number;
      datos: { centro_x_mm?: number; centro_y_mm?: number; angulo_grados?: number };
    }) => ajustarColocacion(colocacionId, datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["colocaciones", ejecucionId] }),
  });
}
```

- [ ] **Step 3: Agregar `obtenerFormato` a `api/catalogo.ts` y `useFormato` a `hooks/useCatalogo.ts`**

En `frontend/src/api/catalogo.ts`, agregar la función (junto a `listarFormatos`, que ya existe):

```typescript
export function obtenerFormato(formatoId: number): Promise<Formato> {
  return apiGet<Formato>(`/formatos/${formatoId}`);
}
```

En `frontend/src/hooks/useCatalogo.ts`, agregar el hook (junto a `useMateriales`, que ya existe):

```typescript
import { obtenerFormato } from "../api/catalogo";

export function useFormato(formatoId: number | null) {
  return useQuery({
    queryKey: ["formato", formatoId],
    queryFn: () => obtenerFormato(formatoId as number),
    enabled: formatoId !== null,
  });
}
```

- [ ] **Step 4: Crear `PlanoEditor.tsx`**

```tsx
import { useState } from "react";
import type { Pieza } from "../../api/piezasYgrupos";
import type { Colocacion } from "../../api/nesting";
import { mmAPx, rotarPunto } from "./geometria";

const ESCALA_PX_POR_MM = 0.3;
const PASO_ROTACION = 15;

interface PlanoEditorProps {
  anchoPlanchaMm: number;
  altoPlanchaMm: number;
  piezas: Pieza[];
  colocaciones: Colocacion[];
  onMover: (colocacionId: number, centroXMm: number, centroYMm: number) => void;
  onRotar: (colocacionId: number, anguloGrados: number) => void;
  colocacionesInvalidas: Set<number>;
}

export default function PlanoEditor({
  anchoPlanchaMm,
  altoPlanchaMm,
  piezas,
  colocaciones,
  onMover,
  onRotar,
  colocacionesInvalidas,
}: PlanoEditorProps) {
  const [arrastrando, setArrastrando] = useState<number | null>(null);
  const [seleccionada, setSeleccionada] = useState<number | null>(null);

  const piezaPorId = new Map(piezas.map((p) => [p.id, p]));

  function alSoltarEnSvg(evento: React.PointerEvent<SVGSVGElement>) {
    if (arrastrando === null) return;
    const svg = evento.currentTarget;
    const rect = svg.getBoundingClientRect();
    const xPx = evento.clientX - rect.left;
    const yPx = evento.clientY - rect.top;
    const centroXMm = xPx / ESCALA_PX_POR_MM;
    const centroYMm = yPx / ESCALA_PX_POR_MM;
    onMover(arrastrando, centroXMm, centroYMm);
    setArrastrando(null);
  }

  return (
    <svg
      width={mmAPx(anchoPlanchaMm, ESCALA_PX_POR_MM)}
      height={mmAPx(altoPlanchaMm, ESCALA_PX_POR_MM)}
      className="border border-line bg-paper"
      onPointerUp={alSoltarEnSvg}
      onPointerMove={(e) => e.preventDefault()}
    >
      {/* Grilla de referencia cada 100mm, tenue — mismo criterio que el plano imprimible del backend */}
      {Array.from({ length: Math.ceil(anchoPlanchaMm / 100) }).map((_, i) => (
        <line
          key={`v${i}`}
          x1={mmAPx(i * 100, ESCALA_PX_POR_MM)}
          y1={0}
          x2={mmAPx(i * 100, ESCALA_PX_POR_MM)}
          y2={mmAPx(altoPlanchaMm, ESCALA_PX_POR_MM)}
          stroke="#E3D9C6"
          strokeWidth={1}
        />
      ))}

      {colocaciones.map((colocacion) => {
        const pieza = piezaPorId.get(colocacion.pieza_id);
        if (!pieza) return null;
        const centro = { x: Number(colocacion.centro_x_mm), y: Number(colocacion.centro_y_mm) };
        const angulo = Number(colocacion.angulo_grados);
        const anchoLocal = Number(pieza.ancho_mm);
        const altoLocal = Number(pieza.alto_mm);
        const esquinaLocal = { x: centro.x - anchoLocal / 2, y: centro.y - altoLocal / 2 };
        const puntos = pieza.contorno_mm
          .map(([lx, ly]) => rotarPunto({ x: esquinaLocal.x + lx, y: esquinaLocal.y + ly }, centro, angulo))
          .map((p) => `${mmAPx(p.x, ESCALA_PX_POR_MM)},${mmAPx(p.y, ESCALA_PX_POR_MM)}`)
          .join(" ");
        const invalida = colocacionesInvalidas.has(colocacion.id);

        return (
          <polygon
            key={colocacion.id}
            points={puntos}
            fill={invalida ? "#C4432A33" : "#2E807433"}
            stroke={invalida ? "#C4432A" : "#2E8074"}
            strokeWidth={2}
            style={{ cursor: "grab" }}
            onPointerDown={() => {
              setSeleccionada(colocacion.id);
              setArrastrando(colocacion.id);
            }}
            onDoubleClick={() => {
              if (seleccionada === colocacion.id) {
                onRotar(colocacion.id, (angulo + PASO_ROTACION) % 360);
              }
            }}
          />
        );
      })}
    </svg>
  );
}
```

> Nota para quien implemente: el arrastre acá usa `onPointerUp` sobre el `<svg>` entero (mueve la pieza que se venía arrastrando a la posición del puntero al soltar) en vez de seguir el puntero en cada `onPointerMove` — es la implementación mínima que cumple "el PATCH se dispara en pointerup, no en cada frame" (spec §6). Seguir el puntero en vivo (feedback visual mientras se arrastra, antes de soltar) es una mejora de UX deseable pero no bloqueante para el ciclo — se puede sumar después con estado local de posición "fantasma" sin cambiar la interfaz de este componente.

- [ ] **Step 5: Reescribir `AjusteTab.tsx`**

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGrupos } from "../../hooks/useGrupos";
import { usePiezas } from "../../hooks/usePiezas";
import { useEjecucionesDeGrupo, useColocaciones, useAjustarColocacion } from "../../hooks/useNesting";
import { urlPlano, urlDxf } from "../../api/nesting";
import { useFormato } from "../../hooks/useCatalogo";
import PlanoEditor from "../../components/PlanoEditor/PlanoEditor";
import Banner from "../../components/Banner";

export default function AjusteTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: grupos } = useGrupos(id);
  const { data: piezas } = usePiezas(id);
  const [grupoId, setGrupoId] = useState<number | null>(null);
  const { data: historial } = useEjecucionesDeGrupo(grupoId ?? -1);
  const ejecucionDefinitiva = historial?.find((e) => e.es_definitiva) ?? historial?.[0];
  const { data: colocaciones } = useColocaciones(ejecucionDefinitiva?.id ?? null);
  const ajustar = useAjustarColocacion(ejecucionDefinitiva?.id ?? -1);
  const [plancha, setPlancha] = useState(0);
  const [motivos, setMotivos] = useState<Map<number, string>>(new Map());

  const grupoActivo = grupos?.find((g) => g.id === grupoId);
  // Las medidas reales de la plancha salen del catálogo (mapeado del
  // Excel real del cliente, ver B-02 en REGISTRO.md) — nunca un valor
  // de prueba: sin esto el editor dibujaría a una escala inventada.
  const { data: formato } = useFormato(grupoActivo?.formato_id ?? null);

  async function alMover(colocacionId: number, centroXMm: number, centroYMm: number) {
    const resultado = await ajustar.mutateAsync({
      colocacionId,
      datos: { centro_x_mm: centroXMm, centro_y_mm: centroYMm },
    });
    setMotivos((prev) => new Map(prev).set(colocacionId, resultado.motivo ?? ""));
  }

  async function alRotar(colocacionId: number, anguloGrados: number) {
    const resultado = await ajustar.mutateAsync({ colocacionId, datos: { angulo_grados: anguloGrados } });
    setMotivos((prev) => new Map(prev).set(colocacionId, resultado.motivo ?? ""));
  }

  const invalidas = new Set(
    Array.from(motivos.entries())
      .filter(([, motivo]) => motivo)
      .map(([id]) => id)
  );

  const colocacionesDePlancha = colocaciones?.filter((c) => c.plancha_indice === plancha) ?? [];

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Ajuste del plano</h1>

      <select
        className="border border-line rounded px-2 py-1 mb-4 bg-paper"
        value={grupoId ?? ""}
        onChange={(e) => setGrupoId(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Elegí un grupo...</option>
        {grupos?.map((g) => (
          <option key={g.id} value={g.id}>
            {g.nombre}
          </option>
        ))}
      </select>

      {ejecucionDefinitiva?.estado === "lista" && grupoActivo && piezas && (
        <>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-sm">
              Plancha {plancha + 1} de {ejecucionDefinitiva.planchas_usadas}
            </span>
            <button
              className="text-xs underline"
              disabled={plancha === 0}
              onClick={() => setPlancha((p) => p - 1)}
            >
              anterior
            </button>
            <button
              className="text-xs underline"
              disabled={plancha + 1 >= (ejecucionDefinitiva.planchas_usadas ?? 1)}
              onClick={() => setPlancha((p) => p + 1)}
            >
              siguiente
            </button>
            <a
              className="text-xs underline ml-4"
              href={urlPlano(ejecucionDefinitiva.id, plancha)}
              target="_blank"
              rel="noreferrer"
            >
              Ver plano imprimible
            </a>
            <a className="text-xs underline" href={urlDxf(ejecucionDefinitiva.id, plancha)}>
              Descargar DXF de corte
            </a>
          </div>

          {[...motivos.values()].some((m) => m) && (
            <div className="mb-3">
              <Banner variante="aviso">Hay colocaciones marcadas en rojo — pasá el cursor para ver el motivo.</Banner>
            </div>
          )}

          {formato ? (
            <PlanoEditor
              anchoPlanchaMm={Number(formato.ancho_mm)}
              altoPlanchaMm={Number(formato.alto_mm)}
              piezas={piezas}
              colocaciones={colocacionesDePlancha}
              onMover={alMover}
              onRotar={alRotar}
              colocacionesInvalidas={invalidas}
            />
          ) : (
            <p className="text-sm text-ink/60">Cargando el formato del grupo...</p>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Verificar en el navegador**

Con un grupo ya anidado (Tarea 10) y su `formato_id` asignado desde el catálogo real (Tarea 9): elegir el grupo en el selector, confirmar que la plancha se dibuja a la escala real (ancho/alto en mm del catálogo, no un valor de prueba) y ver las piezas dibujadas sobre la grilla. Arrastrar una y soltarla en otra posición — confirmar que el PATCH se dispara (Network tab) y que al refrescar la página la pieza sigue en la nueva posición. Doble-click sobre una pieza seleccionada y confirmar que rota 15°. Abrir el link de plano imprimible y confirmar que muestra el SVG con grilla y etiquetas del backend.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/nesting.ts frontend/src/hooks/useNesting.ts frontend/src/api/catalogo.ts frontend/src/hooks/useCatalogo.ts frontend/src/components/PlanoEditor/PlanoEditor.tsx frontend/src/routes/TrabajoWorkspace/AjusteTab.tsx
git commit -m "feat(frontend): editor de plano interactivo a escala real — mover, rotar, resaltar conflicto"
```

---

## Task 13: Presupuestos — clientes, opciones, duplicar, costeo de materiales

**Files:**
- Create: `frontend/src/api/presupuestos.ts`
- Create: `frontend/src/hooks/usePresupuestos.ts`
- Rewrite: `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx` (primera mitad: selector de opción, costeo de materiales)

**Interfaces:**
- Consumes: `apiGet`, `apiPost` (Task 5); `useTrabajo` (Task 6); `Banner` (Task 8).
- Produces: tipos `Cliente`, `Presupuesto`, `ResumenMateriales`; `listarClientes`, `crearCliente`, `crearPresupuesto`, `listarPresupuestosDelTrabajo`, `duplicarPresupuesto`, `obtenerCosteo`, `recalcularMateriales` — la Tarea 14 los extiende con líneas/totales/desglose sobre el mismo archivo.

- [ ] **Step 1: Crear `api/presupuestos.ts`**

```typescript
import { apiGet, apiPost } from "./client";

export interface Cliente {
  id: number;
  nombre: string;
  contacto: string | null;
}

export interface Presupuesto {
  id: number;
  codigo: string;
  cliente_id: number;
  trabajo_id: number | null;
  estado: string;
  validez_dias: number;
  moneda: string;
  margen_pct: string | null;
  iva_pct: string | null;
}

export interface LineaMaterial {
  grupo_id: number;
  grupo_nombre: string;
  material_nombre: string | null;
  formato_descripcion: string | null;
  planchas_usadas: number | null;
  area_total_m2: string | null;
  moneda: string | null;
  ejecucion_id: number | null;
  costo_estimado: string | null;
  advertencias: string[];
}

export interface ResumenMateriales {
  trabajo_id: number;
  lineas: LineaMaterial[];
  costo_total_por_moneda: Record<string, string>;
  advertencias_generales: string[];
}

export function listarClientes(): Promise<Cliente[]> {
  return apiGet<Cliente[]>("/clientes");
}

export function crearCliente(nombre: string, contacto?: string): Promise<Cliente> {
  return apiPost<Cliente>("/clientes", { nombre, contacto });
}

export function listarTodosLosPresupuestos(): Promise<Presupuesto[]> {
  return apiGet<Presupuesto[]>("/presupuestos");
}

export function crearPresupuesto(clienteId: number, trabajoId: number, validezDias: number): Promise<Presupuesto> {
  return apiPost<Presupuesto>("/presupuestos", { cliente_id: clienteId, trabajo_id: trabajoId, validez_dias: validezDias });
}

export function duplicarPresupuesto(presupuestoId: number): Promise<Presupuesto> {
  return apiPost<Presupuesto>(`/presupuestos/${presupuestoId}/duplicar`);
}

export function obtenerCosteo(trabajoId: number): Promise<ResumenMateriales> {
  return apiGet<ResumenMateriales>(`/trabajos/${trabajoId}/costeo`);
}

export function recalcularMateriales(presupuestoId: number) {
  return apiPost(`/presupuestos/${presupuestoId}/recalcular-materiales`);
}
```

- [ ] **Step 2: Crear `hooks/usePresupuestos.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  crearCliente,
  crearPresupuesto,
  duplicarPresupuesto,
  listarClientes,
  listarTodosLosPresupuestos,
  obtenerCosteo,
  recalcularMateriales,
} from "../api/presupuestos";

export function useClientes() {
  return useQuery({ queryKey: ["clientes"], queryFn: listarClientes });
}

export function useCrearCliente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => crearCliente(nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clientes"] }),
  });
}

/** Todos los presupuestos del trabajo, filtrado client-side — no hay
 * filtro por trabajo_id en GET /presupuestos (ver Task 13, backend). */
export function usePresupuestosDelTrabajo(trabajoId: number) {
  const query = useQuery({ queryKey: ["presupuestos"], queryFn: listarTodosLosPresupuestos });
  return {
    ...query,
    data: query.data?.filter((p) => p.trabajo_id === trabajoId),
  };
}

export function useCrearPresupuesto(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clienteId, validezDias }: { clienteId: number; validezDias: number }) =>
      crearPresupuesto(clienteId, trabajoId, validezDias),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["presupuestos"] }),
  });
}

export function useDuplicarPresupuesto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (presupuestoId: number) => duplicarPresupuesto(presupuestoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["presupuestos"] }),
  });
}

export function useCosteo(trabajoId: number) {
  return useQuery({ queryKey: ["costeo", trabajoId], queryFn: () => obtenerCosteo(trabajoId) });
}

export function useRecalcularMateriales(presupuestoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => recalcularMateriales(presupuestoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] }),
  });
}
```

- [ ] **Step 3: Reescribir `CosteoTab.tsx`** (primera mitad — la Tarea 14 completa el cuerpo con líneas/totales/desglose)

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useClientes,
  useCosteo,
  useCrearCliente,
  useCrearPresupuesto,
  useDuplicarPresupuesto,
  usePresupuestosDelTrabajo,
  useRecalcularMateriales,
} from "../../hooks/usePresupuestos";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";

export default function CosteoTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: presupuestos } = usePresupuestosDelTrabajo(id);
  const { data: clientes } = useClientes();
  const crearCliente = useCrearCliente();
  const crearPresupuesto = useCrearPresupuesto(id);
  const duplicar = useDuplicarPresupuesto();
  const [presupuestoActivoId, setPresupuestoActivoId] = useState<number | null>(null);
  const { data: costeo } = useCosteo(id);
  const recalcular = useRecalcularMateriales(presupuestoActivoId ?? -1);
  const [nombreCliente, setNombreCliente] = useState("");
  const [error, setError] = useState<string | null>(null);

  const presupuestoActivo = presupuestos?.find((p) => p.id === presupuestoActivoId) ?? presupuestos?.[0];

  async function alCrearOpcion() {
    let clienteId = clientes?.[0]?.id;
    if (!clienteId && nombreCliente.trim()) {
      const cliente = await crearCliente.mutateAsync(nombreCliente.trim());
      clienteId = cliente.id;
    }
    if (!clienteId) return;
    const presupuesto = await crearPresupuesto.mutateAsync({ clienteId, validezDias: 15 });
    setPresupuestoActivoId(presupuesto.id);
  }

  async function alRecalcular() {
    setError(null);
    try {
      await recalcular.mutateAsync();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo recalcular.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Costeo</h1>

      {(!presupuestos || presupuestos.length === 0) && (
        <div className="mb-4 flex gap-2 items-center">
          {(!clientes || clientes.length === 0) && (
            <input
              className="border border-line rounded px-3 py-2 bg-paper"
              placeholder="Nombre del cliente"
              value={nombreCliente}
              onChange={(e) => setNombreCliente(e.target.value)}
            />
          )}
          <button className="bg-cut text-paper rounded px-4 py-2" onClick={alCrearOpcion}>
            Crear primera opción de presupuesto
          </button>
        </div>
      )}

      {presupuestos && presupuestos.length > 0 && (
        <div className="flex gap-2 mb-4">
          {presupuestos.map((p) => (
            <button
              key={p.id}
              className={`rounded px-3 py-1 text-sm border border-line ${
                presupuestoActivo?.id === p.id ? "bg-cut text-paper" : ""
              }`}
              onClick={() => setPresupuestoActivoId(p.id)}
            >
              {p.codigo}
            </button>
          ))}
          <button
            className="text-xs underline"
            onClick={async () => {
              if (!presupuestoActivo) return;
              const copia = await duplicar.mutateAsync(presupuestoActivo.id);
              setPresupuestoActivoId(copia.id);
            }}
          >
            + Duplicar opción
          </button>
        </div>
      )}

      {presupuestoActivo && (
        <div className="border border-line rounded p-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-medium">Costeo de materiales</h2>
            <button className="text-sm underline" onClick={alRecalcular}>
              Recalcular materiales
            </button>
          </div>

          {error && <Banner variante="error">{error}</Banner>}

          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-line">
                <th>Grupo</th>
                <th>Material</th>
                <th>Planchas</th>
                <th>Costo</th>
              </tr>
            </thead>
            <tbody>
              {costeo?.lineas.map((linea) => (
                <tr key={linea.grupo_id} className="border-b border-line">
                  <td>{linea.grupo_nombre}</td>
                  <td>{linea.material_nombre ?? "sin asignar"}</td>
                  <td className="font-mono">{linea.planchas_usadas ?? "—"}</td>
                  <td className="font-mono text-bronze">
                    {linea.costo_estimado ? `${linea.moneda} ${Number(linea.costo_estimado).toFixed(2)}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {costeo?.advertencias_generales.map((a, i) => (
            <div key={i} className="mt-2">
              <Banner variante="aviso">{a}</Banner>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verificar en el navegador**

Con un trabajo que ya tiene un grupo anidado y marcado definitivo (Tarea 10): crear la primera opción de presupuesto (con un cliente nuevo), confirmar que aparece el chip con su código (`P-2026-0001`), apretar "Recalcular materiales" y ver la línea de costo del grupo. Duplicar la opción y confirmar que aparece un segundo chip.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/presupuestos.ts frontend/src/hooks/usePresupuestos.ts frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx
git commit -m "feat(frontend): clientes, opciones de presupuesto, duplicar y costeo de materiales"
```

---

## Task 14: Líneas de costo, márgenes, totales y desglose

**Files:**
- Modify: `frontend/src/api/presupuestos.ts` (agregar `LineaCosto`, `Totales`, `Desglose`, funciones de líneas/override/margen-iva/totales/desglose)
- Modify: `frontend/src/hooks/usePresupuestos.ts` (agregar hooks correspondientes)
- Modify: `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx` (agregar la sección de líneas, totales y desglose debajo del costeo de materiales)

**Interfaces:**
- Consumes: todo lo de la Tarea 13; `urlPlano` (Task 12) para embeber el plano en el desglose.
- Produces: nada consumido por tareas posteriores — es la última del plan.

- [ ] **Step 1: Agregar a `api/presupuestos.ts`**

```typescript
import { apiGet, apiPatch, apiPost } from "./client";

export interface LineaCosto {
  id: number;
  presupuesto_id: number;
  rubro: "MATERIAL" | "INSUMO" | "MANO_DE_OBRA" | "FLETE" | "INSTALACION" | "OTRO";
  grupo_id: number | null;
  ejecucion_id: number | null;
  descripcion: string;
  cantidad: string | null;
  unidad: string | null;
  precio_unitario: string | null;
  valor_calculado: string | null;
  moneda: string;
  advertencia: string | null;
  valor_override: string | null;
  override_por: string | null;
}

export interface Totales {
  presupuesto_id: number;
  moneda: string;
  subtotales_por_rubro: Record<string, string>;
  costo_total: string;
  margen_pct: string | null;
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

export function listarLineasCosto(presupuestoId: number): Promise<LineaCosto[]> {
  return apiGet<LineaCosto[]>(`/presupuestos/${presupuestoId}/lineas-costo`);
}

export function crearLineaLibre(
  presupuestoId: number,
  datos: { rubro: string; descripcion: string; cantidad: string; unidad?: string; precio_unitario: string }
): Promise<LineaCosto> {
  return apiPost<LineaCosto>(`/presupuestos/${presupuestoId}/lineas-costo`, datos);
}

export function aplicarOverride(lineaId: number, valorOverride: string | null, overridePor: string): Promise<LineaCosto> {
  return apiPatch<LineaCosto>(`/lineas-costo/${lineaId}/override`, {
    valor_override: valorOverride,
    override_por: valorOverride === null ? null : overridePor,
  });
}

export function actualizarMargenEIva(
  presupuestoId: number,
  datos: { margen_pct?: string; iva_pct?: string }
): Promise<Presupuesto> {
  return apiPatch<Presupuesto>(`/presupuestos/${presupuestoId}`, datos);
}

export function obtenerTotales(presupuestoId: number): Promise<Totales> {
  return apiGet<Totales>(`/presupuestos/${presupuestoId}/totales`);
}

export function obtenerDesglose(presupuestoId: number): Promise<Desglose> {
  return apiGet<Desglose>(`/presupuestos/${presupuestoId}/desglose`);
}
```

- [ ] **Step 2: Agregar a `hooks/usePresupuestos.ts`**

```typescript
import {
  actualizarMargenEIva,
  aplicarOverride,
  crearLineaLibre,
  listarLineasCosto,
  obtenerDesglose,
} from "../api/presupuestos";

export function useLineasCosto(presupuestoId: number) {
  return useQuery({ queryKey: ["lineas-costo", presupuestoId], queryFn: () => listarLineasCosto(presupuestoId) });
}

export function useCrearLineaLibre(presupuestoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: Parameters<typeof crearLineaLibre>[1]) => crearLineaLibre(presupuestoId, datos),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] });
      queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] });
    },
  });
}

export function useAplicarOverride(presupuestoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ lineaId, valor, overridePor }: { lineaId: number; valor: string | null; overridePor: string }) =>
      aplicarOverride(lineaId, valor, overridePor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] });
      queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] });
    },
  });
}

export function useActualizarMargenEIva(presupuestoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: { margen_pct?: string; iva_pct?: string }) => actualizarMargenEIva(presupuestoId, datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] }),
  });
}

export function useDesglose(presupuestoId: number | null) {
  return useQuery({
    queryKey: ["desglose", presupuestoId],
    queryFn: () => obtenerDesglose(presupuestoId as number),
    enabled: presupuestoId !== null,
  });
}
```

- [ ] **Step 3: Agregar la sección de líneas/totales/desglose a `CosteoTab.tsx`**

Agregar, dentro del `{presupuestoActivo && (...)}` ya existente (Task 13), después de la tabla de costeo de materiales:

```tsx
<SeccionDesglose presupuestoId={presupuestoActivo.id} />
```

Y, en el mismo archivo, un nuevo componente (usa los imports de `useDesglose`, `useCrearLineaLibre`, `useAplicarOverride`, `useActualizarMargenEIva` y `urlPlano` de `../../api/nesting`):

```tsx
function SeccionDesglose({ presupuestoId }: { presupuestoId: number }) {
  const { data: desglose } = useDesglose(presupuestoId);
  const crearLinea = useCrearLineaLibre(presupuestoId);
  const override = useAplicarOverride(presupuestoId);
  const margenEIva = useActualizarMargenEIva(presupuestoId);
  const [nuevaLinea, setNuevaLinea] = useState({
    rubro: "MANO_DE_OBRA",
    descripcion: "",
    cantidad: "1",
    precio_unitario: "0",
  });

  if (!desglose) return null;
  const { totales } = desglose;

  return (
    <div className="mt-6 border-t border-line pt-4">
      <h2 className="font-medium mb-3">Líneas por rubro</h2>

      {Object.entries(desglose.lineas_por_rubro).map(([rubro, lineas]) => (
        <div key={rubro} className="mb-4">
          <h3 className="text-sm font-medium mb-1">{rubro}</h3>
          <table className="w-full text-sm">
            <tbody>
              {lineas.map((linea) => (
                <tr key={linea.id} className="border-b border-line">
                  <td>{linea.descripcion}</td>
                  <td className="font-mono">{linea.cantidad ?? "—"}</td>
                  <td className="font-mono">
                    {linea.moneda} {Number(linea.valor_override ?? linea.valor_calculado ?? 0).toFixed(2)}
                    {linea.valor_override !== null && <span className="ml-1 text-bronze text-xs">override</span>}
                  </td>
                  <td>
                    <button
                      className="text-xs underline"
                      onClick={() => {
                        const valor = window.prompt("Nuevo valor (vacío para volver al calculado):");
                        if (valor === null) return;
                        override.mutate({
                          lineaId: linea.id,
                          valor: valor === "" ? null : valor,
                          overridePor: "Enzo",
                        });
                      }}
                    >
                      Override
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      <div className="flex gap-2 mb-6">
        <select
          className="border border-line rounded px-2 py-1 bg-paper text-sm"
          value={nuevaLinea.rubro}
          onChange={(e) => setNuevaLinea((n) => ({ ...n, rubro: e.target.value }))}
        >
          <option value="INSUMO">Insumo</option>
          <option value="MANO_DE_OBRA">Mano de obra</option>
          <option value="FLETE">Flete</option>
          <option value="INSTALACION">Instalación</option>
          <option value="OTRO">Otro</option>
        </select>
        <input
          className="border border-line rounded px-2 py-1 bg-paper text-sm flex-1"
          placeholder="Descripción"
          value={nuevaLinea.descripcion}
          onChange={(e) => setNuevaLinea((n) => ({ ...n, descripcion: e.target.value }))}
        />
        <input
          className="border border-line rounded px-2 py-1 bg-paper text-sm w-20 font-mono"
          value={nuevaLinea.cantidad}
          onChange={(e) => setNuevaLinea((n) => ({ ...n, cantidad: e.target.value }))}
        />
        <input
          className="border border-line rounded px-2 py-1 bg-paper text-sm w-28 font-mono"
          value={nuevaLinea.precio_unitario}
          onChange={(e) => setNuevaLinea((n) => ({ ...n, precio_unitario: e.target.value }))}
        />
        <button
          className="bg-cut text-paper rounded px-3 py-1 text-sm"
          onClick={() => nuevaLinea.descripcion.trim() && crearLinea.mutate(nuevaLinea)}
        >
          Agregar línea
        </button>
      </div>

      <div className="flex gap-4 items-center mb-4 text-sm">
        <label>
          Margen %:{" "}
          <input
            className="border border-line rounded px-2 py-1 w-20 font-mono bg-paper"
            defaultValue={totales.margen_pct ?? ""}
            onBlur={(e) => margenEIva.mutate({ margen_pct: e.target.value })}
          />
        </label>
        <label>
          IVA %:{" "}
          <input
            className="border border-line rounded px-2 py-1 w-20 font-mono bg-paper"
            defaultValue={totales.iva_pct ?? "21"}
            onBlur={(e) => margenEIva.mutate({ iva_pct: e.target.value })}
          />
        </label>
      </div>

      <div className="border border-line rounded p-4 font-mono text-sm space-y-1">
        <p>Costo total: {totales.costo_total}</p>
        {totales.monto_margen && <p>Margen: {totales.monto_margen}</p>}
        {totales.precio_venta && <p>Precio de venta: {totales.precio_venta}</p>}
        {totales.monto_iva && <p>IVA: {totales.monto_iva}</p>}
        {totales.total && <p className="text-bronze font-semibold text-base">Total: {totales.total}</p>}
      </div>

      {totales.advertencias.map((a, i) => (
        <div key={i} className="mt-2">
          <Banner variante="aviso">{a}</Banner>
        </div>
      ))}

      <div className="mt-4">
        {Object.values(desglose.lineas_por_rubro)
          .flat()
          .filter((l) => l.rubro === "MATERIAL" && l.ejecucion_id)
          .map((l) => (
            <a
              key={l.id}
              className="text-xs underline mr-3"
              href={urlPlano(l.ejecucion_id as number, 0)}
              target="_blank"
              rel="noreferrer"
            >
              Ver plano de «{l.descripcion}»
            </a>
          ))}
      </div>
    </div>
  );
}
```

Agregar los imports que falten al encabezado de `CosteoTab.tsx`: `useState` (ya está), `useDesglose`, `useCrearLineaLibre`, `useAplicarOverride`, `useActualizarMargenEIva` desde `../../hooks/usePresupuestos`, y `urlPlano` desde `../../api/nesting`.

- [ ] **Step 4: Verificar en el navegador**

Con la opción de presupuesto de la Tarea 13 ya con su línea de material: agregar una línea libre de mano de obra, confirmar que aparece agrupada bajo `MANO_DE_OBRA`. Aplicar un override a la línea de material y confirmar que se marca visualmente. Cargar margen (ej. `30`) e IVA (ej. `21`) y confirmar que el bloque de totales se completa con precio de venta y total. Confirmar el link "Ver plano de..." abre el SVG del backend.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/presupuestos.ts frontend/src/hooks/usePresupuestos.ts frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx
git commit -m "feat(frontend): lineas de costo, overrides, margen/IVA, totales y desglose completo"
```

---

## Self-Review

**Cobertura de la spec:**
- §3 Arquitectura (Vite/React/TS/react-router/react-query/Tailwind, CORS): Tasks 4-6.
- §4 Identidad visual (paleta, tipografía, bordes): Task 4 (tokens), aplicado en todas las pantallas.
- §5 Rutas y pantallas (Piezas/Grupos/Anidado/Ajuste/Costeo): Tasks 8, 9, 10, 12, 13-14 respectivamente.
- §5.1 Validación `.dxf` (`D-11`): Task 8, Step 5.
- §5.2 Comparar formatos (`CART-205`) + aviso al recalcular: Task 3 (backend) + Task 9 (UI de comparación) + Task 13 (botón "Recalcular materiales", con el error del backend mostrado tal cual — el aviso de "esto puede pisar una opción ya mostrada al cliente" queda como mejora de UX posterior, no bloqueante: el dato para construirlo — `linea.ejecucion_id` guardado vs. `costeo.lineas[].ejecucion_id` vivo — ya está expuesto por ambos endpoints).
- §6 Flujo de datos (react-query, keys, invalidación, polling, PATCH en pointerup): Tasks 5, 10, 12.
- §7 Manejo de errores (banners, `valida:false`, sin reintentos): Task 8 (`Banner`), Task 12 (resaltado de conflicto).
- §8 Testing (mm↔px/rotación con tests reales, resto manual): Task 11.
- §9 Fuera de alcance: ningún task lo cubre a propósito (auth, PDF, `.cdr` directo, Deepnest, catálogo de insumos, dos anidados en paralelo).

**Gap encontrado y corregido durante el planning:** la spec no incluía un endpoint para listar el historial de ejecuciones de un grupo (necesario para "Anidado" §5) — se agregó como Task 2.

**Placeholders:** ninguno. La Task 12 tenía originalmente un `TODO(human)` sobre cómo obtener el ancho/alto real de la plancha — se resolvió durante el planning: `GET /formatos/{id}` ya existe en el backend (`rutas_catalogo.py`), así que se agregó `obtenerFormato`/`useFormato` al frontend en vez de tocar el modelo. De paso se corrigió que el borrador original de `AjusteTab.tsx` importaba `PlanoEditor` y calculaba `colocacionesDePlancha`/`invalidas` pero nunca los usaba — ya está cableado.

**Consistencia de tipos:** `Ejecucion.estado` es la unión literal `"encolada" | "corriendo" | "lista" | "cancelada" | "error"` en Task 10 y se usa igual en Tasks 10/12; `Colocacion`/`ColocacionAjustada` en Task 12 coinciden con lo que `PATCH /colocaciones/{id}` devuelve según `esquemas_nesting.py`; `LineaCosto.rubro` en Task 14 coincide con el `Literal` de `LineaCostoCrear` del backend más `"MATERIAL"` (que solo genera `recalcular-materiales`, nunca el formulario de línea libre — el `<select>` de Task 14 correctamente no ofrece `MATERIAL` como opción).
