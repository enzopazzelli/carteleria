# A26 · Sacar lo que no va — plan de implementación

> **Para quien lo ejecute:** usar `superpowers:executing-plans` en esta sesión. Los pasos son casillas (`- [ ]`). **Enzo pidió pasos chicos con su visto bueno**: al terminar cada tarea, mostrar qué cambió y esperar el ok antes de la siguiente.

**Meta:** que la app entre directo sin login, que cada grupo elija **una** chapa sin comparar, y que el presupuesto no aparezca en ninguna pantalla. El recorrido termina en Chapas, con el DXF y el PDF.

**Diseño:** [`diseno.md`](diseno.md) (2026-11-18, a partir de las notas de la demo).

**Tecnología:** FastAPI + SQLAlchemy, React + TypeScript + Vitest. Pruebas con `pytest` (desde `backend/`) y `npm test` / `npm run build` (desde `frontend/`).

## Restricciones globales

- **Sin migración y sin escribir en la base.** Las tablas de usuarios, presupuestos y clientes quedan como están.
- **El servidor del presupuesto, de la comparación y de los usuarios queda montado y con sus pruebas** (diseño §2). Lo que se borra es código de la pantalla que quedó sin forma de llegar.
- Textos en castellano rioplatense. Sin valores nuevos en `REGISTRO.md`.
- Commits en la rama `feat/a26-sacar-lo-que-no-va`, **sin** línea `Co-Authored-By`.
- Pruebas de backend con los temporales en D: (el disco C: puede estar lleno): `python -m pytest -q --basetemp=D:/temp-pruebas/a26`.
- La base real no se toca. El recorrido en el navegador se hace contra una copia (`python scripts/copiar_base.py a26`, desde `backend/`); antes de levantar nada, mirar con `curl -m 3 localhost:8000/trabajos` y `localhost:5173` si hay algo de Enzo corriendo.

## Review Focus

1. **Un pedido que cambia datos sin el encabezado propio** sigue dando 403, aunque ya no haya sesión (Tarea 1, prueba guardiana).
2. **Crear un trabajo e importar un DXF sin sesión** funcionan y dejan `creado_por_id` vacío (Tarea 1).
3. **Cambiar la chapa a un grupo ya anidado**: la tarjeta dice «Falta volver a anidar» y Chapas avisa, como hoy (Tarea 2, recorrido de la Tarea 5).
4. **Un trabajo con todo anidado** dice «Listo para cortar» y lleva a Chapas, tenga o no un presupuesto viejo en la base (Tarea 3).
5. **Enlaces viejos** (`/entrar`, `/cuenta`, `/usuarios`, `/presupuestos`, `/trabajos/N/costeo`) no dejan una pantalla rota: llevan al inicio o a Chapas (Tareas 1 y 3).

---

## Estructura de archivos

| Archivo | Qué cambia |
|---|---|
| `backend/app/api/autenticacion.py` | Nueva dependencia `pedido_propio`: solo el encabezado en los pedidos que cambian datos |
| `backend/app/api/app.py` | Los grupos de rutas usan `pedido_propio` en lugar de `usuario_actual` |
| `backend/app/api/rutas_trabajos.py`, `rutas_importacion.py` | Sin `usuario_actual`: `creado_por_id` queda vacío |
| `backend/tests/test_todas_las_rutas_exigen_sesion.py` | Pasa a `test_todas_las_rutas_piden_el_encabezado.py` |
| `backend/app/pasos.py` (+ `rutas_inicio.py`, esquema) | Sin paso de presupuesto: con todo anidado, «Listo para cortar» → Chapas |
| `frontend/src/App.tsx`, `components/Barra.tsx` | Sin login, sin Presupuestos; título «Cartelería» |
| `frontend/src/api/client.ts` | Sin el aviso de sesión perdida (401) |
| `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx` | Elegir chapa en lugar de comparar |
| `frontend/src/routes/TrabajoWorkspace/WorkspaceLayout.tsx` | Sin la pestaña Costeo |
| `frontend/src/routes/Inicio.tsx`, `components/Tarjeta/*` | Sin presupuestos |
| `frontend/src/routes/TrabajoWorkspace/ChapasTab.tsx`, `historial.ts`, `AnidadoTab.tsx`, `components/ResumenAnidado.tsx` | Textos del corte en lugar del presupuesto |
| Se borran | `Entrar`, `MiCuenta`, `Usuarios`, `RutaProtegida`, `auth/`, `Presupuestos`, `CosteoTab` y lo que solo usaban ellos, con sus pruebas; `comparacionEnCurso.ts` y los ganchos de la comparación |

---

## Tarea 1 · El login

- [x] **Servidor.** En `autenticacion.py`, `pedido_propio(request)`: 403 «Pedido no permitido.» si el método cambia datos y falta `X-Cartel-Pedido`; nada más. `app.py` la pone en cada grupo de rutas en lugar de `usuario_actual`. `usuario_actual` y `exigir_permiso` quedan para las rutas de usuarios y presupuesto que ya los piden.
- [x] **Quién creó.** `crear_trabajo` y `confirmar_importacion` dejan de pedir `usuario_actual`; `creado_por_id` queda vacío.
- [x] **Guardiana.** `test_todas_las_rutas_exigen_sesion.py` → `test_todas_las_rutas_piden_el_encabezado.py`: toda ruta que cambia datos, sin el encabezado, da 403; y una ruta de trabajos sin cookie responde (no 401).
- [x] **Pruebas que esperaban 401** en rutas comunes: se ajustan. Las de `/acceso` y `/usuarios` quedan como están.
- [x] **Pantalla.** `App.tsx` sin `SesionProvider`, `RutaProtegida`, `/entrar`, `/cuenta`, `/usuarios`; esas tres direcciones llevan al inicio. `Barra.tsx` sin nombre, «Cerrar sesión» ni «Usuarios». `client.ts` sin `alPerderLaSesion`; el encabezado propio se sigue mandando.
- [x] Se borran `Entrar.tsx`, `MiCuenta.tsx`, `Usuarios.tsx`, `RutaProtegida.tsx`, `auth/` y sus pruebas, y lo de `api/` que solo usaban ellos.
- [x] **La aprobación del presupuesto sale acá y no en la Tarea 3:** era lo único del presupuesto que usaba la sesión (aprobar pide un usuario con permiso). Se borra `AprobacionSeccion.tsx` y se la saca del Costeo.
- [x] La guía del desarrollo nombra la guardiana nueva.
- [x] `pytest` completo, `npm test` y `npm run build` en verde. Commit: `feat(a26): la app entra directo, sin login`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 2 · Elegir la chapa del grupo

- [x] En `GruposTab.tsx`, cada grupo muestra su chapa por nombre (material, espesor y medida; «Sin chapa» si no tiene) y el botón «Elegir chapa» / «Cambiar chapa».
- [x] El botón abre `ListaDeFormatos` con `unaSola`, con la chapa actual tildada, y «Usar esta chapa» (deshabilitado sin una tildada) llama a `asignarFormato`. Cierra el panel al asignar.
- [x] Sale todo lo de comparar: motor, tiempo, criterio, progreso, tabla de resultados, retomar la última comparación. Se borran `comparacionEnCurso.ts` y los ganchos/llamadas de la comparación que queden sin uso.
- [x] `ResumenAnidado.tsx`: el enlace dice «Cambiar la chapa».
- [x] **Visto en el navegador** contra una copia: «Elegida: …», «Usar esta chapa» y «Cancelar» van **arriba** de la lista (el catálogo es largo y abajo no se veían).
- [x] **Queda sin uso, para la limpieza:** en `PiezasTab.tsx`, la lectura de `?seccionar=…&formato=…`, que armaba solo la comparación. Lo que no entra en la chapa del grupo lo sigue diciendo Piezas (`useASeccionar`) y el anidado («Estas piezas no entran en la chapa…»).
- [x] Pruebas de la pantalla: el texto de la chapa del grupo (con y sin chapa) en una función aparte con su prueba.
- [x] `npm test` y `npm run build` en verde. Commit: `feat(a26): cada grupo elige su chapa, sin comparar`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 3 · El presupuesto

- [x] **Servidor, `pasos.py`.** Sin el paso de presupuesto: si todo está anidado, frase «Listo para cortar» y destino `chapas`. `Destino` pierde `costeo`. `rutas_inicio.py` y el esquema de pasos dejan de mandar el paso `presupuesto` y el presupuesto de la tarjeta; el resumen del inicio deja de mandar los presupuestos. Pruebas de `test_pasos.py` y `test_rutas_inicio.py` ajustadas.
- [x] **Pantalla.** Barra sin «Presupuestos»; `/presupuestos` lleva al inicio. `WorkspaceLayout` sin «Costeo»; `/trabajos/N/costeo` lleva a Chapas. Inicio sin «Últimos presupuestos». Tarjeta sin el paso ni el renglón del presupuesto.
- [x] **Textos.** `historial.ts` («Elegida para cortar», «Vista previa; todavía no elegida para cortar» y los que nombran el presupuesto), `AnidadoTab.tsx` (el aviso al borrar el definitivo), `ResumenAnidado.tsx`. Revisar con `grep -rni presupuest frontend/src` que no quede ningún texto visible.
- [x] `ChapasTab.tsx`: sale el aviso de cambio de cantidad de chapas que dependía de los presupuestos.
- [x] Se borran `Presupuestos.tsx`, `CosteoTab.tsx`, `components/Presupuestos/`, las secciones de cliente y aprobación, el buscador de catálogo del costeo y lo de `api/` y `hooks/` que solo usaban ellos, con sus pruebas.
- [x] **El PDF del diseño anidado tampoco nombra el presupuesto:** sale el código y el cliente del encabezado, y el renglón de cada bloque dice «anidado #N, el definitivo» / «el más reciente: el definitivo (#M) es de antes de…» / «el más reciente (ninguno marcado como definitivo)».
- [x] **Los avisos de anidado vencido** (`anidado_que_cuenta`, los ven Chapas, Anidado y el PDF) dicen «anidá de nuevo antes de cortar»; sin chapa: «Este grupo no tiene chapa: elegila en la pestaña Grupos».
- [x] En Materiales, la revisión de la planilla pierde la nota de los presupuestos ya armados. Las invalidaciones de la caché del costeo salen de los ganchos.
- [x] **Visto en el navegador** contra una copia: inicio, enlaces viejos, Chapas, Anidado y Materiales sin «presupuesto» ni «costeo»; PDF del Parador sin presupuesto.
- [x] `pytest` completo, `npm test` y `npm run build` en verde. Commit: `feat(a26): sin presupuesto: el recorrido termina en Chapas`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 4 · Documentación

- [x] `README.md`, «En qué estamos»: el rumbo nuevo (sin login, sin presupuesto, sin despliegue; producto final DXF + PDF; se instala en cada PC).
- [x] `PLAN-MAESTRO.md §1`: las decisiones del 2026-11-18, que reemplazan el ciclo de cotización y el servidor.
- [x] `docs/plan/1.1-servidor-y-login/` pasa entera a `docs/historico/` (ya no se sigue), actualizando las rutas que la citan.
- [x] `docs/guias/GUIA-DEL-USUARIO.html`: sin entrar, sin comparar, sin presupuesto; cómo elegir la chapa. `GUIA-PROBAR-EL-SISTEMA.md` y `MANUAL-USUARIOS.md`, lo mismo si lo nombran.
- [x] `BITACORA.md`: la entrada de la demo y de este pedido.
- [x] También: `MAPA-DEL-PROYECTO.md §0`, `CONVENCIONES.md` (el ejemplo de carpeta de plan) y la guía del usuario con «Abrir el sistema» en lugar de «Entrar y tu cuenta». Sin enlaces rotos en lo tocado.
- [x] Commit: `docs(a26): el rumbo nuevo después de la demo`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 5 · Verificar y cerrar

- [ ] Recorrido en Chrome sin ventana contra una copia de la base: entra directo; importar el Complejo; armar el grupo; elegir la chapa; anidar; Chapas con DXF y PDF; cambiar la chapa y ver «Falta volver a anidar»; los enlaces viejos del Review Focus.
- [ ] PR a `main` con el resumen y las capturas. Después del ok de Enzo, fusionar, pasar la carpeta a `docs/historico/` y borrar la rama.
