"""Menú para administrar usuarios desde la terminal, hablando con la app (1.1).

    python scripts/administrar_usuarios.py                      # la app de esta computadora (puerto 8000)
    python scripts/administrar_usuarios.py --url https://tu-dominio/api

No toca la base: entra a la app con un usuario que **administra usuarios** y hace lo mismo que la pantalla de
usuarios, así que funciona igual contra la app local o la desplegada, desde cualquier computadora. Quien no
tiene ese permiso no pasa del primer paso. Solo usa la biblioteca estándar: no hay nada que instalar.

«Borrar» es dar de baja: la persona deja de poder entrar y su historial queda. Las personas dadas de baja no
aparecen en la lista; están en la opción «Ver dados de baja», que solo se muestra si hay alguna.

Si la app está caída o el dueño se bloqueó, no sirve: en el servidor queda `python -m app.usuarios restablecer`.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from http.cookiejar import CookieJar
from urllib import error, request

URL_POR_DEFECTO = "http://localhost:8000"
ENCABEZADO_DE_PEDIDO = "X-Cartel-Pedido"  # el mismo que pone la pantalla: sin él la app rechaza los cambios


class ErrorDeLaApp(Exception):
    """Lo que la app contestó mal, ya en palabras para mostrar."""


class Aplicacion:
    """La app por HTTP. Guarda la cookie de la sesión entre pedidos."""

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")
        self._abridor = request.build_opener(request.HTTPCookieProcessor(CookieJar()))

    def pedir(self, metodo: str, ruta: str, cuerpo: dict | None = None):
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        pedido = request.Request(
            self.url + ruta,
            data=datos,
            method=metodo,
            headers={"Content-Type": "application/json", ENCABEZADO_DE_PEDIDO: "1"},
        )
        try:
            with self._abridor.open(pedido, timeout=15) as respuesta:
                texto = respuesta.read().decode("utf-8")
        except error.HTTPError as falla:
            raise ErrorDeLaApp(_mensaje_de(falla)) from falla
        except error.URLError as falla:
            raise ErrorDeLaApp(f"No se pudo conectar con {self.url}: ¿está la app levantada?") from falla
        return json.loads(texto) if texto else None


def _mensaje_de(falla: error.HTTPError) -> str:
    try:
        detalle = json.loads(falla.read().decode("utf-8")).get("detail")
    except (ValueError, AttributeError):
        detalle = None
    if isinstance(detalle, dict):
        detalle = detalle.get("mensaje")
    if isinstance(detalle, str) and detalle:
        return detalle
    if falla.code == 403:
        return "No tenés permiso para administrar usuarios."
    return f"La app contestó con el error {falla.code}."


def _permisos(persona: dict) -> str:
    nombres = [n for n, clave in (("aprueba", "puede_aprobar"), ("administra", "administra_usuarios")) if persona[clave]]
    return ", ".join(nombres) or "diseña"


class Menu:
    def __init__(self, aplicacion, leer=input, leer_secreto=getpass.getpass, mostrar=print) -> None:
        self.app = aplicacion
        self._leer, self._secreto, self.mostrar = leer, leer_secreto, mostrar

    # --- Entrar ---------------------------------------------------------------------------

    def entrar(self) -> bool:
        usuario = self._leer("Usuario: ").strip()
        contrasena = self._secreto("Contraseña: ")
        try:
            self.app.pedir("POST", "/acceso/entrar", {"usuario": usuario, "contrasena": contrasena})
            self.app.pedir("GET", "/usuarios")  # confirma el permiso antes de mostrar nada
        except ErrorDeLaApp as falla:
            self.mostrar(f"No se pudo entrar: {falla}")
            return False
        return True

    # --- Ayudas ---------------------------------------------------------------------------

    def _preguntar(self, texto: str, actual: str | None = None) -> str:
        sufijo = f" [{actual}]" if actual else ""
        return self._leer(f"{texto}{sufijo}: ").strip()

    def _si_no(self, texto: str, actual: bool | None = None) -> bool | None:
        """`None` si se dejó vacío y ya había un valor (no cambia)."""
        marca = "" if actual is None else (" [s]" if actual else " [n]")
        while True:
            respuesta = self._leer(f"{texto} (s/n){marca}: ").strip().lower()
            if not respuesta and actual is not None:
                return None
            if not respuesta:
                return False
            if respuesta in ("s", "n"):
                return respuesta == "s"
            self.mostrar("Contestá s o n.")

    def _elegir(self, personas: list[dict], texto: str) -> dict | None:
        respuesta = self._leer(f"{texto} (número, o Enter para volver): ").strip()
        if not respuesta:
            return None
        if respuesta.isdigit() and 1 <= int(respuesta) <= len(personas):
            return personas[int(respuesta) - 1]
        self.mostrar("Ese número no está en la lista.")
        return None

    def _listar(self, personas: list[dict], titulo: str) -> None:
        self.mostrar(f"\n{titulo} ({len(personas)})")
        for numero, persona in enumerate(personas, 1):
            self.mostrar(f"  {numero:>2}. {persona['usuario']:<16} {persona['nombre']:<24} {_permisos(persona)}")

    def _todos(self) -> tuple[list[dict], list[dict]]:
        todos = self.app.pedir("GET", "/usuarios")
        return [p for p in todos if p["activo"]], [p for p in todos if not p["activo"]]

    # --- Las acciones ---------------------------------------------------------------------

    def crear(self) -> None:
        usuario = self._preguntar("Usuario (una sola palabra)")
        nombre = self._preguntar("Nombre")
        email = self._preguntar("Email (opcional)")
        creado = self.app.pedir("POST", "/usuarios", {
            "usuario": usuario,
            "nombre": nombre,
            "email": email or None,
            "puede_aprobar": bool(self._si_no("¿Puede aprobar presupuestos?")),
            "administra_usuarios": bool(self._si_no("¿Administra usuarios?")),
        })
        self.mostrar(f"\nSe creó «{creado['usuario']}». Tiene que elegir otra contraseña al entrar.")
        self.mostrar(f"Contraseña temporal: {creado['contrasena_temporal']}")
        self.mostrar("Anotala ahora: no se vuelve a mostrar.")

    def editar(self, persona: dict) -> None:
        self.mostrar(f"\nEditando a «{persona['usuario']}». Enter deja cada dato como está; «-» borra el email.")
        cambios: dict = {}
        nombre = self._preguntar("Nombre", persona["nombre"])
        if nombre:
            cambios["nombre"] = nombre
        email = self._preguntar("Email", persona["email"])
        if email:
            cambios["email"] = None if email == "-" else email
        aprueba = self._si_no("¿Puede aprobar presupuestos?", persona["puede_aprobar"])
        if aprueba is not None:
            cambios["puede_aprobar"] = aprueba
        administra = self._si_no("¿Administra usuarios?", persona["administra_usuarios"])
        if administra is not None:
            cambios["administra_usuarios"] = administra
        if not cambios:
            self.mostrar("No cambió nada.")
            return
        self.app.pedir("PATCH", f"/usuarios/{persona['id']}", cambios)
        self.mostrar("Listo.")

    def restablecer(self, persona: dict) -> None:
        if self._si_no(f"¿Restablecer la contraseña de «{persona['usuario']}»?") is not True:
            return
        resultado = self.app.pedir("POST", f"/usuarios/{persona['id']}/restablecer-contrasena")
        self.mostrar(f"\nContraseña temporal: {resultado['contrasena_temporal']}")
        self.mostrar("Se le cerraron las sesiones y tiene que elegir otra al entrar. Anotala ahora: no se vuelve a mostrar.")

    def dar_de_baja(self, persona: dict) -> None:
        if self._si_no(f"¿Dar de baja a «{persona['usuario']}»? Deja de poder entrar; su historial queda") is not True:
            return
        self.app.pedir("POST", f"/usuarios/{persona['id']}/dar-de-baja")
        self.mostrar("Listo: está en «Ver dados de baja».")

    def dados_de_baja(self) -> None:
        while True:
            _, de_baja = self._todos()
            if not de_baja:
                return
            self._listar(de_baja, "Dados de baja")
            persona = self._elegir(de_baja, "¿A quién volver a dar de alta?")
            if persona is None:
                return
            self.app.pedir("POST", f"/usuarios/{persona['id']}/dar-de-alta")
            self.mostrar(f"«{persona['usuario']}» volvió a estar activo. Conserva su contraseña.")

    # --- El menú --------------------------------------------------------------------------

    def correr(self) -> int:
        if not self.entrar():
            return 1
        while True:
            try:
                activos, de_baja = self._todos()
                self._listar(activos, "Usuarios")
                opciones = ["1. Crear", "2. Editar", "3. Restablecer contraseña", "4. Dar de baja"]
                if de_baja:
                    opciones.append(f"5. Ver dados de baja ({len(de_baja)})")
                opciones.append("0. Salir")
                self.mostrar("\n" + "   ".join(opciones))
                eleccion = self._leer("Opción: ").strip()
                if eleccion == "0":
                    return 0
                if eleccion == "1":
                    self.crear()
                elif eleccion in ("2", "3", "4"):
                    persona = self._elegir(activos, "¿A quién?")
                    if persona is not None:
                        {"2": self.editar, "3": self.restablecer, "4": self.dar_de_baja}[eleccion](persona)
                elif eleccion == "5" and de_baja:
                    self.dados_de_baja()
                else:
                    self.mostrar("Esa opción no está.")
            except ErrorDeLaApp as falla:
                self.mostrar(f"\nNo se pudo: {falla}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Menú para administrar usuarios, hablando con la app.")
    parser.add_argument("--url", default=os.getenv("CARTELERIA_URL", URL_POR_DEFECTO), help="dirección de la app (sin el final «/»)")
    args = parser.parse_args(argv)
    try:
        return Menu(Aplicacion(args.url)).correr()
    except (KeyboardInterrupt, EOFError):
        print("\nSalida.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
