# Probar el sistema en tu computadora

> Guía completa para recorrer el cotizador de punta a punta en tu máquina. Para arrancar rápido, el [`README`](../README.md) tiene los cuatro pasos; acá está el detalle, el recorrido por las pantallas y cómo probar con tus propios DXF. Para probar con datos reales **sin tocar tu base real**, ver [`GUIA-PRUEBAS-LOCALES.md §6`](GUIA-PRUEBAS-LOCALES.md).

Guía para probar el cotizador de punta a punta en tu máquina. Todo corre en local, sin instalar bases de datos ni Docker, y **no necesita ningún archivo del cliente**: trae datos de demostración.

## Qué necesitás instalado

| Herramienta | Versión | Cómo chequearla |
|---|---|---|
| Git | cualquiera | `git --version` |
| Python | 3.11 o más nuevo (probado con 3.13) | `python --version` |
| Node.js | 18 o más nuevo (probado con 22) | `node --version` |

Vas a tener **tres terminales abiertas a la vez** (backend, frontend y una para los scripts de demo). Los comandos están escritos para Windows (PowerShell o cmd); en Mac/Linux reemplazá `.venv\Scripts\python` por `.venv/bin/python`.

## 1. Bajar el código

```
git clone https://github.com/enzopazzelli/carteleria.git
cd carteleria
```

## 2. Backend (terminal 1 — queda corriendo)

```
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r scripts/requirements-scripts.txt
.venv\Scripts\python -m uvicorn app.api.app:app --reload
```

La base se crea o se actualiza sola al arrancar; si estaba atrasada, antes guarda un respaldo en `backend/local/respaldo-…`.

**Una sola vez, el primer usuario** (sin él la pantalla no deja entrar). Con el backend ya arrancado una vez:

```
.venv\Scripts\python -m app.usuarios crear enzo --nombre "Enzo" --administrador --puede-aprobar --generar
```

Imprime una contraseña temporal; al entrar, la pantalla te pide elegir una propia (al menos 10 caracteres). Después, las demás personas se crean desde la pantalla **Usuarios** o con el menú de la terminal: [`docs/MANUAL-USUARIOS.md`](MANUAL-USUARIOS.md).

Usamos `.venv\Scripts\python` en vez de "activar" el entorno: evita el bloqueo de scripts de PowerShell y que se mezcle con otro Python. Cuando termine de arrancar, `http://localhost:8000/docs` tiene que mostrar la documentación de la API.

## 3. Datos de demostración (terminal 2, con el backend corriendo)

```
cd backend
.venv\Scripts\python scripts/cargar_catalogo_demo.py
.venv\Scripts\python scripts/generar_dxf_demo.py
```

El primero carga materiales "DEMO ..." (chapa negra, galvanizada, acrílico) con **precios inventados**, marcados como "(simulado)". El segundo crea `backend/local/demo.dxf`, un dibujo de ejemplo. Los dos se pueden correr de nuevo sin duplicar nada.

## 4. Frontend (terminal 3 — queda corriendo)

```
cd frontend
npm ci
npm run dev
```

Abrí **exactamente** `http://localhost:5173` (no `127.0.0.1`, no otro puerto): el backend solo acepta pedidos que vengan de esa dirección.

## 5. Recorrido de prueba

| # | Dónde | Qué hacer | Qué tendrías que ver |
|---|---|---|---|
| 1 | **Inicio** | En «Nuevo trabajo», escribí un nombre y apretá «Crear y cargar el DXF» | Entrás al trabajo: arriba queda la barra (Inicio · Trabajos) y a la izquierda las cinco etapas: Piezas, Grupos, Anidado, Chapas, Costeo |
| 2 | **Piezas** | Dejá la escala en `1`, elegí el archivo `backend/local/demo.dxf` | **11 piezas** con su dibujo, y un aviso: *"Se ignoraron 1 entidad(es)… (1 TEXT)"*. El aviso es a propósito: el texto del dibujo no se corta |
| 3 | **Grupos** | "Nuevo grupo" (ej. «Chapa negra») → tildá "Seleccionar todas" → elegí el grupo en "Mover a grupo…" → "Mover" | Las piezas pasan al grupo |
| 4 | **Grupos** | En el grupo, "Comparar formatos" → tildá 2 o más formatos «DEMO» → "Comparar" → "Usar este" en el que prefieras | Una tabla con planchas, aprovechamiento y costo (marcado "(simulado)"); el grupo queda con su material |
| 5 | **Anidado** | "Anidar" | La ejecución pasa a **lista**, con planchas y % de aprovechamiento. Probá "Marcar definitiva" |
| 6 | **Anidado** | Cambiá kerf, margen, separación o rotación y apretá "Aplicar y recalcular"; probá también "Aprovechar huecos" | Se crea una ejecución nueva; la anterior queda en el historial |
| 7 | **Chapas** | Elegí el grupo arriba. Pasá el mouse por una pieza o una chapa; arrastrá una pieza a otra chapa o a «Chapa nueva». Doble clic en una chapa para retocarla: arrastrá piezas y girá con la rueda del mouse (o los botones ±15° / ±90°) | Todas las chapas juntas y el diseño inicial pintado por chapa; lo que está bajo el mouse se ilumina en los dos. Una pieza que se sale o choca se marca en rojo. "Ver plano imprimible" y "Descargar DXF de corte" exportan cada chapa. "Descargar PDF", arriba a la derecha, baja el PDF del trabajo entero para imprimir en A4 |
| 8 | **Costeo** | Elegí «+ Cliente nuevo…» → "Crear primera opción de presupuesto" → "Recalcular materiales" → agregá líneas (mano de obra, flete…) | El desglose por rubro, con margen, IVA y total |
| 9 | **Anidado** | Con el anidado listo, mirá la tabla de chapas del resumen y apretá «Guardar como retazo» al lado de un sobrante | El botón pasa a «guardado como retazo». En **Materiales**, el material muestra «Retazos: 1 retazo disponible · … m²» y de dónde salió |
| 10 | **Costeo** | «Agregar del catálogo», buscá «corrug», elegí el artículo, escribí una cantidad y «Agregar». Hace falta la planilla cargada: en Materiales, «Actualizar desde la planilla» | La línea con su costo y, en «Presupuesto para el cliente», el precio sugerido con el margen de la planilla |
| 11 | **Costeo** | Apretá «Mandar a aprobar»; después «Aprobar» u «Observar» (con un motivo). Aprobar pide el permiso «puede aprobar»; el nombre sale de tu sesión | El estado cambia y queda el historial. Un presupuesto pendiente o aprobado queda bloqueado hasta que lo vuelvas a borrador |
| 12 | **Costeo** | «Descargar PDF» | El PDF del cliente, sin costos ni márgenes. Con la marca de la empresa si existe `backend/local/empresa/` (ver abajo); sin esa carpeta, sale sin logo ni pie |
| 13 | **Inicio** | Volvé con «Inicio» en la barra | La tarjeta del trabajo, con la miniatura pintada por chapa, los cuatro pasos en verde y el presupuesto. En «Trabajos» están todas, con un buscador; el «⋯» de una tarjeta borra el trabajo, con confirmación |
| 14 | **Piezas** | Cargá un DXF marcando una forma como «no va» y apretá «Cargar»; en otro trabajo elegí el mismo archivo y apretá «Ver cómo se lee» | El dibujo aparece con esa forma ya marcada y el aviso «Se aplicó 1 corrección de la vez anterior», con «Empezar de cero». Si tocás otra forma, el aviso se esconde |
| 15 | **Grupos** | Con un grupo ya anidado, cambiale la chapa al grupo (en Grupos, o en Costeo con «Cambiar material o comparar formatos») y volvé a **Inicio** | La tarjeta dice «Falta volver a anidar»; Chapas y el resumen de Anidado dicen «La chapa cambió después de este anidado: no se cobra»; el PDF lo avisa en rojo; el costeo no lo cobra |

## Qué tener en cuenta (no son errores)

- **Los precios de la demo son inventados.** Cualquier costo marcado "(simulado)" no es un dato real.
- **Kerf, margen y separación son provisorios** (2 / 10 / 5 mm): todavía no se confirmaron con el taller.
- **El anidado acomoda el rectángulo que envuelve a cada pieza**, no su forma real: con piezas curvas o muy irregulares va a dejar huecos. "Aprovechar huecos" intenta meter piezas chicas adentro de los agujeros de otras.
- **Todavía no hay** aviso por mail ni envío al cliente: la aprobación se hace dentro de la app, con tu usuario. El login ya existe (ver el primer usuario, en el paso 2).
- **El logo y los datos de contacto del PDF** viven en `backend/local/empresa/` (`logo.png` y `datos.json`), fuera de git. Sin esa carpeta el PDF sale igual, sin logo ni pie. El formato, en [`docs/GUIA-PRUEBAS-LOCALES.md §5`](GUIA-PRUEBAS-LOCALES.md).
- Todo lo que cargues se guarda en `backend/local/` (no se sube a Git). **Para empezar de cero:** frená el backend y corré `python scripts/limpiar_base.py` desde `backend/`: ofrece borrar solo los trabajos, trabajos y clientes, o dejar todo de fábrica, siempre con respaldo y conservando los usuarios ([manual](MANUAL-USUARIOS.md)). Después repetí el paso 3 si borraste el catálogo.

## Probar con tus propios DXF

- Exportá desde CorelDRAW con *Archivo → Exportar → DXF*. Se leen curvas (splines, círculos, elipses), polilíneas con arcos, líneas y arcos sueltos que cierran una figura, y bloques. **No se leen** el texto (convertilo a curvas antes de exportar), las imágenes ni los rellenos (`HATCH`): el aviso de la pestaña Piezas te dice cuántas entidades ignoró.
- **La escala:** el sistema nunca la adivina, pero te da una referencia: al elegir el archivo, debajo de la cajita aparece «Con esta escala, el dibujo mide … mm (… m)», que se recalcula mientras escribís. Compará ese tamaño con lo que sabés del cartel: si dice 46 mm y el cartel mide casi 5 metros, la escala está mal (por ejemplo, `Complejo` necesita 100). Es cuántos milímetros vale cada unidad del dibujo: 1 si se hizo en milímetros, 10 en centímetros, 1000 en metros. Corel suele exportar en centímetros: probá `10` (mm por unidad del dibujo) y comprobá el ancho de una pieza que conozcas. Elegir el archivo no lo carga: primero ponés la escala y después tocás "Cargar «archivo» a escala N". Si la escala no era, la cambiás y volvés a tocar el mismo botón, sin reabrir el explorador. Cada carga reemplaza las piezas que el trabajo ya tenía.
- Si un contorno no llega a cerrar (los empalmes del dibujo tienen huecos de más de 0,1 mm), aparece como *"N contorno(s) no se pudieron cerrar"*.

## Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Al levantar el backend: `WinError 10013` o "address already in use" | El puerto 8000 lo tiene otra copia del backend | Cerrá esa otra terminal y volvé a correr el comando |
| Al levantar el frontend: "Port 5173 is already in use" | Hay otra copia del frontend abierta | Cerrala: el backend solo acepta el puerto 5173 |
| `vite` "no se reconoce como un comando" | Falta instalar las dependencias | `npm ci` dentro de `frontend/` |
| La página carga pero no aparecen datos, o hay errores de red/CORS | Abriste otra dirección, o el backend no está corriendo | Abrí `http://localhost:5173` y chequeá que `http://localhost:8000/docs` responda |
| "El material «…» no tiene parámetros de corte configurados" | Material creado a mano | Usá los materiales «DEMO», que ya los traen |
| "El formato «…» no tiene precio de referencia cargado" | Formato sin precio | Usá los formatos «DEMO» |
| `No module named …` al correr un script | Usaste otro Python | Corré con `.venv\Scripts\python` (paso 2) |
| El comparador dice "no pudo ubicar todas las piezas" | Alguna pieza no entra en el formato elegido (medí con cuidado la escala) | Elegí un formato más grande o revisá la escala del DXF |

Los tests automáticos: `cd backend` → `.venv\Scripts\python -m pytest -q`; `cd frontend` → `npm test`.

## Qué nos sirve que anotes

Cualquier cosa que te confunda (aunque funcione), el DXF con el que algo no se vio bien (sin mandar datos del cliente por fuera), y en qué paso pasó. Si algo no anda, copiá el texto del error tal cual.
