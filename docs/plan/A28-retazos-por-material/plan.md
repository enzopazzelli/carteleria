# A28 · Retazos agrupados por material — plan de implementación

> **Para quien lo ejecute:** `superpowers:executing-plans`, en esta sesión. **Enzo pidió pasos chicos con su visto bueno**: al terminar cada tarea, mostrar qué cambió y esperar el ok.

**Meta:** una vista «Retazos» en Materiales con todos los retazos juntos, por material y medida, con sus cuentas.

**Diseño:** [`diseno.md`](diseno.md). **Solo pantalla:** sin servidor, sin migración.

## Restricciones

- Pruebas con `npm test` y `npm run build` (desde `frontend/`).
- Textos en castellano rioplatense. Commits en la rama `feat/a28-retazos-por-material`, **sin** `Co-Authored-By`.
- El recorrido en el navegador, contra una copia de la base (`python scripts/copiar_base.py a28`, desde `backend/`); antes, mirar que el 8000 y el 5173 estén libres.

## Review Focus

1. **Medidas iguales juntas**, aunque estén giradas (600 × 400 y 400 × 600).
2. **Retazos sueltos** (de una chapa sin código) también aparecen, bajo su material.
3. **Por defecto solo los disponibles**; la casilla suma usados, en uso y quitados.
4. **Un material sin retazos no aparece.**
5. **Las cuentas** (disponibles y m²) cuadran con las de la otra vista.

---

## Tarea 1 · El armado de los grupos

- [x] `retazosPorMaterial(catalogo, { todos })` en `components/Materiales/retazos.ts`: devuelve, por material con espesor, sus medidas (del lado más largo × el más corto, de la más grande a la más chica) con sus retazos, y las cuentas por medida, por material y total.
- [x] Pruebas: una por punto del Review Focus, más el orden y el material con dos espesores.
- [x] `npm test` y `npm run build` en verde. Commit: `feat(a28): retazos agrupados por material y medida`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 2 · La vista

- [ ] `RetazosPorMaterial.tsx`: la cuenta de arriba, el buscador, la casilla, un bloque por material con sus medidas abribles y el enlace al material.
- [ ] `routes/Materiales.tsx`: los botones «Materiales» / «Retazos»; el enlace de un material vuelve a «Materiales» con ese material elegido.
- [ ] `npm test` y `npm run build` en verde. Commit: `feat(a28): la vista Retazos en Materiales`.
- [ ] **Pausa: mostrar a Enzo y esperar el ok.**

## Tarea 3 · Verificar, documentar y cerrar

- [ ] Recorrido en Chrome sin ventana contra una copia: guardar un sobrante como retazo, ver «Retazos», abrir una medida, la casilla, el buscador y el enlace al material.
- [ ] Guía del usuario, README, entregas hechas y bitácora.
- [ ] PR a `main`. Con el ok de Enzo, fusionar, pasar la carpeta a `docs/historico/` y borrar la rama.
