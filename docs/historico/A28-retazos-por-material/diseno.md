# A28 · Retazos agrupados por material — diseño

> **Origen:** la demo en la cartelería del 2026-11-18. El cliente pidió «agrupar los retazos y poder verlos agrupados por material para saber» qué hay.
>
> **Fecha:** 2026-11-18 · **Rama:** `feat/a28-retazos-por-material` · **Plan:** [`plan.md`](plan.md)

---

## 1. El problema

Hoy los retazos se ven **solo adentro del detalle de cada material** (A21): hay que ir material por material para saber qué sobrante hay. El cliente quiere ver **todos juntos**, separados por material, y los de la misma medida contados juntos.

## 2. Qué se hace

En **Materiales**, arriba, dos vistas: **«Materiales»** (la de siempre) y **«Retazos»** (nueva).

La vista de Retazos:

```
Retazos · 7 disponibles · 3,2 m²                    [Buscar material…]  [ ] Mostrar también usados y quitados

MDF 5 mm · 4 retazos disponibles · 1,9 m²
   1830 × 1200 mm      2 disponibles
        Sobrante de Complejo MB, chapa 2 · disponible
        Sobrante de Parador, chapa 1 · disponible
   600 × 400 mm        2 disponibles
        …
Chapa negra cal. 18 · 3 retazos disponibles · 1,3 m²
   …
```

- **Un grupo por material** (con su espesor), ordenados por nombre. Un material sin retazos no aparece.
- **Dentro de cada material, las medidas iguales juntas**, con cuántas hay, de la más grande a la más chica. Cada medida se abre y lista sus retazos: de dónde salió y en qué anda (disponible, en uso, usado), con las mismas palabras que ya usa el detalle del material.
- **Arriba del todo y en cada material**, la cuenta: «N disponibles · X m²».
- **Por defecto solo los disponibles** (con los que se cuenta). Una casilla muestra también los usados, los que están en uso y los quitados.
- **Un buscador** por nombre de material, como el de la otra vista.
- **El nombre del material es un enlace** que abre ese material en la vista «Materiales», donde se pueden agregar o quitar retazos. **La vista nueva solo se mira**: no cambia nada.

## 3. Cómo

- **Sin cambios en el servidor ni en la base.** El catálogo (`GET /materiales/catalogo`) ya trae, por medida, todos sus retazos con su estado y de dónde salieron, y los retazos que van sueltos como una medida más.
- Una función pura nueva en `components/Materiales/retazos.ts`, `retazosPorMaterial(catalogo, {todos})`, que arma el árbol material → medida → retazos con sus cuentas. Es lo que se prueba.
- Un componente nuevo, `components/Materiales/RetazosPorMaterial.tsx`, y los botones de las dos vistas en `routes/Materiales.tsx`.

## 4. Decisiones mías, para corregir

1. **Una vista aparte** en Materiales (no una columna más en la lista de materiales).
2. **Solo se mira**: quitar y agregar retazos sigue en el detalle del material.
3. **Por defecto solo los disponibles**; los demás, con la casilla.
4. **Medidas iguales juntas** (mismo ancho y alto, sin importar el giro: 600 × 400 y 400 × 600 son la misma).
5. **La cuenta del inicio** («N retazos») no cambia.

## 5. Lo que no cambia

- Guardar un sobrante como retazo, quitarlo y los estados (A21).
- Cómo se usan los retazos al elegir la chapa de un grupo.
