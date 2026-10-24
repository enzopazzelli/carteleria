"""El diseño de un trabajo (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.1 y §5.2`)."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.rutas_disenio import recuperar_posiciones
from app.modelos.trabajo import Pieza, Trabajo

from .test_rutas_nesting import _material_con_formato_y_parametros, cliente  # noqa: F401
from .test_rutas_trabajos import _chapa_en_el_catalogo, _crear_trabajo, _dxf_bytes, _franja, _subir

_CAMPOS = ("disenio_x_mm", "disenio_y_mm", "disenio_angulo_grados")


def _posiciones(cliente, trabajo_id: int) -> dict[int, tuple[float, float, float] | None]:
    with Session(cliente.motor) as sesion:
        piezas = sesion.execute(select(Pieza).where(Pieza.trabajo_id == trabajo_id)).scalars()
        return {
            p.id: None if p.disenio_x_mm is None else tuple(float(getattr(p, campo)) for campo in _CAMPOS)
            for p in piezas
        }


def _como_un_trabajo_viejo(cliente, trabajo_id: int, *, prefijo: str | None = None) -> None:
    """Como quedó un trabajo cargado antes de A14: sin posiciones, y con
    `prefijo` en lugar del nombre del archivo guardado en `id_origen`."""
    with Session(cliente.motor) as sesion:
        for pieza in sesion.execute(select(Pieza).where(Pieza.trabajo_id == trabajo_id)).scalars():
            for campo in _CAMPOS:
                setattr(pieza, campo, None)
            if prefijo is not None:
                pieza.id_origen = pieza.id_origen.replace(f"trabajo-{trabajo_id}-", f"{prefijo}-", 1)
        sesion.commit()


def _recuperar(cliente, trabajo_id: int) -> None:
    with Session(cliente.motor) as sesion:
        recuperar_posiciones(sesion, sesion.get(Trabajo, trabajo_id))
        sesion.commit()


def _dos_cuadrados(msp):
    msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)
    msp.add_lwpolyline([(500, 0), (600, 0), (600, 100), (500, 100)], close=True)


def _cerca(a, b) -> bool:
    return a is not None and b is not None and a == pytest.approx(b, abs=1e-3)


# --- Recuperar dónde estaba cada pieza (§5.1) ---------------------------------


def test_recupera_la_posicion_de_un_trabajo_viejo(cliente, tmp_path):
    trabajo = _crear_trabajo(cliente)
    _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "dos.dxf", _dos_cuadrados))
    _como_un_trabajo_viejo(cliente, trabajo["id"], prefijo="logo")

    _recuperar(cliente, trabajo["id"])

    assert sorted(_posiciones(cliente, trabajo["id"]).values()) == [(0, 0, 0), (500, 0, 0)]


def test_recupera_una_pieza_unida_y_sus_huecos(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)

    def corridas(msp):
        _franja(msp, 300, 400, 1200)
        _franja(msp, 1350, 500, 1000)

    _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "franjas.dxf", corridas), unir="true")
    antes = _posiciones(cliente, trabajo["id"])
    _como_un_trabajo_viejo(cliente, trabajo["id"])

    _recuperar(cliente, trabajo["id"])

    despues = _posiciones(cliente, trabajo["id"])
    assert len(antes) == 3
    assert all(_cerca(despues[pieza_id], posicion) for pieza_id, posicion in antes.items())


def test_recupera_los_tramos_de_un_seccionado(cliente, tmp_path):
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = _crear_trabajo(cliente, "Ele")
    contenido = _dxf_bytes(
        tmp_path,
        "ele.dxf",
        lambda msp: msp.add_lwpolyline(
            [(200, 300), (1700, 300), (1700, 800), (700, 800), (700, 1300), (200, 1300)], close=True
        ),
    )
    _subir(cliente, trabajo["id"], contenido)
    original = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    respuesta = cliente.post(f"/piezas/{original['id']}/seccionado", json={
        "formato_id": formato["id"], "angulo_grados": 30, "desplazamiento_x_mm": 40, "desplazamiento_y_mm": 25,
    })
    assert respuesta.status_code == 201, respuesta.text
    antes = _posiciones(cliente, trabajo["id"])
    _como_un_trabajo_viejo(cliente, trabajo["id"], prefijo="ele")

    _recuperar(cliente, trabajo["id"])

    despues = _posiciones(cliente, trabajo["id"])
    assert len(antes) > 2
    assert all(_cerca(despues[pieza_id], posicion) for pieza_id, posicion in antes.items())


def _tres_cuadrados(msp):
    for x in (0, 500, 1000):
        msp.add_lwpolyline([(x, 0), (x + 100, 0), (x + 100, 100), (x, 100)], close=True)


# --- El pedido del diseño (§5.2) ----------------------------------------------


def test_el_disenio_trae_fondo_piezas_y_nada_sin_lugar(cliente, tmp_path):
    """El fondo es el dibujo entero, también lo que se marcó que no va; las
    piezas son las que se cargaron, cada una en su lugar."""
    trabajo = _crear_trabajo(cliente)
    _subir(
        cliente, trabajo["id"], _dxf_bytes(tmp_path, "tres.dxf", _tres_cuadrados),
        correcciones=json.dumps({f"trabajo-{trabajo['id']}-2": "no_va"}),
    )

    respuesta = cliente.get(f"/trabajos/{trabajo['id']}/disenio")

    assert respuesta.status_code == 200, respuesta.text
    disenio = respuesta.json()
    assert len(disenio["fondo"]) == 3
    assert sorted(min(x for x, _ in forma["contorno_mm"]) for forma in disenio["fondo"]) == pytest.approx([0, 500, 1000])
    assert sorted(p["x_mm"] for p in disenio["piezas"]) == pytest.approx([0, 500])
    assert disenio["cortes"] == [] and disenio["sin_lugar"] == []


def test_pedir_el_disenio_recupera_y_guarda_las_posiciones(cliente, tmp_path):
    trabajo = _crear_trabajo(cliente)
    _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "dos.dxf", _dos_cuadrados))
    _como_un_trabajo_viejo(cliente, trabajo["id"])

    disenio = cliente.get(f"/trabajos/{trabajo['id']}/disenio").json()

    assert len(disenio["piezas"]) == 2 and disenio["sin_lugar"] == []
    assert None not in _posiciones(cliente, trabajo["id"]).values()


def test_el_disenio_trae_los_cortes_de_un_seccionado(cliente, tmp_path):
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = _crear_trabajo(cliente, "Franja")
    contenido = _dxf_bytes(
        tmp_path, "franja.dxf",
        lambda msp: msp.add_lwpolyline([(300, 200), (1800, 200), (1800, 700), (300, 700)], close=True),
    )
    _subir(cliente, trabajo["id"], contenido)
    original = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    cliente.post(f"/piezas/{original['id']}/seccionado", json={
        "formato_id": formato["id"], "angulo_grados": 0, "desplazamiento_x_mm": 0, "desplazamiento_y_mm": 0,
    })

    disenio = cliente.get(f"/trabajos/{trabajo['id']}/disenio").json()

    assert original["id"] not in {p["pieza_id"] for p in disenio["piezas"]}, "la original seccionada no se pinta"
    assert len(disenio["piezas"]) == 2
    assert disenio["cortes"] and all(corte["pieza_id"] == original["id"] for corte in disenio["cortes"])
    for corte in disenio["cortes"]:
        assert all(300 - 0.01 <= x <= 1800 + 0.01 and 200 - 0.01 <= y <= 700 + 0.01 for x, y in corte["puntos"])


def test_un_trabajo_sin_dxf_lista_sus_piezas_sin_lugar(cliente):
    trabajo = _crear_trabajo(cliente)
    with Session(cliente.motor) as sesion:
        pieza = Pieza(
            trabajo_id=trabajo["id"], id_origen="a-mano", ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
            contorno_mm=[["0", "0"], ["100", "0"], ["100", "100"], ["0", "100"]], agujeros_mm=[],
        )
        sesion.add(pieza)
        sesion.commit()
        pieza_id = pieza.id

    disenio = cliente.get(f"/trabajos/{trabajo['id']}/disenio").json()

    assert disenio == {"fondo": [], "piezas": [], "cortes": [], "sin_lugar": [pieza_id]}


def test_volver_a_cargar_el_dxf_tira_el_fondo_guardado(cliente, tmp_path):
    trabajo = _crear_trabajo(cliente)
    _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "dos.dxf", _dos_cuadrados))
    assert len(cliente.get(f"/trabajos/{trabajo['id']}/disenio").json()["fondo"]) == 2

    _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "tres.dxf", _tres_cuadrados))

    assert len(cliente.get(f"/trabajos/{trabajo['id']}/disenio").json()["fondo"]) == 3


def test_borrar_el_trabajo_borra_tambien_el_fondo_guardado(cliente, tmp_path):
    from app import config

    trabajo = _crear_trabajo(cliente)
    _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "dos.dxf", _dos_cuadrados))
    cliente.get(f"/trabajos/{trabajo['id']}/disenio")
    fondo = config.DIRECTORIO_ARCHIVOS / f"trabajo-{trabajo['id']}.fondo.json"
    assert fondo.exists()

    cliente.delete(f"/trabajos/{trabajo['id']}")

    assert not fondo.exists()


def test_el_disenio_de_un_trabajo_que_no_existe_da_404(cliente):
    assert cliente.get("/trabajos/999/disenio").status_code == 404


def test_sin_el_dxf_guardado_queda_sin_posicion(cliente, tmp_path):
    trabajo = _crear_trabajo(cliente)
    _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "dos.dxf", _dos_cuadrados))
    with Session(cliente.motor) as sesion:
        Path(sesion.get(Trabajo, trabajo["id"]).archivo_guardado).unlink()
    _como_un_trabajo_viejo(cliente, trabajo["id"])

    _recuperar(cliente, trabajo["id"])

    assert set(_posiciones(cliente, trabajo["id"]).values()) == {None}
