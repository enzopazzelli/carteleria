# CONTRATO: Python ↔ motor de nesting irregular

> El formato JSON que hablan `backend/app/services/nesting/deepnest_cliente.py` y `nesting-engine/`. Definirlo temprano es lo que permite que el transporte cambie (hoy `subprocess`, mañana HTTP en Docker) sin tocar ninguno de los dos lados.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`PLAN-MOTOR-NESTING-DEEPNEST.md`](PLAN-MOTOR-NESTING-DEEPNEST.md) · [`COMO-FUNCIONA-CADA-MOTOR.md`](COMO-FUNCIONA-CADA-MOTOR.md) · [`REGISTRO.md`](REGISTRO.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-08 · Estado: **spike**, puede cambiar

---

## Reglas que valen para todo el contrato

- **Todas las medidas están en milímetros.** Sin excepción, sin unidades implícitas. Es `CONVENCIONES §6`, la convención que más caro sale equivocar.
- **El JSON es transporte, no fuente de verdad.** JavaScript solo tiene `double`; el backend trabaja en `Decimal`. Al recibir la respuesta, Python re-cuantiza a mm y valida contra `PAR-29` (±0,5 mm). Un resultado que no pase esa validación se rechaza — no se persiste un layout que no se puede cortar.
- **El motor no parsea archivos.** Recibe polígonos ya parseados. El DXF lo hace `ezdxf` en Python (F5), y eso es lo que además permite excluir la dependencia AGPL del upstream.
- **Los polígonos son listas de `[x, y]`**, sin repetir el primer punto al final. Se asumen cerrados.
- **El origen de coordenadas de cada pieza es su propio bounding box** (`[0, ancho] × [0, alto]`), no el del archivo de origen. Es lo que ya produce `GeometriaPieza.contorno_local_mm`.

---

## Entrada

```jsonc
{
  "plancha": { "ancho_mm": 1220, "alto_mm": 2440 },

  "piezas": [
    {
      "id": "repisa-04",           // único; vuelve en la respuesta
      "cantidad": 8,               // opcional, default 1
      "contorno_mm": [[0,0], [300,0], [300,200], [0,200]],
      "agujeros_mm": [             // opcional — CART-505
        [[50,50], [80,50], [80,80], [50,80]]
      ],

      // Corte de líneas compartidas: ver la sección de abajo.
      "contorno_recto": true,      // opcional — toda la pieza es de tramos rectos
      "vertices_exactos": [true, true, false, false]  // opcional, por vértice; gana sobre el anterior
    }
  ],

  "parametros": {                  // PAR-01 a PAR-04
    "kerf_mm": 2,
    "margen_borde_mm": 10,
    "separacion_piezas_mm": 5,
    "rotaciones_permitidas": "LIBRE_0_90"   // o "SOLO_0_180" si el material tiene veta
  },

  "motor": {                       // todo opcional
    "semilla": "presupuesto-1234", // reproducibilidad — ver PLAN §5
    "generaciones": 3,
    "poblacion": 10,
    "tiempo_maximo_ms": 0,         // 0 = sin tope de reloj. Ver la advertencia de abajo
    "estrategia": "box",           // box | gravity | convexhull
    "corte_compartido": true,
    "peso_corte_compartido": 0.5   // 0 = optimizar solo material, 1 = solo tiempo de corte
  }
}
```

### Cómo se traducen los tres parámetros de corte

Deepnest tiene **un solo** `spacing`; el proyecto tiene tres cosas independientes (`DECISIONES §1.4`). El colapso se hace adentro del motor y es reversible — de cara al usuario siguen siendo tres. La semántica que se reproduce es exactamente la de `engine.py`:

- entre dos piezas contiguas queda un hueco real de **kerf + separación**;
- el borde real de una pieza queda a **margen + kerf/2** del borde de la plancha.

De ahí salen los dos offsets que aplica `src/geometria.js`: cada pieza se infla `(kerf + separación) / 2`, cada agujero se **encoge** lo mismo, y la plancha se encoge `margen − separación/2`.

> ⚠️ Si la separación es más del doble del margen de borde, el encogido de plancha daría negativo. El motor usa margen 0 y **avisa**, en vez de anidar sobre el margen. Es una combinación de parámetros que no tiene sentido físico y conviene revisarla.

### `tiempo_maximo_ms` y la reproducibilidad

Con `0`, el motor corta por cantidad de generaciones y el resultado es **reproducible**: misma semilla, mismo layout. Con un tope de reloj (`PAR-09`), el resultado empieza a depender de la carga del servidor y deja de serlo. Es la decisión pendiente de `PLAN-MOTOR-NESTING-DEEPNEST.md` §5.

### Declarar aristas rectas: sin esto no hay corte compartido

El detector de líneas compartidas **ignora toda arista cuyos dos extremos no estén marcados como recta real**. Un tramo recto que en realidad es la discretización de una curva no se puede cortar de una pasada junto a otra pieza, aunque quede paralelo.

`dxf.py` es quien sabe la verdad: si el tramo vino de un `LINE`/`LWPOLYLINE` es recto de verdad; si vino de discretizar un `ARC`/`SPLINE`/`CIRCLE`, no. Mientras eso no se exponga, se declara con `contorno_recto` a nivel pieza.

**Si `corte_compartido` está activo y ninguna pieza declara aristas rectas, el motor devuelve una advertencia** — la feature queda apagada, y quedarse callado sería peor que no tenerla.

---

## Salida

```jsonc
{
  "posiciones": [
    {
      "pieza_id": "repisa-04",
      "instancia": 3,              // 0-based, dentro de `cantidad`
      "plancha_indice": 0,         // 0-based
      "angulo_grados": 90,
      "tx_mm": 412.5,
      "ty_mm": 88.0,
      "largo_corte_compartido_mm": 600
    }
  ],
  "planchas_usadas": 5,
  "piezas_colocadas": 64,
  "piezas_totales": 64,
  "largo_corte_compartido_mm": 23104,
  "aprovechamiento_motor_pct": 71.2,   // INFORMATIVO — ver abajo
  "diagnostico": {
    "generaciones": 3, "evaluaciones": 30, "nfpsCacheados": 812,
    "milisegundos": 93550, "cortadoPorTiempo": false,
    "cortadoPorGeneraciones": true, "semilla": "presupuesto-1234",
    "motor": "deepnest", "corte_compartido_activo": true, "estrategia": "box"
  },
  "advertencias": ["..."]
}
```

### Cómo se interpreta una posición

> **La posición final es: rotar el contorno ORIGINAL `angulo_grados` alrededor del origen, y después trasladarlo `(tx_mm, ty_mm)`.**

El contorno original, no el inflado por el kerf. El inflado es interno al motor y no vuelve en la respuesta.

`deepnest_cliente.py` hornea esa transformación en la geometría al traducir a `PosicionPieza`: devuelve el contorno ya rotado y renormalizado a su bounding box, con `rotada_90=False` y el ángulo real en `angulo_libre_grados`. Sin eso, el visor (`visualizacion.py`) —que solo entiende 0° y 90°, herencia de `ADR-01`— dibujaría mal cualquier pieza a 180° o 270°.

### `aprovechamiento_motor_pct` no es el número del sistema

Vuelve solo como diagnóstico. **El porcentaje que el sistema publica lo calcula Python con `shapely` sobre la geometría real** (`ADR-08`, corrección de `DECISIONES §1.1`). Con dos motores que anidan distinto, la única comparación honesta es con la misma vara — y además el número del motor se calcula sobre el área útil que él conoce, que no es la misma definición que usa el proyecto.

---

## Errores

- Fallo de validación de la entrada, o el motor no pudo producir ninguna colocación → salida por `stderr`, código de salida distinto de 0. `deepnest_cliente.py` lo convierte en `ErrorMotorDeepnest`.
- Problemas que no impiden devolver un resultado (agujeros que se cierran con el kerf, piezas sin colocar, corte compartido inactivo) → `advertencias` en la respuesta, código 0. **Nunca se descarta una pieza en silencio** — mismo criterio que `DECISIONES §1.2`.

---

## Transporte

Hoy: `node src/cli.js --silencioso`, JSON por stdin, JSON por stdout, progreso por stderr. Un proceso por corrida.

Fase 1 (si el spike da go): `POST /nest` sobre el mismo JSON, en un contenedor `nesting-engine` sin puertos publicados. **El contrato no cambia** — cambia quién lo transporta.
