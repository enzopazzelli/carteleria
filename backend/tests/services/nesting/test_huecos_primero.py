"""Meter piezas en huecos antes de acomodar (A10): con cada pieza en su
propio marco, sin chapa todavía."""
from shapely import affinity
from shapely.geometry import Polygon

from app.services.nesting.huecos_primero import Adentro, expandir, meter_en_huecos

CUARTOS = [0, 90, 180, 270]


def cuadrado(lado, x=0, y=0):
    return rectangulo(lado, lado, x, y)


def rectangulo(ancho, alto, x=0, y=0):
    return [(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)]


def item(id, shell, holes=()):
    return {"id": id, "shell": shell, "holes": [list(h) for h in holes]}


def colocado(pieza, adentro):
    """El polígono de `pieza` donde lo dejó `adentro`, en el marco de su contenedora."""
    return affinity.translate(
        affinity.rotate(Polygon(pieza["shell"]), adentro.rotation, origin=(0, 0)), adentro.tx, adentro.ty
    )


def aro(id="aro#0", lado=100, hueco=60):
    borde = (lado - hueco) / 2
    return item(id, cuadrado(lado), [cuadrado(hueco, borde, borde)])


def test_un_cuadrado_entra_en_el_hueco_de_un_aro():
    chico = item("chico#0", cuadrado(30))
    adentro = meter_en_huecos([aro(), chico], 2, CUARTOS, 100)
    assert [(a.id, a.contenedora) for a in adentro] == [("chico#0", "aro#0")]
    assert Polygon(cuadrado(60, 20, 20)).buffer(-2).contains(colocado(chico, adentro[0]))


def test_lo_que_no_entra_queda_afuera():
    # 57 + 2 de cada lado contra la pared son 61: no entra en 60.
    assert meter_en_huecos([aro(), item("chico#0", cuadrado(57))], 2, CUARTOS, 100) == []


def test_un_hueco_mas_chico_que_el_minimo_no_se_llena():
    # Un hueco de 9 × 9 (81 mm²) y una pieza de 5 que entra con 1 de cada lado.
    piezas = [aro(lado=50, hueco=9), item("chico#0", cuadrado(5))]
    assert meter_en_huecos(piezas, 1, CUARTOS, 100) == []
    assert len(meter_en_huecos(piezas, 1, CUARTOS, 50)) == 1


def test_varias_piezas_en_el_mismo_hueco_guardan_la_separacion():
    chicos = [item(f"chico#{n}", cuadrado(20)) for n in range(4)]
    adentro = meter_en_huecos([aro(lado=140, hueco=100), *chicos], 2, CUARTOS, 100)
    assert sorted(a.id for a in adentro) == sorted(c["id"] for c in chicos)
    por_id = {c["id"]: c for c in chicos}
    puestos = [colocado(por_id[a.id], a) for a in adentro]
    hueco = Polygon(cuadrado(100, 20, 20))
    for i, uno in enumerate(puestos):
        assert hueco.buffer(-2 + 1e-6).contains(uno)
        for otro in puestos[i + 1:]:
            assert uno.distance(otro) >= 2 - 1e-6


def test_con_veta_lo_de_adentro_queda_a_0_o_180():
    # El hueco es apaisado (60 × 30): la pieza de 20 × 40 solo entra acostada.
    contenedora = item("aro#0", cuadrado(100), [rectangulo(60, 30, 20, 35)])
    parada = item("chico#0", rectangulo(20, 40))
    assert meter_en_huecos([contenedora, parada], 2, [0, 180], 100) == []
    acostada = meter_en_huecos([contenedora, parada], 2, CUARTOS, 100)
    assert len(acostada) == 1 and acostada[0].rotation % 180 == 90
    echada = item("chico#0", rectangulo(40, 20))
    con_veta = meter_en_huecos([contenedora, echada], 2, [0, 180], 100)
    assert len(con_veta) == 1 and con_veta[0].rotation % 180 == 0


def hueco_inclinado():
    """Un aro con un hueco de 80 × 20 inclinado 30°, y una varilla de 60 × 10
    que solo entra inclinada como él."""
    inclinado = affinity.rotate(Polygon(rectangulo(80, 20, 60, 90)), 30, origin="center")
    return item("aro#0", cuadrado(200), [list(inclinado.exterior.coords)[:-1]]), item("varilla#0", rectangulo(60, 10))


def test_sin_giro_libre_lo_de_adentro_gira_de_a_cuartos():
    contenedora, varilla = hueco_inclinado()
    assert meter_en_huecos([contenedora, varilla], 2, CUARTOS, 100) == []


def test_con_giro_libre_prueba_el_angulo_del_hueco():
    contenedora, varilla = hueco_inclinado()
    adentro = meter_en_huecos([contenedora, varilla], 2, None, 100)
    assert len(adentro) == 1
    assert round(adentro[0].rotation % 180) == 30


def tres_niveles():
    # El hueco de la grande deja lugar solo para la mediana: la chica no
    # entra al lado, y va en el hueco de la mediana.
    grande = item("grande#0", cuadrado(230), [cuadrado(130, 50, 50)])
    mediana = item("mediana#0", cuadrado(120), [cuadrado(60, 30, 30)])
    chica = item("chica#0", cuadrado(30))
    return grande, mediana, chica


def test_pieza_adentro_de_pieza_adentro_de_pieza():
    adentro = meter_en_huecos(list(tres_niveles()), 2, CUARTOS, 100)
    assert [(a.id, a.contenedora) for a in adentro] == [("mediana#0", "grande#0"), ("chica#0", "mediana#0")]


def test_dos_copias_con_hueco_y_una_sola_chica():
    adentro = meter_en_huecos([aro("aro#0"), aro("aro#1"), item("chico#0", cuadrado(30))], 2, CUARTOS, 100)
    assert [a.id for a in adentro] == ["chico#0"]


def test_huecos_que_se_pisan_se_usan_ya_unidos():
    # Dos huecos de 80 × 80 encimados forman uno de 120 × 80; la pieza de
    # 100 × 30 no entra en ninguno de los dos solo, pero sí en la unión.
    contenedora = item("aro#0", cuadrado(200), [cuadrado(80, 20, 20), cuadrado(80, 60, 20)])
    adentro = meter_en_huecos([contenedora, item("largo#0", rectangulo(100, 30))], 2, CUARTOS, 100)
    assert [a.id for a in adentro] == ["largo#0"]


def test_avisa_cuantos_huecos_lleva():
    avances = []
    meter_en_huecos([aro("aro#0"), aro("aro#1"), item("chico#0", cuadrado(30))], 2, CUARTOS, 100,
                    al_avanzar=lambda hechos, total: avances.append((hechos, total)))
    assert avances == [(1, 2), (2, 2)]


def test_deja_de_llenar_cuando_seguir_dice_que_no():
    assert meter_en_huecos([aro(), item("chico#0", cuadrado(30))], 2, CUARTOS, 100, seguir=lambda: False) == []


def material_colocado(pieza, colocacion):
    poligono = Polygon(pieza["shell"], pieza["holes"])
    return affinity.translate(
        affinity.rotate(poligono, colocacion["rotation"], origin=(0, 0)), colocacion["tx"], colocacion["ty"]
    )


def test_expandir_pone_lo_de_adentro_donde_quedo_su_bloque():
    contenedora, chico = aro(), item("chico#0", cuadrado(30))
    bloque = {"id": "aro#0", "rotation": 90, "tx": 500, "ty": 300, "sheet": 1}
    expandidas = expandir([bloque], [Adentro("chico#0", "aro#0", 0, 35, 35)])
    assert expandidas[0] == bloque
    puesto = expandidas[1]
    assert puesto["id"] == "chico#0" and puesto["rotation"] == 90 and puesto["sheet"] == 1
    hueco = Polygon(material_colocado(contenedora, bloque).interiors[0])
    assert hueco.contains(material_colocado(chico, puesto))


def test_expandir_resuelve_varios_niveles():
    grande, mediana, chica = tres_niveles()
    adentro = meter_en_huecos([grande, mediana, chica], 2, CUARTOS, 100)
    expandidas = expandir([{"id": "grande#0", "rotation": 37, "tx": 1000, "ty": 50, "sheet": 0}], adentro)
    por_id = {c["id"]: c for c in expandidas}
    hueco_de_la_mediana = Polygon(material_colocado(mediana, por_id["mediana#0"]).interiors[0])
    assert hueco_de_la_mediana.buffer(-2 + 1e-6).contains(material_colocado(chica, por_id["chica#0"]))


# --- La búsqueda por casillas (A13) -----------------------------------------


def test_cuatro_cuadrados_entran_uno_por_esquina():
    """Hoy el primero iba al centro del hueco y ya no entraba ninguno más."""
    chicos = [item(f"chico#{n}", cuadrado(40)) for n in range(4)]
    adentro = meter_en_huecos([aro(lado=140, hueco=100), *chicos], 2, CUARTOS, 100)
    assert sorted(a.id for a in adentro) == sorted(c["id"] for c in chicos)
    por_id = {c["id"]: c for c in chicos}
    puestos = [colocado(por_id[a.id], a) for a in adentro]
    hueco = Polygon(cuadrado(100, 20, 20))
    for i, uno in enumerate(puestos):
        assert hueco.buffer(-2 + 1e-6).contains(uno)
        for otro in puestos[i + 1:]:
            assert uno.distance(otro) >= 2 - 1e-6


def ele_en_un_hueco_en_ele():
    """Un hueco en «L» con la esquina abajo a la izquierda, y una pieza en «L»
    más chica con la esquina arriba a la derecha: solo entra dada vuelta."""
    hueco = Polygon(rectangulo(100, 30)).union(Polygon(rectangulo(30, 100)))
    contenedora = item("aro#0", cuadrado(140), [list(affinity.translate(hueco, 20, 20).exterior.coords)[:-1]])
    pieza = Polygon(rectangulo(70, 20, 0, 50)).union(Polygon(rectangulo(20, 70, 50, 0)))
    return contenedora, item("ele#0", list(pieza.exterior.coords)[:-1])


def test_una_ele_que_solo_entra_dada_vuelta():
    contenedora, ele = ele_en_un_hueco_en_ele()
    adentro = meter_en_huecos([contenedora, ele], 2, None, 100)
    assert len(adentro) == 1 and round(adentro[0].rotation) % 360 == 180
    assert meter_en_huecos([contenedora, ele], 2, [0], 100) == []


def test_si_no_puede_entrar_ni_un_circulo_no_arma_cuadriculas(monkeypatch):
    from app.services.nesting import huecos_primero
    llamadas = []
    original = getattr(huecos_primero, "_mascara", None)

    def contar(*args, **kwargs):
        llamadas.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(huecos_primero, "_mascara", contar, raising=False)
    assert meter_en_huecos([aro(), item("chico#0", cuadrado(57))], 2, CUARTOS, 100) == []
    assert llamadas == []


def test_corta_adentro_de_un_hueco_cuando_seguir_dice_que_no():
    """`seguir` se consulta antes de cada hueco y antes de cada pieza que se
    intenta poner: un hueco grande no se pasa del tiempo (A13)."""
    respuestas = iter([True, True])
    chicos = [item(f"chico#{n}", cuadrado(40)) for n in range(4)]
    adentro = meter_en_huecos([aro(lado=140, hueco=100), *chicos], 2, CUARTOS, 100,
                              seguir=lambda: next(respuestas, False))
    assert len(adentro) == 1


def test_sin_huecos_da_lo_mismo_con_y_sin_la_casilla():
    """Con piezas sin agujeros no hay nada que meter: marcar «Aprovechar
    huecos» no cambia el anidado (A17). Con un solo hilo y la misma semilla,
    Sparrow da siempre lo mismo."""
    from decimal import Decimal as D

    from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida
    from app.services.nesting.sparrow import OpcionesSparrow, anidar_sparrow
    from app.services.nesting.validacion_manual import GeometriaPieza

    medidas = {"1": (300, 200, 3), "2": (150, 400, 2), "3": (90, 90, 4)}
    piezas = [Pieza(id_, D(ancho), D(alto), cantidad) for id_, (ancho, alto, cantidad) in medidas.items()]
    geometrias = {
        id_: GeometriaPieza(D(ancho), D(alto), [(D(x), D(y)) for x, y in rectangulo(ancho, alto)])
        for id_, (ancho, alto, _) in medidas.items()
    }

    def posiciones(huecos):
        resultado = anidar_sparrow(
            piezas, geometrias, Plancha(D(1000), D(1000)), ParametrosCorte(D(2), D(10), D(5), RotacionPermitida.LIBRE_0_90),
            OpcionesSparrow(segundos_por_busqueda=1, tiempo_maximo_s=20, simplificacion_mm=0, workers=1, semilla=7,
                            usar_anidado_en_huecos=huecos),
        )
        return [(p.pieza_id, p.plancha_indice, p.x_mm, p.y_mm, p.angulo_libre_grados) for p in resultado.posiciones]

    assert posiciones(True) == posiciones(False)
