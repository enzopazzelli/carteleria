# Sparrow integrado: guía de pruebas

Modificación del 01/10/2026 en la copia carteleria-main/carteleria-main.

## Qué se incorporó

Motor irregular Sparrow/Spyrrow 0.9.0 seleccionable en Anidado. Rectpack sigue como opción inicial. No requiere migración: usa el campo motor, las opciones y las colocaciones existentes.

Permite configurar semilla, segundos por búsqueda, tiempo máximo total y simplificación conservadora. Muestra motor y duración en historial; permite cancelar la ejecución activa. El resultado llega al ajuste, plano, DXF y costeo mediante el contrato existente.

El cálculo vive en un proceso aislado; el supervisor lo termina al cancelar o agotar tiempo. No persiste un resultado parcial como válido. Se verifican demanda completa, rotaciones, colisiones, separación y reserva de borde sobre contornos originales. Piezas que no entran fallan antes de encolar. La API guarda las opciones para comparar corridas.

Spyrrow no anida dentro de agujeros por sí mismo. La casilla Aprovechar huecos ejecuta la pasada existente después y se valida de nuevo; no garantiza eliminar chapas. Los materiales con veta conservan restricción 0/180. La simplificación no altera los contornos exportados.

## Cómo probar

1. Preparar backend con el entorno indicado en README, instalando backend/requirements.txt actualizado, y ejecutar migraciones y API. Preparar frontend con npm ci y npm run dev.
2. Importar un DXF y revisar qué formas son piezas a cortar, cantidades, escala y grupos; el motor no clasifica rótulos o marcos.
3. En Anidado seleccionar Sparrow irregular (prueba). Inicio sugerido: semilla 42, búsqueda 2 s, máximo total 120 s, simplificación 0,3 mm. Probar después semillas 7 y 123; comparar material y duración. Una semilla con límite temporal y workers no garantiza posiciones idénticas en máquinas diferentes.
4. Indicar los parámetros de corte reales. El kerf confirmado es 3 mm; margen y separación adicional siguen sin confirmar. No se modificaron los parámetros del catálogo ni se asumió que todos los materiales usan 3 mm.
5. Anidar, revisar el historial y abrir Ajuste para inspeccionar colocaciones. Comparar con Rectangular antes de marcar definitiva. Cambiar parámetros crea otra corrida; no borra las anteriores.
6. Probar Cancelar y probar un tiempo máximo corto. La cancelación termina el worker en cuanto el supervisor la detecta, normalmente dentro de un ciclo de 0,1 s, más demora del sistema.

## Belgrano

Las cuatro cuñas de 1220 mm de alto no entran cuando se reserva medio kerf de 3 mm a cada borde. Sparrow devuelve un error con IDs afectados; nunca se descartan silenciosamente. Resolver con taller si utilizan borde de fábrica, otro formato o seccionado. Esta integración mantiene la regla actual de borde y no implementa excepciones de fábrica.

Para reproducir solo la comparación histórica se pueden usar parámetros cero, identificando claramente la corrida como experimental. Ocho chapas con parámetros cero no valida fabricación con kerf 3.

## Verificación

Pruebas de demanda, rotación, geometría, kerf, worker real, cancelación, timeout y API. Compilación TypeScript/Vite y tests frontend. Resultado de la prueba real integrada en VERIFICACION-MOTOR-INTEGRADO.json, en la raíz del workspace.

## Límites del prototipo

Corrección del 03/10/2026: cuando los anillos de huecos se superponen o son tangentes, se calcula el material como exterior menos la unión de los huecos. Solo se admite esta normalización si el exterior y cada hueco son válidos, están contenidos y el material queda como una única pieza. No se modifican los contornos guardados ni se omiten piezas. Se muestra un aviso con los IDs normalizados. Las geometrías que no admiten esta operación muestran un diagnóstico junto al comparador y un enlace para revisar las piezas afectadas.

La reserva de separación se aplica al contorno de búsqueda con medio gap por lado, evitando un fallo del offset nativo con contornos pequeños. Se valida nuevamente cada colocación contra el material original normalizado, el borde y la distancia mínima. La prueba completa local incluyó las 1.023 piezas del grupo CArtel y devolvió ambos formatos, sin exclusiones.

La comparación de formatos permite elegir Sparrow (opción inicial en Grupos) o Rectangular. Sparrow compara los contornos reales con semilla, búsqueda por chapa, tiempo máximo por formato y simplificación configurables. Usa los parámetros del catálogo de cada material, sin la pasada en huecos; se validan todos los candidatos antes de iniciar búsquedas. Los formatos se calculan en serie y el máximo se aplica a cada uno; la validación geométrica posterior agrega tiempo. La comparación no guarda planos ni ejecuciones: después de «Usar este», ejecutar Sparrow en Anidado con las opciones deseadas. Rectangular usa una heurística rápida para grupos de más de 500 instancias.

La búsqueda multi-chapa es una extracción por área con recálculo, no un mínimo global. El supervisor limita cada ejecución, pero la cola local existente sigue sin límite global de concurrencia. El modo sigue siendo local de pruebas, sin login ni despliegue productivo.
