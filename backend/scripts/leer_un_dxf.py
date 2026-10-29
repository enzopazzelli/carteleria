"""Cómo se lee un DXF, por el mismo camino que la pantalla: el pedido
`POST /trabajos/{id}/dxf/lectura`, que no guarda nada.

Sirve para repetir la tabla del §2 de
`docs/historico/2.1a-lectura-con-imagen/diseno.md` sobre los DXF reales.

    cd backend
    CARTELERIA_DATOS=<copia de los datos> python scripts/leer_un_dxf.py <archivo.dxf> <escala> [trabajo]

Usa el catálogo de la base de `CARTELERIA_DATOS`: correrlo contra una
copia, no contra `backend/local/`, que es la que usa sin la variable. Al
arrancar la app, como el servidor, pone al día esa base si está atrasada,
con su respaldo, vacía su carpeta temporal y corta los anidados que
figuren en curso (A17): con el servidor anidando contra esos datos, los
cortaría. `trabajo` es el número de un trabajo
que exista en esa base (1 si no se pasa); solo se usa para armar los
nombres de las piezas.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.app import app  # noqa: E402


def _resumen(nombre: str, lectura: dict) -> None:
    print(f"  {nombre}: {lectura['a_cortar']} a cortar, {lectura['descartadas']} entran descartadas")
    for forma in lectura["formas"]:
        if not forma["id_origen"].endswith("/unida"):
            continue
        contorno = Polygon(forma["contorno_mm"], forma["agujeros_mm"])
        min_x, min_y, max_x, max_y = contorno.bounds
        print(
            f"    {forma['id_origen']}: {max_x - min_x:.0f} x {max_y - min_y:.0f} mm, "
            f"{contorno.area / 1e6:.2f} m2, {len(forma['agujeros_mm'])} huecos (medidas del dibujo, aproximadas)"
        )
    for aviso in lectura["advertencias"]:
        if "pisa" in aviso or "hueco" in aviso:
            print(f"    aviso: {aviso}")


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ruta, escala = Path(sys.argv[1]), sys.argv[2]
    trabajo = sys.argv[3] if len(sys.argv) > 3 else "1"
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            f"/trabajos/{trabajo}/dxf/lectura",
            files={"archivo": (ruta.name, ruta.read_bytes(), "application/dxf")},
            data={"escala_a_mm": escala},
        )
    if respuesta.status_code != 200:
        sys.exit(f"{respuesta.status_code}: {respuesta.text}")
    cuerpo = respuesta.json()
    print(f"{ruta.name}: {len(cuerpo['sin_unir']['formas'])} formas, {cuerpo['formas_que_se_pisan']} se pisan, "
          f"respuesta de {len(respuesta.content) / 1e6:.1f} MB")
    _resumen("sin unir", cuerpo["sin_unir"])
    if cuerpo["unida"] is not None:
        _resumen("unida   ", cuerpo["unida"])


if __name__ == "__main__":
    main()
