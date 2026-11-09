# 1.1 · Usuarios y servidor — diseño

> **Estado:** 📝 borrador para que Enzo lo apruebe. Todavía no se tocó código.
>
> **De dónde sale.** [`PLAN-MAESTRO.md §6`](../PLAN-MAESTRO.md), sub-proyecto 1.1 («Servidor y login»), y [§7](../PLAN-MAESTRO.md), 4.1 («Servidor y dominio»). Se planifican **juntos, en dos fases** (decisión de Enzo, 2026-11-09): primero todo en Docker en una computadora, con usuarios y login; después se sube al servidor alquilado.
>
> **Sobre los valores.** Los números de este documento (cuánto dura una sesión, cuántos intentos, cuántos días de backup) están en [`REGISTRO.md §2.7`](../../REGISTRO.md) con su ID. Acá se citan por ID y no se repiten. Los supuestos nuevos son `SUP-42`.

---

## 1. Para qué

Que el sistema pueda salir de tu computadora: que cada persona entre con su usuario, que quede registrado quién hizo cada cosa, que el dueño pueda aprobar desde el celular, y que corra en un servidor alquilado, con copias de seguridad que no dependan de ese servidor.

**Criterio de éxito.**
- En una computadora limpia, con Docker y un archivo `.env`, **un solo comando levanta todo**, y ninguna contraseña está escrita en el repositorio.
- **Sin haber entrado, ninguna pantalla ni ninguna ruta del servidor responde datos**, salvo la de entrar y el estado de salud. Una prueba automática lo comprueba para todas las rutas.
- Un diseñador arma un presupuesto y alguien con el permiso «puede aprobar» lo aprueba. El historial dice **quién fue, con su usuario**, no un nombre escrito a mano.
- El dueño **crea y da de baja usuarios desde una pantalla**.
- Cada día se hace una copia a un almacenamiento aparte del servidor, y **se probó restaurarla** en una máquina limpia.
- (Fase B) Desde el celular, en una dirección con HTTPS, el dueño entra y ve lo mismo que en la computadora.

## 2. Lo que decidió Enzo (2026-11-09)

| Tema | Decisión | Qué implica |
|---|---|---|
| Quiénes usan el sistema | **Dos tipos:** quienes diseñan y quien aprueba | Un solo tipo de usuario con **permisos** que se asignan, no cuatro roles. Administración y taller quedan para después |
| Dónde corre | **Un servidor alquilado con dominio propio** | El dueño abre el link de aprobación desde cualquier lado. Hay que elegir proveedor y registrar un dominio (fase B) |
| Cómo entran | **Usuario y contraseña propios** del sistema, con **nombre de usuario corto** («enzo») | Sin depender de Google ni del mail para entrar. El email se guarda aparte, para los avisos |
| Cómo se reparte | **Un plan, dos fases** | Se prueba todo en Docker antes de pagar y exponer algo a internet |
| Visibilidad | **Todos ven todos los trabajos** | Cada trabajo y presupuesto igual guarda quién lo creó |
| Usuarios | **El dueño los administra desde una pantalla, desde el primer día** | Cambia el plan maestro: la pantalla de usuarios deja de postergarse |
| Datos de hoy | **Se llevan el catálogo y los clientes**; sin trabajos de prueba | Un guion pasa esas tablas de SQLite a PostgreSQL; Complejo, Parador y su presupuesto quedan atrás |
| Backups | **Copia diaria a un almacenamiento en la nube aparte del servidor, 30 días** (`PAR-67`) | Cierra `D-08` y define `T-06` |
| Aprobar lo propio | **Sí, con el permiso «puede aprobar»** | No hay segundo control; sí queda registrado quién hizo cada cosa |
| Si se reinicia el servidor | **Alcanza con que la corrida en curso se pierda** | Se mantiene la cola actual (hilos): **sin Redis**. Se actualiza cuando nadie anida |
| Dominio y proveedor | **No hay todavía** | Es una tarea de la fase B; el plan trae una comparación corta |
| Cuántos a la vez | **Hasta 3** (`SUP-42`) | Define el tamaño del servidor |
| En tu computadora | **También pide usuario y contraseña** | No existe un modo sin control; las pruebas automáticas entran solas |

## 3. Qué entra y qué no

| Entra | No entra (queda como está o va a otra etapa) |
|---|---|
| Usuarios con permisos, entrar y salir, sesiones | **Link firmado para aprobar sin entrar:** es 1.4 |
| Todas las rutas exigen sesión, y los permisos se controlan en el servidor | **Mail** (aviso al dueño, envío al cliente, recuperar contraseña por mail): 1.4, 1.5 y 4.2 |
| Quién creó cada trabajo y presupuesto; la aprobación con el usuario que entró | Roles de administración y taller, y un menú distinto por rol |
| La pantalla de usuarios y «Mi cuenta» (cambiar la propia contraseña) | Auditoría general de todo lo que se toca |
| Docker (servidor, base, proxy, copias), PostgreSQL, `.env` | Redis y una cola de trabajos aparte |
| Copias diarias a la nube y restauración probada | WhatsApp, fotomontaje, dashboard |
| Llevar el catálogo y los clientes a PostgreSQL | Verificación en dos pasos, entrar con Google |
| Fase B: el servidor alquilado, dominio, HTTPS y primer despliegue | Varias empresas en un mismo sistema |

## 4. Fase A — usuarios, login y todo en Docker, en una computadora

### 4.1 Quiénes son y qué pueden

Cada persona es un **usuario**, con:
- un **nombre de usuario** corto y único («enzo»), que no distingue mayúsculas;
- su **nombre** para mostrar y, aparte, su **email** (opcional por ahora: hace falta cuando lleguen los avisos);
- su **contraseña**, que **no se guarda**: se guarda una huella que no se puede volver a la contraseña (`argon2id`);
- si está **activo** o dado de baja;
- dos **permisos**, que se tildan:
  - **Puede aprobar:** aprobar y observar presupuestos;
  - **Administra usuarios:** abrir la pantalla de usuarios.

**Todos son diseñadores de base:** cargan trabajos, anidan, arman presupuestos. El dueño tiene los dos permisos. Los permisos se controlan **en el servidor**: la pantalla solo esconde los botones que no corresponden, pero un pedido hecho a mano sin el permiso da «403, no tenés permiso».

### 4.2 Cómo se entra

- Una pantalla de entrada con usuario y contraseña. Si es correcto, el servidor abre una **sesión**: una cookie que el navegador manda sola en cada pedido, que el JavaScript de la página **no puede leer**, solo viaja por HTTPS y no se envía desde otras páginas.
- **Las sesiones se guardan en la base**, no adentro de la cookie: así dar de baja a alguien o cambiarle la contraseña **las cierra al instante**.
- Una sesión se cierra sola tras un tiempo sin uso (`PAR-62`); con la casilla «mantener la sesión abierta en este dispositivo» dura más (`PAR-63`), pensada para el celular del dueño.
- **Protección contra adivinar contraseñas:** tras unos intentos fallidos seguidos (`PAR-65`) la cuenta se bloquea un rato (`PAR-66`). El mensaje no dice si el usuario existe o no.
- **Contraseña:** largo mínimo (`PAR-64`). Si el dueño la restablece, la nueva es temporal y la persona **tiene que cambiarla al entrar**.
- La protección contra pedidos falsificados desde otras páginas (CSRF) va en el plan; el mecanismo exacto es parte de la implementación.

### 4.3 Qué exige sesión

**Todas las rutas del servidor**, salvo dos: entrar y la de estado de salud (`/salud`, que dice si el servidor y la base responden y cuándo fue el último backup). Sin sesión, 401. Sin permiso, 403.

Una **prueba guardiana** recorre todas las rutas registradas y falla, con la ruta, si alguna no exige sesión y no está en la lista de públicas. Así una ruta nueva no puede quedar abierta por olvido. La lista de públicas va a tener una más cuando llegue el link firmado (1.4).

### 4.4 Quién hizo cada cosa

- **Trabajos y presupuestos guardan quién los creó.** Los que ya existen (de antes de tener usuarios) quedan sin dueño; en el servidor se arranca sin trabajos, así que casi no aplica.
- **Los cambios de estado del presupuesto guardan el usuario**, y también el nombre de ese momento: si después le cambian el nombre a alguien, el historial viejo no cambia. Lo mismo para quién hizo un override de precio.
- **Mandar a aprobar y volver a borrador:** cualquier usuario. **Aprobar y observar:** quien tiene «puede aprobar». Puede aprobar lo que armó él mismo (decisión de Enzo).
- La pantalla de Costeo deja de pedir «escribí tu nombre»: usa a quien entró.

### 4.5 La pantalla de usuarios

Solo se ve con «administra usuarios». Lista de usuarios, y para cada uno:
- **Alta:** usuario, nombre, email, permisos y una contraseña inicial temporal.
- **Editar:** nombre, email y permisos.
- **Restablecer la contraseña:** el sistema genera una temporal y **se muestra una sola vez**.
- **Dar de baja y de alta.** Una persona dada de baja no entra más y sus sesiones se cierran; su historial queda.
- **Reglas que protegen al sistema:** nadie puede quitarse a sí mismo el permiso de administrar ni darse de baja si es **el último administrador**.

Además, **«Mi cuenta»** para todos: cambiar la propia contraseña (pidiendo la actual).

### 4.6 El primer usuario y las emergencias

Alguien tiene que crear al primer administrador: por **línea de comandos**, en el servidor o en Docker (`python -m app.usuarios crear …`). El mismo comando sirve para **la emergencia** de que el dueño se bloquee o se olvide su contraseña (restablecer la contraseña de cualquier usuario). Es el único camino que no pasa por la pantalla, y solo lo puede usar quien tiene acceso al servidor.

### 4.7 En tu computadora

También se entra con usuario y contraseña. Se crea tu usuario una vez con el comando. **Las pruebas automáticas entran solas** con un usuario de prueba, salvo las que prueban justamente la entrada y los permisos, que lo hacen sin él.

### 4.8 Docker

`docker compose up` levanta cuatro cosas:

| Pieza | Qué hace |
|---|---|
| **Proxy** (Caddy) | Es lo único que recibe pedidos de afuera. Sirve la pantalla ya compilada y le pasa al servidor lo que va a `/api`. En la fase B saca solo el certificado HTTPS |
| **Servidor** (la API) | Lo mismo que corre hoy, con los anidados en hilos como ahora (sin Redis, por decisión de Enzo) |
| **Base** (PostgreSQL) | **No publica ningún puerto**: solo el servidor la alcanza, por la red interna de Docker |
| **Copias** | Un contenedor programado que hace el backup diario (§4.10) |

Los datos viven en **volúmenes** que sobreviven al reinicio: la base, los archivos generados (DXF, PDF, fondos) y la carpeta de la empresa (logo y datos), que se monta aparte y de solo lectura. Las contraseñas y claves van en un `.env` **fuera de git**, con un `.env.example` versionado y sin valores. Todas las piezas tienen chequeo de salud. Nada está escrito en el repositorio (`ADR-10`).

### 4.9 Un solo origen

Hoy la pantalla tiene la dirección del servidor escrita a mano (`http://localhost:8000`) y el servidor solo acepta pedidos de `localhost:5173`. Con el proxy, **la pantalla y el servidor viven bajo la misma dirección**: la pantalla pide a `/api/...` y el proxy saca el `/api` antes de pasarlo. Eso **no cambia ninguna ruta del servidor**. Además se puede **sacar el CORS** (el permiso para que otras páginas le pidan cosas) y las cookies funcionan sin trucos. En el desarrollo de todos los días, Vite hace el mismo reenvío, así que se trabaja igual que en producción.

### 4.10 PostgreSQL y las migraciones

- Se suma el driver (`psycopg`). El código ya elige la base por `DATABASE_URL`.
- Hoy, con PostgreSQL, el sistema **se niega a actualizar la base** y pide hacerlo a mano. Eso cambia: un paso previo (`migrar`) hace **un volcado de la base y después aplica las migraciones**, antes de que arranque el servidor. El servidor, al arrancar, solo **verifica** que la base esté en la versión del código y, si no, no arranca y dice por qué.
- **El CI corre las migraciones contra PostgreSQL**, y un conjunto de pruebas (modelos, usuarios y permisos) también. La suite completa sigue en SQLite: tarda mucho más contra PostgreSQL, y lo que cambia entre las dos bases es poco.

### 4.11 Copias de seguridad

Cada día, a una hora fija (`PAR-68`), el contenedor de copias:
1. vuelca la base,
2. suma los archivos generados,
3. los sube, **cifrados**, a un almacenamiento en la nube **aparte del servidor**,
4. y borra lo que pasó el plazo (`PAR-67`, 30 días).

Si la copia falla, el contenedor termina con error y el estado de salud (`/salud`) lo dice. También dice si **pasaron más horas de las debidas sin copia** (`PAR-69`). Como todavía no hay mail, alguien tiene que mirar ese estado: se puede apuntar un monitor gratuito que consulte `/salud`.

**Se prueba restaurar de verdad**: una copia se restaura en una máquina limpia y se comprueba que el sistema levanta con los datos. Una copia que nunca se restauró es una suposición.

### 4.12 Llevar el catálogo y los clientes

Un guion pasa de SQLite a PostgreSQL **solo lo que Enzo eligió**: materiales y sus parámetros de corte, las medidas (formatos) y artículos de la planilla con su historial de cargas y de precios, las cotizaciones de moneda, y los clientes. **No** pasan trabajos, piezas, grupos, anidados, presupuestos ni su historial. Los retazos guardados desde el sobrante de una chapa tampoco, porque dependen de un anidado que no viaja. El detalle de tablas va en el plan. El guion **no toca el origen** y puede correrse de nuevo.

## 5. Fase B — el servidor alquilado

La fase A deja todo andando en Docker. La B lo pone en internet:

1. **Elegir proveedor y registrar el dominio** (`T-01` y `T-02`). El plan trae una comparación corta; la decisión es tuya. Dos datos del diseño: el servidor tiene que tener **al menos 4 procesadores** (con 4 núcleos, tres anidados de Sparrow a la vez terminaron bien, medido el 2026-10-23), y conviene que esté en una región con poca latencia desde Argentina. La memoria se mide en la fase B.
2. **Preparar la máquina:** acceso solo con clave (no con contraseña), cortafuegos que deja abiertos solo el acceso remoto, HTTP y HTTPS, actualizaciones de seguridad automáticas, y un usuario que no sea el administrador para correr Docker.
3. **Apuntar el dominio** al servidor. El proxy saca el certificado HTTPS solo.
4. **Primer despliegue** con un guion que baja el código, aplica las migraciones y levanta todo; y **cómo volver atrás** si algo sale mal.
5. **Cargar** el catálogo, los clientes y los usuarios reales; crear al dueño como administrador.
6. **Elegir dónde van las copias** (`T-06`), configurarlas y **restaurar una de prueba**.
7. **Probar desde el celular** y entrar como cada tipo de usuario.

## 6. Casos raros

| Caso | Qué pasa |
|---|---|
| Alguien se olvida la contraseña | El dueño la restablece desde la pantalla; entra con la temporal y elige otra. Si es el dueño, el comando de emergencia |
| Un usuario dado de baja tiene la sesión abierta | Se cierra en el acto: la siguiente acción da 401 |
| Alguien abre el sistema en dos dispositivos | Dos sesiones; cada una se cierra por su cuenta. «Cerrar sesión» cierra solo esa |
| Intentan adivinar una contraseña | Tras los intentos de `PAR-65`, la cuenta se bloquea (`PAR-66`) |
| El último administrador intenta darse de baja | El sistema no lo deja |
| El servidor se reinicia con alguien anidando | Esa corrida pasa a «error» al arrancar y se vuelve a lanzar, como hoy |
| Falla el backup | `/salud` lo dice; el estado pasa a «backup atrasado» pasado `PAR-69` |
| La migración falla al actualizar | El servidor no arranca; el volcado previo queda para volver atrás |
| Se llena el disco | El servidor deja de poder guardar y lo dice en `/salud`; la fase B incluye mirar el espacio |

## 7. Cómo se prueba

- **Automáticas:** contraseñas y huellas; entrar y salir; sesiones, bloqueo e inactividad; 401 y 403 en cada ruta con permiso; la guardiana de rutas; no poder quitarse el último administrador; la aprobación con usuario real. Las pruebas existentes pasan con el usuario de prueba, **sin cambiarles las afirmaciones**.
- **CI con PostgreSQL:** las migraciones y las pruebas de modelos, usuarios y permisos.
- **Recorrido en Chrome** (sin Docker, con SQLite) para las pantallas: crear usuarios, entrar como diseñador y como dueño, aprobar, ver el historial. **Lo de Docker se verifica en el CI** (la pila levanta sana, la base no está expuesta, el 401, el recorrido por HTTP, las copias y su restauración), porque en la computadora de Enzo no hay espacio para instalar Docker; el recorrido con las pantallas se repite en el servidor real.
- **Backup:** restaurar en una máquina limpia, con los datos a la vista.
- **Fase B:** la lista del §5, con el celular.

## 8. Decisiones que tomé yo (Enzo puede cambiarlas)

- **Sesiones en la base con cookie** y no un token firmado que viaja entero: se pueden cerrar al instante.
- **Huellas con `argon2id`** para las contraseñas.
- **Proxy Caddy:** saca el certificado HTTPS solo y su configuración es corta.
- **Un solo origen, con `/api` que el proxy saca**, y se elimina el CORS.
- **Permisos como casillas** (`puede aprobar`, `administra usuarios`), no como roles; la tabla queda lista para sumar roles después.
- **Mandar a aprobar y volver a borrador, para cualquiera;** aprobar y observar, solo con permiso.
- **El comando de línea de comandos es el único camino sin pantalla** y sirve para el primer usuario y para las emergencias.
- **Copias cifradas;** el cifrado lo pone la herramienta de copias y la clave va en el `.env`.
- **El CI corre PostgreSQL solo para migraciones, modelos y usuarios,** no para toda la suite.
- **El email de un usuario es opcional por ahora.**
- **Una sola carpeta de plan** para las dos fases (1.1 y 4.1).

## 9. Lo que depende de afuera

| Qué | Quién | Cuándo hace falta |
|---|---|---|
| Elegir y contratar el servidor (`T-01`) | Enzo | Al empezar la fase B |
| Registrar el dominio (`T-02`) | Enzo | Fase B, antes del primer despliegue |
| Elegir dónde van las copias en la nube (`T-06`) | Enzo | Fase B, antes de activar el backup real |
| Nombres, usuarios y quién tiene qué permiso | El dueño | Al cargar los usuarios reales |

## 10. Qué queda para el plan

Las tablas y campos nuevos, el orden de las tareas, cómo se hace entrar solas a las pruebas existentes, el mecanismo contra pedidos falsificados, la lista exacta de tablas que viajan, y los textos de las pantallas. Se escribe después de que Enzo apruebe este diseño.
