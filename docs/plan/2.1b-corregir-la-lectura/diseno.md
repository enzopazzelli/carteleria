# 2.1b · Corregir a mano la lectura del DXF — diseño

> **Estado:** **construido el 2026-10-13, en la rama `feat/corregir-la-lectura`, a la espera de que Enzo lo fusione.** Lo que el código precisó del diseño está al principio de [`plan.md`](plan.md), y lo que corrigió el ensayo, en el §8.
>
> **De dónde sale.** [2.1a](../../historico/2.1a-lectura-con-imagen/diseno.md) dejó la pantalla que muestra cómo se lee un DXF antes de cargarlo. Ahí se vio que ninguna regla lee bien todos los dibujos: la unión acierta en el aro de `Complejo.dxf` y arruina un logo de la muestra. Enzo pidió poder corregir la lectura a mano.
>
> **Qué lugar ocupa.** Es la segunda parte de 2.1 «Importar y revisar» del [`PLAN-MAESTRO.md`](../PLAN-MAESTRO.md). Retoma el paso B3 del carril B de [`PLAN-RUMBO-ANIDADO-Y-REVISION.md §5`](../../motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md), dentro de la pestaña Piezas y no en una pantalla aparte.
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Este sub-proyecto cambia uno y da de alta otro (§4), junto con el código. Los demás números de esta página son mediciones.

---

## 1. Para qué

Que quien carga un DXF pueda decirle al sistema, sobre el dibujo, qué formas se cortan y cuáles no van, para que un diseño que las reglas leen mal entre bien **sin tocar código**.

**Criterio de éxito:** con un DXF que trae solo el logo «AWADUCT / PERFECTO ETERNO» de la muestra, se llega con clics sobre el dibujo a lo que Enzo dijo que se corta: la palabra de arriba entera, que son cinco formas, y las 16 formas de la leyenda de abajo. Al cargar entran esas 21 piezas y los 8 centros de sus letras, descartados; nada más. Y `Complejo.dxf` con el aro unido da lo mismo que hoy.

---

## 2. Lo que se midió

Todo con guiones de solo lectura, sobre `Muestra Vectores.dxf` del respaldo y sobre el archivo de Enzo. Guiones e imágenes en `backend/local/herramientas-2.1b-2026-10-12/`, fuera del repositorio.

**Cómo es el logo** (34 formas en la muestra, 1203 × 506 mm). Enzo lo explicó sobre el dibujo numerado:

- La palabra de arriba son **cinco formas**: la barra con la «W» (1169 × 342 mm), las dos «A», «DUC» y la «T». Los triangulitos de las «A» y el hueco de la «D» son sus agujeros.
- La leyenda de abajo son 16 formas, una por letra y por punto.
- **Lo que no va:** un contorno que rodea la palabra, otro que rodea la leyenda, y un rectángulo de 1189 × 257 que es **una chapa dibujada**: el diseñador marcó con ella qué parte del diseño entra en una chapa y qué parte en otra. Por eso la mitad de abajo de cada letra grande está dibujada otra vez, como forma aparte: son cinco mitades repetidas, y tampoco van.

**Cómo lo lee hoy el sistema: al revés.** Toma los dos contornos y la chapa como piezas, y la palabra y las 16 letras como sus recortes. No falla ninguna regla: un contorno con formas de su mismo color adentro se lee igual que una «O» con su centro.

**El mismo logo, solo en un archivo, se lee distinto.** El lector decide si una forma es pieza o agujero por cuántos contornos la encierran: con una cantidad par es pieza; con una impar es agujero, y además pieza si mide más de 25 mm. En la muestra al logo lo rodea un fondo gris. Sin él todo cambia de nivel: salen 35 formas y no 34, los centros de las «P» y las «R» pasan a ser formas, y los dos puntos de la leyenda (24 × 21 mm) quedan solo como agujeros del contorno que los rodea.

**El ensayo: los clics sobre un DXF con el logo solo,** por los pedidos de verdad y en un navegador sin ventana, contra una copia de la base.

| Clic | Qué pasa |
|---|---|
| El contorno de arriba, «no va» | Las cinco formas de la palabra pasan solas a «se corta» |
| El contorno de abajo y la chapa dibujada, «no va»: dos clics en el mismo lugar | Las 16 formas de la leyenda pasan solas a «se corta», con los centros de sus letras como recortes. Los dos puntos, que eran agujeros del contorno, aparecen como formas |
| Las mitades repetidas de las dos «A», la «W» y «DUC», «no va»: cuatro clics | Dejan de cortarse dos veces |
| La mitad repetida del palo de la «T»: dos clics | Cae adentro de la letra y el lector la toma por un agujero. El primer clic la pone a cortar, el segundo la saca, y la «T» queda entera |

**Nueve clics** dejan el logo como dijo Enzo: 21 formas a cortar, 8 recortes (los centros de las letras) y 8 que no van. Sin que lo de adentro se vuelva a leer, habría que marcar las 35 de a una.

- **Dos formas pueden estar dibujadas en el mismo lugar:** el contorno de la leyenda y la chapa dibujada. Al sacar la de arriba, la otra queda a la vista y se saca con otro clic.
- **Una forma que cae adentro de otra no siempre es su agujero:** la mitad repetida del palo de la «T».
- **Tiempo:** leer `Complejo.dxf` tarda 0,2 s; es lo que tarda cada clic.

**El detalle del dibujo.** Hoy el dibujo viaja con `PAR-52`, que alcanza para verlo entero. En `Complejo.dxf` (7,76 m de lado) eso es apartarse hasta 1,9 mm: a 8 aumentos son 2 píxeles y las curvas se ven facetadas.

| Detalle | Se aparta hasta | Puntos | Peso de una lectura |
|---|---|---|---|
| 1/4000 del lado mayor (hoy) | 1,94 mm | 2.864 | 79 KB |
| 1/10000 | 0,78 mm | 4.248 | 118 KB |
| **1/20000** | **0,39 mm** | **6.072** | **170 KB** |
| 1/40000 | 0,19 mm | 8.487 | 239 KB |
| El contorno entero | — | 14.291 | 400 KB |

Con 1/20000, a 20 aumentos el error es de un píxel.

---

## 3. Alcance

**Entra:**

- **Corregir con clics** en el dibujo de «Así se lee»: marcar una forma como «se corta» o «no va».
- **Acercar y mover** el dibujo.
- **Lo que no va, no se carga.**
- Dos arreglos del mismo panel que dejó la revisión de 2.1a: «Cargar» apagado si no queda nada para cortar, y el aviso que pide marcar una casilla que ya no está en pantalla.

**No entra:**

| Tema | Por qué | Dónde va |
|---|---|---|
| Elegir qué grupo de formas se une | Con un diseño por archivo (Enzo, 2026-10-12) la casilla para todo el archivo alcanza. Si aparece un diseño que mezcle un aro con un logo, se agrega | Pendiente |
| Recordar las correcciones de una carga a la otra | Lo que se guarda son las piezas ya corregidas. Volver a cargar empieza de cero | — |
| Archivos con varios diseños | Enzo carga un diseño por archivo. Cada clic vuelve a leer el archivo entero: en `Muestra Vectores.dxf` serían 8 s por clic | Carril B, B2 y B4 |
| Marcar de a muchas formas con un recuadro | El logo se resuelve con nueve clics | Pendiente, si hace falta |
| Cambiar cómo decide el lector qué es pieza y qué es agujero | La regla de los niveles (§2) es anterior a esto y la usan todos los archivos. La corrección a mano cubre los casos en que falla | Pendiente |
| Girar una pieza con ángulo libre en el anidado automático | Enzo lo pidió el 2026-10-12, pero es del motor: hoy Sparrow solo prueba cuartos de vuelta | Carril del motor |
| Las miniaturas dadas vuelta de la tabla de Piezas | Es otro arreglo | Pendiente aparte |

---

## 4. Decisiones

| Decisión | Valor | Por qué |
|---|---|---|
| Quién decide después de un clic | **El servidor vuelve a leer** con la lista de correcciones | Lo de adentro de una forma corregida se acomoda solo, y lo que se ve sigue siendo lo que se guarda: dibuja y carga la misma función |
| Qué opciones tiene una forma | Dos: **«se corta»** y **«no va»** | Enzo, sobre el logo: alcanza con eso |
| Qué pasa con lo que no va | **No se carga** (Enzo, 2026-10-12) | La tabla de Piezas queda limpia. Lo que el sistema descarta solo (centros de letras, huecos) sigue entrando atenuado, como hoy |
| Qué hace un clic | En una forma sin corregir, la fuerza a **lo contrario de lo que se ve**. En una que se forzó a cortar, la pasa a **«no va»**. En una que no va, **le saca la corrección** (Enzo, 2026-10-13) | Un solo gesto para corregir y para arrepentirse. El paso por «no va» hace falta para sacar una forma que el lector tomó por agujero: una descartada pasa primero a «se corta» |
| Dónde se dibuja lo que no va | **Al fondo,** tapado por lo que se corta (Enzo, 2026-10-13) | Con el rayado encima, la mitad de la palabra parecía que no se cortaba. Una forma sacada que queda tapada se devuelve con la ✕ de la lista de correcciones |
| Qué forma recibe el clic | **La más chica** que hay debajo del puntero, de las que siguen en el dibujo; lo que no va, solo donde no lo tapa nada | Se puede tocar una letra que está adentro de un contorno. Y de dos formas dibujadas en el mismo lugar, la que se sacó deja a mano a la otra |
| La casilla de unir | Sigue siendo una, para todo el archivo. Las correcciones se conservan al marcarla; las que nombran una forma que no existe en esa lectura no hacen nada. Lo que no va no se une con nada | Con un diseño por archivo alcanza |
| Dónde se guardan las correcciones mientras se corrige | En la pantalla. El servidor no guarda nada: el archivo y la lista viajan en cada pedido | El navegador ya tiene el archivo. Es lo que ya hace la lectura de 2.1a |
| El detalle del dibujo | `PAR-52` pasa de 1/4000 a **1/20000** | Para que al acercar no se vean las curvas facetadas (§2) |
| Cuánto se puede acercar | Hasta **20 aumentos** (`PAR-53`, nuevo) | Es donde el error de `PAR-52` llega a un píxel |

**Cambios en el registro,** junto con el código y no antes: el valor de `PAR-52`, y el alta de `PAR-53` (aumento máximo del dibujo de la lectura).

---

## 5. Cómo funciona

```
clic en una forma → la pantalla suma o saca una corrección → pide la lectura de nuevo, con la lista
                                                                 ↓
        dibujo con tres estados  ←  el análisis fuerza lo corregido y vuelve a decidir lo demás
                                                                 ↓
                              «Cargar» manda la misma lista: lo que no va no se guarda
```

### 5.1 Las correcciones en la lectura

Una corrección es el nombre de una forma y una de dos palabras: `cortar` o `no_va`.

- **Lo corregido manda.** La forma queda con lo que se marcó, diga lo que diga cualquier regla, y con el motivo «lo marcó quien carga». Y es siempre una forma, aunque por su tamaño el lector la tomara solo por un agujero.
- **Una forma que no va no es madre de nadie.** Lo que tiene adentro se lee como si ella no estuviera: deja de ser «su recorte» y pasa por las reglas de siempre. Es lo que hace que sacar un contorno ponga a cortar las letras que encierra. Sus agujeros chicos, que el lector no daba como formas, pasan a serlo: si no, se perderían con ella, como los dos puntos de la leyenda.
- **Tampoco es el hueco de nadie.** La pieza que la tenía adentro queda llena ahí. El lector toma por agujero a todo contorno que cae adentro de otro, y no siempre lo es: la mitad repetida del palo de la «T».
- **Ni se une con nada.** La unión de las formas que se pisan se arma sin lo que no va, que sigue a la vista en la lectura unida.
- **Una forma forzada a cortar nunca pasa a recorte,** aunque esté adentro de otra que se corta. Y como se corta, lo que tiene adentro, de su mismo color, es su recorte.
- **También manda sobre los huecos de una pieza unida,** que entran descartados por cómo se arman: un clic los pone a cortar, y otro los saca, con lo que la pieza unida queda llena ahí.
- El análisis suma un rol, «no va». La importación de varios diseños (`/importaciones/dxf/...`) lo recibe sin cambios: ahí solo se crean las formas con rol «cortar».

### 5.2 Los dos pedidos

`POST /trabajos/{id}/dxf/lectura` y `POST /trabajos/{id}/dxf` reciben un campo más, `correcciones`: un objeto JSON de nombre de forma a `cortar` o `no_va`. Sin el campo, todo anda como hoy.

- **La lectura** sigue devolviendo las dos lecturas, sin unir y unida, cada una con las correcciones aplicadas. Una lectura no hace nada con la corrección de una forma que no tiene.
- De cada forma vuelve **uno de tres estados** (`se_corta`, `descartada`, `no_va`) en vez del sí o no de hoy, y si está corregida. Los totales suman cuántas no van.
- **La carga** no guarda las formas que no van, y avisa cuántas fueron.
- **Lo que no sirve da 400,** con un mensaje que dice qué: un JSON mal escrito, una palabra que no es `cortar` ni `no_va`, o una forma que no es de este archivo. La corrección de una pieza unida que ya no se arma, porque se sacó una de sus formas, no es un error: queda sin efecto.

### 5.3 La pantalla

```
┌─ Así se lee ───────────────────────────────────────────────┐
│                                       [ + ] [ − ] [Ver todo]│
│        el dibujo: rueda para acercar, arrastrar para       │
│        mover, clic en una forma para corregirla            │
├────────────────────────────────────────────────────────────┤
│ Pintado: se corta · Punteado: entra descartada ·           │
│ Rayado rojo: no va                                         │
│ 21 piezas a cortar · 8 entran descartadas · 8 no van       │
│                                                            │
│ Tus correcciones:  0 no va ✕   36 no va ✕   30 no va ✕ …   │
│                    [ Quitar todas ]                        │
│ [ ] Unir las formas que se pisan                           │
│ [ Cargar ]  [ Cancelar ]                                   │
└────────────────────────────────────────────────────────────┘
```

- **Tres estados a la vista:** lo que se corta, pintado; lo que entra descartado, en línea de puntos; lo que no va, rayado en rojo. Lo que corrigió la persona lleva el borde más grueso.
- **Lo que no va se dibuja al fondo,** y lo que se corta lo tapa: el rayado no se ve a través de una pieza. Arriba van las demás formas, de la más grande a la más chica, así la chica queda arriba y recibe el clic. Una forma sin relleno también se puede tocar, en su cuerpo y no solo en su línea.
- **Un clic** fuerza la forma a lo contrario de lo que se ve. Otro clic sobre una que se forzó a cortar la saca, y otro sobre una que no va la deja como la leyó el sistema.
- **Cada corrección figura abajo** con el nombre corto de la forma y una ✕ que la saca. Es también la manera de devolver una forma sacada que quedó tapada por otra. «Quitar todas» vuelve a la lectura del sistema.
- **Acercar y mover:** la rueda acerca hacia donde está el puntero, hasta `PAR-53`; arrastrar mueve; «Ver todo» vuelve al dibujo entero. Soltar después de arrastrar no cuenta como clic.
- **Mientras llega la lectura nueva** se sigue viendo la anterior, atenuada. Si se hace otro clic antes, vale la última respuesta pedida.
- **Al pasar el mouse:** el nombre de la forma, su medida, su estado y el motivo.
- Cambiar el archivo o la escala cierra el panel y borra las correcciones, como ya pasa con la lectura.
- **«Cargar» se apaga** si no queda ninguna forma para cortar, y lo dice.
- La identidad visual es la de [`frontend-cotizador/diseno.md §4`](../../historico/frontend-cotizador/diseno.md).

---

## 6. Cómo se valida

1. **Pruebas automáticas del análisis y del lector,** con piezas y dibujos armados a mano: sacar un contorno pone a cortar lo que encierra; sus agujeros chicos pasan a ser formas; una pieza pierde el agujero que era una forma que no va; una forma forzada a cortar no pasa a recorte y lo de adentro es su recorte; una corrección sobre una forma que no existe no hace nada.
2. **Pruebas de las rutas:** la lectura con correcciones devuelve los tres estados y los totales; la carga no guarda lo que no va; lo que muestra la lectura es lo que guarda la carga, también con correcciones; lo que no va no se une; los tres errores que dan 400, y la corrección de una pieza unida que ya no se arma, que no lo es.
3. **Pruebas de la pantalla** para sus cuentas: qué pasa con cada clic, en qué orden se dibuja, acercar hacia un punto, mover sin salirse, el texto de los totales, y cuál respuesta vale cuando se piden dos lecturas seguidas.
4. **El logo:** un DXF con el logo solo, armado a partir de la muestra y guardado fuera del repositorio. Los nueve clics del §2, por los pedidos y en el navegador, tienen que dejar las 21 formas del criterio de éxito, con la «T» entera.
5. **`Complejo.dxf`:** sin correcciones, con y sin unir, da los mismos totales que hoy (26 y 14; 24 y 34).
6. **En la app,** contra una copia de los datos de Enzo, con capturas: corregir el logo, acercar, cargar.

---

## 7. Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| Cada clic vuelve a mandar el archivo | En un archivo grande, segundos por clic | Con un diseño por archivo son décimas. Se muestra que está leyendo. Los archivos con varios diseños quedan afuera (§3) |
| Al sacar una forma, sus agujeros chicos pasan a ser formas a cortar | En una placa con tornillos, cada tornillo aparece como una forma que hay que sacar también | Se ve en el dibujo apenas pasa. Marcar de a muchas queda anotado (§3) |
| Una forma sacada queda tapada por otra que se corta | No se la puede tocar para devolverla | Se devuelve con la ✕ de la lista de correcciones |
| El mismo dibujo se lee distinto solo que junto a otros | El lector decide pieza o agujero por cuántos contornos encierran a la forma (§2) | La corrección a mano lo resuelve en cada caso. Cambiar esa regla queda afuera (§3) |
| La persona saca todo | «Cargar» borraría las piezas del trabajo | «Cargar» se apaga si no queda nada para cortar |
| Las correcciones se pierden al cambiar el archivo o la escala | Hay que hacerlas de nuevo | Se acepta: son pocos clics, y con otra escala u otro archivo no valdrían |
| Una forma muy chica es difícil de tocar | No se puede corregir sin acercar | Para eso está el acercamiento, hasta `PAR-53` |
| La respuesta de la lectura cambia de forma | El sí o no de «descartada» pasa a ser un estado de tres | Solo la usa esta pantalla, que cambia en el mismo sub-proyecto |
| El dibujo pesa más | Con `PAR-52` en 1/20000, la respuesta de `Complejo.dxf`, que trae sus dos lecturas, pesa 0,3 MB; la de `Muestra Vectores.dxf`, 3,8 MB en vez de 2,3 | Se acepta. En un archivo de varios diseños pesaría varias veces más, y esos quedan afuera |

---

## 8. Lo que corrigió el ensayo (2026-10-13)

Antes de escribir el plan, el código se ensayó entero sobre una copia: los pedidos de verdad y la pantalla en un navegador, con un DXF que trae el logo solo. Cambió esto del diseño aprobado el 2026-10-12:

- **El logo estaba mal contado.** La palabra de arriba son cinco formas, no una: la que mide 1169 × 342 mm es solo la barra con la «W». Con los quince clics de la primera versión salían las letras. El criterio de éxito pasó de 17 piezas con quince clics a 21 con nueve (§1, §2). Lo que Enzo confirmó sobre la imagen no cambia.
- **Tres reglas más para lo que no va** (§5.1), que salen de «no es madre de nadie»: sus agujeros chicos pasan a ser formas, no es el hueco de nadie, y no se une con nada. Sin la primera se perdían los dos puntos de la leyenda; sin la segunda, la «T» se cortaba con un agujero en el palo; sin la tercera, la casilla de unir volvía a meter en una sola mancha los contornos que se habían sacado.
- **El clic tiene un paso más** (§4): de una forma forzada a cortar pasa a «no va». Enzo, 2026-10-13.
- **Lo que no va se dibuja al fondo** (§4, §5.3). Con el rayado encima de lo que se corta, la mitad de la palabra parecía que no iba. Enzo, 2026-10-13.
- **Un error menos** (§5.2): la corrección de una pieza unida que ya no se arma queda sin efecto, en vez de dar 400.
