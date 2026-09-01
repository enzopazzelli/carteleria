# FACTIBILIDAD: NESTING EN EL NAVEGADOR — SVGnest, Deepnest y SheetNest

> Investigación puntual de tres motores de nesting open source, para evaluar si conviene resolver parte del anidado del lado del cliente (navegador) en vez de — o además de — el motor Python de backend que ya cerró `ADR-05` en [`EPICA.md`](EPICA.md).
>
> **No reemplaza ninguna decisión ya tomada.** Es un insumo para cuando se discuta cómo implementar F7 (nesting irregular), no una corrección como las de [`DECISIONES-Y-BLOQUEANTES.md`](DECISIONES-Y-BLOQUEANTES.md).
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) · [`REGISTRO.md`](REGISTRO.md) · [`BITACORA.md`](BITACORA.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-01

---

## Por qué se investigó esto

`EPICA.md §9` (`ADR-05`) ya define el stack de nesting: `rectpack` para el rectangular (F2) y `nest2D`/`libnest2d` para el irregular (F7), con **"alternativa: Deepnest"** anotado al lado en la tabla de stack (`EPICA.md` línea ~396). Esa anotación nunca se investigó a fondo — quedó como nombre suelto. Esta investigación revisa esa alternativa y dos proyectos relacionados para responder una pregunta concreta: **¿conviene, para F7, anidar en el navegador en vez de en un worker de Celery?**

Se estudiaron tres repositorios, a pedido de Enzo:

- [Jack000/SVGnest](https://github.com/Jack000/SVGnest)
- [Jack000/Deepnest](https://github.com/Jack000/Deepnest)
- [ManuelMRosa/SheetNest](https://github.com/ManuelMRosa/SheetNest)

Todos los datos de esta tabla salen de la API de GitHub y de los archivos reales de cada repo (no de memoria ni de suposición), consultados el 2026-09-01.

---

## Resumen ejecutivo

**El hallazgo que más importa: `Deepnest` no tiene archivo de licencia.** La alternativa que `ADR-05` menciona de pasada para F7 no tiene, hoy, un permiso legal explícito de uso — ver detalle abajo. Esto no bloquea nada ahora (F7 es Hito 5, el más lejano), pero conviene que quede escrito antes de que alguien lo dé por sentado en S9-S10.

**Para "nesting en una página web" en general** (más allá de F7): el candidato natural es `SVGnest`, porque ya es 100% navegador (JS + Web Workers, sin backend, sin binarios nativos) y tiene licencia MIT limpia. `Deepnest` es más rápido y completo pero es una app de escritorio Electron con un addon nativo en C++ — llevarlo a la web implica compilar a WebAssembly, no "portarlo" tal cual. `SheetNest` resuelve un problema distinto (desdoblado 3D de chapa metálica) y es escritorio Windows en C#/.NET — no aporta una ruta directa para este proyecto.

**Recomendación:** no tocar `ADR-05` todavía — `nest2D`/`libnest2d` (LGPL-3.0, mantenido activamente por Ultimaker) sigue siendo la opción sólida para F7 en el backend. Si en algún momento se evalúa mover nesting al cliente (por ejemplo, para que el diseñador vea una previsualización instantánea antes de mandar el trabajo al worker), la base debería ser `SVGnest`, no `Deepnest`.

---

## Los tres proyectos, con datos verificados

| | **SVGnest** | **Deepnest** | **SheetNest** |
|---|---|---|---|
| Stack | JS puro, corre en el navegador (Web Workers) | Electron + addon nativo en C++ (Clipper/Minkowski, compilado con `node-gyp`) | C# / .NET desktop, motor DeepNestSharp + Clipper + FreeCAD embebido |
| ¿Corre en un navegador? | **Sí** — es literalmente lo que corre en svgnest.com | **No** — necesita el binario nativo compilado por SO (Windows/Mac), es app de escritorio | **No** — app de escritorio Windows |
| Licencia | MIT | **Sin archivo de LICENSE en el repo** (confirmado en el listado de archivos vía API — no existe) | MIT |
| Actividad | Último push 2024-02-01 · 2.589★ | Último push del repo original: 2020-07-07 · 1.155★ (existe un fork comunitario, "deepnest-next", activo hasta 2025, pero también de escritorio) | Push muy reciente (2026-08-22) · 15★, proyecto joven |
| Dominio | Nesting genérico de formas 2D (vector/SVG) | Igual que SVGnest + anidado dentro de huecos, DXF, corte de líneas compartidas | Fabricación de chapa metálica: desdoblado 3D→2D (FreeCAD) + nesting |

### El detalle de la licencia de Deepnest

Se confirmó por dos vías: el campo `license` de la API de GitHub devuelve `null`, y el listado completo de archivos del repo (`addon.cc`, `binding.gyp`, `main.js`, `minkowski.cc`, `package.json`, etc.) no incluye ningún `LICENSE`, `LICENSE.md`, `LICENSE.txt` ni `COPYING`.

Sin un archivo de licencia, por default aplican todos los derechos reservados del autor: se puede ver y forkear en GitHub (eso lo permite GitHub, no el copyright), pero no hay permiso legal explícito para reusar, modificar o redistribuir el código fuera de ahí. Para un sistema comercial esto no es un detalle técnico — es un bloqueador legal si alguna vez se piensa en incorporar código de Deepnest directamente.

**Por contraste:** `nest2D`/`libnest2d`, que es la opción que `ADR-05` ya eligió para F7, es LGPL-3.0, con Ultimaker (la empresa detrás de Cura) manteniendo activamente los bindings de Python. Licencia clara, proyecto con un mantenedor institucional detrás. No hay ningún motivo, a la luz de esto, para preferir Deepnest sobre lo que ya está decidido.

---

## Tres rutas posibles para nesting en una página web

**Ruta A — Adaptar SVGnest directo, todo del lado del cliente.**
Esfuerzo bajo: se integra el JS tal cual (o se moderniza), sin backend nuevo, sin problema de licencia (MIT), sin binarios que compilar. Limitación real: no anida piezas dentro de huecos de otras piezas y no tiene DXF nativo. Para paneles rectos y letras corpóreas simples (el caso de este proyecto) esa limitación rara vez importa — nesting-en-huecos es más típico de chapa metálica o carpintería con recortes internos grandes.

**Ruta B — Backend con el motor nativo de Deepnest, la web solo como cliente.**
Movería el cálculo pesado a un servicio (Node + addon compilado) con la web subiendo piezas y mostrando el resultado. Arrastra dos problemas: el de licencia de arriba (habría que pedirle permiso explícito al autor, o reimplementar el algoritmo desde la idea general sin copiar código), y que las dependencias son de 2016 (Electron 1.4, `node-gyp` viejo) — hay que portarlas para que compilen hoy. Esfuerzo y riesgo altos, sin ganancia clara sobre lo que ya ofrece `nest2D` en el backend actual.

**Ruta C — Motor propio (o de terceros) compilado a WebAssembly.**
Tomar la idea de Deepnest (Minkowski/NFP en C++) pero compilar a WASM con Emscripten, corriendo del lado del cliente con rendimiento cercano al nativo. Evita el problema de licencia y de infraestructura de servidor. Esfuerzo alto — no se justifica hoy, dado que F2/F7 ya tienen un motor server-side resuelto en `ADR-05`.

`SheetNest` no habilita ninguna ruta directa: es escritorio Windows, y su feature más fuerte (desdoblado 3D de chapa con FreeCAD) resuelve un problema que este proyecto no tiene — cartelería no desdobla chapa plegada, corta paneles planos y letras corpóreas.

---

## Cómo se relaciona con lo ya decidido

- **No cambia `ADR-05`.** El stack de nesting (`rectpack` + `nest2D`, ambos server-side en Celery) sigue siendo la elección correcta para F2 y F7. Esta investigación no encontró ningún motivo técnico o de licencia para moverlo al navegador.
- **Sí es relevante para la mención de "Deepnest" en la tabla de stack de `EPICA.md`.** Esa alternativa quedó anotada sin haberse investigado; ahora que se investigó, el hallazgo de la licencia dice que no es una alternativa segura para usar tal cual. Queda pendiente decidir si se le agrega una nota a esa línea de `EPICA.md` o si se deja este documento como la referencia cuando haga falta.
- **Es un insumo para S9-S10 (F7 / Hito 5), no una decisión bloqueante hoy.** Nadie tiene que actuar sobre esto en Sprint 0.

---

## Próximos pasos

- Si en algún momento se evalúa una previsualización de nesting del lado del cliente (fuera del alcance actual F0-F8), retomar este documento y arrancar por la Ruta A.
- Decidir si la mención de "Deepnest" en la tabla de stack de `EPICA.md` se corrige con una nota de licencia, o si alcanza con este documento como referencia.
- Ninguna acción requerida antes de S9-S10.
