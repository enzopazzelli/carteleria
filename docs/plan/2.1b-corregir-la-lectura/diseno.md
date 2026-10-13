# 2.1b · Corregir a mano la lectura del DXF — diseño

> **Estado:** **diseño, a revisar por Enzo (2026-10-12).** Nada construido. Todavía no tiene `plan.md`.
>
> **De dónde sale.** [2.1a](../../historico/2.1a-lectura-con-imagen/diseno.md) dejó la pantalla que muestra cómo se lee un DXF antes de cargarlo. Ahí se vio que ninguna regla lee bien todos los dibujos: la unión acierta en el aro de `Complejo.dxf` y arruina un logo de la muestra. Enzo pidió poder corregir la lectura a mano.
>
> **Qué lugar ocupa.** Es la segunda parte de 2.1 «Importar y revisar» del [`PLAN-MAESTRO.md`](../PLAN-MAESTRO.md). Retoma el paso B3 del carril B de [`PLAN-RUMBO-ANIDADO-Y-REVISION.md §5`](../../motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md), dentro de la pestaña Piezas y no en una pantalla aparte.
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Este sub-proyecto cambia uno y da de alta otro (§4), junto con el código. Los demás números de esta página son mediciones.

---

## 1. Para qué

Que quien carga un DXF pueda decirle al sistema, sobre el dibujo, qué formas se cortan y cuáles no van, para que un diseño que las reglas leen mal entre bien **sin tocar código**.

**Criterio de éxito:** con un DXF que trae solo el logo «AWADUCT / PERFECTO ETERNO» de la muestra, se llega con clics sobre el dibujo a lo que Enzo dijo que se corta: la palabra de arriba entera (1169 × 342 mm) y las 16 formas de la leyenda de abajo. Al cargar entran esas 17 piezas y los 2 centros de las «O», descartados; nada más. Y `Complejo.dxf` con el aro unido da lo mismo que hoy.

---

## 2. Lo que se midió

Todo con guiones de solo lectura, sobre `Muestra Vectores.dxf` del respaldo y sobre el archivo de Enzo. Guiones e imágenes en `backend/local/herramientas-2.1b-2026-10-12/`, fuera del repositorio.

**Cómo es el logo** (34 formas, 1203 × 506 mm). Enzo lo explicó sobre el dibujo numerado:

- La palabra de arriba viene **entera, como una sola forma**, con los huecos de las letras ya metidos en su contorno.
- La leyenda de abajo son 16 formas, una por letra y por punto.
- **Lo que no va:** un contorno que rodea la palabra, otro que rodea la leyenda, y un rectángulo de 1189 × 257 que es **una chapa dibujada**: el diseñador marcó con ella qué parte del diseño entra en una chapa y qué parte en otra. Por eso la mitad de abajo de cada letra grande está dibujada otra vez, como forma aparte. Tampoco van los triangulitos de las «A» ni el hueco de la «D», que vienen sueltos y con doble línea.

**Cómo lo lee hoy el sistema: al revés.** Toma los dos contornos y la chapa como piezas, y la palabra y las 16 letras como sus recortes. No falla ninguna regla: un contorno con formas de su mismo color adentro se lee igual que una «O» con su centro.

**Prueba descartable: forzar formas de a una y dejar que el análisis vuelva a decidir lo demás.**

| Clic | Qué pasa |
|---|---|
| El contorno de arriba, «no va» | La palabra pasa sola a «se corta» |
| El contorno de abajo, «no va» | Las 16 formas de la leyenda pasan solas a «se corta», con los centros de las «O» como recortes |
| La chapa dibujada, «no va» | Sale |
| Doce clics más | Salen las seis formas repetidas de la mitad de abajo, y los triangulitos de las «A» y el hueco de la «D», que vienen con doble línea |

**Quince clics** dejan el logo como dijo Enzo: 17 formas a cortar, 2 recortes y 15 que no van. Sin que lo de adentro se vuelva a leer, habría que marcar las 34 de a una.

- **Al sacar una forma dibujada con doble línea aparece la de adentro,** que hay que sacar también. Son tres de los quince clics.
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
| Marcar de a muchas formas con un recuadro | El logo se resuelve con quince clics | Pendiente, si hace falta |
| Girar una pieza con ángulo libre en el anidado automático | Enzo lo pidió el 2026-10-12, pero es del motor: hoy Sparrow solo prueba cuartos de vuelta | Carril del motor |
| Las miniaturas dadas vuelta de la tabla de Piezas | Es otro arreglo | Pendiente aparte |

---

## 4. Decisiones

| Decisión | Valor | Por qué |
|---|---|---|
| Quién decide después de un clic | **El servidor vuelve a leer** con la lista de correcciones | Lo de adentro de una forma corregida se acomoda solo, y lo que se ve sigue siendo lo que se guarda: dibuja y carga la misma función |
| Qué opciones tiene una forma | Dos: **«se corta»** y **«no va»** | Enzo, sobre el logo: alcanza con eso |
| Qué pasa con lo que no va | **No se carga** (Enzo, 2026-10-12) | La tabla de Piezas queda limpia. Lo que el sistema descarta solo (centros de letras, huecos) sigue entrando atenuado, como hoy |
| Qué hace un clic | En una forma sin corregir, la fuerza a **lo contrario de lo que se ve**. En una ya corregida, **le saca la corrección** | Un solo gesto para corregir y para arrepentirse |
| Qué forma recibe el clic | **La más chica** que hay debajo del puntero | Se puede tocar una letra que está adentro de un contorno |
| La casilla de unir | Sigue siendo una, para todo el archivo. Las correcciones se conservan al marcarla; las que nombran una forma que no existe en esa lectura no hacen nada | Con un diseño por archivo alcanza |
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

### 5.1 Las correcciones en el análisis

Una corrección es el nombre de una forma y una de dos palabras: `cortar` o `no_va`.

- **Lo corregido manda.** La forma queda con lo que se marcó, diga lo que diga cualquier regla, y con el motivo «lo marcó quien carga».
- **Una forma que no va no es madre de nadie.** Lo que tiene adentro se lee como si ella no estuviera: deja de ser «su recorte» y pasa por las reglas de siempre. Es lo que hace que sacar un contorno ponga a cortar las letras que encierra.
- **Una forma forzada a cortar nunca pasa a recorte,** aunque esté adentro de otra que se corta. Y como se corta, lo que tiene adentro, de su mismo color, es su recorte.
- **También manda sobre los huecos de una pieza unida,** que entran descartados por cómo se arman: un clic los pone a cortar.
- El análisis suma un rol, «no va». La importación de varios diseños (`/importaciones/dxf/...`) lo recibe sin cambios: ahí solo se crean las formas con rol «cortar».

### 5.2 Los dos pedidos

`POST /trabajos/{id}/dxf/lectura` y `POST /trabajos/{id}/dxf` reciben un campo más, `correcciones`: un objeto JSON de nombre de forma a `cortar` o `no_va`. Sin el campo, todo anda como hoy.

- **La lectura** sigue devolviendo las dos lecturas, sin unir y unida, cada una con las correcciones aplicadas. Una lectura no hace nada con la corrección de una forma que no tiene.
- De cada forma vuelve **uno de tres estados** (`se_corta`, `descartada`, `no_va`) en vez del sí o no de hoy, y si está corregida. Los totales suman cuántas no van.
- **La carga** no guarda las formas que no van, y avisa cuántas fueron.
- **Lo que no sirve da 400,** con un mensaje que dice qué: un JSON mal escrito, una palabra que no es `cortar` ni `no_va`, o una forma que no existe en ninguna de las dos lecturas.

### 5.3 La pantalla

```
┌─ Así se lee ───────────────────────────────────────────────┐
│                                       [ + ] [ − ] [Ver todo]│
│        el dibujo: rueda para acercar, arrastrar para       │
│        mover, clic en una forma para corregirla            │
├────────────────────────────────────────────────────────────┤
│ Pintado: se corta · Punteado: entra descartada ·           │
│ Rayado rojo: no va                                         │
│ 17 piezas a cortar · 2 entran descartadas · 15 no van      │
│                                                            │
│ Tus correcciones:  497 no va ✕   527 no va ✕   533 no va ✕ │
│                    [ Quitar todas ]                        │
│ [ ] Unir las formas que se pisan                           │
│ [ Cargar ]  [ Cancelar ]                                   │
└────────────────────────────────────────────────────────────┘
```

- **Tres estados a la vista:** lo que se corta, pintado; lo que entra descartado, en línea de puntos; lo que no va, rayado en rojo. Lo que corrigió la persona lleva el borde más grueso.
- **Las formas se dibujan de la más grande a la más chica,** así la chica queda arriba y recibe el clic. Una forma sin relleno también se puede tocar, en su cuerpo y no solo en su línea.
- **Cada corrección figura abajo** con el nombre corto de la forma y una ✕ que la saca. «Quitar todas» vuelve a la lectura del sistema.
- **Acercar y mover:** la rueda acerca hacia donde está el puntero, hasta `PAR-53`; arrastrar mueve; «Ver todo» vuelve al dibujo entero. Soltar después de arrastrar no cuenta como clic.
- **Mientras llega la lectura nueva** se sigue viendo la anterior, atenuada. Si se hace otro clic antes, vale la última respuesta pedida.
- **Al pasar el mouse:** el nombre de la forma, su medida, su estado y el motivo.
- Cambiar el archivo o la escala cierra el panel y borra las correcciones, como ya pasa con la lectura.
- **«Cargar» se apaga** si no queda ninguna forma para cortar, y lo dice.
- La identidad visual es la de [`frontend-cotizador/diseno.md §4`](../../historico/frontend-cotizador/diseno.md).

---

## 6. Cómo se valida

1. **Pruebas automáticas del análisis,** con piezas armadas a mano: sacar un contorno pone a cortar lo que encierra; una forma forzada a cortar no pasa a recorte y lo de adentro es su recorte; una corrección sobre una forma que no existe no hace nada.
2. **Pruebas de las rutas:** la lectura con correcciones devuelve los tres estados y los totales; la carga no guarda lo que no va; lo que muestra la lectura es lo que guarda la carga, también con correcciones; los tres errores que dan 400.
3. **Pruebas de la pantalla** para sus cuentas: qué pasa con un clic, en qué orden se dibuja, acercar hacia un punto, mover sin salirse, el texto de los totales.
4. **El logo:** un DXF con el logo solo, armado a partir de la muestra y guardado fuera del repositorio. Los quince clics del §2, por el camino de la pantalla, tienen que dejar las 17 formas del criterio de éxito.
5. **`Complejo.dxf`:** sin correcciones, con y sin unir, da los mismos totales que hoy (26 y 14; 24 y 34).
6. **En la app,** contra una copia de los datos de Enzo, con capturas: corregir el logo, acercar, cargar.

---

## 7. Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| Cada clic vuelve a mandar el archivo | En un archivo grande, segundos por clic | Con un diseño por archivo son décimas. Se muestra que está leyendo. Los archivos con varios diseños quedan afuera (§3) |
| Al sacar una forma aparece la de adentro | Hay que sacarla también; en el logo pasa tres veces | Se ve en el dibujo apenas pasa. Marcar de a muchas queda anotado (§3) |
| La persona saca todo | «Cargar» borraría las piezas del trabajo | «Cargar» se apaga si no queda nada para cortar |
| Las correcciones se pierden al cambiar el archivo o la escala | Hay que hacerlas de nuevo | Se acepta: son pocos clics, y con otra escala u otro archivo no valdrían |
| Una forma muy chica es difícil de tocar | No se puede corregir sin acercar | Para eso está el acercamiento, hasta `PAR-53` |
| La respuesta de la lectura cambia de forma | El sí o no de «descartada» pasa a ser un estado de tres | Solo la usa esta pantalla, que cambia en el mismo sub-proyecto |
| El dibujo pesa más | Con `PAR-52` en 1/20000, 170 KB por lectura en `Complejo.dxf` en vez de 79 | Se acepta. En un archivo de varios diseños pesaría varias veces más, y esos quedan afuera |
