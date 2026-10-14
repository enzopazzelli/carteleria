# A8 · Lista de materiales con filtros y retazos de medida libre — diseño

> **Estado:** **construido el 2026-10-14,** con el plan de [`plan.md`](plan.md), en la rama `feat/lista-de-materiales`. Lo que se apartó está al final de ese plan, en «Desvíos».
>
> **De dónde sale.** Pedidos de Enzo del 2026-10-14: «mejorar la parte del menú de chapas a la hora de comparar […] quizá sea mejor una lista de materiales con filtros para chapas, acrílicos, etc., y que no estén en línea, sino en columnas», y «hay veces que existen diseños pequeños que los imprimirán en un retazo de chapa de 1 m × 1 m (por ejemplo; en realidad debería ser libre)». Va en el carril del motor, después de la barra de progreso (A7).
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Este diseño no agrega ninguno.

---

## 1. Para qué

- Que elegir qué formatos comparar sea rápido con el catálogo real (29 formatos hoy, más a medida que se cargue la planilla): ver de un vistazo material, espesor, medida y precio, y filtrar por familia.
- Que un diseño chico pueda cotizarse y anidarse sobre un retazo de la medida que sea, cobrando lo que mide.

## 2. Punto de partida

- **El selector de la comparación** (pestaña Grupos) son casillas seguidas en renglón, una por formato, con el texto «CHA0012 — CHAPA NEGRA cal. 22 1220.00×2440.00».
- **El catálogo no guarda la familia** de un material (chapa, acrílico…): solo se deduce de la primera palabra del nombre. En la base de Enzo: 23 materiales con nombres que empiezan con CHAPA, ACRILICO, ALTO IMPACTO, CORRUGADO y POLICARBONATO.
- **`Formato` ya tiene `es_retazo`** (`backend/app/modelos/catalogo.py`), de un diseño anterior, pero nada lo usa. Un grupo usa un formato del catálogo (`GrupoDeCorte.formato_id`): de ahí salen la medida de la chapa para anidar y el precio para cotizar (precio por m² × área de la chapa × chapas).
- **Crear un formato** ya existe (`POST /materiales/{id}/formatos`), pero quien lo llama tendría que copiar a mano el precio.

## 3. Lo que decidió Enzo (2026-10-14)

| Pregunta | Decisión |
|---|---|
| Cómo se ve la lista | **Una tabla con columnas** (familia, material, espesor, medida, precio por m²), botones para filtrar por familia y un buscador; cada fila se tilda |
| De dónde sale la familia | **Un dato nuevo del material.** Para los que ya existen se completa solo desde el nombre y después se puede corregir |
| Cómo se cobra un retazo | **Por m², al precio del material**: lo que mide el retazo por el precio por m² de la chapa entera |
| Dónde se elige el retazo | **En la lista, como una fila más,** guardado en el catálogo y marcado como retazo, para compararlo y usarlo en el grupo |

## 4. Alcance

**Entra:** la familia del material (dato, migración con su valor inicial, y en las rutas del catálogo); crear y quitar un retazo desde una fila de la lista; la tabla con filtros y buscador en la comparación de la pestaña Grupos.

**Queda afuera:** llevar stock de retazos (que un retazo usado deje de estar: es inventario); usar esta misma tabla en el selector de chapa del panel de seccionado (tiene el mismo problema, puede venir después); editar la familia desde una pantalla (por ahora, por la API: `PATCH /materiales/{id}`).

## 5. Cómo funciona

### 5.1 La familia

- `Material.familia`: texto corto, obligatorio.
- **Una sola regla para deducirla del nombre,** `familia_desde_nombre(nombre)` en el servidor: CHAPA → «Chapas», ACRILICO → «Acrílicos», ALTO IMPACTO → «Alto impacto», CORRUGADO → «Corrugado», POLICARBONATO → «Policarbonato», cualquier otro → «Otros». Sin importar mayúsculas ni tildes, mirando cómo empieza el nombre.
- **La migración** agrega la columna y la completa con esa regla para los materiales que ya están. La regla queda copiada adentro de la migración, como se hace con las migraciones de datos, para que no cambie si después cambia el código.
- **Al crear un material** sin familia, se usa la regla. `MaterialCrear`, `MaterialActualizar` y `MaterialLeer` llevan `familia`.

### 5.2 El retazo

- **`POST /formatos/{id}/retazos`** con `{ancho_mm, alto_mm}`: crea un formato nuevo del mismo material, con esa medida, `es_retazo = True`, y copia de la fila de origen la moneda, la unidad de venta, el precio por unidad de venta y la marca de precio simulado. Contesta **201** con el formato nuevo.
- **Rechaza:** un formato que no existe (**404**); una medida que no es un número positivo y finito, o mayor que 10 000 mm (**422**); un formato de origen que no se vende por m² o que no tiene precio (**400**: el retazo se cobra por m² y no habría cómo).
- **El código** del retazo es el de la fila de origen con «-R» al final (o vacío si no tenía), para reconocerlo en la lista.
- **Quitar un retazo** usa la ruta que ya existe (`DELETE /formatos/{id}`), y la pantalla la ofrece solo en las filas de retazo.
- **Lo demás no cambia:** un retazo se compara, se asigna al grupo con «Usar este» y se anida y cotiza como cualquier formato. Su costo es su área por su precio por m², por cada chapa.

### 5.3 La tabla

- **Un componente nuevo, `ListaDeFormatos`,** que reemplaza las casillas de la comparación. Recibe los formatos, los materiales, los tildados y qué hacer al tildar, y avisa cuando se crea o se quita un retazo.
- **Arriba:** un botón por familia (las que hay en el catálogo, más «Todas»), un buscador (busca en material, espesor, código y medida) y «Seleccionar todas», que tilda solo lo que está a la vista.
- **Columnas:** casilla · Familia · Material · Espesor · Medida (en mm, sin decimales de más: «1220 × 2440») · Precio por m² (con moneda, y «simulado» cuando corresponde; «—» si no se vende por m²) · acciones.
- **Orden:** por familia, material, espesor y medida; los retazos de un formato, debajo de los de su material.
- **Acciones de la fila:** «Retazo…» abre, en la misma fila, dos campos (ancho y alto, en mm) y «Agregar»; una fila de retazo lleva la etiqueta «Retazo» y una ✕ para quitarlo.
- **Las cuentas** (filtrar, ordenar, el texto de la medida y del precio) van en funciones aparte, sin React, para poder probarlas.

## 6. Cómo se valida

- **Pruebas del servidor:** la familia que sale de cada nombre (los cinco prefijos, mayúsculas y tildes, y «Otros»); la migración, de ida sobre una base con materiales y de vuelta; crear un material sin familia la deduce, y con familia la respeta; crear un retazo copia el precio, la moneda y la marca, queda `es_retazo`, y los rechazos de §5.2.
- **Pruebas de la pantalla:** filtrar por familia, buscar, ordenar, la medida y el precio como texto, y «Seleccionar todas» solo sobre lo visible.
- **Recorrido** con Chrome sin ventana sobre una copia de la base: filtrar por Chapas, buscar «negra 22», crear un retazo de 1000 × 1000, compararlo contra la chapa entera, usarlo en el grupo y ver su costo en Costeo.

## 7. Riesgos

| Riesgo | Qué se hace |
|---|---|
| La regla de la familia clasifica mal un nombre que no se esperaba | Cae en «Otros» y se corrige con `PATCH /materiales/{id}`; los cinco prefijos salen de la base real |
| Se acumulan retazos que ya no existen en el taller | La ✕ de la fila los quita; llevar stock queda afuera |
| La tabla con muchos formatos se vuelve larga | Los filtros y el buscador; el catálogo real hoy tiene 29 |
| Un retazo más grande que la chapa de la que sale | Se permite (la medida es libre); el tope de 10 000 mm solo frena valores absurdos |

## 8. Qué cambia en otros documentos

- **[`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md):** en los pendientes del seccionado, la fila «el selector de chapa del panel lista todo el catálogo» suma que la tabla de A8 sirve para eso.
- **[`BITACORA.md`](../../BITACORA.md):** la entrada del día en que se cierre.
- **[`MAPA-DEL-PROYECTO.md`](../../MAPA-DEL-PROYECTO.md):** la fila Catálogo suma la familia y los retazos.
