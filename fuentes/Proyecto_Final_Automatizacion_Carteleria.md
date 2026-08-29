# Proyecto: Automatización de Cotización, Nesting y Aprobación para Empresa de Cartelería

## 1. Resumen ejecutivo

El cliente fabrica carteles de gran formato en chapa (cortados en distintos formatos de material). Hoy pierde tiempo en dos cuellos de botella principales:

1. **Cotizar** — acomodar manualmente las piezas del diseño sobre las planchas de chapa para aprovechar el material, y calcular el costo resultante.
2. **Aprobar y enviar** — el dueño revisa cada presupuesto a mano antes de mandarlo al cliente final, y el envío (con foto del cartel montado en el frente del local) es manual.

Además existe un dashboard en AppSheet, funcional pero lento por la cantidad de tablas que consulta.

El objetivo del proyecto es construir un sistema que:
- Tome las medidas de las piezas (manual al inicio, luego importadas desde Corel).
- Calcule automáticamente cómo anidarlas en el material elegido (nesting) para minimizar desperdicio.
- Genere una cotización con el desglose completo de costos.
- Envíe el presupuesto a aprobación del dueño y, una vez aprobado, lo mande al cliente automáticamente (PDF + fotomontaje del cartel en el frente).
- Reemplace el dashboard actual por uno más liviano, sobre las mismas tablas.

## 2. Alcance por módulos

| Módulo | Descripción | Complejidad |
|---|---|---|
| Alta de piezas | Carga manual (alto × ancho × cantidad) o importada desde Corel (DXF/SVG) | Media |
| Motor de nesting | Bin-packing rectangular (fase 1) → nesting irregular para corpóreas (fase final) | Alta |
| Cotizador | Tabla de precios versionada por m², + estructura, vinilo, mano de obra, flete, margen | Baja-Media |
| Flujo de aprobación | Borrador → pendiente → aprobado/observado → enviado, con notificación al dueño | Media |
| Fotomontaje | Homografía (4 puntos) sobre foto del frente + ajuste de luz/sombra con IA | Alta |
| Envío automático | Generación de PDF + envío por mail/WhatsApp al aprobar | Media |
| Dashboard | Reconstrucción liviana sobre las tablas actuales de AppSheet | Media |

## 3. Fases y cronograma propuesto

Se mantiene la lógica de fases de Enzo, con estimación de tiempos (asumiendo dedicación part-time, ~15-20 hs/semana; ajustar si hay más disponibilidad):

| Fase | Entregable | Duración estimada | Depende de |
|---|---|---|---|
| **0 — Relevamiento** | Definir tabla de precios, catálogo de materiales, formatos de chapa, capas de Corel, casos reales de presupuestos | 1 semana | Reuniones con cliente |
| **1 — MVP cotizador** | Alta manual de piezas + nesting rectangular + cotización + PDF | 3-4 semanas | Fase 0 |
| **2 — Importación Corel** | Macro VBA de exportación DXF/SVG + parser (ezdxf / svgpathtools) | 2-3 semanas | Fase 1 validada en uso real |
| **3 — Flujo de aprobación y envío** | Estados, notificación al dueño (link firmado), envío automático por mail/WhatsApp | 2 semanas | Fase 1 |
| **4 — Fotomontaje** | Homografía + composición + retoques con IA (iluminación, sombra, inpainting) | 3 semanas | Fase 3 |
| **5 — Nesting irregular** | Nesting para letras corpóreas (nest2D / Deepnest) | 3-4 semanas | Fase 1 estabilizada |
| **6 — Dashboard nuevo** | Reemplazo liviano del dashboard AppSheet sobre las mismas tablas | 2-3 semanas | Puede correr en paralelo desde fase 1 |

**Total estimado: ~16-20 semanas de desarrollo efectivo**, repartidas en aproximadamente 4-5 meses considerando idas y vueltas con el cliente, ajustes y validación en uso real entre fases. La fase 6 (dashboard) es independiente y puede adelantarse o correr en paralelo si hay más de una persona trabajando.

> Recomendación: cerrar la Fase 1 como un hito de validación real con el cliente (uso en producción, aunque sea con carga manual) antes de invertir en Corel o fotomontaje — ahí es donde más rápido se ve si el enfoque de nesting rectangular resuelve el problema real.

## 4. Checklist técnico — qué necesitamos antes de arrancar

**Del cliente / negocio:**
- [ ] Tabla de precios actual por m² de cada material, con histórico si existe
- [ ] Listado de formatos de chapa disponibles (medidas estándar)
- [ ] Costos asociados además del material: estructura, tornillería, vinilo/impresión, mano de obra por hora, flete, margen
- [ ] 5-10 presupuestos reales ya hechos, con el detalle de cómo se armaron (para validar el motor contra casos reales)
- [ ] Acceso a archivos .cdr de ejemplo (varios, con distinta complejidad)
- [ ] Acceso a las tablas que usa el dashboard de AppSheet actual (estructura y datos)
- [ ] Definición de quién es "el dueño" que aprueba (uno o varios aprobadores)
- [ ] Fotos de frentes de locales típicos, para probar el fotomontaje

**Técnico / infraestructura:**
- [ ] Definir stack final (backend, frontend, DB) — a decidir según lo que ya uses en Mural/proyectos propios
- [ ] Licencia/versión de CorelDRAW instalada en la empresa (para la macro VBA)
- [ ] Servicio de envío de WhatsApp (WhatsApp Business API o similar) y de mail
- [ ] Definir dónde y cómo se aloja el sistema (servidor propio, cloud, on-premise en la empresa)
- [ ] Librerías: `rectpack`, `ezdxf`, `svgpathtools`, `opencv-python`, y (fase 5) `nest2D` o Deepnest

**Producto / reglas de negocio:**
- [ ] Convención de capas en Corel ("CORTE", "PLEGADO", etc.) acordada con el cliente
- [ ] Definir kerf (ancho de corte) y márgenes de borde por máquina/proceso
- [ ] Definir si las rotaciones de piezas son libres o solo 0°/90°
- [ ] Definir cómo se calcula hoy el desarrollo de piezas con pliegue (si aplica)

## 5. Preguntas pendientes para el cliente

**Sobre el proceso actual:**
1. ¿Cómo calculan hoy el desarrollo de una pieza que lleva pliegue/doblez? ¿La pieza plana es distinta a la pieza final?
2. ¿Todas las piezas de corte son rectangulares, o ya hoy manejan formas irregulares (letras corpóreas) con frecuencia?
3. ¿Cuántos presupuestos hacen por semana/mes en promedio? (para dimensionar la urgencia de cada fase)
4. ¿Quién define hoy el formato de chapa a usar — el operario, un criterio fijo, o se elige según el pedido?

**Sobre Corel y los archivos de diseño:**
5. ¿Los archivos .cdr ya siguen alguna convención de capas, o hay que construirla desde cero con el equipo de diseño?
6. ¿Cuántas personas diseñan en Corel? ¿Están dispuestas a adoptar una convención nueva de capas/nombres?

**Sobre aprobación y envío:**
7. ¿El dueño aprueba desde el celular, la compu, o ambos? ¿Con qué frecuencia querría recibir notificaciones?
8. ¿El presupuesto se manda hoy por WhatsApp, mail, o los dos? ¿Tienen ya WhatsApp Business o hay que gestionarlo?
9. Cuando el dueño "observa" un presupuesto (no lo aprueba tal cual), ¿qué pasa después? ¿Vuelve a quien lo armó, se edita ahí mismo?

**Sobre el fotomontaje:**
10. ¿Tienen ya un banco de fotos de frentes de locales, o se saca una foto nueva por cada proyecto?
11. ¿El fotomontaje es un "nice to have" para vender mejor, o el cliente final lo pide como parte del presupuesto formal?

**Sobre el dashboard actual:**
12. ¿Qué reportes/vistas puntuales usa más el equipo en ese dashboard de AppSheet? (para priorizar qué replicar primero)
13. ¿Cuántos usuarios lo consultan y con qué frecuencia? ¿El problema de velocidad es al cargar, al filtrar, o al actualizar datos?

**Sobre prioridades:**
14. Si tuvieran que elegir un solo problema para resolver primero, ¿es el tiempo de armar el presupuesto, el desperdicio de material, o la demora en la aprobación/envío?

## 6. Notas de diseño (heredadas del análisis de Enzo, para no perder de vista)

- El **nesting rectangular** (bin-packing) cubre la mayoría de los casos reales y es rápido, determinista y explicable — arrancar por ahí, no por el nesting irregular.
- El **.cdr es formato cerrado**: no conviene parsearlo directo. Se automatiza la exportación a DXF/SVG desde una macro en Corel.
- El **fotomontaje robusto** no es un modelo generativo puro (deforma texto/marca), sino composición geométrica: el usuario marca 4 puntos sobre la foto, se aplica homografía (OpenCV) y se pega el render real del cartel. La IA se reserva para iluminación, sombra proyectada e inpainting del cartel viejo.
- Siempre guardar **snapshot inmutable** del presupuesto en el momento del envío, para que cambios futuros en la tabla de precios no alteren presupuestos ya enviados.
- Dejar siempre **override manual** del número final — si el dueño no puede corregir a mano, no va a confiar en el sistema.
