# A27 · Deshacer en el ajuste del anidado — plan de implementación

> **Para quien lo ejecute:** usar `superpowers:executing-plans` en esta sesión. Los pasos son casillas (`- [ ]`). **Enzo pidió pasos chicos con su visto bueno**: al terminar cada tarea, mostrar qué cambió y esperar el ok antes de la siguiente.

**Meta:** que en Chapas se pueda deshacer, uno por uno, mover, girar y pasar una pieza de chapa (con el reacomodo), y que la pieza vuelva exactamente a donde estaba.

**Diseño:** [`diseno.md`](diseno.md) (2026-11-18).

**Tecnología:** FastAPI + SQLAlchemy + Alembic, React + TypeScript + Vitest. Pruebas con `pytest` (desde `backend/`) y `npm test` / `npm run build` (desde `frontend/`).

## Restricciones globales

- **Una migración**, generada con Alembic sobre la cabeza actual (`9d3b6a1c7e45`). Tiene que bajar y subir en SQLite y en PostgreSQL (`tests/postgres`).
- **Sin números mágicos:** los 20 pasos son un `PAR` nuevo en `REGISTRO.md` y una constante en `app/config.py`.
- Las rutas de mover, girar y pasar **responden igual que hoy**; solo anotan un paso antes.
- Textos en castellano rioplatense.
- Commits en la rama `feat/a27-deshacer-en-el-ajuste`, **sin** línea `Co-Authored-By`.
- Pruebas de backend con los temporales en D:: `python -m pytest -q --basetemp=D:/temp-pruebas/a27`.
- La base real no se toca. El recorrido se hace contra una copia (`python scripts/copiar_base.py a27`, desde `backend/`); antes de levantar nada, mirar si el 8000 y el 5173 están libres.

## Review Focus

1. **Pasar una pieza a una chapa nueva y deshacer:** la chapa nueva se va y la pieza vuelve a su lugar exacto (Tarea 2).
2. **Pasar la última pieza de una chapa (que se quita) y deshacer:** la chapa vuelve, con las piezas descartadas que tenía (Tarea 2).
3. **Reacomodo y deshacer:** toda la chapa de destino vuelve como estaba (Tarea 2).
4. **Una vuelta de rueda** (muchos giros de la misma pieza) se deshace de una vez (Tarea 1 y 2).
5. **El paso 21** borra el más viejo (Tarea 1).
6. **Un cambio que falla no anota paso** (Tarea 2).
7. **Borrar el anidado** borra sus pasos (Tarea 1).

---

## Estructura de archivos

| Archivo | Qué cambia |
|---|---|
| `backend/app/modelos/trabajo.py` | Modelo `PasoDelAjuste` y la relación desde `EjecucionNesting` |
| `backend/alembic/versions/<nueva>_pasos_del_ajuste.py` | La tabla |
| `backend/app/config.py`, `docs/REGISTRO.md` | `PASOS_PARA_DESHACER` = 20 (`PAR-70`) |
| `backend/app/services/nesting/deshacer.py` | Nuevo: foto, anotar, deshacer, estado |
| `backend/app/api/rutas_ajuste.py` | Anotar en mover/girar y pasar; `GET`/`POST /ejecuciones/{id}/deshacer`; sale el deshacer del reacomodo en memoria |
| `backend/app/api/esquemas_nesting.py` | `DeshacerLeer` |
| `frontend/src/api/nesting.ts`, `hooks/useNesting.ts` | Pedir el estado y deshacer; refrescar el estado después de cada cambio |
| `frontend/src/routes/TrabajoWorkspace/ChapasTab.tsx` | El botón, Ctrl+Z, el aviso del reacomodo con el general |
| `frontend/src/components/Chapas/ChapaGrande.tsx` | Borrar las marcas rojas después de deshacer |

---

## Tarea 1 · La tabla y el servicio

- [x] `PasoDelAjuste` en `modelos/trabajo.py` (`pasos_del_ajuste`: `id`, `ejecucion_id` con `ondelete="CASCADE"`, `creado_en`, `tipo`, `pieza`, `descripcion`, `foto` JSON) y `EjecucionNesting.pasos_del_ajuste` con `cascade="all, delete-orphan"`, ordenados por `id`.
- [x] La migración con Alembic sobre `9d3b6a1c7e45`; probar `upgrade` y `downgrade`.
- [x] `PAR-70` en `REGISTRO.md` y `config.PASOS_PARA_DESHACER`.
- [x] `services/nesting/deshacer.py`: `foto_de(ejecucion)`, `anotar(sesion, ejecucion, tipo, pieza, descripcion)` (no anota si el último es `girar` de la misma pieza; borra el más viejo pasado el límite), `deshacer(sesion, ejecucion)` (pone la foto y borra el paso; error si no hay) y `estado(ejecucion)` (`cuantos`, `ultimo`).
- [x] Pruebas: anotar y deshacer vuelve exacto; los giros seguidos son uno y uno de otra pieza no; el límite borra el más viejo; deshacer sin pasos da error; borrar el anidado borra los pasos; la migración sube y baja (también en `tests/postgres`).
- [x] `pytest` completo en verde. Commit: `feat(a27): los pasos del ajuste, en la base`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 2 · Las rutas

- [x] `ajustar_colocacion` anota `mover` o `girar` (según qué cambió) antes de tocar; `pasar_a_otra_chapa` anota `pasar` («a la chapa N» o «a una chapa nueva») después de validar y antes de tocar, y no anota si falla.
- [x] `GET /ejecuciones/{id}/deshacer` y `POST /ejecuciones/{id}/deshacer` (409 si no hay nada o si se está anidando el grupo).
- [x] Sale `POST /ejecuciones/{id}/deshacer-reacomodo`, `_para_deshacer`, `_olvidar_para_deshacer` y `puede_deshacer`; `_sigue_igual` y la foto del reacomodo para ese control se quedan.
- [x] Pruebas de la API, una por punto del Review Focus, más: mover y deshacer; girar con la rueda (varios PATCH) y deshacer una vez.
- [x] `pytest` completo en verde. Commit: `feat(a27): deshacer mover, girar y pasar de chapa`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 3 · La pantalla

- [x] `api/nesting.ts`: `estadoDeshacer`, `deshacer`. `hooks/useNesting.ts`: `useDeshacer` (consulta) y `useDeshacerUltimo` (mutación); `useAjustarColocacion` y `useMoverAOtraChapa` refrescan `["deshacer", id]`. Sale `useDeshacerReacomodo`.
- [x] `ChapasTab.tsx`: el botón arriba, al lado de «Descargar PDF»; Ctrl+Z con una función aparte (`esDeshacer(evento)`, que no actúa dentro de un campo de texto) y su prueba; el aviso del reacomodo usa el general.
- [x] `ChapaGrande.tsx`: las marcas rojas se borran después de deshacer.
- [x] `npm test` y `npm run build` en verde. Commit: `feat(a27): el botón Deshacer en Chapas`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 4 · Verificar, documentar y cerrar

- [ ] Recorrido en Chrome sin ventana contra una copia: pasar una pieza a otra chapa y deshacer (vuelve a su lugar); a una chapa nueva y deshacer; girar con la rueda y deshacer de una vez; Ctrl+Z; el botón deshabilitado sin pasos.
- [ ] Guía del usuario (5.5 Chapas y «Lo que todavía no hace»), README («En qué estamos»), bitácora.
- [ ] PR a `main`. Con el ok de Enzo, fusionar, pasar la carpeta a `docs/historico/` y borrar la rama.
- [ ] Antes de usarla con la base real: **respaldo** (la migración lo hace sola al arrancar, igual conviene uno a mano).
