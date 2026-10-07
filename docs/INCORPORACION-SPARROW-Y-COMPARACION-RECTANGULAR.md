# Incorporación de Sparrow y diferencias con el motor rectangular

Documento de la implementación local de Cartelería. Actualizado el 4 de octubre de 2026.

## Qué aporta Sparrow

Sparrow incorpora un anidado irregular: busca acomodar las siluetas exteriores reales de las piezas en las planchas. El motor rectangular reserva un rectángulo envolvente para cada pieza, aunque dentro de ese rectángulo haya mucho espacio vacío.

Por ejemplo, una letra, un círculo o una estrella ocupan menos superficie que su rectángulo envolvente. Sparrow puede acercar otras piezas a sus contornos y aprovechar espacios que el rectangular reserva como ocupados. Esto puede reducir el material consumido, pero no garantiza un mejor resultado en todos los trabajos.

La integración usa el paquete Python `spyrrow==0.9.0`. En la app se identifica como **Sparrow irregular (prueba)** y en la API como `sparrow`. Rectpack permanece disponible como `rectpack`. La interfaz inicia con Sparrow en Grupos y Anidado; la API conserva Rectpack por defecto si no se especifica motor.

## Diferencias principales

| Aspecto | Rectangular — Rectpack | Irregular — Sparrow integrado |
|---|---|---|
| Forma utilizada para buscar | Ancho y alto de cada pieza: rectángulo envolvente | Contorno exterior real, con simplificación conservadora opcional |
| Espacios entre contornos | Reserva toda la celda rectangular | Puede aprovechar espacios exteriores entre formas irregulares |
| Formas recomendadas | Placas rectangulares y estimaciones rápidas | Letras, círculos, estrellas y contornos irregulares |
| Rotación automática | Intercambia ancho y alto cuando está permitido | Prueba 0°, 90°, 180° y 270°; con restricción de veta, 0° y 180° |
| Repetición | Determinista con las mismas entradas y algoritmo | Configurable por semilla; el límite temporal y los workers pueden producir diferencias entre corridas |
| Cálculo | Generalmente más rápido; puede demorarse con muchas piezas | Realiza búsquedas temporizadas y validación geométrica; suele ser más costoso |
| Búsqueda de alternativas | Una heurística de empaquetado | Hasta varios intentos con semillas diferentes |
| Huecos interiores | No los aprovecha en el empaquetado principal | Tampoco los aprovecha en la búsqueda principal actual |
| Óptimo global | No garantizado | No garantizado |

Rectpack usa **MaxRectsBssf** en el anidado habitual. Para comparar grupos de más de 500 instancias usa **GuillotineBssfSas**, que acelera la estimación. Por eso la comparación rectangular rápida puede diferir de la ejecución rectangular posterior.

**Sparrow no usa rotación libre continua en esta integración.** Que admita formas irregulares no significa que la app explore cualquier ángulo.

## Cómo se incorporó

1. La API recibe el motor y sus opciones, obtiene las piezas del grupo y los parámetros de corte, y comprueba que todas puedan entrar en el formato.
2. Se expanden las cantidades: cada unidad de cada pieza debe tener una colocación propia.
3. Sparrow se ejecuta en un proceso Python aislado. El supervisor puede terminarlo al cancelar o alcanzar el tiempo máximo.
4. La integración resuelve una franja de altura fija, selecciona las piezas completas que caben en el ancho de una plancha y vuelve a calcular con las restantes. No corta piezas para hacerlas entrar.
5. Se prueban distintas semillas. Entre resultados completos y válidos se priorizan menos planchas; en empate, menor suma de áreas de los rectángulos que delimitan las piezas de cada plancha.
6. Se validan todas las colocaciones y se guardan mediante el mismo contrato utilizado por Rectpack. El resultado llega al historial, Ajuste, SVG, DXF y Costeo.

El desempate busca una distribución más compacta; **no mide directamente la calidad ni el valor de los retazos reutilizables**. La extracción por planchas tampoco equivale a una optimización conjunta de todas las planchas.

Los mejores resultados completos se escriben de forma atómica. Si se agota el tiempo después de obtener uno, el supervisor puede conservarlo tras validarlo, con una advertencia. Si no hay un resultado completo, devuelve un error; nunca presenta un plano parcial como válido. Una cancelación solicitada termina la ejecución.

## Parámetros y validaciones

| Opción de API | Valor inicial | Rango |
|---|---:|---:|
| `semilla` | 42 | 0–2147483647 |
| `segundos_por_busqueda` | 2 | 1–30 s |
| `tiempo_maximo_s` | 120 | 5–300 s |
| `workers` | 2 | 1–2 |
| `simplificacion_mm` | 0,3 | 0–2 mm |
| `intentos` | 3 | 1–8 |

La interfaz expone las opciones principales; `workers` e `intentos` también pueden configurarse mediante la API. Puede hacer menos intentos si alcanza la cota inferior por área exterior o se agota el tiempo. Más tiempo puede mejorar la búsqueda, sin asegurar menos planchas.

Ambos motores consideran tres valores independientes: kerf o ancho del corte, margen de borde y separación adicional. Sparrow reserva medio kerf en el borde y medio `kerf + separación` por lado entre piezas. Antes de aceptar el resultado comprueba:

- Demanda completa, sin unidades faltantes ni duplicadas.
- Coordenadas finitas, índices de plancha consistentes y rotaciones permitidas.
- Contención dentro del área útil de la plancha.
- Ausencia de superposiciones y cumplimiento de la separación, con las tolerancias numéricas del validador.

La simplificación sirve para buscar y no sustituye los contornos guardados ni exportados. Se acepta una aproximación conservadora que cubra el exterior original y entre en el formato; el resultado se valida contra la geometría original normalizada.

## Agujeros y contornos problemáticos

Sparrow busca con la silueta exterior: los agujeros interiores no quedan disponibles para colocar otras piezas en esa búsqueda. La casilla **Aprovechar huecos** activa una pasada adicional de la app, después del motor, con una nueva validación. Esta pasada no garantiza eliminar planchas y no está disponible en la comparación de formatos.

Para huecos superpuestos o tangentes, la app calcula el material como exterior menos la unión de los huecos. Solo permite esta normalización si el exterior y cada hueco son válidos, los huecos están contenidos y el material resultante sigue siendo una única pieza válida. Conserva los contornos originales y muestra los IDs afectados. Si no puede resolver la geometría, informa el error y permite revisar las piezas; no las excluye silenciosamente.

## Comparación, visualización y costeo

En **Grupos**, se seleccionan formatos candidatos y el motor. La interfaz recomienda el que consuma menos m² de planchas completas; en empate, menos planchas y después menor costo. El costo aparece por separado. La API también admite el criterio de costo.

La comparación usa los parámetros del catálogo de cada material y procesa los candidatos en serie. No guarda planos ni ejecuciones: después de **Usar este**, hay que ejecutar Anidado. Si el grupo tiene parámetros de corte personalizados, o cambian las opciones o la búsqueda temporal, la corrida posterior puede diferir.

En **Anidado** y **Costeo** se muestran material, formato, planchas, consumo total, aprovechamiento y plano por plancha, con zoom y descarga DXF. Se guardan las dimensiones y el material de la ejecución para preservar la referencia del plano histórico. Si cambia el formato elegido, Costeo no combina el plano anterior con el material nuevo: pide recalcular.

El consumo se calcula como:

```text
Material consumido (m²) = planchas × ancho (mm) × alto (mm) / 1.000.000
Aprovechamiento (%) = área de material de las piezas / área total de planchas × 100
```

Un porcentaje más alto no asegura menor consumo ni menor costo. Además, la comparación rectangular rápida calcula su aprovechamiento con los rectángulos envolventes; Sparrow lo calcula con las geometrías reales. Estos porcentajes no deben interpretarse como equivalentes cuando hay formas irregulares o agujeros. El área sin piezas tampoco equivale íntegramente a retazo recuperable.

## Resultado verificado en el trabajo Belgrano

El archivo Corel permitió verificar 409 correspondencias de dimensiones y detectar que el DXF utilizado en la primera prueba estaba a una escala diez veces menor. Se conservó el trabajo original y se creó una copia a escala real con 1023 piezas.

En la comparación real del 4 de octubre, con Sparrow, semilla 42, búsqueda de 2 s, máximo de 120 s por formato y simplificación de 0,3 mm:

| Formato | Planchas | Material consumido | Aprovechamiento real |
|---|---:|---:|---:|
| 1220 × 2440 mm | 2 | 5,9536 m² | 39,5 % |
| 1000 × 2000 mm | 3 | 6,0000 m² | 39,2 % |

El primer formato ahorró 0,0464 m², aproximadamente un 0,77 %, en esta corrida. No es una medición de ahorro frente a Rectpack: ambos resultados de la tabla fueron calculados con Sparrow. Para cuantificar la diferencia entre motores hace falta probarlos sobre las mismas piezas, escala, formato y parámetros.

La ejecución guardada #5, del formato 1000 × 2000, tiene 1023 colocaciones. Se verificaron el plano y la exportación DXF. Los precios del catálogo DEMO son simulados y no constituyen una cotización real.

## Archivos principales y pruebas

- `backend/app/services/nesting/sparrow.py`: entrada, supervisor y validación.
- `backend/app/services/nesting/sparrow_worker.py`: búsqueda y selección de alternativas.
- `backend/app/services/nesting/geometria_material.py`: normalización controlada de huecos.
- `backend/app/services/nesting/engine.py`: motor rectangular.
- `backend/app/services/nesting/comparador.py`: comparación rectangular y recomendación.
- `backend/app/api/rutas_nesting.py`: integración de motores, ejecuciones y comparación.
- `frontend/src/components/ResumenAnidado.tsx`: material, consumo y vista del plano.
- `backend/app/costeo.py`: relación entre plano, formato y costo.

La prueba inicial completa pasó 340 tests del backend y 8 del frontend. Después de corregir la selección de corridas y la compatibilidad entre plano y formato, pasaron 66 tests de costeo y presupuesto, incluidos dos nuevos de regresión. TypeScript compiló sin errores. Estos resultados documentan lo comprobado; no certifican un mínimo global de material ni sustituyen la confirmación de escala y parámetros de fabricación.
