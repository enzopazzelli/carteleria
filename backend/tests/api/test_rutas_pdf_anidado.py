"""El pedido del PDF del diseño anidado (A15, `docs/plan/A15-disenio-anidado-en-pdf/diseno.md §5.5`)."""
from __future__ import annotations

import io
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pypdf import PdfReader
from sqlalchemy.orm import Session

from .ayudas import mensaje_de
from .test_rutas_ajuste import _esperar_estado, _trabajo_anidado_con_dos_piezas, cliente  # noqa: F401

from app.api.rutas_pdf_anidado import anillos_en_chapa, datos_del_pdf, nombre_de_archivo_pdf
from app.api.rutas_trabajos import _ruta_del_fondo
from app.modelos import Trabajo
from app.services.nesting.hojas_pdf import nombre_corto
from app.services.nesting.models import PosicionPieza


def _texto(contenido: bytes) -> str:
    return "\n".join(pagina.extract_text() for pagina in PdfReader(io.BytesIO(contenido)).pages)


def test_devuelve_el_pdf_del_trabajo(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)

    r = cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado")

    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert re.search(r'filename="Prueba-anidado-\d{4}-\d{2}-\d{2}\.pdf"', r.headers["content-disposition"])
    lector = PdfReader(io.BytesIO(r.content))
    assert len(lector.pages) == 2
    assert "Chapa 1" in lector.pages[1].extract_text()


def test_sin_anidado_terminado_da_409(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "Sin anidar"}).json()

    r = cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado")

    assert r.status_code == 409
    assert mensaje_de(r) == "Este trabajo todavía no tiene ningún anidado terminado: anidalo en la pestaña Anidado."


def test_un_trabajo_que_no_existe_da_404(cliente):
    assert cliente.get("/trabajos/999/pdf-anidado").status_code == 404


def test_lo_movido_a_mano_sale_en_su_lugar_nuevo(cliente, tmp_path):
    trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    colocacion = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]
    assert cliente.patch(f"/colocaciones/{colocacion['id']}",
                         json={"centro_x_mm": "900", "centro_y_mm": "900"}).json()["valida"]
    piezas = {p["id"]: p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()}

    with Session(cliente.motor) as sesion:
        datos = datos_del_pdf(sesion, sesion.get(Trabajo, trabajo["id"]), datetime(2026, 10, 25))

    nombre = nombre_corto(piezas[colocacion["pieza_id"]]["id_origen"])
    movida = next(p for c in datos.bloques[0].chapas for p in c.piezas if p.nombre == nombre)
    xs, ys = [x for x, _ in movida.anillos[0]], [y for _, y in movida.anillos[0]]
    assert ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2) == pytest.approx((900, 900))


_VENCIDO = "Las piezas de este grupo cambiaron después de este anidado: anidá de nuevo antes de presupuestar."


def test_el_anidado_vencido_lo_avisa_en_la_hoja_del_disenio(cliente, tmp_path):
    """Sigue en el PDF, para ver qué se anidó, pero no se cobra (A17)."""
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    assert _VENCIDO not in _texto(cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado").content)
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    cliente.patch(f"/piezas/{pieza['id']}", json={"cantidad": 2})

    texto = _texto(cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado").content)

    assert _VENCIDO in texto.replace("\n", " ")


def test_si_se_cobra_otro_que_el_elegido_lo_dice(cliente, tmp_path):
    """El elegido quedó vencido y hay uno más nuevo al día (Enzo, A17,
    opción a): el PDF decía de ese «el más reciente, sin elegir para el
    presupuesto», aunque es el que se cobra (revisión de la tanda 7)."""
    trabajo, grupo, elegido = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    cliente.post(f"/ejecuciones/{elegido}/marcar-definitiva")
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    cliente.patch(f"/piezas/{pieza['id']}", json={"cantidad": 2})
    nuevo = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, nuevo)

    texto = _texto(cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado").content).replace("\n", " ")

    assert (f"anidado #{nuevo}, el que se usa para el presupuesto: el elegido (#{elegido}) "
            "es de antes de que cambiaran las piezas") in texto
    assert _VENCIDO not in texto


def test_un_grupo_sin_anidar_va_al_pie(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G2"})

    texto = _texto(cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado").content)

    assert "Sin anidar" in texto and "G2" in texto


def test_un_nombre_con_acentos_baja_con_nombre_de_archivo_simple(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    with Session(cliente.motor) as sesion:
        sesion.get(Trabajo, trabajo["id"]).nombre = "Cartel «Peña» 2"
        sesion.commit()

    r = cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado")

    assert r.status_code == 200
    assert re.search(r'filename="Cartel-Pena-2-anidado-\d{4}-\d{2}-\d{2}\.pdf"', r.headers["content-disposition"])
    assert "Cartel «Peña» 2" in _texto(r.content)


def test_sin_el_dxf_guardado_sale_igual(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    with Session(cliente.motor) as sesion:
        guardado = sesion.get(Trabajo, trabajo["id"])
        Path(guardado.archivo_guardado).unlink()
        _ruta_del_fondo(guardado).unlink(missing_ok=True)

    r = cliente.get(f"/trabajos/{trabajo['id']}/pdf-anidado")

    assert r.status_code == 200
    assert "Chapa 1" in _texto(r.content)


def test_una_pieza_sin_contorno_va_como_su_rectangulo():
    posicion = PosicionPieza(pieza_id="5#0", plancha_indice=0, x_mm=Decimal(10), y_mm=Decimal(20),
                             ancho_colocado_mm=Decimal(100), alto_colocado_mm=Decimal(50), rotada_90=False)

    assert anillos_en_chapa(posicion, {}) == [[(10, 20), (110, 20), (110, 70), (10, 70)]]


def test_nombre_de_archivo_pdf():
    assert nombre_de_archivo_pdf("Cartel «Peña» 2", date(2026, 10, 25)) == "Cartel-Pena-2-anidado-2026-10-25.pdf"
    assert nombre_de_archivo_pdf("«»", date(2026, 10, 25)) == "trabajo-anidado-2026-10-25.pdf"
