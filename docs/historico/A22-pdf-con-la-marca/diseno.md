# A22 — El PDF del presupuesto con la marca de la empresa

**Estado:** construido el 2026-11-08, en la rama `feat/pdf-con-la-marca`. Enzo aprobó el boceto ese día. Cómo quedó, en §7. Es la parte de «logo, datos fiscales y formato de la empresa en el PDF» del sub-proyecto 4.4 (`B-13` del registro) que ya se puede hacer: lo que falta, los datos fiscales y el texto de condiciones, queda configurable.

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

| Registro | Supuesto | Por qué |
|---|---|---|
| `SUP-32` | El nombre que sale en el pie es «Anibal Dumit Megacarteles». | Es el que figura en su imagen de datos y en el logo. |
| `SUP-32` | La dirección sale en una sola línea: «Andres Chazarreta y Alejandro Aguado · Santiago del Estero · 4200». | Es la de su imagen, sin «Argentina». |
| `SUP-33` | No hay CUIT ni condiciones por ahora: no aparecen. | Enzo no los pasó. |
| `SUP-34` | Los colores son fijos del sistema, no configurables. | Son los de la marca; si cambian, es un cambio de código. |

## 5. Lo que no entra

- **El fotomontaje** (el diseño del cartel sobre la foto del local, que la empresa usa mucho): ya está en el plan como el sub-proyecto 3.2 (`ADR-03`), con su propio diseño. Cuando exista, el PDF tiene un lugar natural para mostrarlo: una segunda hoja con «Cómo quedaría».
- Datos fiscales (razón social, condición ante el IVA) y el texto de condiciones: se cargan cuando la empresa los pase.

## 6. Pasos propuestos

1. La empresa como datos: leer el logo y los datos desde `backend/local/empresa/`, con pruebas.
2. El PDF con la marca, sobre esos datos.
3. Mirarlo en pantalla con el presupuesto real y cerrar: documentos, registro, plan maestro y README.

Cada paso se pide con el ok de Enzo antes de seguir.

## 7. Cómo quedó

**Lo hecho,** en tres pasos, cada uno con el ok de Enzo antes de seguir:

1. **La empresa como datos** (`services/presupuesto/empresa.py`): lee el logo y los datos de contacto de `backend/local/empresa/`. El logo se recorta solo a su contenido. Si la carpeta no está, o un archivo está roto, el PDF sale igual, sin ese dato. Los archivos reales de Enzo están ahí, y sus imágenes originales de la raíz quedaron en el `.gitignore`.
2. **El PDF con la marca** (`pdf.py`): la banda negra inclinada con el logo sobre blanco, «PRESUPUESTO» en naranja y el código en blanco; el recuadro del cliente con la marca naranja al costado; el detalle con la línea naranja; el total en un recuadro negro; y el pie con los datos de contacto en cada hoja. De la segunda hoja en adelante, una banda finita con el código. Si la empresa cargó condiciones, un bloque debajo del total.
3. **El cierre.**

**Lo medido.** El servidor, 1312 pruebas (y las 3 fallas conocidas de antes). Se generó el PDF real del presupuesto del Parador, desde una copia de la base, con y sin la marca y con varias hojas, y se miró cada uno: sale como el boceto aprobado.

**Lo que cambió respecto de este diseño.**
- **La carpeta de la empresa es un valor de configuración** (`DIRECTORIO_EMPRESA`), como la carpeta temporal, y cada prueba la apunta a una carpeta vacía: ninguna prueba lee los datos reales.
- **Un PDF sin marca sale con el estilo nuevo** (la banda y los colores), no con el de antes; solo le faltan el logo y el pie. Sin logo pero con nombre, el nombre ocupa su lugar en la banda.
- **El recuadro del cliente tiene las esquinas casi rectas** (radio de 1,4 mm): con las del boceto, la barra naranja del costado se curvaba como un paréntesis.

**Lo que queda.**
- **Los datos fiscales** (razón social, CUIT, condición ante el IVA) y **el texto de condiciones** (forma de pago, plazo de entrega): se cargan en `datos.json` cuando la empresa los pase; el PDF ya los imprime.
- **Copiar `backend/local/empresa/` al servidor real** cuando exista (etapa 4): git no la lleva.
- **El fotomontaje,** con el diseño del cartel sobre la foto del local (3.2): el PDF tiene lugar para una hoja «Cómo quedaría».
- **Si cambia el nombre o el teléfono,** se edita `datos.json`; si cambian los colores de la marca, es un cambio de código.
