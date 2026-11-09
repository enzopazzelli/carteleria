# 1.1 · Usuarios y servidor — plan de implementación

> **Para quien lo ejecute:** usar `superpowers:executing-plans` (en esta sesión) o `superpowers:subagent-driven-development`. Los pasos son casillas (`- [ ]`). **Enzo pidió pasos chicos con su visto bueno**: no encadenar tareas sin pausar; al terminar cada una, mostrar qué cambió y esperar el ok.

**Meta:** que el sistema tenga usuarios con sesión y permisos, corra en Docker con PostgreSQL y copias diarias, y se pueda subir a un servidor alquilado.

**Arquitectura:** una tabla de usuarios y otra de sesiones; una dependencia de FastAPI que exige sesión a **todos los grupos de rutas** de una sola vez (`include_router(..., dependencies=[...])`) y una prueba guardiana que lo verifica; un proxy (Caddy) que sirve la pantalla y reenvía `/api` al servidor, así que ambos viven bajo el mismo origen; cuatro contenedores (proxy, API, base, copias); y la fase B, que lleva eso a una máquina alquilada.

**Tecnología:** FastAPI + SQLAlchemy + Alembic, PostgreSQL 16 (SQLite se sigue usando para desarrollar y para la suite), `argon2-cffi`, `psycopg`, React + Vite + Vitest, Docker Compose, Caddy, `restic` para las copias.

**Diseño:** [`diseno.md`](diseno.md) (aprobado por Enzo el 2026-11-09). Los valores citados como `PAR-xx` están en [`REGISTRO.md §2.7`](../../REGISTRO.md).

## Entregas

| Entrega | Tareas | Qué deja funcionando | Se puede fusionar sola |
|---|---|---|---|
| **A1. PostgreSQL en el CI** | 1 | El CI prueba las migraciones y el modelo contra PostgreSQL | Sí |
| **A2. Usuarios y login** | 2 a 10 | El sistema pide entrar; hay permisos, quién hizo cada cosa y la pantalla de usuarios | Sí, pero **junto con su pantalla**: el servidor y la pantalla se cambian a la vez |
| **A3. Docker, copias y datos** | 11 a 14 | Todo levanta con un comando, con copias diarias y el catálogo llevado a PostgreSQL. **Se verifica en el CI**, no en la máquina de Enzo | Después de A2 |
| **B. El servidor alquilado** | B1 a B7 | El sistema en internet, con dominio y HTTPS | Después de A3 |

## Restricciones globales

- **Nada de secretos en el repositorio.** Claves y contraseñas, solo en un `.env` fuera de git; el repositorio lleva `.env.example` sin valores (`ADR-10`). Una prueba (Tarea 11) busca contraseñas escritas en `docker-compose.yml`.
- **Ningún número en la lógica.** Los valores de sesión, bloqueo y copias salen de `app/config.py` con su ID de registro (`PAR-62` a `PAR-69`), igual que el resto.
- **Las migraciones tienen que seguir andando en SQLite.** La base real de Enzo ya está en SQLite y se actualiza sola al arrancar la app, con respaldo previo. Todo arreglo de una migración vieja para PostgreSQL tiene que dejar su efecto en SQLite **idéntico**.
- **Las pruebas existentes pasan sin cambiarles las afirmaciones**, con una sola excepción acordada (Tarea 7): **dos** pruebas de `tests/api/test_rutas_presupuesto_aprobacion.py` que dependían del nombre escrito a mano en el cuerpo del pedido, porque ahora figura quien tiene la sesión.
- **Mensajes de error en castellano**, con `ErrorPrevisto` y su código HTTP, como el resto del servidor. Sin códigos de supuestos en lo que ve una persona.
- **Dependencias fijadas a una versión exacta:** `argon2-cffi==23.1.0` y `psycopg[binary]==3.2.9`.
- Commits **sin** línea `Co-Authored-By`. Una rama por entrega: `feat/1.1-postgres-en-el-ci`, `feat/1.1-usuarios-y-login`, `feat/1.1-docker-y-copias`.
- Pruebas del backend con `--basetemp` en D: (`python -m pytest <ruta> -q --basetemp=D:/temp-pruebas/<algo>`; crear antes `D:\temp-pruebas`).
- **No hay Docker ni `psql` en esta máquina, y por ahora no se instalan** (Enzo, 2026-11-09: C: con unos 10 GB libres y D: con unos 21; ver la Tarea 0). **PostgreSQL y Docker se verifican en el CI de GitHub**, que corre en Linux con Docker. Las tareas 1 a 10 no necesitan Docker: se desarrollan con SQLite, como hasta hoy.
- La base real (`backend/local/carteleria.db`) no se toca a mano. Se actualiza sola al arrancar la app, con su respaldo; **Enzo avisa antes de arrancarla con la migración nueva**.
- Todo recorrido en un navegador se hace sobre una copia de la base (`python scripts/copiar_base.py <nombre>`, ver `docs/GUIA-PRUEBAS-LOCALES.md §6`), mirando antes que los puertos estén libres.

## Review Focus

Lo que el diseño implica y ninguna tarea prueba por sí sola; cada línea tiene su prueba en la tarea dueña del código:

1. **Una ruta nueva sin sesión, por olvido:** la guardiana la encuentra y dice cuál (Tarea 6).
2. **Un usuario dado de baja con la sesión abierta:** su siguiente pedido da 401 al instante (Tareas 3 y 4).
3. **El último administrador:** no se puede dar de baja ni quitarle el permiso, ni a sí mismo ni desde otro (Tareas 3 y 8).
4. **Un pedido hecho desde otra página, con la cookie de la persona:** se rechaza (Tarea 4).
5. **Las secuencias de PostgreSQL al copiar con números de `id` fijos:** después de llevar el catálogo, crear un material nuevo no choca con uno viejo (Tarea 13).

---

## Estructura de archivos

| Archivo | Qué hace |
|---|---|
| `backend/app/modelos/usuario.py` (crear) | `Usuario` y `SesionDeUsuario` |
| `backend/app/services/usuarios/` (crear) | `contrasenas.py` (huellas) y `servicio.py` (entrar, sesiones, permisos y reglas) |
| `backend/app/api/autenticacion.py` (crear) | `UsuarioActual`, `usuario_actual`, `exigir_permiso`, la cookie y el encabezado propio |
| `backend/app/api/rutas_acceso.py` (crear) | Entrar, salir, quién soy, cambiar la contraseña y `/salud` |
| `backend/app/api/rutas_usuarios.py` (crear) | La administración de usuarios |
| `backend/app/usuarios.py` (crear) | El comando `python -m app.usuarios` |
| `backend/app/api/app.py` (modificar) | `crear_app()`, sesión en todos los grupos de rutas, sin CORS, sin documentación abierta en producción |
| `backend/app/arranque.py` (modificar) | Con PostgreSQL, verificar la versión en vez de actualizar |
| `backend/scripts/migrar.py`, `llevar_catalogo.py` (crear) | El paso de migraciones con volcado previo, y el pase de catálogo y clientes |
| `frontend/src/api/client.ts` y siguientes (modificar) | Base `/api`, encabezado propio, manejo del 401 |
| `frontend/src/auth/`, `routes/Entrar.tsx`, `MiCuenta.tsx`, `Usuarios.tsx` (crear) | La sesión, la entrada, la cuenta propia y la pantalla de usuarios |
| `backend/Dockerfile`, `proxy/`, `respaldo/`, `docker-compose.yml`, `.env.example` (crear) | Docker |
| `docs/GUIA-SERVIDOR.md` (crear) | Cómo se opera: desplegar, actualizar, volver atrás, copias y restauración, usuarios, emergencias |

---

### Tarea 0: Preparar la máquina (solo `D:\temp-pruebas`; Docker, opcional)

- [ ] **Paso 1:** crear `D:\temp-pruebas` para las pruebas del backend.
- [ ] **Paso 2 (opcional, solo si Enzo quiere ver la pila corriendo en su máquina):** instalar Docker Desktop **en D:**, con `--installation-dir=D:\Docker` y `--wsl-default-data-root=D:\DockerData` (o moviendo después el disco en *Settings → Resources → Advanced → Disk image location*). Limitar WSL a unos 4 GB de memoria (`.wslconfig`): la máquina tiene 11,7 GB. No instalar Docker adentro de la Ubuntu de WSL que ya existe, que parece ser la del otro trabajo. **Estimación, sin medir:** unos 3 a 6 GB de imágenes, más el programa, y el disco virtual no se achica solo. Sin este paso, todo lo de Docker se verifica en el CI y en la fase B.

---

## Entrega A1 — PostgreSQL en el CI

### Tarea 1: Las migraciones y el modelo, probados contra PostgreSQL

**Files:**
- Modify: `backend/requirements.txt` (sumar `psycopg[binary]==3.2.9`), `.github/workflows/ci.yml` (un segundo trabajo con PostgreSQL)
- Create: `backend/tests/postgres/__init__.py`, `backend/tests/postgres/test_migraciones_en_postgres.py`
- Modify si hace falta: `backend/alembic/versions/*` (solo arreglos que no cambien nada en SQLite)

**Interfaces:**
- Produces: la variable de entorno `CARTELERIA_PRUEBAS_POSTGRES_URL` (por ejemplo `postgresql+psycopg://carteleria:clave@localhost:5432/carteleria_prueba`). Las pruebas de `tests/postgres/` **se saltean** si no está.

- [ ] **Paso 1: escribir las pruebas** (todas saltadas sin la variable, con `pytest.mark.skipif`), cada una contra un esquema vacío de la base de prueba:
  - `test_las_migraciones_llegan_a_head_y_crean_todas_las_tablas_del_modelo`: aplicar `alembic upgrade head` y comparar los nombres de las tablas con `Base.metadata.tables`.
  - `test_las_migraciones_se_pueden_deshacer_hasta_el_principio_y_volver_a_subir`: `downgrade base` y de nuevo `upgrade head`, sin error.
  - `test_un_trabajo_con_decimales_y_json_vuelve_igual`: guardar y leer un `Trabajo` con un `Pieza` (contorno en JSON, `Milimetros`) y una `Colocacion`, y comparar los valores exactos.
  - `test_los_booleanos_con_valor_por_defecto_de_las_migraciones_viejas_quedan_bien`: crear un `Formato` con el modelo y leer `disponible` y `medida_a_mano`.
- [ ] **Paso 2: el trabajo del CI.** En `ci.yml`, un trabajo `postgres` con un servicio `postgres:16` (con chequeo de salud), la variable de entorno apuntando a él, `pip install -r requirements-dev.txt`, y `pytest tests/postgres -q`.
- [ ] **Paso 3: subir la rama y mirar el CI.** **Se espera que falle la primera vez**: las 18 migraciones se escribieron para SQLite. Anotar cada falla.
- [ ] **Paso 4: corregir lo que falle,** una causa por commit. Reglas: el arreglo no puede cambiar lo que la migración hace en SQLite (la base real ya la aplicó); si hace falta una condición por motor, usar `op.get_bind().dialect.name`. Volver a correr localmente `python -m pytest tests -q --basetemp=D:/temp-pruebas/a1` entero para confirmar que SQLite sigue igual.
- [ ] **Paso 5: el CI en verde** en los dos trabajos. Commit: `ci(1.1): probar las migraciones y el modelo contra PostgreSQL`.

> **Si iterar contra el CI resulta lento:** probar `pgserver` (PostgreSQL empaquetado como biblioteca de Python), que quizá funcione en Windows sin Docker. No es parte del plan; es un atajo a probar.

---

## Entrega A2 — Usuarios y login

### Tarea 2: Los modelos y su migración

**Files:**
- Create: `backend/app/modelos/usuario.py`, `backend/alembic/versions/<id>_usuarios_y_sesiones.py` (con `down_revision = 'f2c8a4d6e913'`)
- Modify: `backend/app/modelos/__init__.py`, `backend/app/modelos/trabajo.py` (`Trabajo.creado_por_id`), `backend/app/modelos/presupuesto.py` (`Presupuesto.creado_por_id`, `CambioDeEstado.usuario_id`)
- Test: `backend/tests/modelos/test_migracion_usuarios.py`

**Interfaces:**
- Produces:
  - `class Usuario(Base)`, `__tablename__ = "usuarios"`: `id`, `usuario: str` (hasta 40, **único**, siempre en minúsculas), `nombre: str` (120), `email: str | None` (200), `contrasena_hash: str` (255), `activo: bool = True`, `puede_aprobar: bool = False`, `administra_usuarios: bool = False`, `debe_cambiar_contrasena: bool = False`, `intentos_fallidos: int = 0`, `bloqueado_hasta: datetime | None`, `ultimo_ingreso_en: datetime | None`.
  - `class SesionDeUsuario(Base)`, `__tablename__ = "sesiones"`: `id`, `usuario_id` (FK a `usuarios`, `ondelete="CASCADE"`), `token_hash: str` (64, **único**: la huella del token, que no se guarda), `mantener: bool`, `expira_en: datetime`, `ultimo_uso_en: datetime`.
  - `Trabajo.creado_por_id`, `Presupuesto.creado_por_id` y `CambioDeEstado.usuario_id`: FK a `usuarios`, `nullable=True`, `ondelete="SET NULL"`. **Nullable a propósito:** lo anterior a tener usuarios queda sin dueño.

- [ ] **Paso 1: escribir la prueba de migración**, con el estilo de `tests/modelos/test_migracion_correcciones_del_dibujo.py` (`_ANTES = "f2c8a4d6e913"`): la tabla nueva no existe antes y sí después, con sus columnas; las tres columnas nuevas existen y valen `NULL` en las filas viejas; se deshace sin tocar lo demás. Más: no se pueden guardar dos usuarios con el mismo `usuario`; borrar un usuario deja `creado_por_id` en `NULL`; borrar un usuario borra sus sesiones.
- [ ] **Paso 2: correrla y ver que falla** (`ImportError`).
- [ ] **Paso 3: crear los modelos y la migración,** con restricciones con nombre (`uq_usuarios_usuario`, `uq_sesiones_token_hash`) porque SQLite en modo batch las necesita.
- [ ] **Paso 4: correr** esa prueba y todo `tests/modelos`. Todo verde. Con la rama de la Tarea 1 fusionada, el CI también prueba esta migración en PostgreSQL.
- [ ] **Paso 5: commit** `feat(1.1): los usuarios y las sesiones, y quién creó cada trabajo y presupuesto`.

### Tarea 3: Contraseñas y reglas de los usuarios

**Files:**
- Modify: `backend/requirements.txt` (`argon2-cffi==23.1.0`), `backend/app/config.py`
- Create: `backend/app/services/usuarios/__init__.py`, `contrasenas.py`, `servicio.py`
- Test: `backend/tests/services/usuarios/test_contrasenas.py`, `test_servicio.py`

**Interfaces:**
- Consumes: `Usuario`, `SesionDeUsuario` (Tarea 2).
- Produces, en `config.py`: `SESION_HORAS_SIN_USO` (`PAR-62`), `SESION_DIAS_MANTENIDA` (`PAR-63`), `CONTRASENA_LARGO_MINIMO` (`PAR-64`), `INTENTOS_ANTES_DE_BLOQUEAR` (`PAR-65`), `MINUTOS_DE_BLOQUEO` (`PAR-66`), cada uno con su variable de entorno y su comentario con el ID.
- Produces, en `contrasenas.py`: `hacer_huella(contrasena: str) -> str`; `verificar(huella: str, contrasena: str) -> bool`; `validar_largo(contrasena: str) -> None` (levanta `ErrorPrevisto` 400 con el largo mínimo en el mensaje); `generar_temporal() -> str` (aleatoria, cumple el largo mínimo, sin caracteres que se confundan: `0`/`O`, `1`/`l`).
- Produces, en `servicio.py` (todas reciben `ahora: datetime` para no depender del reloj):
  - `crear_usuario(sesion, *, usuario, nombre, email=None, contrasena, puede_aprobar=False, administra_usuarios=False) -> Usuario`: guarda `usuario` en minúsculas y con `debe_cambiar_contrasena=True`. Un nombre repetido da 409 «Ese nombre de usuario ya existe.».
  - `entrar(sesion, usuario: str, contrasena: str, mantener: bool, ahora: datetime) -> tuple[Usuario, str]`: devuelve el usuario y **el token en claro, una sola vez**. Cualquier falla (usuario inexistente, contraseña incorrecta, baja, bloqueada) da **el mismo error 401** «Usuario o contraseña incorrectos. Si fallaste varias veces, esperá unos minutos.».
  - `usuario_de_sesion(sesion, token: str, ahora: datetime) -> Usuario | None`: `None` si no existe, venció, o el usuario está de baja; si es válida, renueva `ultimo_uso_en` y el vencimiento.
  - `cerrar_sesion(sesion, token: str) -> None`; `cerrar_sesiones_de(sesion, usuario_id: int) -> None`.
  - `cambiar_contrasena(sesion, usuario: Usuario, actual: str, nueva: str) -> None` (cierra **las otras** sesiones); `restablecer_contrasena(sesion, usuario: Usuario) -> str` (devuelve la temporal, deja `debe_cambiar_contrasena=True` y cierra todas las sesiones).
  - `actualizar_usuario(sesion, usuario: Usuario, *, nombre=None, email=None, puede_aprobar=None, administra_usuarios=None, quien_pide: Usuario) -> Usuario`; `dar_de_baja(sesion, usuario, *, quien_pide)` y `dar_de_alta(sesion, usuario)`. **Regla:** si dejaría al sistema sin ningún administrador activo, 409 «Tiene que quedar al menos una persona que administre usuarios.», también cuando se la aplica a sí mismo.

- [ ] **Paso 1: escribir las pruebas** (con una base SQLite en `tmp_path` y `ahora` inyectado):
  - `contrasenas`: la huella no es la contraseña y `verificar` acepta la buena y rechaza la mala; dos huellas de la misma contraseña son distintas; `validar_largo` rechaza una corta con el mensaje; `generar_temporal` cumple el largo y no repite.
  - **entrar:** acepta la buena; el mismo error para usuario inexistente, contraseña mala y usuario de baja; tras `INTENTOS_ANTES_DE_BLOQUEAR` fallos seguidos, **hasta la contraseña correcta falla** hasta pasados `MINUTOS_DE_BLOQUEO`; un acierto pone el contador en cero; `ultimo_ingreso_en` se actualiza.
  - **sesión:** una sesión sin uso más de `SESION_HORAS_SIN_USO` ya no vale; usarla antes la renueva; con `mantener=True` vale `SESION_DIAS_MANTENIDA`; **el token no está en la base** (solo su huella).
  - **baja (Review Focus 2):** dar de baja cierra sus sesiones; `usuario_de_sesion` con su token da `None`.
  - **contraseña:** cambiarla exige la actual y cierra las otras sesiones, no la propia; restablecer cierra todas y marca el cambio obligatorio.
  - **último administrador (Review Focus 3):** no se puede dar de baja, ni quitarle `administra_usuarios`, al único administrador activo; sí cuando hay otro.
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: implementar.** El token es `secrets.token_urlsafe(32)`; en la base se guarda su SHA-256. La huella de la contraseña es `argon2id` (`argon2.PasswordHasher`).
- [ ] **Paso 4: correrlas y ver que pasan.**
- [ ] **Paso 5: commit** `feat(1.1): contraseñas, sesiones y las reglas de los usuarios`.

### Tarea 4: La sesión en el servidor (dependencias y cookie)

**Files:**
- Create: `backend/app/api/autenticacion.py`, `backend/tests/conftest.py` (sumar el arnés de sesión)
- Modify: `backend/pytest.ini` (registrar la marca `sin_sesion_de_prueba`)
- Test: `backend/tests/api/test_autenticacion.py`

**Interfaces:**
- Consumes: `usuario_de_sesion` (Tarea 3), `obtener_sesion` (`app/api/dependencias.py`).
- Produces:
  - `@dataclass(frozen=True) class UsuarioActual` con `id: int | None`, `usuario: str`, `nombre: str`, `puede_aprobar: bool`, `administra_usuarios: bool`, `debe_cambiar_contrasena: bool`.
  - `COOKIE_DE_SESION = "sesion"` y `ENCABEZADO_DE_PEDIDO = "X-Cartel-Pedido"`.
  - `usuario_actual(request, sesion=Depends(obtener_sesion)) -> UsuarioActual`: lee la cookie, valida con `usuario_de_sesion`. **401** «Entrá con tu usuario y contraseña.» si falta o no vale. En un pedido que **cambia datos** (todo menos `GET`, `HEAD` y `OPTIONS`) exige el encabezado `X-Cartel-Pedido`; sin él, **403** «Pedido no permitido.».
  - `exigir_permiso(nombre: Literal["puede_aprobar", "administra_usuarios"])`: dependencia que devuelve el `UsuarioActual` o levanta **403** «No tenés permiso para hacer esto.».
  - `poner_cookie(respuesta, token: str, mantener: bool)` y `sacar_cookie(respuesta)`: la cookie es `HttpOnly`, `SameSite=Lax`, `Path=/`, y `Secure` solo cuando `CARTELERIA_ENTORNO=produccion`; con `mantener`, `max_age` de `SESION_DIAS_MANTENIDA`.
  - **El arnés de pruebas:** una fixture `autouse` en `tests/conftest.py` que pone `app.dependency_overrides[usuario_actual]` en un `UsuarioActual` de prueba con **`id=None`**, administrador y con permiso de aprobar (no se guarda en la base, así que no choca con las claves foráneas), **salvo** en las pruebas marcadas `@pytest.mark.sin_sesion_de_prueba`.

- [ ] **Paso 1: escribir las pruebas** con una `FastAPI` mínima de dos rutas (una `GET` y una `POST`) protegidas con `usuario_actual`, y un usuario real de una base en `tmp_path`:
  - sin cookie: 401; con una cookie inventada: 401; con una válida: 200 y devuelve quién es;
  - **un `POST` con la cookie pero sin `X-Cartel-Pedido` da 403** (Review Focus 4: es lo que impide que otra página haga un pedido en nombre de la persona), y con el encabezado da 200; un `GET` no lo necesita;
  - **un usuario dado de baja con la cookie de antes** da 401 en el siguiente pedido (Review Focus 2);
  - `exigir_permiso`: 403 sin el permiso, 200 con él;
  - la cookie sale `HttpOnly` y `SameSite=Lax`; no es `Secure` en desarrollo y sí lo es con `CARTELERIA_ENTORNO=produccion`;
  - con el arnés, una ruta protegida responde sin cookie (para las pruebas que no son de acceso).
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: implementar** `autenticacion.py` y el arnés; **todavía no se exige sesión en ninguna ruta del sistema**, así que la suite no cambia.
- [ ] **Paso 4: correrlas y ver que pasan;** y `python -m pytest tests/api -q --basetemp=D:/temp-pruebas/a4` entero para ver que el arnés no rompió nada.
- [ ] **Paso 5: commit** `feat(1.1): la sesión en el servidor y el arnés de pruebas`.

### Tarea 5: Las rutas de acceso y el estado de salud

**Files:**
- Create: `backend/app/api/rutas_acceso.py`, `backend/app/api/esquemas_acceso.py`
- Modify: `backend/app/config.py` (`DIRECTORIO_ESTADO`, `BACKUP_HORAS_MAXIMAS` = `PAR-69`)
- Test: `backend/tests/api/test_rutas_acceso.py`

**Interfaces:**
- Consumes: `entrar`, `cerrar_sesion`, `cambiar_contrasena` (Tarea 3); `poner_cookie`, `sacar_cookie`, `usuario_actual` (Tarea 4).
- Produces:
  - `POST /acceso/entrar` con `{usuario, contrasena, mantener}`: abre la sesión, pone la cookie y devuelve `YoLeer`. **Pública.**
  - `YoLeer`: `{id, usuario, nombre, email, puede_aprobar, administra_usuarios, debe_cambiar_contrasena}`.
  - `POST /acceso/salir` (cierra solo esta sesión y saca la cookie), `GET /acceso/yo`, `POST /acceso/cambiar-contrasena` con `{actual, nueva}`.
  - `GET /salud`, **pública**: `{"estado": "ok", "base": "ok", "backup": null | {"ultimo": "<iso>", "horas": <n>, "atrasado": <bool>}}`. Lee `DIRECTORIO_ESTADO / "ultimo_backup.json"`; si no existe, `backup` es `null` y no es un problema (en desarrollo no hay copias). `atrasado` es verdadero pasadas `BACKUP_HORAS_MAXIMAS`; en ese caso `estado` es `"backup_atrasado"`. Si la base no responde, 503.

- [ ] **Paso 1: escribir las pruebas** (marcadas `sin_sesion_de_prueba`, con un usuario real):
  - entrar con la contraseña buena da 200 y la cookie; con la mala, 401 con el mismo mensaje que un usuario inexistente; tras varios fallos, la buena también da 401;
  - `GET /acceso/yo` con la cookie dice quién es; sin ella, 401; después de `salir`, 401;
  - `cambiar-contrasena` con la actual mal da 400; con la buena, la nueva sirve para entrar y la vieja no;
  - **`/salud` sin sesión responde 200** con `backup: null`; con un archivo de estado de hace poco, `atrasado: false`; con uno de hace más de `BACKUP_HORAS_MAXIMAS` horas, `atrasado: true` y `estado: "backup_atrasado"`.
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: implementar** y registrar el router en `app.py` **sin** exigir sesión (esa es la tarea siguiente).
- [ ] **Paso 4: correrlas y ver que pasan.**
- [ ] **Paso 5: commit** `feat(1.1): entrar, salir, la cuenta propia y el estado de salud`.

### Tarea 6: Todas las rutas exigen sesión, y la guardiana

**Files:**
- Modify: `backend/app/api/app.py`
- Test: `backend/tests/test_todas_las_rutas_exigen_sesion.py`

**Interfaces:**
- Produces: `crear_app(entorno: str | None = None) -> FastAPI`, con `app = crear_app()` a nivel de módulo (nada cambia para quien ya importa `app`). El entorno sale de `CARTELERIA_ENTORNO` (`produccion` o, por defecto, `desarrollo`).
- `crear_app` **no instala CORS** (ver Tarea 11: el origen es uno solo), registra cada router con `dependencies=[Depends(usuario_actual)]` **salvo** el de acceso y el de salud, y en `produccion` crea la aplicación con `docs_url=None`, `redoc_url=None` y `openapi_url=None`.

- [ ] **Paso 1: escribir la guardiana y las pruebas:**
  - `test_toda_ruta_del_sistema_exige_sesion_salvo_las_publicas` (**Review Focus 1**): recorre `app.routes`, y para cada ruta con su `dependant` comprueba que `usuario_actual` esté entre sus dependencias (las del router incluidas) **o** que el camino esté en `PUBLICAS = {"/acceso/entrar", "/salud"}`. Falla con una lista de caminos y métodos.
  - `test_pedir_sin_sesion_da_401_en_una_muestra_de_rutas` (marcada `sin_sesion_de_prueba`): `GET /trabajos`, `/materiales`, `/presupuestos`, `/tarjetas`, `/clientes`, `POST /trabajos` y `DELETE /presupuestos/1` dan 401; `GET /salud` da 200.
  - `test_en_produccion_no_hay_documentacion_abierta`: con `crear_app("produccion")`, `/docs`, `/redoc` y `/openapi.json` dan 404; con el entorno por defecto, existen.
  - `test_no_hay_cors`: un pedido con `Origin: http://otra-pagina.com` no recibe `access-control-allow-origin`.
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: reescribir `app.py`** con `crear_app`, sacar el middleware de CORS y el comentario que lo justifica, y poner `dependencies=[Depends(usuario_actual)]` en cada `include_router` protegido.
- [ ] **Paso 4: correr la suite completa** (`python -m pytest tests -q --basetemp=D:/temp-pruebas/a6`, unos 6 minutos). **Todo verde, sin cambiar ninguna prueba existente:** el arnés de la Tarea 4 las hace entrar.
- [ ] **Paso 5: commit** `feat(1.1): todas las rutas exigen sesión, con una guardiana que lo vigila`.

### Tarea 7: Permisos, y quién hizo cada cosa

**Files:**
- Modify: `backend/app/api/rutas_presupuesto.py`, `backend/app/api/esquemas_presupuesto.py`, `backend/app/services/presupuesto/estados.py`, `backend/app/api/rutas_trabajos.py`, `backend/app/api/esquemas_trabajos.py`
- Test: `backend/tests/api/test_rutas_presupuesto_aprobacion.py` (dos pruebas se reemplazan, el resto queda), `backend/tests/api/test_permisos.py` (crear), `backend/tests/api/ayudas.py` (sumar `iniciar_sesion`). **`tests/services/presupuesto/test_estados.py` no se toca:** el servicio sigue recibiendo `por`.

**Interfaces:**
- Consumes: `usuario_actual`, `exigir_permiso`, `UsuarioActual` (Tarea 4).
- Cambia: `cambiar_estado(sesion, presupuesto, nuevo, *, por: str, motivo=None, usuario_id: int | None = None)`. **`por` sigue siendo obligatorio en el servicio:** es el nombre **de ese momento**, y `test_estados.py` lo sigue ejercitando tal cual. `usuario_id` es nuevo y opcional. **Quien arma esos dos valores es la ruta**: pasa `por=usuario.nombre` y `usuario_id=usuario.id` de quien tiene la sesión, nunca lo que venga en el cuerpo del pedido.
- Cambia: `CambioDeEstadoCrear.por` pasa a ser **opcional y se ignora**: los clientes viejos que todavía lo mandan siguen andando. `LineaCostoActualizar` ya no exige `override_por`: el servidor usa el nombre de quien hace el pedido.
- Cambia: `POST /presupuestos/{id}/aprobar` y `/observar` dependen de `exigir_permiso("puede_aprobar")`. `/mandar-a-aprobar` y `/volver-a-borrador`, de cualquier usuario con sesión.
- Produce: `Trabajo.creado_por_id` y `Presupuesto.creado_por_id` se llenan al crearlos (y al duplicar un presupuesto, con quien lo duplica); `TrabajoLeer` y `PresupuestoLeer` suman `creado_por: {id: int, nombre: str} | None`.
- Produce en las pruebas: `iniciar_sesion(cliente, usuario: str, contrasena: str) -> None` (entra por `/acceso/entrar` y deja la cookie y el encabezado `X-Cartel-Pedido` en el cliente), y `crear_usuario_de_prueba(motor, usuario, *, puede_aprobar=False, administra_usuarios=False) -> str` (devuelve la contraseña).

- [ ] **Paso 1: escribir las pruebas nuevas** (marcadas `sin_sesion_de_prueba`, con usuarios reales):
  - un diseñador **sin** el permiso: `mandar-a-aprobar` da 200; `aprobar` y `observar` dan 403 y **no se registra el cambio**;
  - con el permiso: aprueba, y el historial dice su nombre y su `usuario_id`; **puede aprobar un presupuesto que armó él mismo** (decisión de Enzo);
  - si después le cambian el nombre a esa persona, **el historial viejo conserva el nombre de ese momento**;
  - un `POST` a `aprobar` con `por` en el cuerpo **no cambia quién figura**: figura quien tiene la sesión;
  - el override de una línea figura con el nombre de quien lo hizo;
  - `POST /trabajos` y `POST /presupuestos` guardan `creado_por`; los de antes dicen `creado_por: null`.
- [ ] **Paso 2: la excepción acordada a «pruebas sin cambiar».** Son **dos** pruebas de `tests/api/test_rutas_presupuesto_aprobacion.py`, porque la identidad ahora sale de la sesión y no del cuerpo del pedido: la que arma el historial con los nombres «Enzo» y «Dueño» escritos a mano (alrededor de las líneas 50 a 63), que pasa a entrar con dos usuarios reales y a comprobar **los mismos pasos y estados**; y `test_observar_sin_motivo_y_sin_nombre_se_rechazan`, que conserva la mitad «sin motivo» y pierde la de «sin nombre» (que sigue cubierta a nivel del servicio por `test_hace_falta_decir_quien_lo_hace`). **Toda otra prueba de esos archivos queda como estaba.** Decirlo en el commit.
- [ ] **Paso 3: correrlas y ver que fallan.**
- [ ] **Paso 4: implementar.** Buscar con `grep` los llamados a `cambiar_estado` (solo `rutas_presupuesto.py` y las pruebas) y a `override_por`.
- [ ] **Paso 5: correr** `tests/api`, `tests/services/presupuesto`, `tests/test_costeo.py`. Todo verde.
- [ ] **Paso 6: commit** `feat(1.1): aprobar requiere el permiso, y todo queda con quién lo hizo`.

### Tarea 8: La administración de usuarios y el comando

**Files:**
- Create: `backend/app/api/rutas_usuarios.py`, `backend/app/api/esquemas_usuarios.py`, `backend/app/usuarios.py`
- Modify: `backend/app/api/app.py` (registrar el router)
- Test: `backend/tests/api/test_rutas_usuarios.py`, `backend/tests/test_comando_usuarios.py`

**Interfaces:**
- Consumes: el servicio de la Tarea 3; `exigir_permiso("administra_usuarios")`.
- Produces: `GET /usuarios`, `POST /usuarios` (`{usuario, nombre, email?, puede_aprobar, administra_usuarios}`: **genera la contraseña temporal y la devuelve una sola vez** en `contrasena_temporal`), `PATCH /usuarios/{id}`, `POST /usuarios/{id}/restablecer-contrasena` (devuelve `{contrasena_temporal}`), `POST /usuarios/{id}/dar-de-baja`, `POST /usuarios/{id}/dar-de-alta`. Todas con `administra_usuarios`; sin él, 403. Una persona sin ese permiso tampoco ve la lista.
- `UsuarioLeer`: `{id, usuario, nombre, email, activo, puede_aprobar, administra_usuarios, debe_cambiar_contrasena, ultimo_ingreso_en}`. **Nunca** la huella.
- Produce el comando `python -m app.usuarios`, con `main(argv: list[str] | None = None) -> int`:
  - `crear <usuario> --nombre "…" [--email …] [--administrador] [--puede-aprobar]`: pide la contraseña sin mostrarla (`getpass`), o con `--generar` crea una temporal y la imprime una vez;
  - `restablecer <usuario>`: genera la temporal y la imprime (es la **emergencia**: no pide estar entrado);
  - `listar`.
  - Usa `DATABASE_URL` o la base por defecto, igual que el servidor.

- [ ] **Paso 1: escribir las pruebas:**
  - rutas: sin permiso, todas dan 403; con permiso: alta (con la temporal en la respuesta), editar, restablecer, baja y alta; un usuario repetido da 409; la respuesta **nunca** trae la huella;
  - **último administrador** (Review Focus 3): intentar darse de baja, o quitarse `administra_usuarios`, siendo el único, da 409 y no cambia nada;
  - la persona dada de baja con la sesión abierta recibe 401 en su siguiente pedido;
  - comando: `crear` con `--generar` imprime la contraseña una vez y el usuario puede entrar con ella; `restablecer` de un usuario bloqueado le **levanta el bloqueo**; `listar` no imprime huellas; un usuario inexistente da código de salida distinto de cero y un mensaje claro.
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: implementar.**
- [ ] **Paso 4: correrlas y ver que pasan;** y la guardiana de la Tarea 6 (que ahora ve rutas nuevas) sigue en verde.
- [ ] **Paso 5: commit** `feat(1.1): la administración de usuarios y el comando para el primero`.

### Tarea 9: La pantalla entra y sale

**Files:**
- Modify: `frontend/src/api/client.ts`, `frontend/src/api/inicio.ts`, `frontend/src/api/nesting.ts`, `frontend/vite.config.ts`, `frontend/src/App.tsx`, `frontend/src/components/Barra.tsx`, `frontend/src/routes/TrabajoWorkspace/AprobacionSeccion.tsx`, `frontend/src/routes/TrabajoWorkspace/CosteoTab.tsx` y la API de presupuestos que mande `por`
- Create: `frontend/src/api/acceso.ts`, `frontend/src/auth/SesionContext.tsx`, `frontend/src/auth/permisos.ts`, `frontend/src/routes/Entrar.tsx`, `frontend/src/routes/MiCuenta.tsx`
- Test: `frontend/src/api/acceso.test.ts`, `frontend/src/api/client.test.ts`, `frontend/src/auth/permisos.test.ts` y las pruebas existentes que nombran `http://localhost:8000`

**Interfaces:**
- Produces:
  - `client.ts`: `export const API_BASE = "/api"`; `pedir` agrega `X-Cartel-Pedido: 1` en **todo** pedido, y ante un **401** avisa a un callback registrado con `alPerderLaSesion(callback)` (la pantalla vuelve a «Entrar»). Los cuatro armadores de enlaces de `inicio.ts` y `nesting.ts` (miniatura, plano, DXF y PDF) usan `API_BASE`.
  - `vite.config.ts`: un `server.proxy` de `/api` a `http://localhost:8000` que **saca** el prefijo (`rewrite`).
  - `acceso.ts`: `type Yo`, `entrar(usuario, contrasena, mantener): Promise<Yo>`, `salir(): Promise<void>`, `quienSoy(): Promise<Yo>`, `cambiarContrasena(actual, nueva): Promise<void>`.
  - `permisos.ts`: `puedeAprobar(yo: Yo | null): boolean` y `administraUsuarios(yo: Yo | null): boolean`.
  - `SesionContext`: `useSesion()` con `{ yo, cargando, entrar, salir }`.
  - Rutas: `/entrar` **fuera** de la barra; todo lo demás, dentro de una ruta protegida que, sin sesión, lleva a `/entrar`; `/cuenta`. Si `debe_cambiar_contrasena`, lleva a `/cuenta` hasta que la cambie.

- [ ] **Paso 1: escribir las pruebas** (Vitest corre en `node`: la lógica va en funciones puras, como el resto del proyecto):
  - `client.test.ts`: el pedido va a `/api/...`; trae el encabezado `X-Cartel-Pedido`; un 401 llama al callback; un error de conexión sigue dando `SIN_CONEXION`;
  - `acceso.test.ts`: `entrar` hace un `POST /api/acceso/entrar` con el cuerpo esperado; un 401 se convierte en el mensaje del servidor;
  - `permisos.test.ts`: con `null` da `false`; con los permisos, `true`;
  - las pruebas que hoy afirman `http://localhost:8000` pasan a afirmar `/api` (es un cambio de **dirección**, no de comportamiento).
- [ ] **Paso 2: correrlas y ver que fallan** (`npm test` desde `frontend/`).
- [ ] **Paso 3: implementar el cliente, `acceso.ts`, los permisos y la configuración de Vite.** Sacar el comentario de `vite.config.ts` que justifica `strictPort` por el CORS: el puerto fijo se mantiene porque los enlaces del proxy lo suponen.
- [ ] **Paso 4: implementar las pantallas:** «Entrar» (usuario, contraseña y la casilla «mantener la sesión abierta en este dispositivo»), «Mi cuenta» (cambiar la contraseña), el menú de la barra con el nombre y «Cerrar sesión», y **sacar el campo «escribí tu nombre»** de la aprobación: los botones «Aprobar» y «Observar» solo se ven con `puedeAprobar(yo)`; y la API de presupuestos deja de mandar `por`.
- [ ] **Paso 5: correr** `npm test` completo y `npm run build`. Verde y sin errores de tipos.
- [ ] **Paso 6: commit** `feat(1.1): la pantalla entra con usuario y contraseña, y el menú muestra quién es`.

### Tarea 10: La pantalla de usuarios

**Files:**
- Create: `frontend/src/api/usuarios.ts`, `frontend/src/routes/Usuarios.tsx`, `frontend/src/routes/usuariosForm.ts`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/Barra.tsx` (el lugar «Usuarios», solo con permiso)
- Test: `frontend/src/api/usuarios.test.ts`, `frontend/src/routes/usuariosForm.test.ts`

**Interfaces:**
- Produces: `usuarios.ts` con `listarUsuarios()`, `crearUsuario(datos)`, `actualizarUsuario(id, datos)`, `restablecerContrasena(id)`, `darDeBaja(id)`, `darDeAlta(id)`; `usuariosForm.ts` con `validarUsuarioNuevo(datos): string | null` (usuario corto en minúsculas y sin espacios, nombre obligatorio, email con forma de email si se escribe).
- La ruta `/usuarios` solo se ve con `administraUsuarios(yo)`; la barra no muestra el lugar sin él. **La contraseña temporal se muestra una sola vez**, en un aviso que pide anotarla.

- [ ] **Paso 1: escribir las pruebas** de las llamadas (rutas y cuerpos) y de `validarUsuarioNuevo` (cada regla, con su mensaje).
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: implementar** la API, la validación y la pantalla (lista, alta, edición de nombre, email y permisos, restablecer, baja y alta); el error 409 del último administrador se muestra con el texto del servidor.
- [ ] **Paso 4: `npm test` y `npm run build`.**
- [ ] **Paso 5: recorrido en Chrome sin ventana** sobre una copia de la base (`copiar_base.py`), con el servidor y Vite levantados: crear el primer usuario por el comando, entrar, crear un diseñador desde la pantalla, entrar como él, armar un presupuesto y mandarlo a aprobar, comprobar que **no ve** «Aprobar», entrar como el dueño y aprobar, y mirar el historial con los dos nombres. **Mirar las capturas.** Al terminar, cerrar solo los procesos propios y borrar la copia.
- [ ] **Paso 6: commit** `feat(1.1): la pantalla de usuarios`. **Cierre de la entrega A2:** correr la suite completa del backend, el frontend, abrir el PR y esperar el CI y el visto bueno de Enzo para fusionar. **Antes de fusionar, respaldar la base real** (la migración de la Tarea 2 se aplica al arrancar la app) y avisar que después de actualizar hay que crear el primer usuario con `python -m app.usuarios crear`.

---

## Entrega A3 — Docker, copias y datos

### Tarea 11: Todo con Docker

**Files:**
- Create: `backend/Dockerfile`, `proxy/Dockerfile`, `proxy/Caddyfile`, `docker-compose.yml`, `.env.example`, `.dockerignore`, `backend/scripts/migrar.py`, `docker/probar_pila.sh`, `docs/GUIA-SERVIDOR.md`
- Modify: `.github/workflows/ci.yml` (un tercer trabajo, `docker`)
- Modify: `backend/app/arranque.py`, `.gitignore` (`.env`)
- Test: `backend/tests/test_arranque.py` (sumar), `backend/tests/test_docker_sin_secretos.py`

**Interfaces:**
- `backend/Dockerfile`: `python:3.11-slim` (la misma versión que el CI), instala `requirements.txt` y el cliente de PostgreSQL (`pg_dump`), corre como usuario sin privilegios, `CMD uvicorn app.api.app:app --host 0.0.0.0 --port 8000`.
- `proxy/Dockerfile`: en dos etapas. La primera compila el frontend (`node`, `npm ci`, `npm run build`); la segunda es `caddy`, con `dist` y el `Caddyfile`.
- `proxy/Caddyfile`: sirve `dist` para todo lo que no sea `/api`; para `/api/*` **saca el prefijo** y reenvía a `api:8000`; con `{$DOMINIO}` como dirección (en local, `:80`).
- `docker-compose.yml`: `db` (`postgres:16`, **sin `ports`**, volumen, chequeo de salud con `pg_isready`), `migrar` (un solo paso, corre `scripts/migrar.py`), `api` (`depends_on` de `migrar` con `service_completed_successfully`, y de `db` sano; `CARTELERIA_ENTORNO=produccion`; `CARTELERIA_DATOS=/datos`; **sin `ports`**), `proxy` (único con `ports`: `${PUERTO_WEB:-8080}:80` y `443` en la fase B) y, en la Tarea 12, `respaldo`. Volúmenes: `datos_db`, `datos_archivos` (en `/datos/archivos`), `datos_empresa` (montado de solo lectura en `/datos/empresa`) y `estado` (para `ultimo_backup.json`, de solo lectura en la API).
- `.env.example`: todas las variables, **sin valores reales**: `POSTGRES_PASSWORD`, `DOMINIO`, `PUERTO_WEB`, y las de las copias (Tarea 12).
- `arranque.py`: con una base que **no** es SQLite, `poner_la_base_al_dia` ya no pide actualizarla a mano: **verifica** que la versión de la base sea la del código. Si no, levanta `BaseDesactualizada` («La base está en la versión X y este servidor necesita la Y: aplicá las migraciones antes de arrancar.») y el servidor no arranca. Una base más nueva que el código sigue dando el error de siempre.
- `migrar.py`: con una base PostgreSQL, **primero un volcado** (`pg_dump -Fc` a `/datos/volcados/<fecha>-antes-de-<versión>.dump`) y **después** `alembic upgrade head`. Si no hay nada que migrar, no hace volcado.

- [ ] **Paso 1: escribir las pruebas** (sin PostgreSQL real, con las funciones de versión sustituidas):
  - `test_arranque.py`: con una URL de PostgreSQL y la base **al día**, no pasa nada; **atrasada**, levanta `BaseDesactualizada` con el mensaje; vacía (instalación nueva), tampoco arranca solo: pide migrar; con SQLite el comportamiento de siempre **no cambia** (las pruebas que ya hay lo cubren);
  - `test_docker_sin_secretos.py`: el `docker-compose.yml` no contiene ninguna cadena del tipo `password: <valor>` ni claves fijas; **ningún servicio salvo `proxy` tiene `ports`**; el `.env.example` existe y ninguna de sus variables trae un valor que no sea un ejemplo evidente; `.env` está en `.gitignore`.
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: implementar** el cambio de `arranque.py`, `migrar.py`, los Dockerfile, el Caddyfile, el compose y el `.env.example`, y empezar `docs/GUIA-SERVIDOR.md` (levantar, ver el estado, crear el primer usuario, actualizar, volver atrás).
- [ ] **Paso 4: correr** las pruebas nuevas y `tests/test_arranque.py` entero.
- [ ] **Paso 5: verificar en el CI.** `docker/probar_pila.sh` arma un `.env` con claves **al azar** a partir de `.env.example` (nada se versiona), y comprueba, en este orden: `docker compose build`; `up -d` y que **todo quede sano** dentro de un plazo; `GET /api/salud` da 200; **`docker compose port db 5432` no devuelve nada** (la base no está publicada); `GET /api/trabajos` sin sesión da 401; la pantalla carga en `/` y trae el HTML de la aplicación; `docker compose exec api python -m app.usuarios crear … --generar` crea el primer usuario; entrar con `curl` y su cookie da 200 en `/api/acceso/yo`; un `POST` sin el encabezado `X-Cartel-Pedido` da 403; `down -v`. El trabajo `docker` del CI corre ese script y, si algo falla, muestra `docker compose logs`. **Se espera iterar contra el CI** (subir, esperar, corregir): no hay Docker local.
- [ ] **Paso 6: commit** `feat(1.1): todo corre con Docker, sin contraseñas en el repositorio`.

### Tarea 12: Las copias de seguridad

**Files:**
- Create: `respaldo/Dockerfile`, `respaldo/respaldar.sh`, `respaldo/restaurar.sh`, `respaldo/entrada.sh`, `docker-compose.prueba.yml`
- Modify: `docker-compose.yml` (el servicio `respaldo`), `.env.example`, `docs/GUIA-SERVIDOR.md`

**Interfaces:**
- `respaldo/Dockerfile`: `alpine` con `restic`, `postgresql-client` y `bash`.
- `respaldar.sh`: (1) `pg_dump -Fc` de la base; (2) `restic backup` del volcado, de `/datos/archivos` y de `/datos/empresa`, con la etiqueta `diario`; (3) `restic forget --keep-daily "$BACKUP_DIAS" --prune` (`PAR-67`); (4) **solo si todo salió bien**, escribe `/estado/ultimo_backup.json` con la fecha. Si algo falla, sale con error y **no** actualiza el archivo.
- `entrada.sh`: programa `respaldar.sh` todos los días a `BACKUP_HORA` (`PAR-68`), en hora de Argentina (`TZ=America/Argentina/Buenos_Aires`).
- `restaurar.sh <snapshot>`: baja del repositorio la copia indicada (o la última) y deja el volcado y los archivos en una carpeta; **no pisa la base en uso**: la restauración real a un servidor nuevo se documenta paso a paso en la guía.
- Variables: `RESTIC_REPOSITORY`, `RESTIC_PASSWORD` (cifra las copias), las credenciales del almacenamiento compatible con S3, `BACKUP_DIAS`, `BACKUP_HORA`.
- `docker-compose.prueba.yml`: un servicio MinIO (almacenamiento compatible con S3) para **probar sin una cuenta real**.

- [ ] **Paso 1: la prueba, que es un recorrido real, dentro de `docker/probar_pila.sh copias` (corre en el CI):** con `docker compose -f docker-compose.yml -f docker-compose.prueba.yml up -d`, cargar un par de datos (el usuario, un cliente), correr `docker compose exec respaldo respaldar.sh` y comprobar que el repositorio en MinIO tiene una copia, que `ultimo_backup.json` existe y que `GET /api/salud` dice `backup.atrasado: false`.
- [ ] **Paso 2: probar que falla bien:** cambiar a propósito la clave del almacenamiento, correr `respaldar.sh`: **sale con error y no actualiza `ultimo_backup.json`**; con el archivo de estado viejo, `/api/salud` dice `atrasado: true` pasadas `PAR-69` horas.
- [ ] **Paso 3: la política de días:** crear copias con fechas distintas (o bajar `BACKUP_DIAS` a 1 para la prueba) y comprobar que `forget --prune` borra las viejas y deja las del plazo.
- [ ] **Paso 4: restaurar de verdad,** que es lo que importa (también en el CI): con `docker compose down -v` (borra los datos de prueba), levantar una pila **nueva** vacía, correr `restaurar.sh`, volcar con `pg_restore` y copiar los archivos, y comprobar que **el usuario y el cliente están** y que se puede entrar. Escribir el procedimiento, tal como se hizo, en `docs/GUIA-SERVIDOR.md`.
- [ ] **Paso 5: commit** `feat(1.1): copias diarias cifradas a un almacenamiento aparte, con restauración probada`.

### Tarea 13: Llevar el catálogo y los clientes

**Files:**
- Create: `backend/scripts/llevar_catalogo.py`
- Test: `backend/tests/test_scripts.py` (sumar), `backend/tests/postgres/test_llevar_catalogo_en_postgres.py`

**Interfaces:**
- Produce: `llevar_catalogo(origen_url: str, destino_url: str | None, *, reemplazar: bool = False, simular: bool = False) -> dict[str, int]` (cuántas filas pasaron, o pasarían, de cada tabla) y `main(argv)`: `python scripts/llevar_catalogo.py --desde sqlite:///... --hacia postgresql+psycopg://... [--reemplazar]` o `--simular` (sin `--hacia`): **lee el origen y dice cuánto pasaría de cada tabla, sin escribir nada**. Sirve para comprobar, con la base real de Enzo y sin PostgreSQL, que los números son los esperados.
- **Qué pasa** (en este orden, por las claves foráneas): `materiales`, `parametros_corte`, `formatos`, `articulos`, `cargas_de_planilla`, `cambios_de_precio`, `cotizaciones_moneda`, `clientes`. **De `formatos` solo las filas sin `origen_ejecucion_id`**: los retazos guardados desde el sobrante de un anidado no viajan. **No pasa** ninguna otra tabla (trabajos, piezas, grupos, anidados, presupuestos, historial, correcciones, usuarios).
- **Conserva los `id`** (las referencias entre tablas dependen de ellos). Con PostgreSQL, al terminar **ajusta cada secuencia** al `max(id)`.
- **No toca el origen** (lo abre solo para leer). Si el destino ya tiene filas en alguna de esas tablas, **se niega** salvo con `--reemplazar`, que primero las vacía.

- [ ] **Paso 1: escribir las pruebas** con dos bases SQLite en `tmp_path` (la de destino, vacía con `create_all`):
  - pasan las ocho tablas con sus filas, con los mismos `id` y los mismos valores (incluso `Decimal`);
  - **un `formato` con `origen_ejecucion_id` no pasa;** un retazo hecho a mano (sin origen) sí;
  - ningún trabajo, presupuesto ni usuario del origen aparece en el destino;
  - el origen queda **idéntico** (mismos conteos y mismas filas);
  - con el destino ya cargado, se niega y no cambia nada; con `reemplazar=True`, deja solo lo del origen;
  - correrlo dos veces con `--reemplazar` da lo mismo;
  - **`simular`** devuelve los mismos conteos que una corrida real y **no crea ni una fila** en el destino (ni exige que exista).
- [ ] **Paso 2: la prueba de PostgreSQL** (en el trabajo `postgres` del CI): después de llevar el catálogo, **crear un material nuevo desde el modelo no choca con ninguno de los llevados** (**Review Focus 5**), y lo mismo con un cliente y un formato.
- [ ] **Paso 3: correrlas y ver que fallan.**
- [ ] **Paso 4: implementar.** Copiar en lotes; usar el modelo (`Base.metadata`) y no SQL escrito a mano.
- [ ] **Paso 5: correr** las pruebas de SQLite y, en el CI, las de PostgreSQL.
- [ ] **Paso 6: probarlo con datos reales, sin Docker:** `python scripts/llevar_catalogo.py --desde sqlite:///<copia de la base de Enzo> --simular` (sobre una **copia**, `copiar_base.py llevar`). Comprobar los conteos (44 materiales, 59 medidas, 288 artículos, y los clientes). **La primera corrida real contra PostgreSQL es en el servidor, en B5.**
- [ ] **Paso 7: commit** `feat(1.1): llevar el catálogo y los clientes a PostgreSQL`.

### Tarea 14: Recorrido completo, documentos y cierre de la fase A

**Files:**
- Modify: `README.md`, `docs/MAPA-DEL-PROYECTO.md`, `docs/GUIA-SERVIDOR.md`, `docs/GUIA-PRUEBAS-LOCALES.md`, `docs/BITACORA.md`, `docs/REGISTRO.md` (cerrar `D-08` y mover `PAR-62` a `PAR-69` de «provisorio» a lo que corresponda), `docs/plan/PLAN-MAESTRO.md`

- [ ] **Paso 1: la suite completa del backend y del frontend**, y el CI en verde con los dos trabajos.
- [ ] **Paso 2: el recorrido completo, por HTTP, en el CI** (`docker/probar_pila.sh recorrido`): el primer usuario por el comando; entrar; crear un diseñador por la API de usuarios; el diseñador arma un presupuesto y lo manda a aprobar; **`aprobar` le da 403**; el dueño aprueba; el historial dice los dos nombres; cerrar sesión; **intentos fallidos hasta el bloqueo**; una copia y su restauración. **El recorrido con Chrome, mirando las pantallas, se hizo en la Tarea 10 (con SQLite) y se repite en el servidor real en B7.**
- [ ] **Paso 3: documentos.** El README («En qué estamos» y el recorrido), el mapa, la guía de pruebas, `GUIA-SERVIDOR.md` completa (levantar, actualizar, volver atrás, copias y restauración, usuarios y emergencias, qué mirar en `/salud`), el registro y la bitácora.
- [ ] **Paso 4: PR de la entrega A3,** esperar el CI y el visto bueno de Enzo. Al fusionar, la carpeta se queda en `docs/plan/` hasta cerrar también la fase B.

---

## Fase B — El servidor alquilado

Es operación más que código: cada paso termina con algo que se mira. Los pasos con **Enzo** necesitan una cuenta, un pago o una decisión suya.

### B1: Elegir el servidor y el dominio (`T-01`, `T-02`)

- [ ] **Claude:** buscar en el momento (los precios y las regiones cambian) y armar una comparación corta de tres o cuatro proveedores, con los **mínimos de este diseño**: **4 procesadores o más** (`SUP-42`), memoria a medir, región con poca latencia desde Argentina, pago con tarjeta, copias de seguridad propias del proveedor opcionales. Más una guía de qué dominio registrar y dónde.
- [ ] **Enzo:** elige, contrata y registra. Comparte la dirección IP del servidor y el acceso por clave (nunca la contraseña por chat).
- **Se mira:** el servidor responde por SSH con la clave; el dominio está registrado y se puede editar su DNS.

### B2: Preparar la máquina

- [ ] Acceso **solo con clave** (sin contraseña, sin entrar como administrador directo). Un usuario para correr Docker. Cortafuegos con solo SSH, HTTP y HTTPS abiertos. Actualizaciones de seguridad automáticas. Docker instalado.
- **Se mira:** un intento de entrar con contraseña es rechazado; un escaneo de puertos desde afuera solo ve 22, 80 y 443.

### B3: El dominio y el certificado

- [ ] Apuntar el dominio (o un subdominio, por ejemplo `presupuestos.<dominio>`) a la IP del servidor. Poner `DOMINIO` en el `.env`.
- **Se mira:** al levantar, Caddy saca el certificado solo; `https://<dominio>/api/salud` da 200 con candado válido; `http://` redirige a `https://`.

### B4: El primer despliegue, y cómo volver atrás

- [ ] Un guion `scripts/desplegar.sh` que baja el código a una versión indicada (una etiqueta de git), construye, aplica las migraciones (con el volcado previo) y levanta. Documentar **cómo volver atrás**: volver a la etiqueta anterior y restaurar el volcado previo.
- **Se mira:** desplegar la versión actual; después desplegar una versión anterior y confirmar que vuelve; el estado de salud da 200 en ambas.

### B5: Los datos y las personas reales

- [ ] Llevar la carpeta de la empresa (logo y datos) al volumen. Con un túnel SSH a la base, correr `llevar_catalogo.py` desde la computadora de Enzo. Crear al dueño como administrador con el comando y **cambiar su contraseña temporal**. El dueño crea a los diseñadores desde la pantalla.
- **Se mira:** en Materiales están los 44 materiales y la planilla; un presupuesto de prueba sale en PDF **con la marca**.

### B6: Las copias de verdad (`T-06`)

- [ ] **Enzo:** elegir el almacenamiento en la nube y crear sus credenciales. Poner las variables en el `.env` del servidor, activar el servicio de copias.
- [ ] **Restaurar una copia real en otra máquina** y comprobar que levanta con los datos.
- **Se mira:** `/api/salud` dice `backup.atrasado: false`, y la copia restaurada tiene los usuarios y el catálogo.

### B7: La prueba final, desde el celular

- [ ] Entrar desde el celular del dueño, ver el inicio, abrir un presupuesto. Entrar como diseñador y verificar que no puede aprobar. **Repetir el recorrido de Chrome sin ventana de la Tarea 10 contra la dirección real** (se corre desde la computadora de Enzo, sin Docker) y mirar las capturas. Apuntar un monitor gratuito de disponibilidad a `https://<dominio>/api/salud`.
- [ ] **Documentos:** cerrar `T-01`, `T-02` y `T-06` en el registro; actualizar el README y la bitácora; pasar la carpeta a `docs/historico/`.

---

## Autorevisión

- **Cobertura del diseño:** §4.1 y §4.2 → Tareas 2, 3 y 4; §4.3 → Tarea 6; §4.4 → Tarea 7; §4.5 y §4.6 → Tareas 8 y 10; §4.7 → arnés de la Tarea 4; §4.8 y §4.9 → Tareas 9 y 11; §4.10 → Tareas 1 y 11; §4.11 → Tarea 12; §4.12 → Tarea 13; §5 → Fase B.
- **Nombres consistentes:** `Usuario`, `SesionDeUsuario`, `UsuarioActual`, `usuario_actual`, `exigir_permiso`, `COOKIE_DE_SESION`, `ENCABEZADO_DE_PEDIDO`, `crear_app`, `iniciar_sesion`, `llevar_catalogo`, `BaseDesactualizada`.
- **Lo que queda a criterio de quien implemente:** el diseño visual de las pantallas, los textos exactos de los errores no listados, y cómo se divide un archivo si `servicio.py` crece.
- **Riesgos conocidos:** las 18 migraciones se escribieron para SQLite; no se sabe cuántas fallan en PostgreSQL hasta correr el CI (Tarea 1). Si son muchas, esa tarea crece y conviene tratarla como una entrega propia. Y sin Docker local, **la entrega A3 se itera contra el CI**: cada vuelta cuesta unos minutos.
