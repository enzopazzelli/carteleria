# Prototipo — dashboard rápido (F8)

Maqueta interactiva de un reemplazo del dashboard de AppSheet, pensada para verse y probarse antes de escribir backend. **No es código de producción** — es HTML/CSS/JS en un solo archivo, sin build, sin dependencias.

## Cómo abrirlo

Doble clic en [`index.html`](index.html), o arrastralo a cualquier navegador. No necesita servidor.

## Qué tiene

Las 9 vistas del dashboard real (Inicio, Proyectos, Stock e Inventario, Registros, Cotizaciones, Control de Taller, Lista de Precios, Compras, Configuración), con:

- **Datos de muestra**, no reales. Categorías, procesos y formatos de chapa siguen la nomenclatura real de la empresa (no son sensibles); clientes, operarios y montos son inventados.
- Un selector **"Viendo como"** en la barra lateral que simula iniciar sesión con cada uno de los 6 roles y restringe el menú según la matriz de permisos (editable en Configuración → Habilitación de módulos por rol).
- Formularios funcionales pero **solo en memoria del navegador** — registrar un proceso de producción, mover stock, aprobar una cotización, etc. actualiza la pantalla al instante pero no persiste en ningún lado ni sobrevive a un F5.

## Qué NO tiene

- Backend, base de datos o conexión a las tablas reales de AppSheet.
- Los datos reales de la empresa (nunca se cargaron acá — ver `CONVENCIONES.md §4` del proyecto).
- La vista de Compras está **inferida** de la tabla `COMPRAS` del xlsx, no de una captura real — es la más floja de las 9.

## Por qué se ve así de rápido

Todo el dataset vive en el propio HTML: cambiar de módulo o tipear en un buscador no dispara ningún pedido de red. Es la demostración de la idea real detrás de F8 (`ADR-06` en `docs/EPICA.md`): el dashboard de producción no debería consultar las tablas operativas en vivo, sino leer agregados precalculados que se refrescan cada `PAR-23` (15 min) — el contador "Datos actualizados hace…" de la barra lateral no es decorativo, cuenta ese intervalo real.

## Documentación relacionada

- [`../docs/DASHBOARD-VISTAS.md`](../docs/DASHBOARD-VISTAS.md) — de qué tabla real sale cada vista y cómo construirla en serio. Léelo antes de tocar este HTML en profundidad.
- [`../docs/REGISTRO.md`](../docs/REGISTRO.md) — `D-09` registra la decisión pendiente sobre qué tan lejos llega F8 (solo lectura vs. absorber también las escrituras que este prototipo muestra).
