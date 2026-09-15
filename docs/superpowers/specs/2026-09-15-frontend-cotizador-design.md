# DISEÑO: frontend del cotizador — herramienta interna, ciclo completo

> Índice del proyecto: [`../../README.md`](../../README.md) · [`../MAPA-DEL-PROYECTO.md`](../MAPA-DEL-PROYECTO.md) · [`../PLAN-SLICE-VERTICAL.md`](../PLAN-SLICE-VERTICAL.md) · [`../PLAN-SLICE-COTIZADOR.md`](../PLAN-SLICE-COTIZADOR.md) · [`../REGISTRO.md`](../REGISTRO.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-15

---

## 1. Contexto y objetivo

`F2` (nesting rectangular) y `F3` (cotizador) están completos por API salvo PDF (ver `MAPA-DEL-PROYECTO.md`). No existe ningún frontend: todo el pipeline —desde subir un DXF hasta el desglose completo del presupuesto, con costeo, overrides, líneas libres, margen, IVA y total— solo es accesible por HTTP directo o Swagger (`/docs`).

**Objetivo de este slice:** una herramienta interna (para Enzo, único usuario, sin auth) que permita recorrer el ciclo completo de un pedido real de punta a punta, incluyendo el ajuste manual de piezas sobre el plano. No es el producto final que va a usar el taller o los clientes — es el paso que valida que el ciclo funciona, y la base sobre la que se construye el producto real más adelante (agregando `CART-002`/auth y pulido cuando haga falta).

**Qué NO resuelve este slice** (explícitamente diferido, no un olvido):
- Autenticación, roles y navegación por rol (`CART-002`/`CART-005`) — sigue sin haber una razón concreta para construirlos.
- PDF del presupuesto (`CART-309`/`310`) — depende de `WeasyPrint`, no instalado; además diseñar un PDF sin saber el layout de esta pantalla sería al revés.
- Subir `.cdr` directo — ver `D-11` en `REGISTRO.md` y la sección 5.1 más abajo.
- Conectar Deepnest a la API — sigue sin haber un trabajo real esperando eso.

---

## 2. El flujo real y cómo mapea a la API

El pedido real, tal como lo describe Enzo: el cliente pide (a veces con un diseño tentativo) → el equipo diseña → se pasa a Corel para sacar tamaños y materiales (exportando DXF) → con eso se arma la cotización, a veces **varias opciones** (ej. una más económica) → se comparte la elegida con el cliente.

Esto mapea a un dato clave del modelo ya existente: `Presupuesto.trabajo_id` es nullable y **no único** — el endpoint `POST /presupuestos/{id}/duplicar` copia cliente, `trabajo_id`, líneas de costo y overrides a un presupuesto nuevo. Es decir, **un `Trabajo` (las piezas, los grupos, el anidado) puede tener varios `Presupuesto` (opciones de precio)** compartiendo la misma base física. La arquitectura de navegación sigue esta jerarquía real, no una lista plana de presupuestos:

```
Trabajo (el pedido)
 ├─ Piezas          (una vez)
 ├─ Grupos de corte (una vez)
 ├─ Anidado         (una vez, con historial de ejecuciones)
 ├─ Ajuste del plano (una vez, sobre la ejecución definitiva)
 └─ Costeo
     ├─ Presupuesto "Opción A · estándar"   (líneas, overrides, totales, desglose)
     ├─ Presupuesto "Opción B · económica"  (independiente, vía duplicar)
     └─ ...
```

---

## 3. Arquitectura y stack

- **Carpeta nueva:** `frontend/`, hermana de `backend/` — SPA con Vite + React + TypeScript.
- **Routing:** `react-router`.
- **Datos de servidor:** `@tanstack/react-query` — caché, invalidación tras mutaciones, y `refetchInterval` para el polling del anidado (evita `useEffect`+`setInterval` a mano repetido en cada pantalla).
- **Estilos:** Tailwind CSS.
- **Capa `api/`:** un archivo por router del backend (`clientes.ts`, `presupuestos.ts`, `trabajos.ts`, `nesting.ts`, `ajuste.ts`), funciones tipadas envolviendo `fetch` — mismo mapeo 1:1 que ya tienen `rutas_*.py` en el backend.
- **Backend — dos cambios chicos, ambos envoltorios de código de dominio ya probado, ningún cambio de modelo de datos:**
  1. `CORSMiddleware` en `app.py` con origen `http://localhost:5173` (puerto de Vite).
  2. `POST /grupos/{id}/comparar-formatos` (nueva ruta, cubre `CART-205`): recibe una lista de `formato_id` candidatos, arma `Plancha`/`ParametrosCorte`/`precio_por_plancha` para cada uno (mismo criterio que ya usa `_datos_para_anidar` en `rutas_nesting.py`) y llama a `comparar_formatos`/`formato_recomendado` de `services/nesting/comparador.py` — que ya existe y está probado. Devuelve planchas/aprovechamiento/costo por formato, **sin persistir nada ni tocar el grupo**.

---

## 4. Identidad visual (Tailwind)

Ángulo: no es un dashboard genérico — es una herramienta para cortar chapa/acrílico y presupuestar con precisión en milímetros y pesos. La identidad viene de ahí (planos técnicos, taller, materiales), corrida hacia un tono cálido ("mesa de taller con papel kraft", no "oficina fría").

**Paleta base** (tokens con un rol fijo cada uno, nunca decorativo):

| Token | Hex | Rol |
|---|---|---|
| `paper` | `#F5F1E8` | Fondo — beige kraft |
| `ink` | `#2B2420` | Texto — marrón oscuro, no negro puro |
| `line` | `#E3D9C6` | Hairlines y grilla técnica |
| `cut` | `#2E8074` | Todo lo geométrico/corte: piezas, plano, contornos |
| `bronze` | `#C9922E` | Todo lo monetario: costos, márgenes, totales |
| `conflict` | `#C4432A` | Colocación inválida (lo que ya devuelve `PATCH /colocaciones/{id}` con `valida:false`) |

**Tipografía:** `IBM Plex Sans` para todo el texto e interfaz. `IBM Plex Mono` **solo** para valores numéricos reales en tablas y campos (mm, ángulos, montos) — nunca para etiquetas ni decoración; es para que columnas de números (medidas, costos) se puedan comparar de un vistazo.

**Bordes:** radio suave (6-8px) en botones e inputs — es lo que más aporta a la sensación "amigable" sin tocar la tipografía.

**Layout:** riel lateral fijo con el trabajo activo y sus etapas en secuencia real (Piezas → Grupos → Anidado → Ajuste → Costeo) — acá corresponde marcar secuencia porque cada etapa es un estado real con su propio endpoint, no decoración. `●` = etapa con datos cargados (sale de la API), `○` = todavía vacía.

**Principios:** un color = una función siempre; números en tabular/mono para poder comparar; paneles planos separados por hairlines, sin tarjetas-con-sombra genéricas.

---

## 5. Rutas y pantallas

- **`/`** — lista de trabajos (cliente, nombre, qué etapas ya tienen datos, fecha). Alta de trabajo + cliente nuevo.
- **`/trabajos/:id/piezas`** — subir DXF (ver §5.1 sobre validación de formato), tabla de piezas con mini-preview SVG del contorno, ancho/alto/cantidad, descartar.
- **`/trabajos/:id/grupos`** — crear grupos de corte, mover piezas a un grupo, y **comparar formatos antes de asignar uno** (ver §5.2) — recién al elegir uno se asigna al grupo (`formato_id`).
- **`/trabajos/:id/anidado`** — anidar por grupo (`POST /grupos/{id}/anidar`), polling de estado mientras esté `encolada`/`corriendo`, historial de ejecuciones (comparar aprovechamiento/planchas), marcar definitiva.
- **`/trabajos/:id/ajuste`** — editor SVG interactivo: fetch `GET /trabajos/{id}/piezas` (contorno_mm) + `GET /ejecuciones/{id}/colocaciones` (posición/ángulo), dibuja las piezas sobre una grilla mm tenue, arrastrar para mover, botones rotar ±15°/±90°, resaltado en `conflict` cuando `valida:false` (con el `motivo` en tooltip, sin bloquear el movimiento). Selector de plancha si hay más de una. Enlaces a plano imprimible (`GET .../plano`, SVG) y DXF de corte (`GET .../dxf`, descarga).
- **`/trabajos/:id/costeo`** — chips por presupuesto (opción), botón "Duplicar opción" (`POST /presupuestos/{id}/duplicar`); dentro de la opción activa: costeo de materiales (`GET /trabajos/{id}/costeo`), líneas por rubro con overrides, formulario de línea libre (insumos/mano de obra/flete/instalación), margen/IVA, totales, y el desglose final (`GET /presupuestos/{id}/desglose`) con el plano embebido sin salir de la pantalla.

### 5.1 Validación del archivo en Piezas — ver `D-11`

El parser (`parsear_dxf`) solo entiende `.dxf`. Un `.cdr` nativo de CorelDRAW no se sube ni se intenta parsear en este slice: el input de la pantalla de Piezas **exige `.dxf`**, y si alguien sube otra extensión se rechaza en el cliente mismo, con un mensaje en la voz de la interfaz, específico y accionable (no genérico):

> "Este archivo es `.cdr`. Exportá el DXF desde Corel (Archivo → Exportar → DXF) y subí ese archivo."

`D-11` en `REGISTRO.md` deja registrado que existe una vía técnica probada (`libcdr`, `SPIKE-CDR.md`) para aceptar `.cdr` directo en el futuro, pendiente de `SUP-05`/`B-15` (si el equipo de diseño adopta una convención de capas) — no se construye ahora porque sin capas confiables el parser no sabría qué es corte y qué es grabado/decoración.

### 5.2 Comparar formatos antes de asignar material (`CART-205`)

**El origen de esta sección:** para ofrecer una variante más económica o en otro material, hace falta poder ver el costo de las mismas piezas en formatos distintos *antes* de comprometerse a uno. El límite real del modelo: una `Pieza` pertenece a un solo `GrupoDeCorte` (un solo material vigente) a la vez — no puede haber dos anidados persistidos en paralelo, en materiales distintos, para el mismo lote de piezas. La solución elegida es **comparar sin persistir, decidir, después anidar de verdad** (no "dos anidados simultáneos", que exigiría cambiar el modelo de datos).

En la pantalla de Grupos, antes de fijar un `formato_id`: el usuario elige 2 o más formatos candidatos del catálogo, la UI llama a `POST /grupos/{id}/comparar-formatos` (nueva ruta, ver §3) y muestra una tabla — un formato por fila, con planchas necesarias, % de aprovechamiento y costo total, destacando el de menor costo (mismo criterio que `formato_recomendado`: nunca el de mayor aprovechamiento porcentual si no es el más barato). Elegir una fila hace el `PATCH` real del `formato_id` del grupo; recién ahí ese grupo se puede anidar (§`/trabajos/:id/anidado`).

**Aviso al recalcular materiales de un presupuesto ya existente:** si el material de un grupo cambió (o se volvió a anidar) *después* de que una opción de presupuesto ya tiene sus líneas de material calculadas, volver a tocar "Recalcular materiales" en esa opción las reemplaza por el estado actual — no hay versionado de "qué material regía cuando se calculó esta opción". La pantalla de Costeo muestra una confirmación antes de recalcular si detecta que el `grupo_id`/`ejecucion_id` que ya tienen las líneas de esa opción no coincide con el que devuelve hoy `GET /trabajos/{id}/costeo`, para no pisar sin querer una opción que ya se le mostró al cliente.

---

## 6. Flujo de datos

React Query para todo el estado de servidor, con query keys por recurso (`['piezas', trabajoId]`, `['colocaciones', ejecucionId]`, etc.) y mutaciones que invalidan lo relacionado. El polling del anidado usa `refetchInterval` que se apaga solo al llegar a un estado terminal (`lista`/`error`/`cancelada`).

En el editor SVG de Ajuste: arrastrar actualiza el estado local al toque (fluido, sin esperar red), pero el `PATCH /colocaciones/{id}` se dispara recién en `pointerup` — no en cada frame de movimiento, para no bombardear la API mientras se arrastra.

---

## 7. Manejo de errores

Los errores HTTP (`400`/`404`/`409`) del backend ya traen mensaje humano (`HTTPException(status, "...")`) — se muestran tal cual en un banner, sin inventar texto genérico. `valida:false` en el ajuste no es un error HTTP (la respuesta es `200`): se resuelve con resaltado visual + `motivo`, nunca bloqueando el movimiento — así lo decidió a propósito el backend (`ColocacionAjusteLeer`). Sin reintentos automáticos: si falla un DXF corrupto o mal formado, se muestra el motivo y decide el usuario si reintenta.

---

## 8. Testing

Sin suite grande de componentes: es herramienta interna y el valor está en que el ciclo ande de punta a punta. Test unitario puro para la única lógica no trivial: la conversión mm↔px y la rotación alrededor del centro en el editor SVG — un bug ahí no se nota leyendo el código, se nota arrastrando mal una pieza. El resto se verifica usándolo contra la API local con un DXF real (ver `GUIA-PRUEBAS-LOCALES.md` para los archivos de prueba disponibles — notar que ninguno de los `.dxf`/`.cdr` de prueba actuales representa el trabajo real de chapa, según la nota de `B-02`/`§3` de `REGISTRO.md`).

---

## 9. Fuera de alcance de este slice

- Auth/roles (`CART-002`/`CART-005`).
- PDF (`CART-309`/`310`).
- Subir `.cdr` directo (`D-11`, diferido).
- Deepnest conectado a la API.
- Catálogo de insumos no dimensionales (`CART-106` — pintura, tornillería, etc.) más allá de lo que ya soporta la línea libre por texto. **No confundir con el comparador de formatos (`CART-205`, §5.2), que sí entra en este slice** — son historias distintas.
- Dos anidados persistidos en paralelo para el mismo lote de piezas en materiales distintos (ver §5.2) — se resuelve comparando y decidiendo, no manteniendo ambos vivos a la vez.
