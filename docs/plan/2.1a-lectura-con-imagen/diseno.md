# 2.1a · Lectura del DXF con imagen antes de cargar — diseño

> **Estado:** **construido el 2026-10-12, en la rama `feat/lectura-con-imagen`, a la espera de que Enzo lo fusione.** Lo que el código precisó del diseño está al principio de [`plan.md`](plan.md).
>
> **De dónde sale.** Enzo eligió seguir con la regla de las islas. Al mirarla resultó que para las letras ya estaba construida (2026-10-07 y 2026-10-08), y que en su trabajo «Complejo» el problema era otro: el aro se lee mal. Enzo explicó cómo se lee, pidió que la solución sirva para próximos diseños sin tocar código cada vez y que la carga muestre una imagen antes de confirmar.
>
> **Qué lugar ocupa.** Es la primera parte de 2.1 «Importar y revisar» del [`PLAN-MAESTRO.md`](../PLAN-MAESTRO.md). La segunda, **2.1b**, es la pantalla para corregir a mano, que retoma el carril B de [`PLAN-RUMBO-ANIDADO-Y-REVISION.md §5`](../../motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md) y tendrá su propio diseño.
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Este sub-proyecto dio de alta tres el 2026-10-12 (§4). Los números de esta página son mediciones, no parámetros.

---

## 1. Para qué

Que un dibujo hecho con franjas, como el aro de `Complejo.dxf`, se pueda cargar bien leído, y que quien carga **vea cómo lo leyó el sistema antes de que se guarde nada**.

**Criterio de éxito:** con `Complejo.dxf` a escala 100, la pantalla muestra el dibujo antes de cargar; con la casilla de unir marcada se ve el aro como una sola pieza, y al cargar quedan el aro (4610 × 4610 mm, 25 huecos), la cruz y las 22 letras a cortar, y 34 formas descartadas (los 25 huecos del aro y los 9 centros de letras). Con la casilla sin marcar no se une nada, en ningún archivo.

---

## 2. Lo que se midió

Todo con guiones de solo lectura, sobre el archivo y la base de Enzo y sobre los demás DXF reales. Guiones, imágenes y resultados en `backend/local/herramientas-lectura-2026-10-12/`, fuera del repositorio.

**Cómo se dibuja el aro.** Cada franja viene con dos líneas cerradas: el borde de afuera y el de adentro. El cuerpo es lo que queda entre las dos; lo de adentro del borde interior es hueco (Enzo, 2026-10-12). Son ocho líneas del mismo color:

| Franja | Borde de afuera | Borde de adentro | Área |
|---|---|---|---|
| El borde | círculo de 4610 | círculo de 4433 | 1,25 m² |
| Los rayos | el mismo círculo de afuera, entrando en V | el mismo círculo de adentro, con una V más honda | 1,67 m² |
| Los triángulos | estrella de 3831 | estrella de 3378 | 1,37 m² |
| El sol | 2429 × 2356 | 1913 × 1864 | 1,23 m² |

Las franjas se pisan entre sí en 1,22 m². Unidas dan **una sola pieza de 4,30 m² con 25 huecos**. La cruz del centro (511 × 950, 0,10 m²) es maciza y queda suelta, a 71 mm del resto. Enzo confirmó el dibujo pintado así.

**Cómo lo lee el sistema hoy.** El lector arma una pieza con cada línea cerrada: la franja y, además, todo lo de adentro de su borde interior. Para una letra, la regla de los recortes (`CART-511`) descarta lo segundo, que es el centro de la «O». Para el aro no actúa, porque exige que la pieza de afuera se corte, y una forma que no entra en ninguna chapa queda como referencia.

**Lo que eso hizo en la base de Enzo.** El grupo del trabajo «Complejo» tiene 45 piezas vivas y 23,70 m²:

| Qué es | Tramos | Área |
|---|---|---|
| Interior del aro | 8 | 12,07 m² |
| Interior de los triángulos | 4 | 4,77 m² |
| Interior del sol, sin la cruz | 2 | 1,11 m² |
| **Huecos que se están anidando** | **14** | **17,95 m² (76 %)** |

El borde y los rayos no están en el grupo. **Las mediciones de 19 y 18 chapas de [`A6`](../../historico/A6-reparto-por-chapa/diseno.md) (2026-10-10) se hicieron sobre ese grupo:** hay que repetirlas con el trabajo bien leído.

**Prueba descartable de las dos reglas del §5,** sobre lo que entrega el lector:

| Archivo | Formas | Uniones | Qué une | Resultado |
|---|---|---|---|---|
| `Complejo.dxf` de hoy | 40 | 1 | las 8 líneas del aro | bien: 1 pieza de 4,30 m², 25 huecos, la cruz suelta |
| `Complejo.dxf` anterior (respaldo) | 162 | 1 | el mismo aro | bien |
| `Muestra Vectores.dxf` (respaldo) | 2.154 | 2 | el aro, y un logo de 28 líneas | el aro, bien. **El logo, mal:** una mancha de 1203 × 506 que se come 27 letras |
| `strat.dxf` (guitarra) | 120 | 2 | dos grupos chicos de herrajes | dudoso: uno pierde un agujero |
| `carrusel`, `esqueletos`, `repisas` | 35, 15, 12 | 0 | — | sin cambios |

- **Unir acierta en uno de los tres dibujos que tienen formas que se pisan.** En el logo, según Enzo, se cortan las letras de arriba enteras y las de la leyenda de abajo, y el espacio entre las dos palabras no va: ninguna regla lo hubiera leído.
- **La regla de los huecos en piezas grandes no cambia nada en cuatro archivos.** En el `Complejo.dxf` anterior lee bien un aro de 1989 × 2000 que ya viene unido: sus 25 huecos pasan a recorte y la cruz, que hoy sale como recorte por error, vuelve a cortarse. En la Muestra cambia dos formas de ese mismo aro, en el mismo sentido.
- **Sin unir, esa regla sola no arregla el aro de 4,6 m:** lo lee de otra manera igual de mala (marca la cruz como recorte). Hace falta la unión.
- **Tiempo:** en el archivo más grande, 4,2 s de lectura y 0,5 s de buscar y unir.

**Con el código construido** las cantidades de la tabla de arriba cambian en dos archivos, porque ahora cuentan los bordes de adentro rectangulares: en `Muestra Vectores.dxf` la unión reemplaza 39 líneas y en `strat.dxf`, 13. La tabla que vale es la de la Tarea 7 de [`plan.md`](plan.md).

---

## 3. Alcance

**Entra:**

- Una regla nueva del análisis: **los recortes de huecos también en piezas grandes.**
- Un paso nuevo de la importación: **unir las formas que se pisan**, solo cuando la persona lo pide.
- La carga de la pestaña Piezas en dos tiempos: **ver cómo se lee**, y recién después **cargar**.

**No entra:**

| Tema | Por qué | Dónde va |
|---|---|---|
| Corregir a mano con clics, y unir grupo por grupo | Es lo que resuelve casos como el logo. Necesita su propio diseño | 2.1b |
| Acercar y mover el dibujo | Para mirar un trabajo no hace falta; para un archivo con muchos diseños, sí | 2.1b |
| La importación de varios diseños (`/importaciones/dxf/...`) | Ninguna pantalla la usa todavía. Recibe la regla de los huecos porque comparte el análisis; la unión, no | 2.1b |
| Las miniaturas dadas vuelta de la tabla de Piezas | Es otro arreglo. El dibujo nuevo sale derecho | Pendiente aparte |
| Guardar en el trabajo si se cargó uniendo | No hay nada que vuelva a leer el archivo. El nombre de la pieza unida lo dice | — |

---

## 4. Decisiones

| Decisión | Valor | Por qué |
|---|---|---|
| Cuándo se une | **Solo si la persona marca la casilla,** apagada de entrada | Acierta en uno de tres dibujos (§2). Unir reemplaza formas: un error no se arregla con «Restaurar» |
| A qué se aplica la casilla | Al archivo entero | Elegir grupo por grupo necesita la pantalla de 2.1b |
| La regla de los huecos en piezas grandes | **Automática**, como la de las letras | No tocó nada de más en los DXF reales, y lo que descarta queda a la vista y se restaura con un clic |
| Qué pasa con los huecos de una pieza unida | Entran como filas **descartadas**, igual que el centro de una letra | Nada se pierde en silencio, y si un hueco resulta ser una pieza se restaura. `P-29` (si esos recortes se usan) sigue abierta |
| Quién dibuja | La pantalla, con las formas que manda el servidor | Es el mismo dibujo que 2.1b va a hacer clicable |
| Cuántas lecturas manda el servidor | Las dos, sin unir y unida, en una sola respuesta | Marcar la casilla cambia el dibujo sin volver a leer el archivo |
| Si ver la lectura guarda algo | No. El archivo vuelve a viajar al cargar | El navegador ya lo tiene. Es el patrón del seccionado: proponer sin guardar, después aplicar |
| Dónde vive el código | Módulo nuevo en `services/ingesta/`. El lector (`dxf.py`) no se toca | Separa leer geometría de decidir qué significa, como ya hace `analisis.py` |
| Cómo se llaman las formas nuevas | Con el nombre de la línea más grande del grupo: la unida suma `/unida` y cada hueco suma `/hueco` y su número (`trabajo-1-39/unida`, `trabajo-1-39/hueco7`) | Mismo criterio que los tramos del seccionado (`/t1`) |

**Altas en el registro** (2026-10-12, provisorias; el valor de cada una está en [`REGISTRO.md §2.1`](../../REGISTRO.md)):

| ID | Qué es |
|---|---|
| `PAR-50` | A qué distancia dos bordes cuentan como que se tocan |
| `PAR-51` | Cuánta área tienen que compartir dos formas para contar como que se pisan |
| `PAR-52` | Con cuánto detalle viaja cada contorno para el dibujo, como fracción del lado mayor del dibujo |

---

## 5. Cómo funciona

```
DXF → leer líneas → [ unir, si se pidió ] → analizar → dibujo y resumen → «Cargar» → piezas
      (no cambia)     nuevo                 regla nueva  nuevo, no guarda    (ya existe)
```

### 5.1 Los recortes de huecos también en piezas grandes

Hoy una forma es el recorte de un hueco si está adentro de otra **que se corta** (en una hoja armada siempre; fuera de las hojas, solo si tiene su mismo color). Cambia qué cuenta como «que se corta»:

- También cuenta una forma que **no entra en ninguna chapa**: se va a seccionar.
- **Salvo que sea un rectángulo** (`PAR-43`): eso es un tablero o un marco, y lo que tiene adentro son piezas.
- Lo mismo vale para la forma de adentro: que no entre en ninguna chapa no le impide ser un recorte.
- **Sin chapas en el catálogo la regla no actúa:** ahí no entra nada, y eso no dice nada de la pieza.

Sigue yendo de afuera hacia adentro, así que un recorte no es madre de nadie: la cruz, que está adentro de un hueco, se sigue cortando.

Para esto el análisis tiene que saber **por qué** una forma quedó como referencia. Hoy lo dice solo el texto del motivo.

### 5.2 Unir las formas que se pisan

1. **Cuáles se pisan.** Dos formas del mismo color se pisan si comparten más área que `PAR-51` y ninguna está limpia adentro de la otra. «Limpia» quiere decir que sus bordes no se acercan a menos de `PAR-50`. Los rectángulos (`PAR-43`) no se pisan con nadie: son hojas, marcos o tableros. Adentro de una franja, en cambio, un rectángulo es su borde de adentro como cualquier otra forma: una ventana. Dos formas sin color conocido cuentan como del mismo color: la persona pidió unir y ve el resultado antes de cargar.
2. **El grupo.** Las formas que se pisan entre sí, más las que tienen limpias adentro.
3. **Cuerpo y hueco.** Dentro del grupo, de afuera hacia adentro: la primera línea es un borde de afuera, la que tiene limpia adentro es su borde de adentro, la siguiente vuelve a ser un borde de afuera. El cuerpo de cada franja es su borde de afuera menos sus bordes de adentro.
4. **Unir.** Los cuerpos que se pisan pasan a ser una sola pieza. Un cuerpo que no pisa a ningún otro queda como estaba.
5. **Lo que sale.** La pieza unida reemplaza a las líneas que la formaban. Cada hueco suyo que no sea chico pasa a ser además una forma propia, que la regla del §5.1 deja descartada; «chico» es lo mismo que para el lector, que a un agujero de tornillo lo deja solo como agujero. Los agujeros chicos de las líneas unidas se conservan. Una forma de otro color que quedó sobre la pieza unida sigue siendo una pieza y no le abre un hueco. Los huecos se numeran de abajo hacia arriba y de izquierda a derecha, como los tramos del seccionado, para que el número no cambie entre una lectura y otra. Lo que estaba adentro de una línea reemplazada pasa a colgar del hueco que lo contiene.

Lo que no se pisa con nada no cambia: sale igual que hoy.

**Sin la casilla** el paso 1 corre igual, para avisar: «Hay 8 formas que se pisan entre sí».

### 5.3 Ver cómo se lee

Un pedido nuevo, `POST /trabajos/{id}/dxf/lectura`, recibe el archivo y la escala y devuelve, sin tocar la base:

- **La lectura sin unir,** y si hay formas que se pisan, también **la lectura unida.**
- De cada lectura: las formas con su contorno y sus huecos en la posición del dibujo, si se cortan o entran descartadas y por qué, los totales y los avisos.
- «Se corta» es todo lo que no entra descartado, igual que en la carga de hoy: incluye lo que después hay que seccionar.

`POST /trabajos/{id}/dxf`, la carga de hoy, acepta además si hay que unir (el campo `unir`). Las dos rutas usan la misma función para leer, así que lo que se ve es lo que se carga.

### 5.4 La pantalla

En la pestaña Piezas, el botón pasa a decir **«Ver cómo se lee»**. Abre un panel:

```
┌─ Así se lee ──────────────────────────────────────────────┐
│   lo que se corta, pintado · los huecos, en blanco ·      │
│   lo que entra descartado, en línea de puntos             │
├───────────────────────────────────────────────────────────┤
│ 24 piezas a cortar · 34 entran descartadas                │
│ Hay 8 formas que se pisan entre sí.                       │
│ [x] Unir las formas que se pisan                          │
│ Cargar reemplaza las 62 piezas que ya tiene este trabajo. │
│ [ Cargar ]   [ Cancelar ]                                 │
└───────────────────────────────────────────────────────────┘
```

- La casilla aparece solo si hay formas que se pisan.
- El relleno es semitransparente: donde dos piezas se pisan se ve más oscuro, y un dibujo mal leído salta a la vista.
- Cambiar la escala o el archivo cierra el panel: hay que volver a ver la lectura.
- La identidad visual es la de [`frontend-cotizador/diseno.md §4`](../../historico/frontend-cotizador/diseno.md).

---

## 6. Cómo se valida

1. **Pruebas automáticas del análisis,** con piezas armadas a mano: un recorte adentro de una pieza grande; adentro de un rectángulo grande, no; lo que está adentro de un recorte se sigue cortando.
2. **Pruebas automáticas de la unión:** dos franjas que se pisan dan una pieza con su hueco; una forma limpia adentro de otra no se toca; dos colores no se unen; un rectángulo no participa; una pieza adentro de un hueco queda suelta.
3. **Pruebas de las rutas:** ver la lectura no escribe en la base; devuelve las dos lecturas; cargar con y sin unir.
4. **Pruebas de la pantalla** para lo que arma el dibujo y el resumen.
5. **Los DXF reales:** repetir la tabla del §2 con el código construido. Tiene que dar lo mismo.
6. **En la app,** contra una copia de los datos de Enzo: el criterio de éxito del §1.

---

## 7. Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| La unión lee mal un dibujo | Varias formas pasan a ser una mancha | Se ve en la imagen antes de cargar, y la casilla está apagada de entrada |
| Un archivo trae un aro y un logo | La casilla une los dos o ninguno | Se carga sin unir y se corrige a mano, como hoy. Elegir por grupo es 2.1b |
| La regla de los huecos descarta piezas de verdad | Letras del mismo color adentro de una placa grande que no es rectángulo entran descartadas | Es el mismo supuesto que ya rige para placas chicas. Se ven en línea de puntos y se restauran con un clic |
| En un aro sin unir, la regla de los huecos marca la cruz como recorte | Hoy esa cruz queda viva | La imagen lo muestra y el aviso de formas que se pisan lleva a la casilla |
| Muchas filas descartadas | El aro suma 25 filas atenuadas a la tabla de Piezas | Se acepta. Si molesta, se decide en 2.1b |
| Un archivo muy grande | La respuesta con las formas pesa parecido al DXF | `PAR-52` achica los contornos para el dibujo. Se mide con `Muestra Vectores.dxf` |
| Volver a cargar el trabajo «Complejo» | Se pierden sus seccionados, grupos y anidados de prueba | Ya pasa hoy al recargar. Probar primero sobre una copia |
