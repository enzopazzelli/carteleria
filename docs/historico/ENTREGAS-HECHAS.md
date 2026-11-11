# Entregas hechas

> Lo que ya está en `main`, entrega por entrega y de la más nueva a la más vieja, con las migraciones aplicadas en la base real. Es historia: lo que sigue y lo que espera a alguien está en el [`README`](../../README.md) («En qué estamos») y en el [`PLAN-MAESTRO.md §7`](../plan/PLAN-MAESTRO.md). Cada entrega tiene su diseño en [`historico/`]().

**Hecho el 2026-11-09, en la base real:** la migración de A24 (la tabla de correcciones del dibujo), con respaldo manual y automático antes. La tabla quedó vacía y los 2 trabajos, intactos.

**Hecho el 2026-11-08, en la base real:** las migraciones de A20, de A21 y de A23 y la primera carga de la planilla, con respaldos antes de cada una en `backend/local/`.
- Entraron 288 artículos: los 27 códigos enlazados y 261 nuevos. El catálogo pasó de 23 a 44 materiales y de 30 a 59 formatos.
- `CHA0013` quedó con la medida a mano, 1250 × 2500, confirmada por Enzo (el 0,7 es el espesor).


**Ya está en `main`:**
- **Una referencia para la escala, desde el 2026-11-11.** Al elegir el DXF, debajo de la cajita de escala aparece «Con esta escala, el dibujo mide 4.610 × 7.760 mm (4,61 × 7,76 m)», que se recalcula mientras se escribe, y una explicación fija de qué es la escala (1 si el dibujo está en milímetros, 10 en centímetros, 1000 en metros). El servidor mide el dibujo en sus propias unidades con `POST /dxf/medida`; la pantalla multiplica. No hay alarmas: es solo la referencia. Sin migración.
- **Una sola regla de qué anidado cuenta para el presupuesto (A25), desde el 2026-11-09.**
  - **Para qué:** que el costeo, la tarjeta del inicio, el PDF y Chapas digan lo mismo de un grupo. Antes cada uno lo decidía por su cuenta, y solo el costeo notaba si la chapa cambiaba después de anidar.
  - **Cómo funciona:** un solo módulo del servidor (`app/anidado_que_cuenta.py`) dice cuál anidado del grupo se muestra, si se cobra y, si no, por qué: no tiene material, no hay anidado, no tiene piezas, las piezas cambiaron o la chapa cambió. Se muestra aunque no se cobre: la miniatura, el PDF y Chapas lo siguen dibujando, con su aviso.
  - **Lo que se nota:** si le cambiás la chapa a un grupo ya anidado, la tarjeta del inicio dice «Falta volver a anidar», el PDF lleva el aviso en rojo, y Chapas y Anidado dicen el motivo («La chapa cambió después de este anidado: no se cobra»). Un grupo sin material tampoco se da por terminado.
  - **Una guardiana** (`tests/test_regla_unica_del_anidado.py`) falla, con el archivo y la línea, si otro módulo vuelve a decidirlo por su cuenta.
  - **Todavía no:** limpiar un detalle de antes, que se conserva: con la chapa cambiada el costeo da dos avisos seguidos («el material o formato cambió…» y «todavía no tiene un anidado terminado»).

  Ver [`historico/A25-regla-unica-del-anidado/`](A25-regla-unica-del-anidado/diseno.md).
- **Recordar las correcciones de la lectura (A24), desde el 2026-11-09.**
  - **Para qué:** que lo que marcaste sobre un dibujo (esta forma se corta, esta no va) no se pierda si volvés a cargar el mismo archivo.
  - **Cómo funciona:** al apretar «Cargar» se guardan las correcciones, por la huella del contenido del archivo y no por su nombre. Al abrir «Ver cómo se lee» con el mismo archivo, aunque sea en otro trabajo, el dibujo aparece ya corregido, con un aviso («Se aplicó 1 corrección de la vez anterior») y un botón «Empezar de cero». Si marcás algo a mano, el aviso se esconde. Cargar sin ninguna corrección borra lo guardado de ese archivo.
  - **Lo que no recuerda:** la unión de formas («Unir las formas que se pisan»), que se decide cada vez; y un dibujo cambiado, aunque sea en un milímetro, no recibe nada.
  - **En la base:** una tabla nueva (migración `f2c8a4d6e913`, aplicada en la base real el 2026-11-09, con respaldo).

  Ver [`historico/A24-recordar-correcciones/`](A24-recordar-correcciones/diseno.md).
- **Agregar materiales del catálogo al presupuesto (A23), desde el 2026-11-08.**
  - **Para qué:** un cartel lleva más que la chapa que se anida: corrugado, vinilos, pintura, tornillos, iluminación, y también diseño, montaje y traslado. Antes se escribían a mano, con descripción, cantidad y precio.
  - **Cómo se usa:** en el Costeo, en «Líneas por rubro», el botón **«Agregar del catálogo»** abre un buscador de los 288 artículos de la planilla: por texto, sin distinguir tildes ni mayúsculas, y con un filtro por categoría. Se elige el artículo, se escribe la cantidad (en m², metros, unidades o litros, según el artículo) y se agrega.
  - **Qué toma de la planilla:** el texto, la unidad, el costo y el margen de venta, así que la línea tiene **precio sugerido** y se marca si se baja. Un artículo sin margen usa el margen general. Un artículo sin precio se agrega, pero la línea queda sin costo hasta que se le ponga un valor a mano.
  - **Lo que no cambia solo:** el precio se copia al agregar; si la planilla cambia después, el presupuesto armado queda como estaba.
  - **Todavía no:** actualizar los precios de un presupuesto armado, y agrupar renglones chicos en el PDF.

  Ver [`historico/A23-materiales-en-el-presupuesto/`](A23-materiales-en-el-presupuesto/diseno.md).
- **El PDF del presupuesto con la marca de la empresa (A22), desde el 2026-11-08.**
  - **Para qué:** que quien recibe el presupuesto vea de quién es y cómo contactarlos.
  - **Cómo se ve:** el logo a la izquierda, una banda negra inclinada con «PRESUPUESTO» en naranja y el código, el recuadro del cliente con una marca naranja, el detalle con una línea naranja y el total en un recuadro negro. El pie lleva el nombre, la dirección, el WhatsApp, el mail, la web y el Instagram, en cada hoja. De la segunda hoja en adelante, una banda finita con el código.
  - **De dónde salen el logo y los datos:** de `backend/local/empresa/` (`logo.png` y `datos.json`), **fuera de git**: el repositorio es público. Si falta la carpeta, el PDF sale igual, sin logo ni pie. Para cambiar un dato, se edita `datos.json`.
  - **Todavía no:** los datos fiscales y las condiciones de pago (el PDF ya los imprime cuando se carguen en `datos.json`), y el fotomontaje del cartel sobre la foto del local (3.2).

  Ver [`historico/A22-pdf-con-la-marca/`](A22-pdf-con-la-marca/diseno.md).
- **La cuenta de los retazos (A21), desde el 2026-11-08.**
  - **Para qué:** que el taller sepa con qué retazos cuenta, en vez de que el sobrante de cada chapa se pierda de vista.
  - **Guardar:** en la tabla de chapas del resumen del anidado, al lado de cada sobrante que llega al mínimo (hoy 250 × 250 mm), un botón «Guardar como retazo». Crea el retazo con esa medida, del mismo material y al precio por m² de su chapa. El mismo sobrante no se guarda dos veces.
  - **En Materiales:** arriba de las medidas de cada material, «Retazos: 1 retazo disponible · 2,22 m²». Cada retazo dice de dónde salió («Sobrante de Parador, chapa 2» o «a mano») y en qué anda:
    - **disponible:** ningún trabajo lo usa;
    - **en uso:** lo usa un trabajo cuyo presupuesto no está aprobado (sigue pudiéndose elegir);
    - **usado:** lo usa un trabajo con el presupuesto aprobado. Si el presupuesto vuelve a borrador, se libera solo.
  - **En el inicio:** el número de retazos cuenta solo los disponibles.
  - **Todavía no:** cobrar por lo usado, y proponer un retazo al anidar un trabajo nuevo.

  Ver [`historico/A21-cuenta-de-retazos/`](A21-cuenta-de-retazos/diseno.md).
- **La aprobación del presupuesto (A20), desde el 2026-11-08.**
  - **Para qué:** que quede asentado que el dueño vio un presupuesto y lo dio por bueno, o que lo devolvió con una observación, y quién y cuándo.
  - **Los estados:** borrador, pendiente de aprobación, observado y aprobado. Mandarlo a aprobar exige que esté completo, y dice qué falta si no.
  - **En el Costeo:** una franja con el estado, los botones de cada paso, tu nombre (se recuerda) y el historial. Un presupuesto pendiente o aprobado queda bloqueado; para tocarlo hay que volverlo a borrador, con un motivo. El PDF se baja igual.
  - **Todavía no:** el aviso por mail con link para aprobar desde el celular, y el envío al cliente. Hace falta tener servidor y buzón.

  Ver [`historico/A20-aprobacion-del-presupuesto/`](A20-aprobacion-del-presupuesto/diseno.md).
- **Los presupuestos con precio sugerido (A19), desde el 2026-11-07.**
  - **Para qué:** que el presupuesto salga con la ganancia que corresponde aunque lo arme alguien que no sabe, y que una baja se note. El dueño lo pidió porque los empleados cobraban mucho menos de lo que podían.
  - **El precio sugerido:** cada material toma el primer margen de la planilla, que es un multiplicador del costo (la chapa × 3, el MDF × 5); lo que no tiene margen usa el margen general del presupuesto. El margen se guarda al «Recalcular materiales».
  - **En el Costeo:** al lado de cada producto, el sugerido, el precio (que se cambia a mano) y la ganancia. Un producto por debajo del sugerido va en amarillo, con cuánto, y arriba hay un aviso.
  - **«Presupuestos»** se prende en la barra: la lista de todos, con buscador, marca los que tienen productos por debajo, abre su Costeo y baja su PDF. El cliente no ve nada de esto.
  - **Queda para el dueño** cuándo se usa el segundo margen de la planilla (× 6, `P-36`).

  Ver [`historico/A19-presupuestos-y-precio-sugerido/`](A19-presupuestos-y-precio-sugerido/diseno.md).
- **La pantalla de Materiales con la planilla de precios (A18), desde el 2026-11-07.**
  - **De dónde salen los precios:** los materiales y sus precios salen de la planilla de la empresa (`CARTELERIA 2026.xlsx`, hoja `COTIZADOR`, la misma de AppSheet).
  - **Cómo se actualizan:** en Materiales, «Actualizar desde la planilla» la sube y muestra una revisión antes de aplicar: qué precios cambian, qué entra, qué ya no está y qué hay que mirar.
  - **La pantalla, en dos columnas:** a la izquierda, un buscador y las categorías; a la derecha, el material elegido, con si se anida, el corte de cada espesor, las medidas con su proveedor, su costo por m² y sus retazos.
  - **Dos proveedores para un código:** cuenta el último al que le cambió el precio, o el marcado con «Usar este». En el trabajo no se elige proveedor.
  - **La lectura del DXF** sigue mirando solo las medidas de Chapas, Acrílicos y Policarbonato (`PAR-60`).
  - **Para Vale:** en Anidado, el motor, la semilla, la búsqueda, el tiempo, la simplificación y «Vaciar chapas» pasaron a un desplegable «Opciones avanzadas», cerrado. Si alguna no es la de siempre, dice «cambiadas». Lo que se manda al motor no cambió.

  Ver [`historico/A18-pantalla-de-materiales/`](A18-pantalla-de-materiales/diseno.md).
- **Pulir lo que quedó suelto (A17), cerrado el 2026-10-29.** Un sprint de 41 tareas en 7 tandas para cerrar los pendientes chicos de las tablas del plan maestro. Lo que más se nota:
  - la base se pone al día sola al arrancar;
  - en Chapas, si una pieza no entra en otra chapa, esa chapa se reacomoda, con «Deshacer»;
  - cuando una pestaña no pudo cargar, un aviso con «Reintentar»;
  - en Piezas, las descartadas van plegadas;
  - un anidado cuyas piezas cambiaron después ya no se cobra, y lo dicen el Costeo, el inicio, Anidado, Chapas y el PDF.

  Ver [`historico/A17-pulir-lo-suelto/`](A17-pulir-lo-suelto/diseno.md).
- **La página de inicio (A16), desde el 2026-10-26.** Una barra fija arriba en todas las pantallas: Inicio · Trabajos, y Presupuestos y Materiales apagados hasta que tengan su pantalla. El inicio va en dos columnas. A la izquierda, las tarjetas de los 6 trabajos tocados más recientemente: cada una con la miniatura del diseño pintado por chapa, en qué paso quedó y qué sigue («Falta anidar Calibre 22», «Falta el presupuesto»), las chapas y el material, y el presupuesto. Tocarla lleva a ese paso. A la derecha, «Nuevo trabajo», los últimos presupuestos (cada uno abre su Costeo y baja su PDF) y cuántos materiales hay. La sección Trabajos muestra todas las tarjetas con un buscador, y un trabajo se borra desde el «⋯» de su tarjeta, con confirmación; mientras se anida, no se puede borrar. Ver [`historico/A16-pagina-de-inicio/`](A16-pagina-de-inicio/diseno.md).
- **El diseño anidado en PDF (A15), desde el 2026-10-25.** Un PDF por trabajo, para imprimir en A4 y en color, que se baja desde la pestaña Chapas o desde el resumen del anidado. Por cada material trae una hoja con el diseño entero pintado del color de cada chapa, a todo el ancho, con lo usado y el sobrante de cada chapa abajo; después, las chapas juntas, hasta 4 por hoja, todas a escala 1:20, con una grilla cada 10 cm y el número de cada pieza, para reconocer lo cortado y marcar a mano. Una barra de 50 cm al pie deja comprobar con una regla que la hoja salió en tamaño real. Ver [`historico/A15-disenio-anidado-en-pdf/`](A15-disenio-anidado-en-pdf/diseno.md).
- **Las chapas en conjunto y el diseño inicial (A14), desde el 2026-10-24.** La pestaña **Chapas** reemplaza a Ajuste: muestra todas las chapas del anidado juntas, con el diseño inicial arriba pintado del color de cada chapa y lo que falta en rojo; pasar el mouse por una pieza o una chapa la ilumina en los dos lados. Una pieza se arrastra a otra chapa o a una chapa nueva y el sistema le busca lugar; con doble clic una chapa se abre grande para retocarla. En Grupos, en Piezas y en los mensajes, cada pieza nombrada lleva su forma y su lugar en el diseño. Ver [`historico/A14-chapas-en-conjunto/`](A14-chapas-en-conjunto/diseno.md).
- **Llenar mejor los huecos (A13), desde el 2026-10-23.** Cada pieza se busca por casillas adentro de los huecos, contra la pared y probando muchos más giros, incluida dada vuelta. Con el parador entran 30 piezas en los huecos en lugar de 20, y el sobrante crece de 1220 × 509 a 1220 × 761 sin gastar más chapa. Ver [`historico/A13-llenar-mejor-los-huecos/`](A13-llenar-mejor-los-huecos/diseno.md).
- **El plano y Ajuste se ven derechos, desde el 2026-10-23.** Se veían de cabeza respecto del DXF (la «A» como una «∀»); el DXF para la máquina siempre estuvo bien. Con eso, el sobrante arriba queda arriba también en el archivo.
- **El material usado en ancho × alto (A12), desde el 2026-10-23.** El resumen del anidado dice lo usado como lo diría el dueño, «6 chapas enteras + 1220 × 1650 + 1220 × 900», con una tabla de lo usado y el sobrante de cada chapa; una chapa es «entera» si lo que sobra no llega al retazo más chico que se guarda (250 × 250 mm, a confirmar con el dueño). En Anidado se elige si el sobrante queda arriba, como bloque de todo el ancho (por defecto), o al costado. Con el parador sobra arriba un retazo de 1220 × 527. Ver [`historico/A12-material-usado-y-sobrante/`](A12-material-usado-y-sobrante/diseno.md).
- **Varios anidados a la vez, confirmado el 2026-10-23.** Tres a la vez terminan bien, cada uno dentro de su tiempo máximo, con la barra de avance y el servidor respondiendo. Con la máquina compartida cada uno busca menos, pero en la medición no salió peor: tres Complejo juntos dieron 7, 8 y 7 chapas (uno solo, 8). Detalle en el [`PLAN-MAESTRO.md §7`](../plan/PLAN-MAESTRO.md).
- **El giro de las piezas grandes (A11), desde el 2026-10-23.** Con «Girar a cualquier ángulo», Complejo fallaba: Sparrow inclinaba los tramos del aro y quedaban más anchos que la chapa, y la comparación terminaba enseguida con el mismo error. Ahora cada pieza que no entra a cualquier ángulo gira solo en los ángulos con los que entra entera, y el resultado la nombra en un aviso; las demás siguen girando libre. Complejo da 8 chapas, con y sin giro libre. Ver [`historico/A11-giro-de-las-piezas-grandes/`](A11-giro-de-las-piezas-grandes/diseno.md).
- **Aprovechar huecos primero (A10).** Las piezas chicas se meten en los huecos de las grandes *antes* de acomodar, y solo se acomoda lo que queda afuera. Con el parador, lo ocupado de la chapa bajó de 1103 a 930 mm, y ese paso tarda segundos: la pasada vieja tardaba 236 s y no ganaba nada.
- Con eso vinieron:
  - la barra de avance dice en qué anda, se puede cancelar y todo entra en el tiempo máximo;
  - en Ajuste, una pieza se mueve con lo que tiene adentro;
  - en el DXF, lo de adentro va primero;
  - un anidado que quedó colgado al cerrar el programa pasa a error al arrancar.
- Ver [`historico/A10-huecos-primero/`](A10-huecos-primero/diseno.md).
- Cómo probar Sparrow (semilla, tiempo, simplificación, cancelar): [`GUIA-SPARROW-PRUEBAS.md`](../GUIA-SPARROW-PRUEBAS.md).

**El orden de corte ya no es pregunta para el taller:** se da por bueno que la máquina corta en el orden del archivo, con lo de adentro de un hueco primero (`SUP-18` en el [registro](../REGISTRO.md)).
