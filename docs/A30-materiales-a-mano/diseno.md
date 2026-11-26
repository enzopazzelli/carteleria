# A30: cargar materiales a mano

*Diseño corto, 2026-11-26. Pedido de Enzo: la cartelería ahora trabaja con más chapas y materiales que los 44 del instalador, y tienen que poder cargarlos ellos.*

## Para qué

Que alguien de la cartelería agregue un material nuevo (o una medida de chapa nueva) desde la pantalla de Materiales, sin planilla y sin pedirle nada a Enzo, y que ese material aparezca en «Elegir chapa» de Grupos.

## Qué entra

- **Nuevo material**: botón en Materiales con nombre, espesor (opcional), medida de la chapa (ancho × alto, en mm) y categoría (automática según el nombre, o una de las que ya hay).
- **+ Medida** sobre un espesor y **+ Espesor** sobre un material: agregar otra medida u otro espesor.
- **Editar** nombre y espesor, **Quitar** una medida y **Borrar material**: solo en lo cargado a mano.
- **Costo por m² (opcional).** El anidado no lo usa, pero el servidor no deja crear retazos de una chapa sin precio por m² (A8): sin él, «Guardar como retazo» y «+ Retazo» fallan. El formulario lo dice. Los parámetros de corte siguen en «Corte».

## Qué no entra

- No se toca el servidor (ya tiene crear, editar y borrar de materiales y formatos).
- No se editan los materiales que vienen de la planilla (los pisaría la próxima carga).
- No hay «slots» vacíos en la base: con el botón no hacen falta.

## Supuestos míos (a confirmar)

- El nombre se guarda en mayúsculas, como los de la planilla; la pantalla lo muestra en minúsculas, igual que hoy.
- La medida nueva lleva un código propio «MANO-XXXXXX». Sin código, los retazos que salgan de esa chapa quedaban sueltos en la lista (se cuelgan del código de su chapa, `código-R`). Se sigue marcando «cargada a mano» porque ninguna fila de la planilla tiene ese código.
- Para borrar un material, primero se quitan sus medidas una por una: si un grupo usa una, el servidor avisa y no se borra nada más.

## Enfoques

1. **Solo pantalla sobre las rutas que ya existen (elegido).** Sin migración ni riesgo para la base.
2. Plantilla de Excel con el formato de AppSheet: descartado, es una planilla de 30 columnas hecha para otro programa.
3. Slots vacíos con nombre fijo: descartado, no se les puede poner el nombre real sin esta pantalla.
