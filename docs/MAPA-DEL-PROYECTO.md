# MAPA DEL PROYECTO — dónde estamos parados

> Vista de conjunto para ubicarse: qué está construido, qué está a medias, qué está bloqueado y qué falta. Los diagramas son Mermaid y se ven directamente en GitHub y en VS Code.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) · [`BACKLOG.md`](BACKLOG.md) · [`REGISTRO.md`](REGISTRO.md) · [`COMO-FUNCIONA-CADA-MOTOR.md`](COMO-FUNCIONA-CADA-MOTOR.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-08 · Rama actual: `feat/F2-motor-nesting-rectangular`

---

## En una frase

**Está construido el corazón del dominio —el motor de nesting y todo lo que lo rodea— y no está construida ninguna de las fundaciones.** No hay API, ni base de datos, ni usuarios, ni Docker: el backend son módulos de Python puro que hoy se manejan desde un visor local. Se salteó el orden del roadmap a propósito, para poder probar el nesting con datos reales antes de comprometerse con la infraestructura.

---

## 1. Las nueve features y cómo dependen entre sí

```mermaid
flowchart TD
    F0["F0 · Fundaciones<br/>usuarios, roles, deploy<br/>S1 · 24 pts"]
    F1["F1 · Catálogo y precios<br/>S1 · 26 pts"]
    F2["F2 · Motor de nesting rectangular<br/>EL CORAZÓN<br/>S2 · 54 pts"]
    F3["F3 · Cotizador y PDF<br/>S3 · 47 pts"]
    F4["F4 · Aprobación y envío<br/>S4 · 37 pts"]
    F5["F5 · Importación desde Corel<br/>S5-S6 · 50 pts"]
    F6["F6 · Fotomontaje<br/>S7-S8 · 42 pts"]
    F7["F7 · Nesting irregular<br/>S9-S10 · 39 pts"]
    F8["F8 · Dashboard rápido<br/>carril B · 44 pts"]

    F0 --> F1 --> F2 --> F3 --> F4
    F2 -.->|"F2 validada en uso real"| F5
    F3 --> F6
    F4 --> F6
    F2 -.->|"F2 estabilizada"| F7
    APPSHEET(["Acceso a tablas<br/>de AppSheet"]) --> F8

    classDef hecho fill:#cfe8d5,stroke:#3d7a52,color:#14351f
    classDef parcial fill:#fdf0c8,stroke:#a8862a,color:#3d3007
    classDef nada fill:#eeeeee,stroke:#999,color:#555
    classDef adelantada fill:#d7e6f5,stroke:#3d6b96,color:#12314d

    class F0,F1,F3,F4,F6 nada
    class F2 parcial
    class F5,F7 adelantada
    class F8 parcial
```

| Color | Significa |
|---|---|
| 🟩 verde | terminado |
| 🟨 amarillo | en curso, parcial |
| 🟦 azul | **adelantada fuera de orden** — se construyó una parte antes de tiempo, porque hacía falta para probar F2 |
| ⬜ gris | sin empezar |

**Lo que salta a la vista: la cadena `F0 → F1 → F2` está invertida.** F2 se construyó primero, sobre nada. Es una decisión defendible (probar el motor con datos reales antes de invertir en infraestructura) pero tiene una consecuencia concreta: **F2 no se puede dar por terminada hasta que exista F1**, porque su fuente de parámetros y precios hoy son archivos sueltos y valores provisorios.

---

## 2. El flujo real del dato, y dónde se corta

```mermaid
flowchart LR
    subgraph existe ["CONSTRUIDO Y PROBADO CON DATOS REALES"]
        direction TB
        DXF["Archivo DXF<br/>del diseñador"] --> PARSER["Parseo<br/>ingesta/dxf.py<br/>contornos + agujeros"]
        PARSER --> MOTOR{"Motor de<br/>nesting"}
        MOTOR --> RECT["rectpack<br/>bounding box<br/>instantáneo"]
        MOTOR --> DEEP["deepnest<br/>forma real<br/>minutos"]
        RECT --> LAYOUT["Layout anidado"]
        DEEP --> LAYOUT
        LAYOUT --> AJUSTE["Ajuste manual<br/>mover, rotar, tandas<br/>quitar piezas"]
        AJUSTE --> APROV["Aprovechamiento real<br/>shapely, ADR-08"]
        AJUSTE --> PLANO["Plano imprimible<br/>para el operario"]
        AJUSTE --> DXFOUT["DXF de corte<br/>para la máquina"]
    end

    subgraph falta ["NO EXISTE"]
        direction TB
        PRECIOS["Catálogo de precios<br/>con vigencia (F1)"]
        COSTEO["Cotizador<br/>desglose editable (F3)"]
        PDF["PDF del presupuesto"]
        APROB["Aprobación del dueño<br/>y envío al cliente (F4)"]
    end

    APROV -.->|"acá se corta"| PRECIOS
    PRECIOS --> COSTEO --> PDF --> APROB

    classDef ok fill:#cfe8d5,stroke:#3d7a52,color:#14351f
    classDef no fill:#eeeeee,stroke:#999,color:#555
    class DXF,PARSER,MOTOR,RECT,DEEP,LAYOUT,AJUSTE,APROV,PLANO,DXFOUT ok
    class PRECIOS,COSTEO,PDF,APROB no
```

**El corte está justo después del aprovechamiento.** Todo lo que va del DXF al plano de corte funciona hoy con archivos reales del cliente. Lo que sigue —convertir eso en un presupuesto— no existe, y es exactamente lo que cierra **H1**.

---

## 3. Qué hay construido, historia por historia

```mermaid
flowchart TB
    subgraph F2b ["F2 · Motor de nesting rectangular"]
        direction TB
        C201["CART-201 · Carga manual de piezas"]
        C202["CART-202 · Motor bin packing"]
        C203["CART-203 · Kerf, margen, separación"]
        C204["CART-204 · Rotación por veta"]
        C205["CART-205 · Comparador de formatos"]
        C206["CART-206 · Aprovechamiento y materiales"]
        C207["CART-207 · Plano para el taller"]
        C208["CART-208 · Visor del anidado"]
        C209["CART-209 · Desarrollo de plegado"]
        C210["CART-210 · Parámetros del trabajo"]
    end

    subgraph F5b ["F5 · Importación (adelantada)"]
        C503["CART-503 · Parsear DXF"]
        C505["CART-505 · Agujeros reales"]
        C501["CART-501 · Convención de capas"]
        C502["CART-502 · Export desde Corel"]
    end

    subgraph F7b ["F7 · Nesting irregular"]
        SPIKE["Spike deepnest headless<br/>ANDA · go técnico"]
        HUECOS["Anidado en huecos"]
        COMPART["Corte de líneas compartidas"]
        SERV["Servicio en Docker"]
    end

    classDef hecho fill:#cfe8d5,stroke:#3d7a52,color:#14351f
    classDef parcial fill:#fdf0c8,stroke:#a8862a,color:#3d3007
    classDef nada fill:#eeeeee,stroke:#999,color:#555

    class C201,C202,C203,C204,C205,C206,C208,C503,C505,SPIKE,HUECOS,COMPART hecho
    class C207,C210 parcial
    class C209,C501,C502,SERV nada
```

**Parciales, y por qué:**

- **`CART-207` (plano para el taller)** — el plano imprimible y el DXF de corte existen y funcionan, pero viven en el visor local, no en el producto. Falta además marcar los cortes compartidos.
- **`CART-210` (parámetros del trabajo)** — se puede ajustar kerf, margen y separación en vivo y re-anidar, pero sin persistencia: no queda registrado con qué parámetros se calculó un trabajo.

---

## 4. El motor de nesting: dónde quedó la decisión

```mermaid
flowchart TD
    START(["¿Qué motor usar?"]) --> TIPO{"¿Qué tipo<br/>de pieza?"}
    TIPO -->|"Paneles rectos"| RECTA["rectpack<br/>·<br/>instantáneo y determinista<br/>deepnest NO ahorra planchas acá"]
    TIPO -->|"Letras corpóreas,<br/>formas curvas"| IRREG{"¿El material<br/>es la restricción?"}
    IRREG -->|"Sobra plancha"| EMPATE["Los dos empatan<br/>·<br/>gana rectpack por velocidad"]
    IRREG -->|"La plancha aprieta"| GANA["deepnest<br/>·<br/>MIDIÓ 1 plancha vs 2<br/>53,9% vs 26,9% de aprovechamiento"]

    GANA --> COSTO["Cuesta 150 s<br/>vs milisegundos"]
    COSTO --> OK["Aceptable: el trabajo<br/>manual lleva HOY 2 HORAS"]

    classDef verde fill:#cfe8d5,stroke:#3d7a52,color:#14351f
    classDef amarillo fill:#fdf0c8,stroke:#a8862a,color:#3d3007
    class RECTA,GANA,OK verde
    class EMPATE,COSTO amarillo
```

Detalle completo, con todas las mediciones: [`COMO-FUNCIONA-CADA-MOTOR.md`](COMO-FUNCIONA-CADA-MOTOR.md).

**Lo que falta decidir (`D-01`):** si los dos motores conviven o si se elige uno. Las mediciones dicen que no compiten por el mismo trabajo, y eso empuja a que convivan.

**Lo que falta construir para que deepnest sea producción:** el servicio en Docker (Fase 1 del plan) y traducir la capa de paralelismo a `worker_threads` — hoy corre en serie y es la mayor parte de esos 150 segundos.

---

## 5. Lo que bloquea, y a qué

```mermaid
flowchart LR
    B03["B-03 · Kerf y margen<br/>reales por material"] --> PAR["PAR-01/02/03<br/>hoy son PROVISORIOS"]
    B04["B-04 · Qué materiales<br/>tienen veta"] --> PAR04["PAR-04<br/>hoy se asume sin veta"]
    B06["B-06 · Proporción de piezas<br/>rectas vs corpóreas"] --> PRIO["Prioridad real de F7"]
    B17["B-17 · Baseline<br/>de métricas"] --> METRICAS["PAR-32 a PAR-36<br/>sin esto no se<br/>demuestra valor"]
    B01["B-01 · Tabla de precios<br/>vigente"] --> F1X["F1 · sin precios<br/>no hay presupuesto"]
    B02["B-02 · Formatos<br/>de material"] --> F1X
    B09["B-09 · Presupuestos<br/>reales de ejemplo"] --> H1X["Validación de H1"]

    PAR --> CORTE["Todo lo que se corta<br/>sale con medidas<br/>sin confirmar"]

    classDef bloq fill:#f7d4d4,stroke:#a83f2c,color:#4d1408
    classDef efecto fill:#fdf0c8,stroke:#a8862a,color:#3d3007
    classDef parcial fill:#e2e2f0,stroke:#6a6a9a,color:#25254a
    class B03,B04,B06,B01 bloq
    class B02,B09,B17 parcial
    class PAR,PAR04,PRIO,METRICAS,F1X,H1X,CORTE efecto
```

**El más urgente es `B-03`.** Todo lo que el sistema calcula hoy —planchas, aprovechamiento, costo, y el DXF que iría a la máquina— usa kerf, margen y separación **provisorios, inventados por nosotros**. Mientras eso siga así, ningún número es presentable ante el taller. Es una conversación de media hora con el operario, no un desarrollo.

`B-17` mejoró parcialmente: ya sabemos que **el armado manual lleva unas 2 horas**, que es el primer número duro de baseline.

---

## 6. Los hitos contra el calendario

```mermaid
flowchart LR
    H1["H1 · semana 7<br/>Cotizador con nesting<br/>MVP en uso real"]
    H2["H2 · semana 9<br/>Aprobación y envío"]
    H6["H6 · semana 12<br/>Dashboard rápido<br/>(carril paralelo)"]
    H3["H3 · semana 13<br/>Importación desde Corel"]
    H4["H4 · semana 17<br/>Fotomontaje"]
    H5["H5 · semana 21<br/>Nesting irregular"]

    H1 --> H2 --> H3 --> H4 --> H5
    H6 -.->|"en paralelo, no bloquea"| H3

    HOY(["HOY: motor de nesting construido,<br/>fundaciones en cero"])
    HOY ==>|"falta F0, F1 y F3"| H1

    classDef hito fill:#d7e6f5,stroke:#3d6b96,color:#12314d
    classDef hoy fill:#fdf0c8,stroke:#a8862a,color:#3d3007
    class H1,H2,H3,H4,H5,H6 hito
    class HOY hoy
```

> El calendario es el del plan original. **No refleja el avance real**: el trabajo hecho hasta ahora está repartido entre F2, F5 y F7, y las fundaciones siguen en cero. Sirve para ver el orden previsto y qué tan lejos está cada hito, no como compromiso de fechas.

---

## 7. Lo que yo haría ahora, en orden

1. **Cerrar `B-03` y `B-04` con el taller.** Media hora de conversación que vuelve presentables todos los números que ya calculamos. Es lo que más valor desbloquea por hora invertida.
2. **Construir F0 + F1.** Sin API ni base de datos, todo lo construido depende de un script local que no puede usar nadie más. Es el cuello de botella real, no el nesting.
3. **Decidir `D-01`** con las mediciones que ya están sobre la mesa.
4. **Terminar `CART-207` y `CART-210`** dentro del producto, no en el visor local.
5. **F3**, que es lo único que falta para H1.

Lo que **no** haría todavía: optimizar deepnest. Anda, ya sabemos cuánto rinde y cuánto cuesta, y el paralelismo pendiente es una mejora conocida que se puede hacer cuando haga falta.
