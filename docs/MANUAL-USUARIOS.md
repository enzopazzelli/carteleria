# Manual de usuarios y de la base de desarrollo

Para el dueño. Cómo entrar, cómo se administran las personas que usan el sistema y cómo limpiar la base cuando se está probando. Todo en lenguaje corriente: si algo no se entiende, es un error del manual.

## 1. Quién puede hacer qué

Cada persona tiene un **usuario** (una sola palabra, por ejemplo `vale`) y una **contraseña**. Además puede tener dos permisos:

| Permiso | Qué deja hacer |
|---|---|
| **Puede aprobar** | Aprobar o devolver un presupuesto |
| **Administra usuarios** | Crear personas, cambiarles los permisos, darlas de baja, restablecer contraseñas |

Quien no tiene ninguno es un **diseñador**: arma trabajos y presupuestos, y los manda a aprobar. Todos ven todos los trabajos. Tiene que haber **siempre al menos una persona que administre usuarios**: el sistema no deja darla de baja ni sacarle el permiso si es la última.

## 2. Entrar y cambiar la contraseña

- **Entrar:** la pantalla de entrada pide usuario y contraseña. «Mantener la sesión abierta en este dispositivo» deja la sesión abierta 30 días (pensado para el celular); sin marcar, se cierra después de 12 horas sin uso.
- **Primera vez:** cuando alguien recibe una contraseña **temporal** (porque se lo dio de alta o se la restablecieron), el sistema lo lleva a **Mi cuenta** y no lo deja ir a otro lado hasta elegir una propia.
- **Cambiarla cuando se quiera:** en **Mi cuenta**, con la contraseña actual y la nueva. La nueva tiene que tener **al menos 10 caracteres** y ser distinta de la actual. Al cambiarla se cierran las sesiones de los otros dispositivos.
- **Si se olvida:** no puede recuperarla sola (todavía no hay mail). Se la pide a quien administra usuarios, que le **restablece la contraseña** y le da una temporal.
- **Si falla 5 veces seguidas:** la cuenta se bloquea 15 minutos. Restablecer la contraseña también levanta el bloqueo.

Nadie ve la contraseña definitiva de otra persona: el sistema solo guarda una huella, no la contraseña.

## 3. Administrar usuarios: dos caminos

### 3.1 Desde la pantalla

Entrando con un usuario que administra usuarios, aparece **Usuarios** en la barra de arriba. Ahí se puede crear una persona, editarla, restablecerle la contraseña y darla de baja o de alta. Es el camino de todos los días.

### 3.2 Desde la terminal, con el menú

Sirve para administrar sin abrir el navegador, o contra la app desplegada desde cualquier computadora. **Habla con la app**, no con la base: entra con un usuario que administra usuarios y hace lo mismo que la pantalla.

Desde la carpeta `backend/`:

```
python scripts/administrar_usuarios.py                              # la app de esta computadora
python scripts/administrar_usuarios.py --url https://tu-dominio/api # la app en el servidor
```

También se puede fijar la dirección una vez con la variable `CARTELERIA_URL`. No hay que instalar nada.

1. Pide **usuario y contraseña**. Si la persona no administra usuarios, no pasa de ahí.
2. Muestra la lista de personas activas y el menú:

```
1. Crear   2. Editar   3. Restablecer contraseña   4. Dar de baja   5. Ver dados de baja (2)   0. Salir
```

| Opción | Qué hace |
|---|---|
| **1. Crear** | Pide usuario, nombre, email (opcional) y los dos permisos. Muestra una **contraseña temporal una sola vez**: anotala y pasásela a la persona. |
| **2. Editar** | Elegís a quién por su número. Enter deja cada dato como está; en el email, `-` lo borra. |
| **3. Restablecer contraseña** | Pide confirmación y da una temporal nueva. Le cierra las sesiones abiertas y le levanta el bloqueo. |
| **4. Dar de baja** | Pide confirmación. La persona deja de poder entrar al instante; su historial queda. |
| **5. Ver dados de baja** | Solo aparece si hay alguno. Lista a los dados de baja; elegir uno lo **vuelve a dar de alta**, con la misma contraseña que tenía. |

**«Borrar» es dar de baja.** Nadie se elimina de la base: el historial de quién aprobó o cambió qué tiene que seguir diciendo quién fue. Por eso los dados de baja no aparecen en la lista principal, sino en la opción 5.

### 3.3 Emergencia: nadie puede entrar

Si la app está caída, o se bloqueó la única cuenta que administra usuarios, el menú no sirve (necesita entrar). En el servidor queda el comando de siempre, que trabaja directo sobre la base:

```
python -m app.usuarios restablecer enzo      # da una contraseña temporal y levanta el bloqueo
python -m app.usuarios crear enzo --nombre "Enzo" --administrador --puede-aprobar --generar
python -m app.usuarios listar
```

Solo lo puede usar quien tiene acceso al servidor. Tiene que ser desde `backend/`.

## 4. Limpiar la base de desarrollo

**Solo para la base local de pruebas, nunca para el servidor.** Borra datos, así que antes de cada borrado el script hace un respaldo, te muestra cuántas filas se llevaría (sin borrar todavía) y te pide escribir `BORRAR`. Cualquier otra cosa cancela.

Desde `backend/`, con **la app cerrada** (si hay algo escuchando en los puertos 8000 o 5173, el script se niega a correr):

```
python scripts/limpiar_base.py
```

| Opción | Qué borra | Qué conserva |
|---|---|---|
| **A. Trabajos** | Trabajos con sus piezas y anidados, presupuestos, retazos, las correcciones del dibujo y los archivos guardados de cada trabajo | Clientes, materiales y precios, usuarios |
| **B. Trabajos y clientes** | Lo de A y los clientes | Materiales y precios, usuarios |
| **C. De fábrica** | Todo lo anterior y además los materiales, las medidas, los artículos y la planilla cargada | **Solo los usuarios.** Después hay que volver a cargar la planilla de precios |
| **D. Sesiones** | Cierra las sesiones abiertas de todos (tienen que volver a entrar) | Todo lo demás |

- **Los usuarios no se borran nunca**, en ninguna opción.
- El respaldo queda en `backend/local/respaldo-AAAA-MM-DD-antes-de-limpiar/carteleria.db`. Para volver atrás, se cierra la app y se copia ese archivo sobre `backend/local/carteleria.db`.
- Para limpiar una **copia** y no la base real: `CARTELERIA_DATOS=local/copias/<nombre> python scripts/limpiar_base.py` (la copia se arma con `scripts/copiar_base.py`, ver [`GUIA-PRUEBAS-LOCALES.md §6`](GUIA-PRUEBAS-LOCALES.md)).

## 5. Si algo sale mal

| Qué pasa | Qué hacer |
|---|---|
| «Usuario o contraseña incorrectos» y no se sabe por qué | El sistema no dice si falló el usuario o la contraseña, a propósito. Probar de nuevo; si falló 5 veces, esperar 15 minutos o pedir que se la restablezcan |
| El menú dice «No se pudo conectar» | La app no está levantada, o la dirección es otra (`--url`) |
| El menú dice «No tenés permiso para administrar usuarios» | Entrar con otro usuario, o pedirle a quien administre que te dé el permiso |
| «Ese nombre de usuario ya existe» | Puede estar dado de baja: mirar la opción 5 |
| «Tiene que quedar al menos una persona que administre usuarios» | Darle el permiso a otra persona antes de sacárselo o darla de baja |
| El script de limpiar dice «Hay una app escuchando» | Cerrar la app (y el frontend) antes de limpiar |
