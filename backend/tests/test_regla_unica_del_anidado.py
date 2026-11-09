"""Una guardiana para que la regla de «qué anidado cuenta para el presupuesto» no se
vuelva a repartir (A25, tarea 6, `docs/plan/A25-regla-unica-del-anidado/diseno.md`).

Hasta A25 la regla estaba en cuatro lugares: el costeo, la tarjeta del inicio, el
PDF y Chapas. Ahora vive en `app/anidado_que_cuenta.py`. Esta prueba mira el código
fuente: si otro módulo vuelve a armar su propio «vencido» o a comparar la chapa por
su cuenta, falla diciendo el archivo y la línea.
"""
from __future__ import annotations

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

#: Donde vive la regla.
EL_MODULO = "anidado_que_cuenta.py"


def _donde(patron: str) -> list[tuple[str, int, str]]:
    """Cada línea de `app/` que coincide con `patron`: (archivo, número de línea, texto)."""
    encontradas = []
    for ruta in sorted(APP.rglob("*.py")):
        for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1):
            if re.search(patron, linea):
                encontradas.append((ruta.relative_to(APP).as_posix(), numero, linea.strip()))
    return encontradas


def _afuera_de(permitidos: set[str], encontradas: list[tuple[str, int, str]]) -> list[str]:
    return [f"{archivo}:{numero}: {texto}" for archivo, numero, texto in encontradas if archivo not in permitidos]


def test_solo_el_modulo_de_la_regla_pregunta_si_un_anidado_esta_al_dia_con_las_piezas():
    # `anidado_vigente` se define en el modelo (la propiedad `vencido` la usa) y la llama la regla.
    sobran = _afuera_de({"modelos/trabajo.py", EL_MODULO}, _donde(r"\banidado_vigente\b"))

    assert not sobran, (
        "Otro módulo decide por su cuenta si un anidado está al día con las piezas. "
        f"Preguntale a `anidado_que_cuenta`: {sobran}"
    )


def test_la_eleccion_vieja_del_costeo_ya_no_existe():
    assert not _donde(r"\b_ejecucion_para_costear\b"), (
        "Volvió `_ejecucion_para_costear`: la elección de qué anidado cuenta vive en `anidado_que_cuenta`."
    )


def test_solo_el_modulo_de_la_regla_compara_la_chapa_de_la_corrida_con_la_de_hoy():
    comparaciones = _donde(r"(!=|==)\s*formato\.(ancho|alto)_mm|formato\.(ancho|alto)_mm\s*(!=|==)")

    sobran = _afuera_de({EL_MODULO}, comparaciones)

    assert not sobran, (
        "Otro módulo compara la chapa con la que se anidó contra la de hoy. "
        f"Eso es parte de «por qué no se cobra»: {sobran}"
    )


#: Quién más lee el snapshot de la chapa (`parametros["formato"]`) y para qué. Ninguno decide si se
#: cobra: leen con qué medida se anidó, para dibujar o mostrar. Un lector nuevo se suma acá, con su motivo.
LECTORES_DEL_SNAPSHOT_DE_LA_CHAPA = {
    EL_MODULO: "compara la chapa de la corrida con la de hoy (es la regla)",
    "api/rutas_ajuste.py": "dibuja el editor de Ajuste con la plancha con que se anidó",
    "api/rutas_nesting.py": "rearma la plancha al ejecutar y guarda el snapshot al anidar",
    "api/rutas_pdf_anidado.py": "muestra el material y la plancha con que se anidó",
}


def test_quien_lee_el_snapshot_de_la_chapa_esta_a_la_vista():
    lectores = _donde(r"""\.get\(["']formato["']\)""")

    desconocidos = _afuera_de(set(LECTORES_DEL_SNAPSHOT_DE_LA_CHAPA), lectores)

    assert not desconocidos, (
        "Un módulo nuevo lee el snapshot de la chapa. Si decide si el anidado se cobra, eso va en "
        "`anidado_que_cuenta`; si solo muestra o dibuja, sumalo a LECTORES_DEL_SNAPSHOT_DE_LA_CHAPA "
        f"con su motivo: {desconocidos}"
    )
