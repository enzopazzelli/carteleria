# PLANILLA: parámetros reales del taller

> Para llenar **con el operario, frente a la máquina**. Cierra `B-03` y `B-04`, y de paso responde tres preguntas nuevas que aparecieron al construir el motor de nesting.
>
> Las preguntas y cómo formularlas están en [`GUION-ENTREVISTAS-RELEVAMIENTO.md`](GUION-ENTREVISTAS-RELEVAMIENTO.md) (`P-03`, `P-04`). Esto es dónde anotar las respuestas.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`REGISTRO.md`](REGISTRO.md) · [`MAPA-DEL-PROYECTO.md`](MAPA-DEL-PROYECTO.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-10

---

## Por qué esto es lo más urgente del proyecto

**Todo lo que el sistema calcula hoy usa valores que inventamos nosotros.** Las planchas necesarias, el porcentaje de aprovechamiento, el costo, y el DXF que iría a la máquina salen de un kerf de 2 mm, un margen de 10 mm y una separación de 5 mm que nadie confirmó. El motor funciona; los números no son presentables.

Es media hora de conversación y desbloquea más que cualquier desarrollo pendiente.

---

## 1. Parámetros de corte, por material

Una fila por material **y espesor** — `SUP-03` supone que el kerf es constante por esa combinación, y esa suposición hay que confirmarla o romperla acá.

| Material | Espesor / calibre | Kerf (mm)<br/>`PAR-01` | Margen de borde (mm)<br/>`PAR-02` | Separación entre piezas (mm)<br/>`PAR-03` | ¿Tiene veta?<br/>`PAR-04` |
|---|---|---|---|---|---|
| Chapa negra | cal. 14 | | | | |
| Chapa negra | cal. 16 | | | | |
| Chapa negra | cal. 18 | | | | |
| Chapa negra | cal. 20 | | | | |
| Chapa negra | cal. 22 | | | | |
| Chapa galvanizada | cal. 18 | | | | |
| Chapa galvanizada | cal. 20 | | | | |
| Chapa galvanizada | cal. 25 | | | | |
| Chapa galvanizada | cal. 27 | | | | |
| Acero inox. A240 430 | 0,70 mm | | | | |
| Polyfan | | | | | |
| MDF | | | | | |
| Acrílico (cristal) | | | | | |
| Acrílico (blanco) | | | | | |
| PVC | | | | | |
| ACM | | | | | |

**Cómo preguntar cada columna, si no usan los términos:**

- **Kerf** — *"cuando corta, ¿cuánto material se come la línea de corte?"* Si no lo saben de memoria: cortar dos piezas pegadas de una chapa de descarte y medir la separación real que queda.
- **Margen de borde** — *"en el borde de la chapa, ¿dejan un margen que nunca usan? ¿de cuánto?"*
- **Separación entre piezas** — *"¿dejan aire entre pieza y pieza, además de lo que se come el corte?"* Es distinto del kerf: **si contestan uno solo, hay que preguntar explícitamente por el otro** (`ADR-09`, `DECISIONES §1.4`).
- **Veta** — *"¿hay materiales que no se pueden girar, que tienen una dirección?"* Si dudan: *"¿hay piezas que siempre salen en el mismo sentido?"*

> ⚠️ **Si no saben el kerf**, el peor resultado es que inventemos otro número. Anotar "no sabe" es una respuesta válida y útil: significa que hay que medirlo, no que se puede estimar.

---

## 2. Preguntas nuevas, que salieron de construir el motor

Ninguna de estas estaba en el relevamiento original. Aparecieron al medir el motor contra archivos reales.

### 2.1 ¿Cuánto vale un metro de corte que no se repite?

El motor irregular detecta **corte de líneas compartidas**: dos piezas que comparten un borde recto se cortan de una sola pasada. Medido sobre `repisas.dxf`, encontró **47 metros** de corte compartido en un trabajo de 128 unidades.

**Hoy no podemos traducir eso a plata.** Hace falta alguno de estos:

- Costo por metro lineal de corte: `_______` $/m
- O bien: velocidad de corte (`____` m/min) y costo por hora de máquina (`____` $/h)
- ¿El costo cambia según el material o el espesor? ☐ Sí ☐ No — si sí, ¿cómo?

Sin este dato, el corte compartido es una función que anda pero que no sabemos si conviene activar.

### 2.2 ¿Qué se hace con el retazo?

El motor puede acomodar las piezas para dejar el sobrante como **una franja entera al final de la plancha** en vez de tiras finas repartidas. Eso solo vale la pena si el retazo se guarda y se reusa.

- ¿Guardan los retazos para otro trabajo? ☐ Sí ☐ No ☐ A veces
- Si sí: ¿desde qué tamaño vale la pena guardarlo? `______ × ______` mm
- ¿Lo registran en algún lado, o es "está en el rincón"? `___________________`
- ¿Alguna vez arrancan un trabajo desde un retazo en vez de una plancha nueva? ☐ Sí ☐ No

### 2.3 ¿Cuánto lleva hoy armar el anidado, y de qué depende?

Ya sabemos que ronda las **2 horas** (`B-17`). Falta afinarlo, porque es el baseline de `PAR-32`:

- ¿Esas 2 horas son de un trabajo típico o de uno complejo? `___________________`
- ¿Un trabajo simple cuánto lleva? `______` · ¿Uno complicado? `______`
- ¿Incluye armar el presupuesto, o es solo acomodar las piezas? ☐ Solo anidar ☐ Anidar + presupuestar
- ¿Cuántos trabajos así hacen por semana? `______`

---

## 3. Cómo se corta y qué formato quiere la máquina

Esto define si el DXF que exportamos sirve tal cual (`exportacion_dxf.py`).

- ¿Qué máquina/s cortan? Marca y modelo: `___________________`
- ¿Con qué programa se le manda el trabajo? `___________________`
- ¿Ese programa lee DXF? ☐ Sí ☐ No ☐ Otro formato: `__________`
- ¿Quién arma el programa de corte hoy — el operario, el diseñador? `___________________`
- ¿Usan capas para distinguir corte de otras cosas? ☐ Sí ☐ No
  - Si sí, **con qué nombres**: `___________________` ← esto cierra `CART-501`/`ADR-02` y hoy es una convención que propusimos nosotros (`CORTE`/`PLEGADO`/`GUIA`/`TEXTO`)
- ¿La máquina compensa el kerf sola, o el archivo tiene que venir compensado? ☐ La máquina ☐ El archivo

> Si la respuesta a la última es "el archivo", **cambia cómo exportamos**: hoy el DXF lleva el contorno real de la pieza y el kerf se usa solo para separar. Conviene preguntarlo antes de que alguien corte con nuestro archivo.

---

## 4. Materiales: qué se anida y qué no

El relevamiento ya mostró que no todo entra al motor de nesting. Confirmar la clasificación:

| Material | Se anida por área | Se cobra por metro lineal | Lo provee a veces el cliente |
|---|---|---|---|
| Chapa (todas) | ☐ | ☐ | ☐ |
| Polyfan | ☐ | ☐ | ☐ |
| MDF | ☐ | ☐ | ☐ |
| Acrílico | ☐ | ☐ | ☐ |
| PVC | ☐ | ☐ | ☐ |
| ACM | ☐ | ☐ | ☐ |
| Tubos estructurales | ☐ | ☐ | ☐ |
| Tiras de LED | ☐ | ☐ | ☐ |

Y las medidas que faltan confirmar (hoy están puestas de mercado, no del cliente):

- Acrílico: `______ × ______` mm
- PVC: `______ × ______` mm
- ACM: `______ × ______` mm

---

## 5. Qué hacer con esto después

1. Cargar los valores en `REGISTRO.md`: `PAR-01` a `PAR-04` dejan de ser 🔴 provisorios.
2. Marcar `B-03` y `B-04` como resueltos, con fecha.
3. Si aparece el costo por metro de corte, darlo de alta como `PAR-xx` nuevo — es lo que permite decidir si el corte compartido se activa.
4. Si la convención de capas del taller es distinta de la nuestra, **usar la de ellos** en `exportacion_dxf.py` y en `dxf.py`. La convención existe para que el archivo se entienda en el taller, no al revés.
