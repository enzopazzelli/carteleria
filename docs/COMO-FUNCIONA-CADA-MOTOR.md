# LOS DOS MOTORES DE NESTING: CÓMO FUNCIONA CADA UNO Y QUÉ DA CADA UNO

> Guía para decidir con cuál avanzar. No es un plan ni una decisión tomada: es la explicación de las dos máquinas que hoy conviven en el repositorio, y de qué las diferencia de verdad.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`PLAN-MOTOR-NESTING-DEEPNEST.md`](PLAN-MOTOR-NESTING-DEEPNEST.md) · [`PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](PLAN-MOTOR-NESTING-PYTHON-NATIVO.md) · [`GUIA-PRUEBAS-LOCALES.md`](GUIA-PRUEBAS-LOCALES.md) · [`REGISTRO.md`](REGISTRO.md)
>
> **Versión:** 1.1 · **Fecha:** 2026-09-08 (corrección de escala: 2026-09-11)

---

> ⚠️ **`carrusel.dxf`/`repisas.dxf` no son diseños del cliente (2026-09-14).** Se bajaron de internet como contenido genérico para poder probar el pipeline sin esperar archivos reales — Enzo confirmó que el trabajo real de la cartelería es de otra escala (chapas de ~2 m, letras corpóreas y paneles grandes, no decoraciones de centímetros). **Ningún número de este documento —planchas usadas, % de aprovechamiento, tamaño de sobrante— representa un trabajo real, a ninguna escala.**
>
> Lo que sí sigue siendo válido, y es la razón por la que este documento no se borra: la **mecánica** de cada motor — cómo compacta cada uno, cómo se comporta el corte compartido, por qué Deepnest gana cuando el material aprieta y empata cuando sobra plancha. Esas relaciones no dependen de qué se esté cortando. Los números puntuales (2 planchas vs 1, 800×800 mm, etc.) quedan como *ilustración de la mecánica*, no como benchmark de producción.
>
> (De paso, al convertir los `.cdr` originales de estos tres archivos —`SPIKE-CDR.md`— se encontró que además la escala que se venía usando estaba mal: `10` en vez de `1`. Quedó corregido en `GUIA-PRUEBAS-LOCALES.md`, aunque ya no es el punto central: el problema no era solo la escala, era que estos archivos nunca representaron el trabajo real.)
>
> **El benchmark real espera a tener geometría de corte real del cliente** — `Muestra Vectores.cdr` es la primera muestra real que hay, pero es un panel de referencia/portfolio, no confirmado todavía como un trabajo para anidar (ver `SPIKE-CDR.md`).

---

## Cómo probarlos vos mismo

```powershell
cd nesting-engine
npm install                          # una sola vez
cd ../backend
python -X utf8 scripts/comparar_motores.py --dxf "../modelos/repisas.dxf" --escala-a-mm 1 --catalogo local/catalogo_chapa.json --repetir 4 --piezas-rectas --out local/comparacion.html
```

> Los comandos de esta guía van **en una sola línea**. En PowerShell el `\` no continúa la línea (eso es bash): si hace falta cortarlos, el carácter es la comilla invertida `` ` ``. El `-X utf8` es solo para que la consola muestre bien los acentos.

Corre los dos motores sobre las mismas piezas, con los mismos `PAR-01/02/03/04`, imprime la tabla comparativa y deja un HTML con los dos anidados lado a lado. Todo local, nada sale de tu máquina.

Tres flags que cambian mucho el resultado y conviene entender antes de sacar conclusiones:

- **`--repetir N`** — cantidad de cada pieza. Con una sola unidad de cada una, los dos motores suelen entrar en una plancha y **la comparación no distingue nada** (ver "La trampa de la métrica" más abajo). Los trabajos reales repiten piezas.
- **`--piezas-rectas`** — declara que los contornos son tramos rectos de verdad. Sin esto, el corte de líneas compartidas **queda apagado**, y no por un bug: ver más abajo.
- **`--generaciones` / `--poblacion`** — el presupuesto de búsqueda de Deepnest. Es lo que domina el tiempo de cómputo.

---

## 1. `rectpack` — el motor que ya está andando

**Qué hace, en una frase:** acomoda **rectángulos** en una plancha, de forma determinista y casi instantánea.

**Cómo funciona.** Cada pieza entra al motor como su *bounding box* — el rectángulo más chico que la contiene. Es `ADR-01`, y es una decisión, no una limitación accidental: en cartelería la mayoría de lo que se corta son paneles rectos. El algoritmo es `MaxRectsBssf` (*best short side fit*): mantiene una lista de rectángulos libres y, para cada pieza, elige el hueco donde el lado corto sobrante es el menor. No hay búsqueda ni azar: una pasada, decisiones locales, resultado inmediato.

Los tres parámetros de corte se aplican por geometría, no como opciones del algoritmo (`engine.py`):

1. **Margen de borde** (`PAR-02`) achica el área útil de la plancha antes de empezar.
2. **Kerf** (`PAR-01`) infla cada pieza medio kerf por lado. Cuando dos piezas quedan contiguas, los dos medios kerf se combinan en el único corte que las separa.
3. **Separación** (`PAR-03`) agrega espacio extra encima del kerf, nunca en su lugar.

**Qué te da:**

- **Determinismo garantizado.** Las mismas piezas dan siempre el mismo anidado. `engine.py` lo dice sin vueltas: *"es un requisito de adopción del sistema (`CART-202`): si el número cambia solo, nadie confía en él"*. Un presupuesto que cambia de precio al recalcularlo destruye la credibilidad ante el taller.
- **Velocidad.** Milisegundos. Cumple `PAR-25` con muchísimo margen.
- **Ninguna infraestructura.** Es una librería Python adentro del mismo proceso. Sin contenedor, sin segundo lenguaje, sin nada que mantener.
- **Nunca descarta piezas en silencio.** Si algo no entra, falla ruidosamente (`DECISIONES §1.2`).

**Qué NO te da:**

- **No ve la forma real.** Una letra "C" ocupa el rectángulo completo aunque sea casi todo aire. Todo lo que se pierde entre la silueta y su rectángulo es desperdicio que el motor no puede recuperar.
- **No anida dentro de huecos.** El *packer* solo sabe de rectángulos libres; el agujero de una "O" no es uno de ellos.
- **No optimiza el corte compartido.** Un packer tipo guillotina *tiende* a alinear bordes por su propia mecánica, pero no lo busca ni lo mide.
- **Solo rota 0°/90°.** `ADR-01`.

**Lo que se le agregó encima** (`anidado_huecos.py`, la Capa 2 de [`PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](PLAN-MOTOR-NESTING-PYTHON-NATIVO.md)): una segunda pasada *greedy* que, sobre el resultado ya anidado, intenta meter piezas chicas dentro de los agujeros reales de las ya colocadas. Prueba una grilla de posiciones y varios ángulos, y compara dos planes por hueco. **No es una optimización conjunta** — es un rescate posterior, sobre decisiones que el packer ya tomó mirando solo rectángulos.

---

## 2. Deepnest — el motor del spike

**Qué hace, en una frase:** acomoda **siluetas reales** mediante una búsqueda evolutiva, aceptando gastar tiempo de cómputo a cambio de apretar más.

**Cómo funciona.** Dos capas, y entender la diferencia entre ellas explica todo lo demás.

**Capa de abajo — colocación por NFP.** El *No-Fit Polygon* de dos piezas A y B es el polígono que describe todas las posiciones donde B tocaría a A sin superponerse. Se calcula con la diferencia de Minkowski. Con eso, "¿esta pieza choca acá?" deja de ser una intersección de polígonos y pasa a ser "¿este punto está adentro de este polígono?" — muchísimo más barato, y se puede cachear. Para colocar una pieza: se toma la región válida de la plancha, se le restan los NFP de todo lo ya colocado, y **se le vuelven a sumar los huecos interiores de esas piezas**. Ese último paso es, literalmente, el anidado en huecos: el agujero de una pieza ya colocada vuelve a ser espacio disponible.

Esta capa es *greedy*: coloca una pieza a la vez, en la mejor posición local según la estrategia elegida (`box` minimiza el bounding box, `gravity` comprime a la izquierda, `convexhull` minimiza la envolvente).

**Capa de arriba — algoritmo genético.** Como la capa de abajo es greedy, el resultado depende mucho del **orden** en que se colocan las piezas y del **ángulo** de cada una. El GA trata ese orden y esos ángulos como el genoma: arranca de una población, evalúa cada individuo corriendo la colocación completa, y cruza y muta los mejores. Cada generación son `población` anidados completos.

De ahí sale todo lo bueno y todo lo malo de este motor.

**Qué te da:**

- **Anida la silueta real, no el rectángulo.** Dos "C" pueden encastrarse una en la panza de la otra.
- **Anida dentro de huecos, como parte de la optimización.** No es un rescate posterior: el hueco es espacio válido desde el primer momento, y compite de igual a igual con el resto de la plancha.
- **Persigue el corte de líneas compartidas.** No lo detecta al final: el largo de línea compartida se **resta de la función de fitness**, así que el optimizador busca activamente layouts donde las piezas compartan borde. Cuánto pesa contra el ahorro de material se regula con `peso_corte_compartido` (0 = solo material, 1 = solo tiempo de máquina).
- **Rota a 0/90/180/270** (o 0/180 si el material tiene veta, `PAR-04`).
- **Se le puede pedir que amontone contra el ancho** (`orientacion="apilar_en_ancho"`). Por default ninguna de sus estrategias tiene preferencia por un eje útil: `box` y `convexhull` no tienen preferencia, y `gravity` comprime el ancho, o sea que sobre una plancha parada produce una columna alta y angosta y deja el sobrante como una tira fina al costado — inservible para re-stockear. Con esta opción se le manda la plancha transpuesta y se rota el resultado -90° al volver, así llena a lo ancho y el sobrante queda como una franja entera al final del largo. Medido sobre 10 piezas del carrusel en 1220 × 2440: pasa de ocupar 426 × 959 a **1142 × 419**, y el sobrante de una tira de 1481 mm a **1220 × 2021 de plancha limpia**.

  > Solo sirve para materiales **sin veta**. La rotación de -90° gira todas las piezas: {0, 90, 180, 270} es cerrado bajo esa operación, pero {0, 180} —lo legal con veta— pasaría a {90, 270}, o sea todas las piezas cortadas contra la veta. El cliente lo rechaza en vez de entregar un layout que el taller no puede cortar.

**Qué NO te da:**

- **No es rápido.** En las mediciones de abajo: decenas de segundos a minutos donde `rectpack` tarda milisegundos.
- **No es determinista por naturaleza.** El GA usa azar. En esta integración se lo hizo reproducible reemplazando `Math.random()` por un PRNG sembrado, y la semilla viaja en el resultado. Pero si algún día se corta por reloj en vez de por generaciones, la reproducibilidad se pierde de nuevo — es una decisión pendiente.
- **No sirve para piezas cargadas a mano.** Necesita contorno real. Una pieza de `CART-201` (alto × ancho tipeados) no tiene silueta que anidar.
- **Trae un runtime nuevo.** Node, más un contenedor, más un segundo lenguaje a mantener.

---

## 3. Lo que hay que entender antes de mirar los números

### La trampa de la métrica: el aprovechamiento no siempre distingue

El aprovechamiento se calcula como *área real de las piezas ÷ (planchas usadas × área de plancha)*. Si los dos motores colocan **todas** las piezas y usan **la misma cantidad de planchas**, el numerador y el denominador son idénticos en los dos — **el porcentaje da exactamente igual den el layout que den.** No es un empate: es una métrica que en ese caso no mide nada.

Esto importa porque el aprovechamiento es la métrica insignia del proyecto (`PAR-33`: +5 puntos contra el baseline `B-17`). **`PAR-33` solo puede distinguir a los motores en trabajos donde uno use menos planchas que el otro.**

Por eso la comparación agrega **compacidad**: cuánto del espacio que el layout *abarca* (el bounding box de lo colocado en cada plancha) es material de verdad. Un motor que aprieta más deja más plancha libre contigua al final.

### Y la métrica que de verdad importa para el flujo del taller: el sobrante útil

La compacidad tampoco alcanza, porque premia apretar sin mirar **qué forma tiene lo que sobra**. Y el flujo real —el operario deselecciona piezas, las manda a otra tanda, y el sistema re-anida con lo que queda (`CART-210`)— no se decide por lo apretado que quedó, sino por si sobró un pedazo de plancha **entero y utilizable**.

Por eso el comparador mide el **mayor rectángulo libre** de la plancha menos ocupada. Y el resultado da vuelta el ranking de la compacidad. Mismo trabajo (8 piezas distintas × 6 = 48 unidades del carrusel, chapa de 1220 × 2440):

| | rectpack | deepnest |
|---|---|---|
| Compacidad del layout | 52,32 % | **63,16 %** |
| **Mayor sobrante útil** | **740 × 620 mm** (15,4 %) | 220 × 2440 mm (18,0 %) |

**Deepnest aprieta más y sin embargo deja un sobrante peor.** Su sobrante tiene más área (18 % contra 15,4 %) pero es una tira de 22 cm de ancho: ahí solo entra una pieza de menos de 220 mm. El de `rectpack` es un bloque de 74 × 62 cm, donde entra casi cualquier cosa.

No es un accidente de configuración: las tres estrategias de Deepnest (`box`, `gravity`, `convexhull`) dan la misma forma de sobrante, una tira de 200-220 mm. Es consecuencia de cómo coloca —greedy por NFP, apoyando cada pieza contra lo ya colocado— que naturalmente llena desde un lado y arrincona lo que sobra contra el borde opuesto.

> **Dos límites de esta métrica, para no sobreinterpretarla.**
>
> 1. "El mayor rectángulo libre" es un proxy. La pregunta real es "¿entra la próxima tanda?", y eso depende de qué piezas tenga. Un sobrante de 220 × 2440 es excelente si lo que viene son listones largos y angostos.
> 2. **Solo compara a igualdad de planchas.** Se mide sobre la plancha menos ocupada, así que el motor que abre una plancha de más aparece con un sobrante enorme — que es exactamente la plancha que no debería haber abierto. Cuando el número de planchas difiere, la métrica que vale es el aprovechamiento. El comparador lo avisa en pantalla cuando pasa.

### El anidado en huecos existe, pero el motor solo lo usa bajo presión

Deepnest ofrece el hueco de una pieza colocada como espacio válido desde el primer momento. Lo que **no** hace es preferirlo: su función de fitness minimiza el *bounding box* de lo colocado, y una vez que una pieza grande fija ese rectángulo, meter una pieza chica en un hueco interior y apoyarla en un recoveco cóncavo del borde **puntúan exactamente igual**. Gana la posición que se evalúe primero.

Medido sobre la rueda real de `carrusel.dxf` (316 × 316 mm, ocho huecos de 98 × 68 mm):

| Escenario | Piezas dentro de un hueco |
|---|---|
| Rueda + 4 piezas chicas, chapa de 1220 × 2440 | **0** — las cuatro van a los recovecos cóncavos del borde de la rueda |
| Rueda + 24 piezas chicas, chapa de 340 × 340 | **8** |

Las dos son el comportamiento correcto. En el primer caso sobra plancha y las dos ubicaciones valen lo mismo; en el segundo, no usar los huecos obligaría a abrir otra plancha, y ahí el motor los usa.

Dos consecuencias prácticas:

1. **Un 0 en "piezas dentro de un hueco" no significa que la feature no funcione.** El comparador lo aclara en la salida cuando pasa.
2. **Aun sin usar los huecos, Deepnest está aprovechando espacio que `rectpack` no puede.** En el primer escenario las cuatro piezas chicas quedaron dentro del *bounding box* de la rueda, sin tocar su material: en las zonas cóncavas que un packer de rectángulos da por ocupadas. Eso ya es material recuperado.

### El corte compartido hay que declararlo

`mergedLength`, el detector de líneas compartidas, **ignora toda arista cuyos extremos no estén marcados como "recta real"**. No es un capricho: un tramo recto que en realidad es la discretización de una curva no se puede cortar de una sola pasada junto a otra pieza, aunque quede paralelo por casualidad.

El Deepnest original deduce esa marca dentro de su propio simplificador de polígonos, que depende de `@deepnest/svg-preprocessor` — la dependencia **AGPL** que este proyecto excluye a propósito. No es una pérdida: nosotros tenemos el dato mejor y de primera mano. `dxf.py` sabe si un tramo vino de un `LINE`/`LWPOLYLINE` (recto de verdad) o de discretizar un `ARC`/`SPLINE`/`CIRCLE`. Se declara en el contrato en vez de re-deducirse.

Mientras `dxf.py` no exponga ese dato, el flag `--piezas-rectas` lo declara para todas. **Sin ese flag el corte compartido da 0 y el motor lo avisa** — se eligió avisar en vez de simular que la feature funcionó.

---

## 4. Mediciones reales

Sobre `modelos/repisas.dxf` (16 piezas distintas, 4 con agujeros), escala 10, chapa de catálogo de 1220×2440 mm, con los `PAR-01/02/03` provisorios:

| | rectpack | deepnest | rectpack | deepnest |
|---|---|---|---|---|
| | **64 unidades** (×4) | | **128 unidades** (×8) | |
| Planchas usadas | 5 | 5 | 10 | 10 |
| Piezas colocadas | 64/64 | 64/64 | 128/128 | 128/128 |
| Aprovechamiento real | 63,39 % | 63,39 % | 63,39 % | 63,39 % |
| **Compacidad del layout** | 67,14 % | **79,43 %** | 67,95 % | **75,67 %** |
| Corte compartido | 0 mm | **23.104 mm** | 0 mm | **46.910 mm** |
| Tiempo | ~0,00 s | **93,55 s** | ~0,00 s | **124,49 s** |

Lo que dicen estos números:

- **Deepnest NO ahorró ni una plancha en ninguna de las dos corridas.** Es el resultado más importante de la tabla, y va en contra de lo que uno esperaría. La explicación es que `repisas.dxf` son paneles casi rectangulares: contra ese tipo de pieza, un packer de rectángulos ya está cerca de lo mejor posible, y anidar la silueta real no tiene nada que recuperar. **El aprovechamiento dio idéntico las dos veces — y `PAR-33`, la métrica insignia del proyecto, no distinguiría entre los dos motores en este trabajo.**
- **Deepnest sí aprieta más: 12 puntos de compacidad con 64 unidades, 8 con 128.** Deja más plancha libre contigua. Eso es potencial de ahorro, no ahorro realizado — se convierte en planchas menos solo si el trabajo tiene la mezcla de piezas adecuada.
- **47 metros de corte compartido** en el trabajo de 128 unidades son 47 metros que la máquina no repite. Es la única ventaja que Deepnest mostró de forma inequívoca. Cuánto vale en plata depende del costo por metro de corte — un dato que hoy no tenemos (no está en `REGISTRO.md`) y que hace falta para valuar la feature.
- **93 y 124 segundos contra milisegundos.** `PAR-25` pide 3 segundos para el trabajo de referencia de `PAR-26` (200 piezas / 20 planchas). El trabajo de 128 unidades es más chico que ese y ya tardó cuarenta veces más que el presupuesto. **Deepnest, tal como está, no cumple `PAR-25`.**

**La lectura de esta tabla, sola:** contra paneles rectos — que son el caso dominante de F2, "el corazón del proyecto" — Deepnest cuesta dos minutos y un runtime nuevo para ganar corte compartido y nada más.

### Y ahora el caso irregular, que da vuelta la conclusión

Sobre `modelos/carrusel.dxf` (piezas curvas, con agujeros reales), 15 piezas distintas × 3 = 45 unidades, misma chapa:

| | rectpack | deepnest |
|---|---|---|
| Planchas usadas | 1 | 1 |
| Piezas colocadas | 45/45 | 45/45 |
| Aprovechamiento real | 5,33 % | 5,33 % (degenerada otra vez) |
| **Compacidad del layout** | **32,07 %** | **61,11 %** |
| Corte compartido | 0 mm | 0 mm (piezas curvas: no hay rectas que compartir) |
| Tiempo | ~0,00 s | ~2 min |

> El presupuesto de búsqueda cambia el resultado y conviene tenerlo a la vista: con el default (3 generaciones, población 10) Deepnest da **61,11 %**; recortado a 2 y 6 da 59,54 %, y a 1 y 2 baja a 58,00 %. Más búsqueda, mejor layout, más tiempo — es la perilla principal del motor.

**Deepnest empaqueta estas piezas en algo más de la mitad del espacio que necesita `rectpack`** — 61,1 % de compacidad contra 32,1 %. Casi el doble. Es exactamente lo que la teoría predecía y lo que los paneles rectos no podían mostrar: contra siluetas curvas con agujeros, anidar el rectángulo desperdicia la mitad del material, y anidar la forma real no.

Que las dos entren igual en una plancha es un artefacto de la prueba: estas piezas son chicas contra una chapa de 1220×2440. En un trabajo donde el material fuera el límite, esa diferencia de compacidad **es** la diferencia en planchas.

### El caso que sí ahorra una plancha

Todas las mediciones de arriba se hicieron sobre la chapa del catálogo (1220 × 2440), donde el material nunca fue la restricción: entraba todo, y por eso el aprovechamiento no distinguía nada. Repitiendo el carrusel completo (47 piezas) sobre una plancha de **800 × 800**, donde el material sí aprieta:

| | rectpack | deepnest |
|---|---|---|
| **Planchas usadas** | **2** | **1** |
| Piezas colocadas | 47/47 | 47/47 |
| **Aprovechamiento real** | **26,94 %** | **53,88 %** |
| Compacidad del layout | 51,35 % | 58,55 % |
| Tiempo | ~0,00 s | 148,01 s |

**Deepnest ahorró una plancha entera y duplicó el aprovechamiento.** Es la primera medición de todo el spike en la que `PAR-33` distingue entre los dos motores — y lo hace por **+26,9 puntos porcentuales**, cuando el objetivo del proyecto es +5.

Tres cosas que este resultado deja claras:

1. **La ventaja de Deepnest se cobra cuando el material es la restricción.** Con plancha de sobra, apretar no sirve de nada y los dos empatan. Todas las mediciones anteriores estaban midiendo un caso donde no había nada que ganar.
2. **Se gana sin usar los huecos.** "Piezas dentro de un hueco" sigue dando 0: lo que produjo el ahorro fue anidar la silueta real y aprovechar las zonas cóncavas, no el anidado en agujeros.
3. **Y sigue costando 148 segundos.** El ahorro es enorme; el precio también.

**La conclusión combinada de las tablas es más útil que cualquiera sola:** los dos motores no compiten por el mismo trabajo. Contra paneles rectos, `rectpack` ya está cerca del techo y Deepnest solo aporta corte compartido. Contra piezas irregulares, Deepnest gana por goleada y `rectpack` está tirando material. Y eso es precisamente el reparto F2 / F7 que el roadmap ya tenía escrito, ahora con números.

---

## 5. Cómo decidir

Las preguntas que estos números dejan sobre la mesa, en orden de cuánto pesan:

1. **¿El tiempo es un problema real o de configuración?** Los 93 s son con la capa de paralelismo corriendo **en serie**: el upstream repartía el cálculo de NFP entre Web Workers, y esa capa no corre en Node (ver `PLAN-MOTOR-NESTING-DEEPNEST.md` §2.1), así que en el spike se corre secuencial. Traducirla a `worker_threads` es trabajo acotado y debería dar una mejora grande. Además, `--generaciones`/`--poblacion` son presupuesto puro: bajarlos acelera todo y empeora el layout. **Antes de descartar Deepnest por lento hay que medir con el pool de workers.**
2. **¿Cuánto vale un metro de corte no repetido?** Sin ese número, los 23 metros son un dato lindo sin traducción a plata. Es una pregunta para el taller.
3. **¿Hay trabajos reales donde Deepnest use menos planchas?** Es lo único que mueve `PAR-33`. Se contesta corriendo la comparación con las cantidades de presupuestos reales (`B-09`).
4. **~~¿El nesting corre mientras alguien espera?~~ RESPONDIDA (2026-09-08).** Sí, corre con alguien esperando — **pero el trabajo manual que reemplaza lleva hoy unas 2 horas** (ver la nota de `B-17` en `REGISTRO.md`). Contra ese baseline, 150 segundos es una reducción del 98%, no un problema. Esto **da vuelta el criterio con el que se venía juzgando a Deepnest**: `PAR-25` (3 s) es un umbral que fijamos nosotros para el motor rectangular, donde la respuesta tiene que ser interactiva. Para F7 deja de ser criterio de rechazo.

5. **¿Qué pesa más: apretar o dejar un sobrante usable?** Es la pregunta que abre la métrica de sobrante útil, y la única que no se puede contestar sin el taller. Si el flujo real es "un trabajo, una tanda, se corta y listo", gana apretar y Deepnest se lleva todo. Si es "arranco con lo urgente y la semana que viene meto el resto en lo que sobró", la forma del sobrante puede valer más que dos puntos de aprovechamiento, y ahí `rectpack` tiene una ventaja que nadie había mirado.

**Lo que las mediciones sugieren con más fuerza es que la pregunta "cuál de los dos" está mal planteada.** Los números dicen cosas distintas según el tipo de pieza, y coinciden con el reparto que el roadmap ya tenía: `rectpack` para F2 (paneles rectos, respuesta inmediata, determinista), Deepnest para F7 (irregular, donde duplica la compacidad y el tiempo importa menos porque no hay nadie mirando la pantalla).

Y hay una tercera forma, que las mediciones hacen visible: **no son excluyentes en el tiempo.** `rectpack` puede dar la respuesta inmediata que ve el usuario, y Deepnest correr después en background para mejorarla, avisando "encontramos cómo ahorrar una plancha" cuando la encuentre. Es más trabajo que elegir uno, pero no exige que ninguno gane en todo, y esquiva la pregunta que hoy no se puede contestar con honestidad: cuál conviene sin saber si el usuario está esperando.

---

## 6. Estado del código

| | Dónde | Estado |
|---|---|---|
| `rectpack` | `backend/app/services/nesting/engine.py` | Producción, con tests |
| Anidado en huecos (Capa 2) | `backend/app/services/nesting/anidado_huecos.py` | Construido, sin integrar a `aprovechamiento.py` |
| Motor Deepnest headless | `nesting-engine/` | **Spike.** Anda, con 5 pruebas de humo verdes |
| Cliente Python del spike | `backend/app/services/nesting/deepnest_cliente.py` | Spike: habla por `subprocess`, un proceso por corrida |
| Comparador | `backend/scripts/comparar_motores.py` | Herramienta de decisión, descartable |

Nada de Deepnest está integrado al flujo del producto. Se puede borrar `nesting-engine/` y las dos referencias de Python y el sistema queda exactamente como estaba.
