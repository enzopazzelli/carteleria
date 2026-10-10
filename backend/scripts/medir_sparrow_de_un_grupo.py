"""Anida con Sparrow un grupo ya cargado, varias veces, con y sin la etapa
de vaciar chapas, y muestra planchas, aprovechamiento y tiempo.

Es la medición del criterio de éxito de `docs/plan/A6-reparto-por-chapa/`.
Corre por el mismo camino que la app (`anidar_sparrow`: worker aparte,
tiempo máximo y validación) y no guarda nada.

**Usar siempre una copia de la base**, con la máquina libre:

    set CARTELERIA_DATOS=<carpeta con una copia de carteleria.db>
    python scripts/medir_sparrow_de_un_grupo.py --grupo 1 --corridas 3
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session  # noqa: E402

from app import config  # noqa: E402
from app.api.rutas_nesting import _datos_para_anidar, _geometrias_del_grupo  # noqa: E402
from app.modelos.base import crear_motor  # noqa: E402
from app.modelos.trabajo import GrupoDeCorte  # noqa: E402
from app.services.nesting.aprovechamiento import calcular_aprovechamiento  # noqa: E402
from app.services.nesting.sparrow import OpcionesSparrow, anidar_sparrow  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--grupo", type=int, required=True)
    parser.add_argument("--corridas", type=int, default=3)
    parser.add_argument("--segundos-por-busqueda", type=int, default=OpcionesSparrow.segundos_por_busqueda)
    parser.add_argument("--tiempo-maximo-s", type=int, default=OpcionesSparrow.tiempo_maximo_s)
    args = parser.parse_args()

    print(f"Datos: {config.DIRECTORIO_DATOS}")
    with Session(crear_motor()) as sesion:
        grupo = sesion.get(GrupoDeCorte, args.grupo)
        if grupo is None:
            sys.exit(f"No existe el grupo {args.grupo}.")
        plancha, params, piezas = _datos_para_anidar(sesion, grupo)
        geometrias = _geometrias_del_grupo(grupo)

    print(f"Grupo «{grupo.nombre}»: {sum(p.cantidad for p in piezas)} piezas, chapa {plancha.ancho_mm} x {plancha.alto_mm}")
    for vaciar in (False, True):
        for corrida in range(args.corridas):
            opciones = OpcionesSparrow(
                semilla=OpcionesSparrow.semilla + corrida,
                segundos_por_busqueda=args.segundos_por_busqueda,
                tiempo_maximo_s=args.tiempo_maximo_s,
                vaciar_chapas=vaciar,
            )
            inicio = time.monotonic()
            resultado = anidar_sparrow(piezas, geometrias, plancha, params, opciones)
            aprovechamiento = calcular_aprovechamiento(resultado, plancha, geometrias).porcentaje_aprovechamiento
            print(
                f"vaciar chapas: {'sí' if vaciar else 'no'} | corrida {corrida + 1} | "
                f"{resultado.planchas_usadas} planchas | {aprovechamiento:.1f} % | {time.monotonic() - inicio:.0f} s"
            )


if __name__ == "__main__":
    main()
