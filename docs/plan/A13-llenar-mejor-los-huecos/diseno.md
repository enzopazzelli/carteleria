# A13 · Llenar mejor los huecos — diseño

> **Estado:** escrito el 2026-10-23, después de una prueba descartable que Enzo pidió (§2). **Aprobado por Enzo ese día** («Si»). El plan está en [`plan.md`](plan.md). **Construido el 2026-10-23** en la rama `feat/llenar-huecos`, las tres tareas con pausa al final de cada una, sin fusionar en `main`. Cómo quedó y lo medido, en §8. Al escribir el plan cambió cómo se usa la cuadrícula (§5.1, puntos 2, 3 y 5).
>
> **De dónde sale.** Enzo, el 2026-10-23, probando la app: «vi que había huecos que estaban siendo aprovechados pero podían meterse alguna pieza más dentro». Es el paso 9 de «Lo que sigue» en el [`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md). Resuelve dos pendientes de aprovechar huecos primero (A10): a lo sumo 17 piezas por hueco, y que con giro libre no se pruebe dar vuelta una pieza adentro de un hueco. Es del motor, por eso lleva la letra A.
>
> **Sobre los valores.** No agrega parámetros al [`REGISTRO.md`](../../REGISTRO.md): el tamaño de las casillas y el paso de los giros son detalles internos de la búsqueda, como lo era la grilla de 4 × 4 que reemplazan. El área mínima de un hueco sigue siendo `PAR-39`.

---

## 1. Para qué

Que entren más piezas adentro de los huecos de las otras. Lo que va adentro de un hueco no ocupa chapa: con el parador queda un sobrante más grande, y en un trabajo grande puede ahorrarse una chapa.

Enzo acepta que el anidado tarde **uno o dos minutos más** por esto.

## 2. Punto de partida

**Cómo trabaja hoy** (`huecos_primero.py`, de A10). Antes de acomodar, se recorren los huecos del más grande al más chico. Para cada uno se prueban las piezas de la de más área a la de menos. Cada pieza se lleva a unos pocos puntos del hueco (el centro y una grilla de 4 × 4, del más cercano al centro al más lejano), con hasta cuatro giros (0°, 90° y los dos del hueco). Se queda en el primer lugar donde entra. Por eso:

- **La primera pieza va al medio del hueco** y lo parte en pedazos donde después no entra casi nada.
- **Hay pocos lugares** (17 como mucho) **y pocos giros**: nunca se prueba la pieza dada vuelta.

**La prueba descartable** (2026-10-23, `backend/local/herramientas-huecos-2026-10-23/spike.py`, fuera de git) hizo otra búsqueda: el hueco como una cuadrícula de casillas de 4 mm, todos los lugares donde entra cada pieza en cada giro de una sola cuenta, la pieza en el lugar más abajo y a la izquierda, y el control con la geometría exacta. Con el parador:

| | Hoy | Prueba |
|---|---|---|
| Piezas adentro de huecos | 19 | **30** |
| Material adentro | 0,246 m² | **0,361 m²** |
| Parte de los huecos usada | 20,8 % | **30,5 %** |
| Tiempo de este paso | 2,4 s | 39 s |

- Con casillas de 3 mm y giros de a 10°, las mismas 30 piezas en 112 s: más fino no gana.
- Con Complejo no entra ninguna pieza en sus 17 huecos, ni hoy ni con la prueba (son más chicos que cualquier pieza), pero la prueba tardó 24 s en descubrirlo.

## 3. Lo que decidió Enzo (2026-10-23)

| Pregunta | Decisión |
|---|---|
| Qué se busca | **Que entren más piezas en los huecos que ya se usan**: «podían meterse alguna pieza más» |
| Cuánto más puede tardar | **«Quizá un minuto o 2»** |
| Cómo se busca | **Lo de la prueba** (§2), aprobado al pedir el diseño: casillas, la pieza contra la pared, más giros |

## 4. Alcance

**Entra:** la búsqueda adentro de cada hueco (`huecos_primero.py`): dónde y con qué giro va cada pieza. Lo que entra y lo que sale de `meter_en_huecos` no cambia.

**Queda afuera:**
- el orden en que se prueban las piezas (de la de más área a la de menos, como hoy) y el orden de los huecos (del más grande al más chico). Probar otros órdenes podría ganar más; queda para después de medir esto *(decisión mía)*;
- todo lo demás del anidado: Sparrow, el reparto en chapas, vaciar chapas, Ajuste y el DXF.

## 5. Cómo funciona

### 5.1 La búsqueda en un hueco

Para cada hueco, mientras entre alguna pieza:

1. **Lo libre:** el hueco achicado en la separación entre piezas (`gap`, como hoy), menos lo ya puesto en él, agrandado en `gap`.
2. **La cuadrícula:** casillas sobre el rectángulo de lo libre, **de 4 mm como mucho**, más chicas en un hueco chico, para que el lado corto de su rectángulo mínimo tenga unas 20 casillas. Una casilla cuenta libre si su centro cae adentro de lo libre.
3. **Cada pieza, en cada giro:** su contorno exterior girado y pasado a casillas del mismo tamaño (las que tienen el centro adentro). Una sola correlación por FFT entre las dos cuadrículas da, de una vez, todos los lugares donde la pieza no pisa ninguna casilla ocupada. La cuadrícula **propone** lugares; no decide. *(Al escribir el plan: la prueba achicaba lo libre y agrandaba la pieza media casilla para ir a lo seguro, pero así se pierden unos 6 mm por lado con casillas de 4 mm, y una pieza que entra justa, como las de las pruebas de A10, no aparecía nunca.)*
4. **Dónde va:** en el lugar más abajo y, entre esos, el más a la izquierda, en el marco de la pieza dueña del hueco. Así queda contra la pared y lo libre que sobra queda junto.
5. **El control exacto:** la pieza tiene que quedar adentro del hueco achicado y a no menos de `gap` de lo ya puesto, con la geometría de verdad (`shapely`). Se prueban, en el orden del punto 4, los primeros **20** lugares que propone la cuadrícula; si ninguno pasa, se sigue con otro giro.
6. Las piezas se prueban de la de más área a la de menos, y la primera que entra se pone. Después se vuelve a empezar con lo que quedó libre.

Solo con `numpy` (ya viene con `shapely`) y `shapely.contains_xy`. **No se suma ninguna biblioteca** *(decisión mía: `scipy` está en esta máquina, pero el proyecto no la declara)*.

### 5.2 Los giros

- **Con giro libre:** de 0° a 345° de a **15°**, más los cuatro del hueco (el ángulo de su rectángulo mínimo y sus cuartos de vuelta). Se prueba la pieza dada vuelta.
- **Con veta o sin giro libre:** solo los giros permitidos, como hoy. El control final del anidado rechaza cualquier otro.
- Una pieza grande (A11) adentro de un hueco puede quedar en un ángulo que no está en su lista. Está bien, porque va adentro de su contenedora, como ya decía A11.

### 5.3 Rápido cuando no entra nada

Complejo tiene que seguir tardando segundos en este paso, no 24 s. Antes de armar cuadrículas se descarta lo que no puede entrar:
- **la pieza entera:** si su material es más que lo libre, o si el círculo más grande que cabe en su contorno exterior (sin sus propios huecos: lo que tiene que entrar es la silueta entera) no cabe en lo libre del hueco. Una pieza que contiene un círculo de radio *r* no entra en un hueco donde no cabe uno de ese radio. Se calcula una vez por pieza y por hueco;
- **cada giro:** si su rectángulo no entra en el de lo libre.

El constructor puede sumar otros descartes; lo que se pide es el tiempo de §6, tarea 3.

### 5.4 El tiempo

- **Hasta la mitad del tiempo máximo del anidado**, como hoy (`seguir`). Hoy se mira entre un hueco y otro; ahora también entre una pieza puesta y la siguiente, para que un hueco grande no se pase.
- **La barra** sigue diciendo «Metiendo piezas en los huecos: 12 de 39», hueco por hueco.

### 5.5 Lo que no cambia

- `meter_en_huecos` devuelve lo mismo (`Adentro`: pieza, contenedora, giro y corrimiento) y `expandir` no se toca.
- Una pieza que ya tiene algo adentro no entra en otro hueco, y una pieza puesta en un hueco recibe después las suyas (los huecos van del más grande al más chico), como hoy.
- Se deja de comparar «el plan con la primera pieza y el plan sin ella», que hoy duplica el trabajo de cada hueco *(decisión mía: la prueba ganó 11 piezas sin eso; si se pierde algo, se ve en la medición)*.

## 6. Tareas

1. **La búsqueda nueva** (`huecos_primero.py`, §5.1 a §5.3). Pruebas:
   - en un hueco cuadrado con lugar de sobra para cuatro cuadrados, uno por esquina (por ejemplo, de 40 × 40 en un hueco de 100 × 100), entran los cuatro; hoy el primero va al centro y no entra ninguno más. La cuadrícula pierde unos milímetros por lado, así que la prueba no usa medidas justas;
   - una pieza que solo entra dada vuelta (por ejemplo una «L» en un hueco en «L» girado 180°) entra con giro libre;
   - con veta, todas las de adentro quedan en 0° o 180°;
   - lo de adentro nunca pisa la pared del hueco ni queda a menos de `gap` de otra;
   - si no entra nada, no devuelve nada;
   - las pruebas que ya existen de A10 siguen pasando.
2. **El tiempo** (§5.4): la búsqueda corta a la mitad del tiempo máximo también adentro de un hueco, y la barra sigue avanzando hueco por hueco.
3. **Medir y cerrar,** sobre una copia de la base:
   - **el parador:** al menos 30 piezas adentro, este paso en menos de un minuto, y el anidado entero en no más chapas que hoy;
   - **Complejo:** este paso en menos de 5 s, y el anidado igual que hoy;
   - **el recorrido en la pantalla:** la barra, el resultado y Ajuste moviendo una pieza con lo de adentro;
   - **los documentos**, y los dos pendientes de A10 que esto resuelve.

## 7. Riesgos

- **Más piezas adentro no siempre es menos chapa:** si lo que entra son piezas chicas que de todos modos cabían afuera, se gana sobrante pero no chapa. Se mide con el anidado entero.
- **Tiempo con muchos huecos grandes:** el parador tiene 28 huecos y tardó 39 s. Un trabajo con el doble podría llegar al tope de la mitad del tiempo máximo; ahí la búsqueda corta y sigue con lo que tenga, como hoy.
- **La cuadrícula** propone lugares cada una casilla: un lugar justo que cae entre dos casillas puede no aparecer. Las casillas más chicas en los huecos chicos y los 20 lugares probados lo achican, y las pruebas de A10 con medidas justas lo cuidan. La medición compara piezas adentro con lo de hoy y con lo nuevo.

## 8. Cómo quedó (2026-10-23)

**El código.** En `huecos_primero.py`, `_llenar_hueco` reemplaza a la grilla de 4 × 4, `_intentar` y `_llenar` (con sus dos planes). Lo arman `_casilla` (el lado de las casillas para lo libre), `_mascara` (las casillas con el centro adentro), `_angulos` (de a 15° más los del hueco, o los fijos) y `_tamano_rapido`. Los descartes antes de armar cuadrículas: el material contra lo libre, el círculo más grande de la pieza contra el de lo libre y el rectángulo de cada giro. `seguir` se consulta antes de cada hueco y antes de cada pieza. La firma de `meter_en_huecos`, `Adentro` y `expandir` no cambiaron.

**Desvíos.**
- **La cuadrícula propone y no decide** (§5.1), y **las casillas se achican en un hueco chico**. Se cambió al escribir el plan: la de la prueba perdía unos 6 mm por lado y no veía las piezas que entran justas.
- **Tamaños rápidos para la FFT** (`_tamano_rapido`): la cuadrícula se agranda con ceros hasta un tamaño con factores 2, 3 y 5. Con Complejo, este paso bajó de 8,6 s a 4,5 s, y con el parador de 15 a 5 s, con el mismo resultado.
- **La cuadrícula de lo libre se arma recién cuando una pieza pasa los descartes:** en un hueco donde no entra nada no se arma ninguna.
- **Una medición mal hecha, corregida:** el cálculo de Sparrow corre en un proceso aparte que carga el código de la carpeta desde donde se lanza. Las primeras corridas «de `main`» se lanzaron desde la rama y usaron el código nuevo. Se repitieron desde una copia de `main`.

**Medido** sobre una copia de la base de la reunión (`backend/local/tmp-a13/medicion/`), con `backend/local/herramientas-a13-2026-10-23/paso_huecos.py` y `medir.py`, fuera de git.

| | `main` | Con este cambio |
|---|---|---|
| Parador, solo este paso | 19 piezas adentro (0,246 m²), 2,4 s | **31 piezas adentro (0,367 m²), 5,2 s** |
| Complejo, solo este paso (no entra nada) | 0, 0,1 s | 0, **4,7 s** |
| Parador, el anidado entero (sobrante arriba) | 1 chapa, 20 adentro; usa 1220 × 1931 y sobra **1220 × 509** | 1 chapa, 30 adentro; usa 1220 × 1679 y sobra **1220 × 761**; 10,5 s |
| Complejo, el anidado entero | 7 chapas, 232 s | 7 chapas, 238 s |

- **Con el parador, el sobrante crece un 50 %** (de 509 a 761 mm de alto) y no se gasta más chapa. Con Complejo no cambia nada: sus huecos son más chicos que cualquier pieza.
- **Lo que pedía §6:** parador con al menos 30 adentro y este paso en menos de 60 s, sí (31, 5 s); Complejo en menos de 5 s, sí (4,5 a 4,7 s, justo).
- **El recorrido de la pantalla** (`recorrido-a13.mjs`, capturas al lado) salió todo BIEN y sin errores en la consola: la barra dice «Metiendo piezas en los huecos», el resultado avisa «30 piezas van adentro de huecos de otras», y en Ajuste una figura con 7 piezas adentro se movió junto con ellas.
- Backend: 843 pruebas en verde.

**Lo que quedó vivo.**

| Pendiente | De dónde sale | Depende de |
|---|---|---|
| Todavía queda libre cerca del 70 % de los huecos del parador. Probar otro orden de piezas (no solo de la más grande a la más chica) o varios órdenes podría meter más | §4 | Medir si vale el tiempo |
| Con Complejo este paso tarda 4,5 s en descubrir que no entra nada, justo debajo de lo pedido: un trabajo con muchos más huecos chicos podría pasarse | §8 | Que aparezca un caso |
| Repetir las mediciones con varias corridas: cada una se hizo una vez | §8 | — |

