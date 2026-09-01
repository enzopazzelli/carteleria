# PLAN: MOTOR DE NESTING NATIVO — SIN SERVICIOS EXTERNOS

> Plan de contingencia a [`PLAN-MOTOR-NESTING-DEEPNEST.md`](PLAN-MOTOR-NESTING-DEEPNEST.md): cómo acercarse al valor de Deepnest (huecos, corte de líneas compartidas) sin sumar ningún proceso externo — todo corriendo dentro del mismo backend Python que ya define `ADR-05`, sin un microservicio Node ni ninguna llamada de red a otro runtime.
>
> **Interpretación de "sin consumir otros servicios"** (para confirmar): un servicio es un proceso separado al que hay que llamar por red — el microservicio Node de `deepnest-next` entra en esa categoría. Las librerías Python que ya corren adentro del mismo proceso del backend (`shapely`, `rectpack`, `nest2D`) no cuentan como "otro servicio": no hay red, no hay otro runtime, no hay otro contenedor que mantener. Este plan se queda solo con eso.
>
> Es un plan, no una ejecución. No modifica todavía `REGISTRO.md`, `BACKLOG.md` ni `EPICA.md`.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) · [`REGISTRO.md`](REGISTRO.md) · [`PLAN-MOTOR-NESTING-DEEPNEST.md`](PLAN-MOTOR-NESTING-DEEPNEST.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-01

---

## Contexto

El plan de Deepnest (`deepnest-next` como microservicio Node) resuelve `D-01` sumando un segundo runtime al stack: Node + un toolchain nativo (Rust/C++) para compilar `node-calculateNFP`, un contenedor más en el VPS, y un riesgo legal residual documentado (código heredado sin licencia propia). Es una apuesta razonable, pero es exactamente lo que hay que evitar si en algún momento no se puede o no conviene sumar esa complejidad — por costo de infraestructura, porque el VPS no da abasto, o simplemente porque un equipo de dos personas part-time no quiere mantener un segundo lenguaje en producción.

Este documento es esa alternativa: **qué tan lejos se puede llegar quedándose enteramente en Python**, sin ningún servicio externo, aunque eso signifique resignar algo de lo que Deepnest ofrece "gratis".

## Lo que ya sabemos que no alcanza tal cual

`nest2D` (binding de `libnest2d`, la opción por default de `D-01` en `ADR-05`) lo dice en su propia documentación oficial: **"funciona bien para rectángulos y polígonos convexos cerrados, sin considerar huecos ni concavidades."** No hay mención de corte de líneas compartidas en ningún lado de su documentación.

Es decir: **el motor Python que ya está elegido no soporta anidado-en-huecos ni corte de líneas compartidas, tal cual viene.** Esto no es un problema nuevo que este plan introduce — es la razón por la que Enzo empezó a mirar Deepnest en primer lugar. La pregunta real no es "¿Python o Deepnest?" sino **"¿construimos huecos y corte compartido nosotros, encima de lo que ya tenemos en Python, o los importamos ya hechos desde un servicio externo?"**

---

## Diseño: motor en capas, todo dentro del proceso Python

```
Capa 1 — Colocación primaria (sin cambios respecto a ADR-05)
  F2 (rectangular)  → rectpack
  F7 (irregular)     → nest2D / libnest2d
        │
        ▼
Capa 2 — Anidado en huecos (nuevo, construido con Shapely)
        │
        ▼
Capa 3 — Corte de líneas compartidas (nuevo, ajuste al packer + post-proceso)
        │
        ▼
Capa 4 — Timeout y mejor resultado parcial (ya existía: CART-703, PAR-09)
```

### Capa 2 — Anidado en huecos

Shapely ya modela los huecos de un polígono como parte de su tipo nativo (`Polygon.interiors`) — no hace falta ninguna librería nueva para detectarlos, ya es una dependencia existente por `ADR-08`.

**Enfoque de dos pasadas**, en vez de un único algoritmo que considera todo a la vez (que es lo que hace Deepnest internamente):

1. La Capa 1 coloca las piezas "grandes" con `rectpack`/`nest2D`, como hoy.
2. Sobre el resultado, se calculan los huecos interiores de cada pieza colocada (`Polygon.interiors` de Shapely) y se descartan los que no llegan a un área mínima aprovechable (nuevo parámetro, ver más abajo).
3. Para cada hueco que sobrevive el filtro, se intenta encajar ahí alguna de las piezas pendientes más chicas: se prueban traslaciones/rotaciones con `shapely.affinity` y se valida con `hueco.contains(pieza_transformada)`. Es un *fit* greedy, no una optimización global.
4. Las piezas que entraron en un hueco salen de la lista de piezas a nestear en el packer principal — son "gratis": no consumen plancha nueva.

**Por qué alcanza para este caso de uso:** en Deepnest, esta feature nació para nesting genérico (formas arbitrarias, muchas piezas, huecos irregulares). En cartelería, los huecos que importan son sobre todo los de letras corpóreas (la "O", la "A", la "P", la "8") — geometrías conocidas, pocos huecos por pieza, relativamente simples. Un *fit* greedy de dos pasadas no es tan bueno como una optimización conjunta, pero para este universo de formas debería capturar la mayor parte del ahorro real sin la complejidad de un motor de NFP-con-huecos integrado.

### Capa 3 — Corte de líneas compartidas

Esta es más simple de lo que parece **para F2** (que es además donde más vale, según ya se había concluido en `FACTIBILIDAD-NESTING-WEB.md`): un packer tipo guillotina como `rectpack` ya tiende a producir filas/columnas de piezas con bordes alineados — el trabajo real no es "inventar" el corte compartido, es **detectarlo y aprovecharlo**:

1. Post-proceso sobre el layout ya calculado: para cada par de piezas rectangulares adyacentes, si un borde de una es paralelo y está a una distancia menor a una tolerancia (nuevo parámetro) del borde de la otra, se marcan como **par de corte compartido**.
2. Para esos pares, la separación entre piezas (`PAR-03`) se reduce a un único paso de corte (kerf) en vez de kerf + separación por partida doble — la máquina corta una sola vez y separa las dos piezas.
3. El plano de corte (`CART-207`/`CART-705`) resalta estos pares para que el operario sepa que ahí va una sola pasada.

**Para F7 (irregular),** el mismo mecanismo aplica pero rinde mucho menos: dos curvas orgánicas rara vez son colineales por casualidad. Coherente con lo ya señalado en `FACTIBILIDAD-NESTING-WEB.md`: el corte compartido vale sobre todo en paneles rectos, no en letras corpóreas.

### Capa 4 — Timeout y mejor resultado parcial

Sin cambios: se reutiliza el patrón que `CART-703` ya define (devolver el mejor resultado encontrado hasta el timeout `PAR-09`, no quedarse esperando un óptimo).

---

## Qué se gana y qué se resigna frente al plan de Deepnest

| | Este plan (Python nativo) | Plan Deepnest (`deepnest-next`) |
|---|---|---|
| Infraestructura nueva | Ninguna — mismo backend, mismo contenedor | Un contenedor Node + toolchain nativo (Rust/C++) |
| Riesgo legal | Ninguno — todo lo que se usa ya está en `ADR-05` (`shapely`, `rectpack`, `nest2D`, LGPL/BSD) | Riesgo residual documentado (código heredado sin licencia propia) |
| Anidado en huecos | Aproximado, dos pasadas, greedy — bueno para huecos simples (letras) | Integrado en el motor, optimización conjunta |
| Corte de líneas compartidas | Bueno para F2 (rectangular), débil para F7 (irregular) | Nativo para ambos, pero más relevante también en F2 |
| DXF | Sin cambios — `ezdxf`/`svgelements` en Python, F5, no depende de cuál motor de nesting se elija | Igual, sin cambios |
| Costo de construcción | Código nuevo en Python, sin spike de viabilidad de Electron/headless | Spike de extracción del núcleo de Electron (el riesgo técnico más grande de ese plan) |
| Mantenimiento a largo plazo | Un solo lenguaje, un solo runtime, lo que ya elegía `ADR-05` | Un segundo lenguaje/runtime a mantener de por vida |

**Este plan no llega al mismo resultado que Deepnest — llega a una aproximación razonable, más barata y sin riesgo nuevo.** Si en el punto de validación de H1 (fin de S3, ya previsto en `EPICA.md §8`) esta aproximación no alcanza el objetivo de aprovechamiento (`PAR-33`), ahí es cuando se justifica escalar al plan de Deepnest — no antes.

---

## Nuevos parámetros propuestos (a dar de alta en `REGISTRO.md` si se ejecuta este plan)

| Parámetro propuesto | Qué es | Default sugerido |
|---|---|---|
| Área mínima de hueco aprovechable | Debajo de este umbral, no vale la pena intentar encajar nada ahí | A definir — probablemente relacionado al tamaño mínimo de pieza que se corta |
| Tolerancia de alineación para corte compartido | Distancia máxima entre dos bordes para considerarlos "el mismo corte" | A definir — del orden del kerf (`PAR-01`) |
| Flag de motor avanzado | Permite apagar las Capas 2 y 3 si en producción no rinden, sin tocar la Capa 1 | Habilitado, con rollback fácil |

No se les asigna número `PAR-xx` todavía — eso es parte de ejecutar este plan (Fase de documentación), no de plantearlo.

---

## Cómo se relaciona con `D-01` y con el plan de Deepnest

`D-01` en `REGISTRO.md` está planteado como binario: `nest2D` o Deepnest. Este plan propone que en realidad hay una tercera vía — **`nest2D` + Capas 2 y 3 construidas en Python** — que no estaba contemplada como opción explícita. Si se ejecuta, `D-01` se resolvería así en vez de a favor de uno u otro proyecto externo.

**Recomendación de secuencia, si se decide entre los dos planes:** empezar por este (sin infraestructura nueva, sin riesgo legal, reutiliza lo que `ADR-05` ya adoptó) y medir contra `PAR-33` en el punto de validación de H1. Si el aprovechamiento real con las Capas 2 y 3 no alcanza el objetivo, recién ahí se justifica el costo y el riesgo de sumar el microservicio Node de `PLAN-MOTOR-NESTING-DEEPNEST.md`.

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| El *fit* greedy de huecos puede fallar en casos con muchas piezas candidatas — sin optimización conjunta, puede dejar afuera un hueco que un algoritmo integrado sí hubiera aprovechado | Aceptado: el objetivo es "suficientemente bueno" (`NFR-02`), no óptimo. Se mide contra el baseline real en H1 |
| Detectar "bordes paralelos y cercanos" para corte compartido puede generar falsos positivos en piezas que en la práctica no se pueden cortar juntas (distinto espesor, distinto material) | El chequeo de corte compartido solo aplica entre piezas del mismo material y espesor — mismo criterio que ya usa `materiales_parametros` |
| Construir las Capas 2 y 3 a mano es trabajo de desarrollo real, no una librería que se instala | Se acota con un spike inicial (ver Fases) antes de comprometer el resto del esfuerzo |
| Puede no alcanzar el nivel de Deepnest y de todas formas haga falta escalar más adelante | Aceptado explícitamente arriba — es el motivo de tener los dos planes documentados |

---

## Fases

1. **Spike de la Capa 2** (anidado en huecos): probar el enfoque de dos pasadas contra 3-5 piezas reales con hueco conocido (letras corpóreas). Éxito = el *fit* greedy coloca correctamente piezas chicas dentro de huecos grandes conocidos.
2. **Spike de la Capa 3** (corte compartido): probar la detección de bordes paralelos sobre un layout real de `rectpack`. Éxito = detecta correctamente los pares que un ojo humano marcaría como "esto se corta junto".
3. **Integración con F2/F7**: las Capas 2 y 3 se insertan como paso posterior al packer existente, sin tocar `rectpack`/`nest2D` en sí.
4. **Medición en H1**: comparar `PAR-33` (mejora de aprovechamiento) con y sin las Capas 2 y 3 activas, contra el baseline real (`B-17`).

---

## Verificación

- Casos con piezas de hueco conocido (letras "O", "A", "B") — verificar que piezas chicas terminan ubicadas dentro del hueco cuando corresponde, y que no se fuerza un encaje que no entra.
- Casos con paneles rectos adyacentes — verificar que el plano de corte marca correctamente los pares de corte compartido, y que nunca cruza esa marca entre materiales o espesores distintos.
- Comparación directa del % de aprovechamiento (Shapely, `ADR-08`) con y sin las Capas 2 y 3, sobre el mismo conjunto de piezas.

---

## Próximo paso

Ninguno todavía — este documento queda como alternativa documentada junto a `PLAN-MOTOR-NESTING-DEEPNEST.md`, a la espera de que se decida cuál encarar primero (o si se encara este como el default y el otro como escalamiento).
