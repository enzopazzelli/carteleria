# A26 · Sacar lo que no va — diseño

> **Origen:** la demo en la cartelería del 2026-11-18. El cliente pidió quitar el login, el presupuesto y «Comparar formatos»; el producto final es **el DXF de corte y el PDF del diseño anidado**. Tampoco va a haber despliegue: la app se instala en cada computadora, como la demo.
>
> **Fecha:** 2026-11-18 · **Rama:** `feat/a26-sacar-lo-que-no-va` · **Plan:** [`plan.md`](plan.md)
>
> Los otros dos pedidos de la demo van aparte, después de este: el **deshacer en el ajuste** (A27) y los **retazos agrupados por material** (A28).

---

## 1. Qué se pidió y qué se hace

| Pedido | Qué se hace |
|---|---|
| Quitar el login | La app entra directo, sin «Entrar», «Mi cuenta» ni «Usuarios». Ninguna ruta del servidor pide sesión. |
| Quitar «Comparar formatos» | En su lugar, **elegir una sola chapa** por grupo: la que se va a anidar. El cliente: «es un despropósito tener que elegir dos chapas». |
| Quitar el presupuesto | Salen el menú Presupuestos, la pestaña Costeo, los presupuestos del inicio y el paso «Presupuesto» de las tarjetas. Lo que queda al final del recorrido es Chapas, con el DXF y el PDF. |

## 2. Apagar, no borrar

Lo que guarda datos queda: **no hay migración y no se borra nada de la base**. Las tablas de usuarios, sesiones, presupuestos, clientes y aprobaciones quedan como están, sin uso. Si el cliente cambia de idea, todo vuelve sin volver a cargar nada.

El código del servidor del presupuesto, de la comparación y de los usuarios **queda montado y con sus pruebas**: es mucho (el presupuesto toca unos 60 archivos) y está mezclado con el inicio y con la regla de qué anidado cuenta. Sacarlo es una limpieza aparte, si después de un tiempo se confirma que no vuelve.

En la pantalla, en cambio, **lo que queda sin forma de llegar se borra**, con sus pruebas: pantallas muertas confunden a quien lee el código, y si hacen falta vuelven con git. La regla: si el código es de la pantalla y nada lo usa, sale; si es del servidor, queda.

## 3. El login

- **Servidor.** La dependencia que pedía sesión en todas las rutas (`usuario_actual`, puesta una vez por grupo de rutas en `app.py`) se reemplaza por una que **solo pide el encabezado propio** en los pedidos que cambian datos (`X-Cartel-Pedido`, que la pantalla ya manda siempre). Sin cookie de sesión ya no hay nada que robar, pero el encabezado sigue frenando que una página ajena abierta en el mismo navegador mande pedidos a `localhost:8000`, y no cuesta nada.
- **Quién creó el trabajo.** Crear un trabajo y confirmar una importación guardaban el usuario (`creado_por_id`). Pasa a quedar vacío; la columna ya admite vacío.
- **Las rutas del presupuesto que miran el usuario** (autor, aprobar) quedan como están: nadie las llama.
- **Pantalla.** Salen `Entrar`, `Mi cuenta`, `Usuarios`, la ruta protegida y el aviso de «se perdió la sesión» del cliente de la API. La barra pierde el nombre y «Cerrar sesión».
- **La prueba guardiana** que verificaba que toda ruta pide sesión pasa a verificar que toda ruta que cambia datos pide el encabezado propio.

## 4. Elegir la chapa del grupo

Hoy la única forma de darle chapa a un grupo es «Usar este» en el resultado de la comparación, que obliga a comparar al menos dos.

- En la pestaña Grupos, cada grupo muestra **su chapa por nombre** («Chapa: Alucobond blanco 3 mm · 1500 × 3000 mm», o «Sin chapa») y un botón **«Elegir chapa»** / **«Cambiar chapa»**.
- El botón abre **la misma lista de chapas** que usaba la comparación, en modo de elegir una sola (ya existe: es la del panel de seccionar). Mantiene los filtros por familia, el buscador y los retazos, también los de medida libre.
- **«Usar esta chapa»** la asigna al grupo. No anida nada.
- Si el grupo ya tenía un anidado y se le cambia la chapa, ese anidado deja de contar como terminado, igual que hoy (regla única de qué anidado cuenta, A25): el inicio y el PDF avisan que hay que volver a anidar.
- El enlace del resumen del anidado «Cambiar material o comparar formatos» pasa a decir **«Cambiar la chapa»**.
- Sale de la pantalla todo lo de comparar: motor, tiempo máximo, criterio, la barra de progreso y la tabla de resultados.

## 5. El presupuesto

- **Barra:** sale «Presupuestos».
- **Trabajo:** sale la pestaña «Costeo». Un enlace viejo a `/costeo` lleva a Chapas.
- **Inicio:** sale el recuadro «Últimos presupuestos».
- **Tarjeta del trabajo:** salen el paso «Presupuesto» y el renglón del presupuesto. Con todo anidado, la tarjeta dice **«Listo para cortar»** y lleva a Chapas, donde están el DXF y el PDF. Esto cambia en el servidor (`app/pasos.py`), que es quien decide la frase y a dónde lleva.
- **Textos que nombran el presupuesto** fuera de esas pantallas pasan a hablar del corte: por ejemplo, «Elegida para el presupuesto» → «Elegida para cortar». Si borrar un anidado avisaba que «el costeo va a usar el más reciente», ahora dice que **Chapas, el DXF y el PDF** van a usar el más reciente.
- **Chapas** dejaba de avisar un cambio de cantidad de chapas solo si había presupuestos; ese aviso sale (no hay presupuestos que avisar).

## 6. Decisiones mías, para corregir

1. **El nombre de la barra** pasa de «Cotizador» a **«Cartelería»**, como el acceso del escritorio de la demo. Ya no cotiza.
2. **Los precios en Materiales quedan** (la planilla los trae y no molestan). Si el cliente no los quiere ver, es un cambio chico aparte.
3. **El servidor de la comparación y del presupuesto queda montado** (§2). No se llama desde ninguna pantalla.
4. **La guía del usuario** se actualiza en este mismo pedido: hoy explica el login, la comparación y el presupuesto.

## 7. Lo que no cambia

- Importar, piezas, grupos, anidar, Chapas, el ajuste a mano, el DXF y el PDF.
- La pantalla de Materiales, con sus retazos.
- La base: sin migración.
- El instalador de la demo (fuera del repo): se rearma con esta versión cuando Enzo lo pida.
