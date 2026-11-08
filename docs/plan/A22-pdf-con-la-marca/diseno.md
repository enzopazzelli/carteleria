# A22 — El PDF del presupuesto con la marca de la empresa

**Estado:** aprobado por Enzo el 2026-11-08, sobre un boceto con sus datos reales. Es la parte de «logo, datos fiscales y formato de la empresa en el PDF» del sub-proyecto 4.4 (`B-13` del registro) que ya se puede hacer: lo que falta, los datos fiscales y el texto de condiciones, queda configurable.

## 1. Qué problema resuelve

El PDF que recibe el cliente sale hoy en blanco y negro, con un recuadro punteado donde iría el logo y sin ningún dato de la empresa. Quien lo recibe no ve de quién es ni cómo contactarla. Se quiere que salga con la marca de Anibal Dumit Megacarteles.

## 2. Lo que se decidió

- **El estilo:** la «banda» del boceto que eligió Enzo, con los colores de su logo: **negro** (`#0d0d0d`) y **naranja** (`#ff5d00`).
  - Arriba, el logo sobre blanco a la izquierda; a la derecha, una banda negra con el borde inclinado, «PRESUPUESTO» en naranja y el código en blanco, con una franja naranja debajo.
  - El cliente y las fechas en un recuadro gris con una marca naranja al costado.
  - El detalle con una línea naranja bajo el encabezado, y el total en un recuadro negro.
  - Un pie con una línea naranja y los datos de contacto.
- **El logo es `logoblanco.png`** (1080 × 1080, fondo transparente, letras negras y naranjas). Las versiones con fondo negro que también hay (`logo.png` de 204 px y `logo.jpg` de 500 px) son de baja resolución y no sirven para imprimir.
- **El logo y los datos de contacto no van a git.** El repositorio es público: tu WhatsApp, tu dirección y el logo quedarían a la vista de cualquiera. Se guardan en `backend/local/empresa/` (carpeta que git ya ignora, como la base de datos). Al armar el servidor real hay que copiar esa carpeta.
- **Sin esa carpeta, el PDF sale igual con el estilo nuevo,** pero sin logo y sin pie de contacto. Los tests no dependen de ella.
- **Los datos se escriben como los dio la empresa,** sin agregar tildes que su imagen no tiene.
- **Qué no cambia:** el PDF sigue mostrando solo el detalle y los importes que ve el cliente, sin costos ni márgenes. Los textos que escribe una persona se siguen escapando.

## 3. Qué hay en `backend/local/empresa/`

- `logo.png`: el logo (se recorta al contenido al leerlo).
- `datos.json`: `nombre`, `direccion`, `whatsapp`, `mail`, `web`, `instagram`, y opcionales `cuit` y `condiciones`. Lo que está vacío no aparece en el pie. Si hay `condiciones`, se imprime un bloque debajo del total.

## 4. Supuestos que hay que confirmar

| Supuesto | Por qué |
|---|---|
| El nombre que sale en el pie es «Anibal Dumit Megacarteles». | Es el que figura en su imagen de datos y en el logo. |
| La dirección sale en una sola línea: «Andres Chazarreta y Alejandro Aguado · Santiago del Estero · 4200». | Es la de su imagen, sin «Argentina». |
| No hay CUIT ni condiciones por ahora: no aparecen. | Enzo no los pasó. |
| Los colores son fijos del sistema, no configurables. | Son los de la marca; si cambian, es un cambio de código. |

## 5. Lo que no entra

- **El fotomontaje** (el diseño del cartel sobre la foto del local, que la empresa usa mucho): ya está en el plan como el sub-proyecto 3.2 (`ADR-03`), con su propio diseño. Cuando exista, el PDF tiene un lugar natural para mostrarlo: una segunda hoja con «Cómo quedaría».
- Datos fiscales (razón social, condición ante el IVA) y el texto de condiciones: se cargan cuando la empresa los pase.

## 6. Pasos propuestos

1. La empresa como datos: leer el logo y los datos desde `backend/local/empresa/`, con pruebas.
2. El PDF con la marca, sobre esos datos.
3. Mirarlo en pantalla con el presupuesto real y cerrar: documentos, registro, plan maestro y README.

Cada paso se pide con el ok de Enzo antes de seguir.
