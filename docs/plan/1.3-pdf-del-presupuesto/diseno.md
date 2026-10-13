# 1.3 · PDF del presupuesto — diseño

> **Estado:** **construido el 2026-10-12,** en la rama `worktree-pdf-presupuesto`, con el plan de [`plan.md`](plan.md). Lo que se apartó está al final de ese plan, en «Desvíos». Se trabajó en una carpeta aparte del repositorio, en paralelo a la lectura del DXF (2.1a), que no tocó ninguno de estos archivos.
>
> **Cambio del 2026-10-13: el PDF pasó de WeasyPrint a ReportLab.** Lo decidió Enzo antes de fusionar, para no depender de MSYS2 en su máquina ni de Pango en el servidor, y quedó construido ese mismo día. Esta página ya describe ReportLab; lo que se apartó del plan está en sus «Desvíos». Enzo pidió además una pantalla para retocar el presupuesto con el PDF real al lado: va aparte, con su propio diseño.
>
> **De dónde sale.** Es el sub-proyecto 1.3 de [`PLAN-MAESTRO.md §6`](../PLAN-MAESTRO.md), «PDF mínimo» (`CART-309`). Al diseñarlo, Enzo pidió que antes de sacar el PDF se puedan cambiar el texto y el precio de cada ítem y el total, así que el alcance creció: toma de 1.2 la edición del presupuesto (§3).
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Los números del ejemplo del §5 son inventados, para mostrar la cuenta.

---

## 1. Para qué

Que un presupuesto se baje como un PDF listo para mandarle al cliente, con lo que el cliente tiene que ver y nada de lo interno, y que antes de bajarlo se puedan ajustar el texto y el precio de cada ítem y el total.

**Criterio de éxito:** desde la pestaña Costeo, con un presupuesto completo, se cambia el texto de un ítem, se escribe un precio a mano, se fija el total, y el PDF que se descarga muestra exactamente esos ítems y ese total. En el PDF no aparece ningún costo interno ni el margen.

---

## 2. Punto de partida

- El presupuesto existe con su cliente, código, días de validez (`PAR-11`), moneda, margen (`PAR-12`) e IVA (`PAR-13`), y sus líneas de costo por rubro (`CART-301` a `CART-308`).
- Las líneas guardan **costos**. El precio existe solo como total: `_calcular_totales`, en `backend/app/api/rutas_presupuesto.py`, suma los costos, aplica el margen y el IVA y redondea una vez al final (`PAR-16`). No hay precio por línea.
- En la pestaña Costeo se puede agregar una línea a mano, corregir el valor de una línea (el override de `ADR-07`) y cargar margen e IVA. No se puede editar ni borrar una línea ya cargada, ni cambiar la validez, aunque el servidor ya lo permite. Cambiar el cliente de un presupuesto no lo permite ni el servidor.
- Nada en el sistema genera documentos.

---

## 3. Alcance

**Entra**, en tres tramos que se construyen en este orden. Cada uno deja algo andando:

1. **Reglas y datos.** Qué ve el cliente en cada ítem, calculado en un solo lugar (§5, §6, §7). Sin pantalla.
2. **El PDF.** La hoja, la ruta que lo devuelve y el enlace para descargarlo (§9).
3. **La edición en Costeo.** Texto y precio por ítem, total fijado, editar y borrar líneas, validez y cliente (§8).

**No entra:**

| Tema | Por qué | Dónde va |
|---|---|---|
| La lista de presupuestos fuera del trabajo, y presupuestos sin trabajo en pantalla | Es el resto de 1.2. Acá se edita desde Costeo, que ya existe | 1.2 |
| Aprobación y envío por mail | Son otros sub-proyectos | 1.4 y 1.5 |
| Guardar el PDF generado | Se genera cada vez que se pide. El congelado llega con el envío | 1.5 |
| Logo, datos fiscales y formato de la empresa (`B-13`) | Dependen de la empresa. Va un formato propio, con el logo como espacio reservado | 4.4 |
| Juntar varias líneas de costo en un solo ítem del cliente | No se pidió. Con texto y precio por ítem alcanza para esta etapa | Se anota para 2.3 |
| Registrar quién cambió un texto, un precio o el total | No hay usuarios todavía | 1.1 y 2.5 |
| Documento interno, plano de corte adentro, fotomontaje | Ya los postergaba el plan maestro | 2.3 y 3.2 |

---

## 4. Decisiones

De Enzo, el 2026-10-12:

| Decisión | Valor | Registro |
|---|---|---|
| Qué ve el cliente en el cuerpo | **Cada ítem con su importe**, más subtotal, IVA y total | — |
| Con qué herramienta se genera | **ReportLab**, con la hoja dibujada en código (2026-10-13). Reemplazó a WeasyPrint, que es la que nombra `ADR-05`: usaba una plantilla HTML, pero necesitaba Pango, y en Windows eso pedía instalar MSYS2 | Cierra `D-16` |
| Cómo se prueba en Windows | Con lo que instala `pip`, como el resto: ReportLab no necesita nada más (§10). Sin Docker | — |
| Presupuesto incompleto | **No se genera el PDF** y se dice qué falta (§5.4) | — |
| Qué se puede cambiar antes de sacarlo | El texto y el precio de cada ítem, y el total final | — |
| Qué pasa con los ítems al fijar el total | **Se ajustan todos**, también los que tienen precio escrito a mano | — |

De este diseño, para que Enzo las corrija si no son:

| Decisión | Valor | Por qué |
|---|---|---|
| Los precios por ítem | Van sin IVA | El documento muestra subtotal, IVA y total por separado |
| El total fijado | Es el número final, con IVA | Es el que se quiere redondear |
| La fecha del presupuesto | El día en que se genera el PDF. «Válido hasta» es esa fecha más los días de `PAR-11` | Hoy no hay fecha de emisión. Cuando exista el envío (1.5), la fecha queda congelada ahí |
| Un precio a mano en una línea sin costo | No alcanza: la línea sigue contando como incompleta | Sin costo no se conoce el margen. El override de `ADR-07` sigue siendo la forma de completar un costo (`D-18`) |
| Lo que se escribe a mano | Nunca se pisa. El ajuste por el total fijado se calcula cada vez | Mismo criterio que el override: al quitar el total fijado, cada precio vuelve a lo que se escribió |
| Las pruebas que generan un PDF | Corren en cualquier máquina, sin saltear ninguna | Con ReportLab no hay bibliotecas del sistema que puedan faltar: Vale no tiene que instalar nada aparte para correr la suite |

---

## 5. Reglas de precio

### 5.1 La cuenta

1. **Precio base de un ítem.** Si tiene precio escrito a mano, es ese. Si no, es su costo más el margen (`PAR-12`). El costo es el valor efectivo de la línea: el override si lo hay, el calculado si no.
2. **Sin total fijado**, el subtotal es la suma de los precios base y el total es el subtotal más el IVA (`PAR-13`).
3. **Con total fijado**, el total es ese número. De ahí sale el subtotal, y todos los ítems se multiplican por el mismo factor para que sumen ese subtotal.
4. **El costo interno nunca cambia** por nada de esto.

### 5.2 Ejemplo

Cuatro líneas, margen del 30 % y un precio escrito a mano (Instalación, 150.000). La tercera columna fija el total en 1.400.000.

| Ítem | Costo interno | Precio base | Con el total fijado |
|---|---|---|---|
| Chapa | 400.000,00 | 520.000,00 (costo más margen) | 516.883,92 |
| Mano de obra | 300.000,00 | 390.000,00 (costo más margen) | 387.662,95 |
| Flete | 80.000,00 | 104.000,00 (costo más margen) | 103.376,79 |
| Instalación | 120.000,00 | 150.000,00 (a mano) | 149.101,13 |
| **Subtotal** | 900.000,00 | 1.164.000,00 | 1.157.024,79 |
| IVA | | 244.440,00 | 242.975,21 |
| **Total** | | 1.408.440,00 | **1.400.000,00** |
| Margen resultante | | 29,33 % | 28,56 % |

El factor es 0,994008. Al redondear cada ítem la suma da un centavo de más, y se lo resta la Chapa, que es el ítem más grande.

### 5.3 Redondeo

Sigue el criterio de `CART-307`: se redondea una sola vez, al final, con la precisión de `PAR-16`.

- **Total:** el fijado, o la suma de precios base más IVA, redondeada.
- **Subtotal:** con total fijado, el total dividido por uno más la alícuota, redondeado. Sin total fijado, la suma de precios base, redondeada.
- **IVA:** total menos subtotal. Así el documento siempre suma, aunque ese número pueda diferir en un centavo de la alícuota aplicada al subtotal.
- **Ítems:** cada precio base por el factor, redondeado. Si la suma no da el subtotal, la diferencia de centavos va al ítem de mayor importe; si hay empate, al primero.

Sin precios a mano y sin total fijado, el subtotal y el total dan lo mismo que hoy.

### 5.4 Qué cuenta como incompleto

Con cualquiera de estos casos no se genera el PDF, y la respuesta dice cuál:

- No hay ninguna línea.
- Una línea no tiene costo, ni calculado ni por override.
- Una línea está en una moneda distinta de la del presupuesto.
- Falta el IVA.
- Falta el margen y algún ítem no tiene precio a mano.
- Hay total fijado y la suma de los precios base es cero: no hay cómo repartir.

Es la misma definición que el plan maestro fija para mandar a aprobar (§6 de `PLAN-MAESTRO.md`), más lo que agrega mostrar un precio por ítem.

### 5.5 Lo que se ve adentro y no sale en el PDF

Al fijar el total, el margen deja de ser un dato que se carga y pasa a ser un resultado. La pantalla muestra el **margen resultante** (subtotal menos costo total, en plata y en porcentaje) y avisa si el subtotal queda por debajo del costo.

---

## 6. Datos

Una sola migración de Alembic, con tres columnas que admiten vacío:

| Columna | Qué guarda | Vacío significa |
|---|---|---|
| `lineas_costo.texto_cliente` | El texto del ítem para el cliente | Se usa la descripción de la línea |
| `lineas_costo.precio_cliente` | El precio a mano, sin IVA, en la moneda del presupuesto | Se usa costo más margen |
| `presupuestos.total_fijado` | El total final, con IVA | El total es la suma de los ítems más IVA |

- **Duplicar un presupuesto** copia las tres. Esa ruta enumera los campos uno por uno, y ya una vez se quedó atrás con las líneas.
- **Recalcular materiales** no las toca: actualiza el costo de las líneas de material y deja el texto y el precio a mano como están.

---

## 7. Servidor

Una carpeta nueva, `backend/app/services/presupuesto/`, con tres piezas. Cada una se prueba sola.

| Pieza | Qué hace | De qué depende |
|---|---|---|
| `totales.py` | La cuenta del §5. Es `_calcular_totales`, que se muda desde el archivo de rutas y se amplía. Devuelve los ítems (costo, precio base, de dónde sale, precio final), subtotal, IVA, total, margen resultante, los avisos y la lista de lo que falta | Los modelos |
| `documento.py` | Arma el **documento del cliente**: código, cliente, fecha, válido hasta, moneda, ítems con texto e importe, subtotal, IVA y total. No tiene ningún campo de costo ni de margen: el PDF no puede mostrar lo que el documento no trae. Si falta algo, no arma nada y devuelve la lista | `totales.py` |
| `pdf.py` y `fuentes/` | Dibuja el documento en la hoja con ReportLab: encabezado, cliente, tabla de ítems, totales y «Página X de Y». Escapa el texto que escribe una persona, porque ReportLab lee etiquetas dentro del texto: sin eso, un «<b>» en el nombre del cliente pondría negrita | `documento.py` |

**Rutas:**

| Ruta | Qué cambia |
|---|---|
| `PATCH /lineas-costo/{id}/cliente` | Nueva. Guarda el texto y el precio para el cliente de una línea de cualquier rubro, también de material. Un valor nulo lo limpia |
| `PATCH /presupuestos/{id}` | Suma el total fijado y el cambio de cliente |
| `GET /presupuestos/{id}/pdf` | Nueva. Devuelve el PDF, con el código como nombre de archivo. Si está incompleto responde 409 con la lista de lo que falta |
| `GET /presupuestos/{id}/totales` y `/desglose` | Mismos campos que hoy, calculados con la cuenta nueva. El desglose suma los ítems del cliente, el margen resultante y la lista de lo que falta: es lo que lee la pantalla |

Un importe que no es un número, o que es negativo, se rechaza al entrar con un mensaje, no con un error del servidor.

---

## 8. Pantalla

Una sección nueva en la pestaña Costeo, **Presupuesto para el cliente**, en su propio archivo: `CosteoTab.tsx` ya tiene dos componentes adentro.

```
Presupuesto para el cliente                         Válido por [ n ] días
Cliente: [Farmacia Central ▾]

Texto para el cliente               Costo    Precio base      En el presupuesto
[Chapa negra cal. 20 — 1220×2440]   400.000   520.000 calc.    516.883,92
[Mano de obra — armado          ]   300.000   390.000 calc.    387.662,95
[Flete                          ]    80.000   104.000 calc.    103.376,79
[Instalación                    ]   120.000  [150.000] a mano  149.101,13

Total final: [1.400.000] fijado · quitar        Margen resultante: 28,56 %
Subtotal 1.157.024,79 · IVA 242.975,21

[ Descargar PDF ]
```

- Cada campo se guarda al salir de él, igual que hoy el margen y el IVA.
- Un precio a mano y el total fijado tienen su «quitar», que vuelve al valor calculado.
- La columna «En el presupuesto» es lo que va a leer el cliente. Coincide con el precio base mientras no haya total fijado.
- Si está incompleto, el botón queda apagado y arriba aparece la lista de lo que falta.
- En la sección de líneas que ya existe se suma editar y borrar las líneas cargadas a mano.
- Leer un importe escrito por una persona («1.400.000», «1400000,50») y mostrarlo con formato de pesos va en funciones aparte, con sus pruebas, como `cargaDxf.ts`.

---

## 9. El PDF

- **Hoja:** A4. Encabezado con el título, el código y el espacio reservado para el logo; cliente y contacto; fecha y «válido hasta»; la tabla de ítems con su importe; subtotal, IVA y total; número de página al pie.
- **El espacio del logo** se dibuja como un recuadro vacío a la vista. Deja claro que el formato es provisorio hasta 4.4.
- **Fecha:** la del día en que se genera, en hora de Argentina (§4).
- **Importes:** con el formato de la moneda del presupuesto (`PAR-14`).
- **Tipografía:** una de licencia libre, guardada en el repo junto al código que dibuja la hoja. El servidor no tiene las de Windows, y así el PDF sale igual en los dos lados.
- **Nombre del archivo:** el código del presupuesto.
- **Cuánto tarda:** 0,01 s una hoja y 0,04 s cuatro, medido en la máquina de Enzo (con WeasyPrint era alrededor de un segundo). Se genera dentro del pedido, sin cola.

---

## 10. Instalación

| Dónde | Qué hace falta |
|---|---|
| Dependencias de Python | `reportlab`. En las de desarrollo, `pypdf`, para leer el texto del PDF en las pruebas |
| Windows, para desarrollar | Nada aparte |
| GitHub, que corre las pruebas en Linux | Nada aparte |
| El servidor | Nada aparte |

Probado el 2026-10-13 en la máquina de Enzo: con ReportLab 4.4.4 la suite entera del backend pasa sin la variable que usaba WeasyPrint para encontrar Pango. Lo que se instaló para WeasyPrint el 2026-10-12 (MSYS2 en `D:\msys64` y la variable `WEASYPRINT_DLL_DIRECTORIES`) ya no hace falta.

---

## 11. Cómo se valida

- **La cuenta:** cada fila del ejemplo del §5.2 y cada caso del §5.4, como prueba. Y que sin precios a mano ni total fijado los totales den lo mismo que hoy.
- **El documento:** que no tenga forma de llevar un costo o un margen.
- **El PDF, de punta a punta:** se pide por la ruta, se lee su texto y se comprueba que están los ítems y el total, y que **no** están el costo total ni el margen. Corre en la máquina de Enzo y en GitHub.
- **La pantalla:** las funciones que leen y muestran importes, con sus pruebas. El recorrido completo lo hace Enzo sobre un presupuesto suyo: cambia un texto, escribe un precio, fija el total, descarga el PDF y lo mira.

---

## 12. Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| La otra rama en curso (la lectura del DXF) también agrega una migración | Al fusionar la segunda, Alembic encuentra dos puntas | La que se fusiona segunda encadena su migración detrás de la otra. Es una línea |
| Un total fijado mal escrito deja el precio por debajo del costo | Se presupuesta a pérdida sin notarlo | La pantalla muestra el margen resultante y avisa (§5.5) |
| El formato real de la empresa (`B-13`) pide cosas que la hoja no tiene | Hay que cambiar cómo se dibuja la hoja | Está en `pdf.py`, separado de la cuenta y del documento, y se cambia en 4.4 sin tocar lo demás. Es código y no HTML: lo cambia quien programa. Enzo lo aceptó al elegir ReportLab |
| Con el motor sin conectar, una línea de material no tiene costo | No sale el PDF de un presupuesto con chapa | Es consecuencia aceptada del plan maestro (§10). El override de `ADR-07` la completa mientras `D-18` siga con su valor por defecto |
| El PDF se ve distinto en el servidor | Sorpresa en la etapa 4 | La tipografía va en el repo y las pruebas corren en Linux desde el primer día |

---

## 13. Qué cambia en otros documentos

Al construir, no antes:

- `REGISTRO.md`: se cierra `D-16` con ReportLab (primero se había cerrado con WeasyPrint), y se dan de alta las decisiones del §4 que quedan por confirmar con el dueño (la fecha del presupuesto y si el total fijado es con IVA).
- `PLAN-MAESTRO.md §6`: la fila de 1.3 con lo que tomó de 1.2.
- `GUIA-PRUEBAS-LOCALES.md`: la sección del PDF.
- `BITACORA.md` y `MAPA-DEL-PROYECTO.md`: al cerrar cada tramo.
