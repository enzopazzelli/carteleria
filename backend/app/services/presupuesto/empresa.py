"""Los datos de la empresa para el PDF del presupuesto: el logo y los datos de
contacto (A22, `docs/plan/A22-pdf-con-la-marca/diseno.md`).

Salen de una carpeta **fuera de git** (`backend/local/empresa/`): el
repositorio es público y ahí irían un WhatsApp y una dirección reales. Si la
carpeta no está, o un archivo está roto, el PDF sale igual, sin logo o sin pie:
generar un presupuesto nunca falla por la decoración.

- `logo.png`: el logo; se recorta al contenido al leerlo.
- `datos.json`: `nombre`, `direccion`, `whatsapp`, `mail`, `web`, `instagram` y,
  si hay, `cuit` y `condiciones`. Lo vacío no aparece.
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops

from ... import config
from ...registro import registro

_CAMPOS = ("nombre", "direccion", "whatsapp", "mail", "web", "instagram", "cuit", "condiciones")


@dataclass(frozen=True)
class Empresa:
    nombre: str | None = None
    direccion: str | None = None
    whatsapp: str | None = None
    mail: str | None = None
    web: str | None = None
    instagram: str | None = None
    cuit: str | None = None
    condiciones: str | None = None
    #: El logo como PNG, ya recortado a su contenido.
    logo: bytes | None = None
    #: Ancho dividido por alto del logo recortado.
    proporcion_del_logo: float | None = None

    def titulo_del_pie(self) -> str:
        """El nombre, con el CUIT si lo hay."""
        return "  ·  ".join(parte for parte in (self.nombre, f"CUIT {self.cuit}" if self.cuit else None) if parte)


def carpeta_de_la_empresa() -> Path:
    return config.DIRECTORIO_EMPRESA


def _leer_datos(archivo: Path) -> dict[str, str]:
    try:
        crudo = json.loads(archivo.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        registro().warning("No se pudieron leer los datos de la empresa en %s: el PDF sale sin ellos.", archivo)
        return {}
    if not isinstance(crudo, dict):
        registro().warning("Los datos de la empresa en %s no tienen la forma esperada (un dato por nombre): el PDF sale sin ellos.", archivo)
        return {}
    datos = {}
    for campo in _CAMPOS:
        valor = crudo.get(campo)
        if isinstance(valor, str) and valor.strip():
            datos[campo] = valor.strip()
    return datos


def _leer_logo(archivo: Path) -> tuple[bytes, float] | None:
    if not archivo.exists():
        return None
    try:
        imagen = Image.open(archivo).convert("RGBA")
        # Lo que no es transparente; si el fondo es blanco y no transparente, lo que no es blanco.
        caja = imagen.split()[3].getbbox()
        if caja is not None and caja == (0, 0, *imagen.size):
            fondo = Image.new("RGB", imagen.size, (255, 255, 255))
            caja = ImageChops.difference(imagen.convert("RGB"), fondo).getbbox() or caja
        if caja is None:
            return None
        recortada = imagen.crop(caja)
        salida = io.BytesIO()
        recortada.save(salida, format="PNG")
        return salida.getvalue(), recortada.size[0] / recortada.size[1]
    except (OSError, ValueError):
        registro().warning("No se pudo leer el logo de la empresa en %s: el PDF sale sin él.", archivo)
        return None


def cargar_empresa(carpeta: Path | None = None) -> Empresa:
    """Los datos de la empresa, o una `Empresa()` vacía si no están."""
    carpeta = carpeta if carpeta is not None else carpeta_de_la_empresa()
    datos = _leer_datos(carpeta / "datos.json")
    logo = _leer_logo(carpeta / "logo.png")
    return Empresa(**datos, logo=logo[0] if logo else None, proporcion_del_logo=logo[1] if logo else None)


def lineas_del_pie(empresa: Empresa) -> list[str]:
    """Las líneas de contacto del pie, sin el nombre: solo lo que hay."""
    lineas = []
    if empresa.direccion:
        lineas.append(empresa.direccion)
    contacto = [f"WhatsApp {empresa.whatsapp}" if empresa.whatsapp else None, empresa.mail]
    if any(contacto):
        lineas.append("  ·  ".join(parte for parte in contacto if parte))
    redes = [empresa.web, f"Instagram @{empresa.instagram.lstrip('@')}" if empresa.instagram else None]
    if any(redes):
        lineas.append("  ·  ".join(parte for parte in redes if parte))
    return lineas
