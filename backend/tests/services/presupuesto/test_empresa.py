"""Los datos de la empresa para el PDF: el logo y los datos de contacto que se
leen de una carpeta fuera de git (A22, `docs/plan/A22-pdf-con-la-marca/diseno.md`)."""
from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from app.services.presupuesto.empresa import Empresa, cargar_empresa, lineas_del_pie

DATOS = {
    "nombre": "Anibal Dumit Megacarteles",
    "direccion": "Andres Chazarreta y Alejandro Aguado · Santiago del Estero · 4200",
    "whatsapp": "+54 9 385 471-8352",
    "mail": "anibaldumitmegacarteles@gmail.com",
    "web": "anibaldumit.com",
    "instagram": "anibaldumit.mc",
}


def _logo(carpeta, *, lienzo=(200, 200), contenido=(40, 60, 160, 120)):
    """Un logo con fondo transparente y algo de color adentro."""
    imagen = Image.new("RGBA", lienzo, (0, 0, 0, 0))
    imagen.paste((255, 93, 0, 255), contenido)
    imagen.save(carpeta / "logo.png")


def test_sin_la_carpeta_no_hay_empresa_y_no_falla(tmp_path):
    empresa = cargar_empresa(tmp_path / "no-existe")
    assert empresa == Empresa()
    assert empresa.logo is None
    assert lineas_del_pie(empresa) == []


def test_lee_los_datos_de_contacto(tmp_path):
    (tmp_path / "datos.json").write_text(json.dumps(DATOS), encoding="utf-8")
    empresa = cargar_empresa(tmp_path)
    assert empresa.nombre == "Anibal Dumit Megacarteles"
    assert empresa.whatsapp == "+54 9 385 471-8352"
    assert empresa.instagram == "anibaldumit.mc"
    assert empresa.cuit is None and empresa.condiciones is None


def test_un_dato_vacio_o_que_no_es_texto_se_ignora_y_las_claves_de_mas_tambien(tmp_path):
    datos = {**DATOS, "mail": "   ", "web": ["x"], "cuit": "", "color_favorito": "rojo"}
    (tmp_path / "datos.json").write_text(json.dumps(datos), encoding="utf-8")
    empresa = cargar_empresa(tmp_path)
    assert empresa.mail is None and empresa.web is None and empresa.cuit is None
    assert empresa.nombre == "Anibal Dumit Megacarteles"


@pytest.mark.parametrize("contenido", ["esto no es json", "[1, 2, 3]", ""])
def test_un_archivo_de_datos_roto_no_rompe_el_pdf(tmp_path, contenido):
    (tmp_path / "datos.json").write_text(contenido, encoding="utf-8")
    assert cargar_empresa(tmp_path) == Empresa()


def test_un_archivo_guardado_con_el_bloc_de_notas_de_windows_se_lee(tmp_path):
    # El Bloc de notas puede guardar con una marca invisible al principio (BOM).
    (tmp_path / "datos.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(DATOS).encode("utf-8"))
    assert cargar_empresa(tmp_path).nombre == "Anibal Dumit Megacarteles"


def test_un_telefono_o_un_cuit_escritos_como_numero_valen_igual(tmp_path):
    (tmp_path / "datos.json").write_text(json.dumps({**DATOS, "whatsapp": 5493854718352, "cuit": 20123456789}), encoding="utf-8")
    empresa = cargar_empresa(tmp_path)
    assert (empresa.whatsapp, empresa.cuit) == ("5493854718352", "20123456789")


def test_un_dato_que_no_es_texto_ni_numero_se_ignora_y_queda_en_el_registro(tmp_path, caplog):
    (tmp_path / "datos.json").write_text(json.dumps({**DATOS, "mail": ["a@b.com"], "web": True}), encoding="utf-8")
    with caplog.at_level("WARNING"):
        empresa = cargar_empresa(tmp_path)
    assert empresa.mail is None and empresa.web is None
    assert "«mail»" in caplog.text and "«web»" in caplog.text


@pytest.mark.parametrize(("escrito", "esperado"), [("@anibaldumit.mc", "anibaldumit.mc"), ("anibaldumit.mc", "anibaldumit.mc"), ("@", None), ("  @ ", None)])
def test_el_instagram_se_guarda_sin_arroba_y_uno_vacio_no_cuenta(tmp_path, escrito, esperado):
    (tmp_path / "datos.json").write_text(json.dumps({**DATOS, "instagram": escrito}), encoding="utf-8")
    assert cargar_empresa(tmp_path).instagram == esperado


def test_un_logo_con_fondo_blanco_y_sin_transparencia_tambien_se_recorta(tmp_path):
    imagen = Image.new("RGB", (200, 200), (255, 255, 255))
    imagen.paste((255, 93, 0), (40, 60, 160, 120))
    imagen.save(tmp_path / "logo.png")
    assert Image.open(io.BytesIO(cargar_empresa(tmp_path).logo)).size == (120, 60)


def test_un_logo_que_la_biblioteca_rechaza_por_enorme_no_rompe_el_pdf(tmp_path, monkeypatch):
    _logo(tmp_path)
    (tmp_path / "datos.json").write_text(json.dumps(DATOS), encoding="utf-8")

    def _bomba(*_args, **_kwargs):
        raise Image.DecompressionBombError("demasiado grande")

    monkeypatch.setattr(Image, "open", _bomba)
    empresa = cargar_empresa(tmp_path)
    assert empresa.logo is None and empresa.nombre == "Anibal Dumit Megacarteles"


def test_el_logo_se_recorta_al_contenido_y_dice_su_proporcion(tmp_path):
    _logo(tmp_path, lienzo=(200, 200), contenido=(40, 60, 160, 120))
    empresa = cargar_empresa(tmp_path)
    assert empresa.logo is not None
    imagen = Image.open(io.BytesIO(empresa.logo))
    assert imagen.size == (120, 60)
    assert empresa.proporcion_del_logo == pytest.approx(2.0)


def test_un_logo_que_no_es_una_imagen_se_ignora(tmp_path):
    (tmp_path / "logo.png").write_bytes(b"no soy un png")
    (tmp_path / "datos.json").write_text(json.dumps(DATOS), encoding="utf-8")
    empresa = cargar_empresa(tmp_path)
    assert empresa.logo is None
    assert empresa.nombre == "Anibal Dumit Megacarteles"


def test_el_pie_lleva_solo_lo_que_hay(tmp_path):
    (tmp_path / "datos.json").write_text(json.dumps(DATOS), encoding="utf-8")
    assert lineas_del_pie(cargar_empresa(tmp_path)) == [
        "Andres Chazarreta y Alejandro Aguado · Santiago del Estero · 4200",
        "WhatsApp +54 9 385 471-8352  ·  anibaldumitmegacarteles@gmail.com",
        "anibaldumit.com  ·  Instagram @anibaldumit.mc",
    ]
    solo_mail = Empresa(mail="a@b.com")
    assert lineas_del_pie(solo_mail) == ["a@b.com"]


def test_el_cuit_va_con_el_nombre_y_las_condiciones_se_guardan(tmp_path):
    datos = {**DATOS, "cuit": "20-12345678-9", "condiciones": "Pago 50 % al aprobar."}
    (tmp_path / "datos.json").write_text(json.dumps(datos), encoding="utf-8")
    empresa = cargar_empresa(tmp_path)
    assert empresa.cuit == "20-12345678-9"
    assert empresa.condiciones == "Pago 50 % al aprobar."
    assert "CUIT 20-12345678-9" in empresa.titulo_del_pie()
