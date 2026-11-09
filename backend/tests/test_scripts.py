"""Las herramientas de `scripts/` que leen datos reales. El visor
interactivo (`servidor_visor.py`) se borró el 2026-10-28 (A17): lo
reemplaza la pestaña Chapas."""
import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def test_los_scripts_leen_el_catalogo_que_arma_hoy_el_extractor(tmp_path):
    """Desde el 2026-09-22 `extraer_catalogo_chapa_xlsx.py` escribe el
    precio como `costo_unidad_venta` con su `unidad_venta`, y los scripts
    seguían buscando `precio_referencia_m2` (A10). Un catálogo de antes se
    sigue leyendo."""
    import json
    from decimal import Decimal as D

    spec = importlib.util.spec_from_file_location("_datos_reales", SCRIPTS / "_datos_reales.py")
    datos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(datos)
    base = {"material": "CHAPA NEGRA", "calibre": 22, "espesor_mm": None, "moneda": "ARS"}
    catalogo = {"formatos": [
        {**base, "codigo": "CHA1", "ancho_mm": "1000.00", "alto_mm": "2000.00", "costo_unidad_venta": 10000, "unidad_venta": "M2"},
        {**base, "codigo": "CHA2", "ancho_mm": "1220.00", "alto_mm": "2440.00", "costo_unidad_venta": None, "unidad_venta": "M2"},
        {**base, "codigo": "CHA3", "ancho_mm": "1000.00", "alto_mm": "1000.00", "costo_unidad_venta": 500, "unidad_venta": "UN"},
        {**base, "codigo": "VIEJO", "ancho_mm": "500.00", "alto_mm": "500.00", "precio_referencia_m2": 4000},
    ], "sin_parsear": [], "advertencias": []}
    ruta = tmp_path / "catalogo.json"
    ruta.write_text(json.dumps(catalogo), encoding="utf-8")

    opciones, _ = datos.opciones_desde_catalogo(ruta)
    assert [o.precio_por_plancha for o in opciones] == [D(20000), D(1000)]
    precios = {f["codigo"]: f["precio_referencia_m2"] for f in datos.formatos_del_catalogo(ruta)}
    assert precios == {"CHA1": 10000, "CHA2": None, "CHA3": None, "VIEJO": 4000}


# --- Los guiones para probar sin tocar la base real (A24 y A25) ---------------


def _cargar(nombre):
    spec = importlib.util.spec_from_file_location(nombre, SCRIPTS / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _base_con_un_trabajo(carpeta: Path, version: str | None = "abc123") -> Path:
    """Una base mínima con un trabajo y su DXF, como las que deja la app."""
    import sqlite3

    (carpeta / "archivos").mkdir(parents=True)
    dxf = carpeta / "archivos" / "trabajo-1.dxf"
    dxf.write_bytes(b"dxf de prueba")
    conexion = sqlite3.connect(carpeta / "carteleria.db")
    conexion.execute("create table trabajos (id integer primary key, nombre text, archivo_guardado text)")
    conexion.execute("insert into trabajos values (1, 'Cartel', ?)", (str(dxf),))
    if version is not None:
        conexion.execute("create table alembic_version (version_num text)")
        conexion.execute("insert into alembic_version values (?)", (version,))
    conexion.commit()
    conexion.close()
    return dxf


def _archivo_guardado(base: Path) -> str:
    import sqlite3

    conexion = sqlite3.connect(base)
    try:
        return conexion.execute("select archivo_guardado from trabajos where id = 1").fetchone()[0]
    finally:
        conexion.close()


def test_copiar_base_deja_el_origen_como_estaba_y_la_copia_apunta_a_sus_propios_dxf(tmp_path):
    copiar = _cargar("copiar_base")
    origen, copia = tmp_path / "origen", tmp_path / "copia"
    dxf_del_origen = _base_con_un_trabajo(origen)

    resultado = copiar.copiar_base(origen, copia)

    assert resultado == {"trabajos": [(1, "Cartel")], "version": "abc123"}
    assert _archivo_guardado(copia / "carteleria.db") == str(copia / "archivos" / "trabajo-1.dxf")
    assert (copia / "archivos" / "trabajo-1.dxf").read_bytes() == b"dxf de prueba"
    # Lo que importa: la base de origen no cambió, ni su DXF.
    assert _archivo_guardado(origen / "carteleria.db") == str(dxf_del_origen)
    assert dxf_del_origen.read_bytes() == b"dxf de prueba"


def test_copiar_base_pisa_una_copia_anterior(tmp_path):
    copiar = _cargar("copiar_base")
    origen, copia = tmp_path / "origen", tmp_path / "copia"
    _base_con_un_trabajo(origen)
    copiar.copiar_base(origen, copia)
    (copia / "archivos" / "sobra.dxf").write_bytes(b"de la vez anterior")

    copiar.copiar_base(origen, copia)

    assert not (copia / "archivos" / "sobra.dxf").exists()


def test_copiar_base_se_niega_a_pisar_el_origen(tmp_path):
    import pytest

    copiar = _cargar("copiar_base")
    origen = tmp_path / "origen"
    _base_con_un_trabajo(origen)

    for peligrosa in (origen, origen / "archivos", tmp_path):  # el origen, sus DXF o algo que lo contiene
        with pytest.raises(ValueError):
            copiar.copiar_base(origen, peligrosa)
    # Y el origen sigue entero.
    assert (origen / "carteleria.db").exists() and (origen / "archivos" / "trabajo-1.dxf").exists()


def test_copiar_base_puede_dejar_la_copia_adentro_de_la_carpeta_de_origen(tmp_path):
    # Es lo que hace por defecto: la base real está en `local/` y la copia en `local/copias/<nombre>`.
    copiar = _cargar("copiar_base")
    origen = tmp_path / "local"
    _base_con_un_trabajo(origen)

    copiar.copiar_base(origen, origen / "copias" / "prueba")

    assert (origen / "copias" / "prueba" / "carteleria.db").exists()
    assert (origen / "carteleria.db").exists()


def test_copiar_base_no_borra_una_carpeta_que_no_es_una_copia(tmp_path):
    import pytest

    copiar = _cargar("copiar_base")
    origen, ajena = tmp_path / "origen", tmp_path / "mis-cosas"
    _base_con_un_trabajo(origen)
    ajena.mkdir()
    (ajena / "importante.txt").write_text("no se toca", encoding="utf-8")

    with pytest.raises(ValueError):
        copiar.copiar_base(origen, ajena)
    assert (ajena / "importante.txt").read_text(encoding="utf-8") == "no se toca"


def test_copiar_base_funciona_con_una_base_sin_version_de_migracion(tmp_path):
    copiar = _cargar("copiar_base")
    origen = tmp_path / "origen"
    _base_con_un_trabajo(origen, version=None)

    assert copiar.copiar_base(origen, tmp_path / "copia")["version"] is None


def _dxf_de_dos_rectangulos(ruta: Path) -> None:
    import ezdxf

    documento = ezdxf.new()
    msp = documento.modelspace()
    msp.add_lwpolyline([(0, 0), (300, 0), (300, 200), (0, 200)], close=True)
    msp.add_lwpolyline([(500, 0), (640, 0), (640, 90), (500, 90)], close=True)
    documento.saveas(ruta)


def test_la_lectura_de_referencia_ve_cada_forma_y_detecta_un_cambio(tmp_path):
    import copy

    corpus = _cargar("lectura_del_corpus")
    ruta = tmp_path / "dos.dxf"
    _dxf_de_dos_rectangulos(ruta)

    antes = corpus.leer_uno(ruta, "1")

    assert len(antes["sin_unir"]) == 2
    assert {forma["rol"] for forma in antes["sin_unir"].values()} == {"se_corta"}
    assert corpus.diferencias({"dos.dxf": antes}, {"dos.dxf": antes}) == []

    cambiado = copy.deepcopy(antes)
    una_forma = next(iter(cambiado["sin_unir"]))
    cambiado["sin_unir"][una_forma]["rol"] = "descartada"
    lineas = corpus.diferencias({"dos.dxf": antes}, {"dos.dxf": cambiado})
    assert lineas and any(una_forma in linea for linea in lineas)


def test_la_lectura_de_referencia_saltea_los_dibujos_que_no_estan(tmp_path):
    corpus = _cargar("lectura_del_corpus")
    _dxf_de_dos_rectangulos(tmp_path / "Complejo.dxf")

    lectura = corpus.leer(tmp_path)

    assert list(lectura) == ["Complejo.dxf"]  # los otros ocho del corpus no están en la carpeta
