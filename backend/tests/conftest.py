"""Lo que vale para todas las pruebas."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _carpeta_temporal_de_la_prueba(tmp_path, monkeypatch):
    """Cada prueba tiene su propia carpeta temporal (revisión de la tanda 5
    de A17). El arranque de la app la vacía, y una prueba que arranca sin
    `dependency_overrides` vaciaba la de los datos de verdad
    (`<CARTELERIA_DATOS>/tmp`, o `backend/local/tmp` sin la variable), donde
    puede estar anidando el servidor."""
    from app import config

    monkeypatch.setattr(config, "DIRECTORIO_TEMPORAL", tmp_path / "tmp-de-la-app")
    # Ninguna prueba lee el logo ni los datos de contacto reales de la empresa (A22).
    monkeypatch.setattr(config, "DIRECTORIO_EMPRESA", tmp_path / "sin-empresa")


@pytest.fixture(autouse=True)
def _usuario_de_prueba(request):
    """El arnés de la sesión (1.1). Todas las rutas del sistema exigen haber entrado; las pruebas que no
    son de acceso entran solas, con un usuario de prueba que puede aprobar y administrar y **no está en la
    base** (`id=None`): así no choca con las claves foráneas ni hace falta crearlo en cada base de prueba.

    Las que prueban justamente la entrada y los permisos se marcan `@pytest.mark.sin_sesion_de_prueba` y
    entran de verdad, con usuarios que dan de alta ellas."""
    if request.node.get_closest_marker("sin_sesion_de_prueba"):
        yield
        return
    from app.api.app import app
    from app.api.autenticacion import UsuarioActual, usuario_actual

    app.dependency_overrides[usuario_actual] = lambda: UsuarioActual(
        id=None, usuario="prueba", nombre="Prueba", puede_aprobar=True, administra_usuarios=True,
        debe_cambiar_contrasena=False,
    )
    yield
    # Los armadores de cliente de las pruebas de la API hacen `clear()` al terminar; esto es por las que no.
    app.dependency_overrides.pop(usuario_actual, None)
