"""La lectura de referencia de los DXF de prueba: para ver, después de cada cambio en el lector, si cambió algo.

Guarda cómo se lee hoy cada dibujo, forma por forma, y después compara. Es lo que hay que correr
antes de dar por bueno cualquier cambio en `app/services/ingesta/dxf.py` o en las uniones: el lector
decide qué es pieza y qué es agujero, y un arreglo que mejora un dibujo puede empeorar otro
(`docs/BITACORA.md`, 2026-11-09).

Lee con la misma función que `POST /trabajos/{id}/dxf/lectura` (`rutas_trabajos._leer`), sin
correcciones, y guarda las dos lecturas: tal como viene y unida. Por forma: qué es (se corta,
descartada, no va), por qué, su área, el área de cada hueco y adentro de qué pieza está. Por
archivo: los avisos de la pantalla. No usa ninguna base: las chapas son fijas.

    python -X utf8 scripts/lectura_del_corpus.py guardar    # sacar la foto, antes de tocar el lector
    python -X utf8 scripts/lectura_del_corpus.py comparar   # después: dice «sin diferencias» o lista lo que cambió

Los dibujos no están en el repositorio (`modelos/` está en `.gitignore`: son de clientes). Se buscan en
la carpeta que diga `--modelos` o la variable `CARTELERIA_MODELOS`; por defecto, `modelos/` en la raíz
del repo. Los que no estén se saltean, y se comparan solo los que haya. La foto se guarda en
`local/lectura-del-corpus.json`, que tampoco va a git.

Ojo con cuánto pesa cada dibujo: `Muestra Vectores`, `muestra 2` y `strat` son de un formato viejo, con
la cotización y las chapas dibujadas adentro. No darle peso a lo que cambie solo ese texto.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from shapely.geometry import Polygon  # noqa: E402

from app.api.rutas_trabajos import _leer  # noqa: E402
from app.services.nesting.models import Plancha  # noqa: E402

#: Archivo y escala a mm con la que se carga.
CORPUS = {
    "Complejo.dxf": "100",
    "Muestra Vectores.dxf": "100",
    "muestra 2.dxf": "100",
    "Corporeas para chapa 1,22 x 2,44.dxf": "100",
    "Parador corte conjunto.dxf": "100",
    "strat.dxf": "1",
    "carrusel.dxf": "1",
    "esqueletos.dxf": "1",
    "repisas.dxf": "1",
}
FORMATOS = [
    Plancha(ancho_mm=Decimal("1220"), alto_mm=Decimal("2440")),
    Plancha(ancho_mm=Decimal("1500"), alto_mm=Decimal("3000")),
]
REFERENCIA = BACKEND / "local" / "lectura-del-corpus.json"
#: De cada archivo y cada lectura, cuántas diferencias se muestran con detalle.
DETALLES_POR_ARCHIVO = 5


def carpeta_de_dibujos(indicada: Path | None = None) -> Path:
    return indicada or Path(os.environ.get("CARTELERIA_MODELOS") or BACKEND.parent / "modelos")


def _area(anillo) -> float:
    return Polygon([(float(x), float(y)) for x, y in anillo]).area if len(anillo) >= 3 else 0.0


def _forma(lectura, pieza) -> dict:
    huecos = sorted(round(_area(agujero)) for agujero in pieza.agujeros_mm)
    return {
        "rol": lectura.estado(pieza.id),
        "motivo": lectura.motivo(pieza.id),
        "area_mm2": round(_area(pieza.contorno_mm) - sum(_area(agujero) for agujero in pieza.agujeros_mm)),
        "huecos_mm2": huecos,
        "contenida_en": pieza.contenida_en_id,
    }


def leer_uno(ruta: Path, escala: str) -> dict:
    """Cómo se lee un dibujo, forma por forma, tal como viene y unido."""
    lecturas = _leer(ruta, Decimal(escala), None, FORMATOS, {})
    resultado = {
        "escala_a_mm": escala,
        "no_cerrados": len(lecturas.resultado.contornos_no_cerrados),
        "duplicadas_descartadas": lecturas.resultado.lineas_duplicadas_descartadas,
        "formas_que_se_pisan": lecturas.formas_que_se_pisan,
    }
    for cual, lectura in (("sin_unir", lecturas.sin_unir), ("unida", lecturas.unida)):
        if lectura is not None:
            resultado[f"{cual}/avisos"] = lectura.advertencias
            resultado[cual] = {pieza.id: _forma(lectura, pieza) for pieza in lectura.piezas}
    return resultado


def leer(modelos: Path) -> dict:
    """La lectura de todos los dibujos del corpus que estén en `modelos`."""
    corpus = {}
    for nombre, escala in CORPUS.items():
        if not (modelos / nombre).exists():
            print(f"  {nombre}: no está en {modelos}, se saltea")
            continue
        inicio = time.perf_counter()
        corpus[nombre] = leer_uno(modelos / nombre, escala)
        cuentas = []
        for cual in ("sin_unir", "unida"):
            formas = corpus[nombre].get(cual)
            if formas is not None:
                roles: dict[str, int] = {}
                for forma in formas.values():
                    roles[forma["rol"]] = roles.get(forma["rol"], 0) + 1
                cuentas.append(f"{cual} {roles}")
        print(f"  {nombre}: {'; '.join(cuentas)} ({time.perf_counter() - inicio:.1f} s)")
    return corpus


def diferencias(antes: dict, ahora: dict) -> list[str]:
    """Qué cambió entre dos lecturas, en líneas para mostrar; vacío si es lo mismo. De cada archivo se
    muestran las primeras diferencias con detalle y, al final, cuántas hubo."""
    lineas: list[str] = []
    por_archivo: dict[tuple[str, str], int] = {}
    for nombre in ahora:
        viejo, nuevo = antes.get(nombre, {}), ahora[nombre]
        for clave in sorted(set(viejo) | set(nuevo)):
            if isinstance(nuevo.get(clave), dict) or isinstance(viejo.get(clave), dict):
                viejas, nuevas = viejo.get(clave) or {}, nuevo.get(clave) or {}
                for forma in sorted(set(viejas) | set(nuevas)):
                    if viejas.get(forma) != nuevas.get(forma):
                        cuantas = por_archivo[(nombre, clave)] = por_archivo.get((nombre, clave), 0) + 1
                        if cuantas <= DETALLES_POR_ARCHIVO:
                            lineas.append(f"  {nombre} {clave} {forma}: antes {viejas.get(forma)}, ahora {nuevas.get(forma)}")
            elif viejo.get(clave) != nuevo.get(clave):
                por_archivo[(nombre, clave)] = 1
                lineas.append(f"  {nombre} {clave}: antes {viejo.get(clave)}, ahora {nuevo.get(clave)}")
    lineas += [f"  {nombre} {clave}: {cuantas} diferencia(s)" for (nombre, clave), cuantas in por_archivo.items()]
    return lineas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analizador.add_argument("accion", choices=["guardar", "comparar"])
    analizador.add_argument("--modelos", type=Path, help="carpeta con los dibujos (por defecto CARTELERIA_MODELOS o modelos/)")
    argumentos = analizador.parse_args(argv)

    modelos = carpeta_de_dibujos(argumentos.modelos)
    if argumentos.accion == "guardar":
        lectura = leer(modelos)
        if not lectura:
            print(f"No encontré ningún dibujo del corpus en {modelos}.", file=sys.stderr)
            return 1
        REFERENCIA.parent.mkdir(parents=True, exist_ok=True)
        REFERENCIA.write_text(json.dumps(lectura, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
        print("guardada en", REFERENCIA)
        return 0

    if not REFERENCIA.exists():
        print(f"No hay foto para comparar ({REFERENCIA}): primero, «guardar».", file=sys.stderr)
        return 1
    lineas = diferencias(json.loads(REFERENCIA.read_text(encoding="utf-8")), leer(modelos))
    print("\n".join(lineas) if lineas else "sin diferencias")
    return 1 if lineas else 0


if __name__ == "__main__":
    sys.exit(main())
