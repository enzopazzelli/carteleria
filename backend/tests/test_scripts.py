"""Las herramientas de `scripts/` que se abren con doble clic tienen que
poder arrancar: un import roto las deja caídas sin que la suite lo note."""
import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def test_el_visor_se_puede_importar():
    """`Visor de anidado.cmd` levanta este script. Se cayó cuando se borró
    `anidado_huecos.py` (revisión de A10)."""
    spec = importlib.util.spec_from_file_location("servidor_visor", SCRIPTS / "servidor_visor.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert hasattr(modulo, "PUERTO_DEFAULT")
