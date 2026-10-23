from decimal import Decimal as D
import pytest
from app.services.nesting.models import Pieza,Plancha,ParametrosCorte,RotacionPermitida
from app.services.nesting.validacion_manual import GeometriaPieza
from app.services.nesting.sparrow import preparar_entrada,convertir_y_validar,anidar_sparrow,OpcionesSparrow

def datos(kerf=0):
    pieces=[Pieza('1',D(20),D(10),2)]
    g={'1':GeometriaPieza(D(20),D(10),[(D(0),D(0)),(D(20),D(0)),(D(20),D(10)),(D(0),D(10))])}
    return pieces,g,Plancha(D(100),D(100)),ParametrosCorte(D(kerf),D(0),D(0),RotacionPermitida.LIBRE_0_90)

def test_bloquea_pieza_al_borde_con_kerf():
    p,g,_,params=datos(3)
    with pytest.raises(ValueError,match='no entran'):
        preparar_entrada(p,g,Plancha(D(20),D(10)),params,OpcionesSparrow())

def test_rechaza_duplicados_y_separacion_insuficiente():
    entry=preparar_entrada(*datos(3),OpcionesSparrow())
    q={'id':'1#0','sheet':0,'rotation':0,'tx':1.5,'ty':1.5}
    with pytest.raises(ValueError,match='duplicadas'): convertir_y_validar(entry,[q,q])
    with pytest.raises(ValueError,match='separación'):
        convertir_y_validar(entry,[q,{**q,'id':'1#1','tx':22.5}])

def test_valida_rotacion_y_demanda():
    entry=preparar_entrada(*datos(3),OpcionesSparrow())
    result=convertir_y_validar(entry,[{'id':'1#0','sheet':0,'rotation':0,'tx':1.5,'ty':1.5},{'id':'1#1','sheet':0,'rotation':180,'tx':60,'ty':20}])
    assert result.planchas_usadas==1
    assert len(result.posiciones)==2
    assert result.posiciones[1].angulo_libre_grados==D(180)

def test_worker_real_y_validacion_final():
    result=anidar_sparrow(*datos(3),OpcionesSparrow(segundos_por_busqueda=1,tiempo_maximo_s=20,simplificacion_mm=0))
    assert len(result.posiciones)==2
    assert result.planchas_usadas==1

def test_cancelacion_mata_worker():
    with pytest.raises(ValueError,match='cancelado'):
        anidar_sparrow(*datos(),OpcionesSparrow(segundos_por_busqueda=10),cancelada=lambda:True)

def test_timeout_mata_worker():
    with pytest.raises(ValueError,match='tiempo máximo'):
        anidar_sparrow(*datos(),OpcionesSparrow(segundos_por_busqueda=10,tiempo_maximo_s=0.01))


def test_canoniza_ruido_de_rotacion_pero_rechaza_angulo_libre():
    entry=preparar_entrada(*datos(),OpcionesSparrow(giro_libre=False))
    placed=[{'id':'1#0','sheet':0,'rotation':0,'tx':0,'ty':0},{'id':'1#1','sheet':0,'rotation':179.99999,'tx':60,'ty':20}]
    assert convertir_y_validar(entry,placed).posiciones[1].angulo_libre_grados==D(180)
    placed[1]['rotation']=170
    with pytest.raises(ValueError,match='Rotación'):convertir_y_validar(entry,placed)


def test_worker_con_contorno_muy_pequeno_y_separacion_real():
    p,g,plancha,params=datos(3)
    p.append(Pieza('2',D('0.026'),D('0.027')))
    g['2']=GeometriaPieza(D('0.026'),D('0.027'),[(0,0),(.026,0),(.026,.027),(0,.027)])
    result=anidar_sparrow(p,g,plancha,params,OpcionesSparrow(segundos_por_busqueda=1,tiempo_maximo_s=30))
    assert {q.pieza_id for q in result.posiciones} == {'1#0','1#1','2#0'}


def test_huecos_superpuestos_se_normalizan_sin_omitir_piezas():
    p,g,plancha,params=datos()
    g['1'].agujeros_local_mm.extend([
        [(2,2),(6,2),(6,6),(2,6)],[(4,4),(8,4),(8,8),(4,8)],
    ])
    entry=preparar_entrada(p,g,plancha,params,OpcionesSparrow())
    assert entry['normalizadas']==['1']
    assert len(entry['items'])==2
    assert len(g['1'].agujeros_local_mm)==2


from app.services.nesting import sparrow_worker


def entrada_de_cuadrados(cantidad,lado=40,**opciones):
    """`cantidad` cuadrados iguales para una chapa de 100 x 100 con kerf 2:
    de 40 entran cuatro por chapa; de 60, uno."""
    piezas=[Pieza('1',D(lado),D(lado),cantidad)]
    g={'1':GeometriaPieza(D(lado),D(lado),[(D(0),D(0)),(D(lado),D(0)),(D(lado),D(lado)),(D(0),D(lado))])}
    params=ParametrosCorte(D(2),D(0),D(0),RotacionPermitida.LIBRE_0_90)
    return preparar_entrada(piezas,g,Plancha(D(100),D(100)),params,OpcionesSparrow(segundos_por_busqueda=1,simplificacion_mm=0,**opciones))


def test_entra_en_una_chapa_devuelve_posiciones_que_validan():
    entrada=entrada_de_cuadrados(4)
    originales,de_busqueda=sparrow_worker.formas(entrada)
    colocadas=sparrow_worker.entra_en_una_chapa(['1#0','1#1','1#2','1#3'],originales,de_busqueda,entrada)
    assert colocadas is not None
    result=convertir_y_validar(entrada,[{**q,'sheet':0} for q in colocadas])
    assert result.planchas_usadas==1
    assert len(result.posiciones)==4


def test_entra_en_una_chapa_dice_que_no_si_no_caben():
    entrada=entrada_de_cuadrados(2,lado=60)
    originales,de_busqueda=sparrow_worker.formas(entrada)
    assert sparrow_worker.entra_en_una_chapa(['1#0','1#1'],originales,de_busqueda,entrada) is None


def una_por_chapa(data):
    """Un punto de partida malo a propósito: cada pieza sola en su chapa."""
    return [{'id':p['id'],'sheet':n,'rotation':0,'tx':data['borde'],'ty':data['borde']} for n,p in enumerate(data['items'])]

def chapas_usadas(colocadas):
    return len({q['sheet'] for q in colocadas})


def test_resolver_vacia_las_chapas_que_dejo_la_primera_etapa(monkeypatch):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    colocadas=sparrow_worker.resolver(entrada)
    assert convertir_y_validar(entrada,colocadas).planchas_usadas==1


def test_resolver_con_la_etapa_apagada_devuelve_la_primera(monkeypatch):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60,vaciar_chapas=False)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    assert chapas_usadas(sparrow_worker.resolver(entrada))==4


def test_resolver_sin_tiempo_para_consultar_devuelve_la_primera(monkeypatch):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=1)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    assert chapas_usadas(sparrow_worker.resolver(entrada))==4


def encimadas(ids,originals,shapes,data):
    """Todas las piezas en el mismo lugar: no valida."""
    return [{'id':k,'rotation':0,'tx':data['borde'],'ty':data['borde']} for k in ids]

def rota(ids,originals,shapes,data):
    raise RuntimeError('falla de prueba')

class Panico(BaseException):
    """Como `pyo3_runtime.PanicException`, con la que spyrrow avisa sus
    fallas internas: no desciende de `Exception`."""

def panico(ids,originals,shapes,data):
    raise Panico('pánico de prueba')

@pytest.mark.parametrize('consulta',[encimadas,rota,panico])
def test_un_reparto_que_falla_no_pierde_la_primera_etapa(monkeypatch,consulta):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    monkeypatch.setattr(sparrow_worker,'entra_en_una_chapa',consulta)
    colocadas=sparrow_worker.resolver(entrada)
    assert chapas_usadas(colocadas)==4
    convertir_y_validar(entrada,colocadas)


import json
from pathlib import Path
from app.services.nesting.sparrow import ruta_de_avisos


def avisos_escritos(salida):
    return json.loads(ruta_de_avisos(salida).read_text(encoding='utf8'))


@pytest.mark.parametrize('consulta',[encimadas,rota,panico])
def test_un_reparto_que_falla_queda_en_los_avisos(monkeypatch,tmp_path,consulta):
    """Antes quedaba solo en el registro del worker, que se borra."""
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    monkeypatch.setattr(sparrow_worker,'entra_en_una_chapa',consulta)
    salida=tmp_path/'salida.json'

    sparrow_worker.resolver(entrada,salida)

    [aviso]=avisos_escritos(salida)
    assert 'vaciar chapas' in aviso


def test_una_pasada_que_falla_despues_de_la_primera_no_pierde_lo_encontrado(monkeypatch,tmp_path,capsys):
    """De 60 entra uno por chapa, y por área podrían ser dos: el worker
    prueba una segunda pasada. Si esa falla, vale la primera. El aviso no
    trae la causa: va al registro del worker (A9)."""
    entrada=entrada_de_cuadrados(4,lado=60,intentos=2,tiempo_maximo_s=60,vaciar_chapas=False)
    llamadas=[]
    def pasada(data):
        llamadas.append(1)
        if len(llamadas)>1: raise Panico('pánico de prueba')
        return una_por_chapa(data)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',pasada)
    salida=tmp_path/'salida.json'

    colocadas=sparrow_worker.resolver(entrada,salida)

    assert len(llamadas)==2
    assert chapas_usadas(colocadas)==4
    assert avisos_escritos(salida)==['Una de las vueltas de búsqueda falló: quedó el mejor resultado de las anteriores.']
    assert 'pánico de prueba' in capsys.readouterr().err


def test_una_pasada_posterior_que_no_valida_no_pierde_lo_encontrado(monkeypatch,tmp_path,capsys):
    entrada=entrada_de_cuadrados(4,lado=60,intentos=2,tiempo_maximo_s=60,vaciar_chapas=False)
    llamadas=[]
    def pasada(data):
        llamadas.append(1)
        if len(llamadas)>1:  # todas encimadas en la misma chapa: no valida
            return [{'id':p['id'],'sheet':0,'rotation':0,'tx':data['borde'],'ty':data['borde']} for p in data['items']]
        return una_por_chapa(data)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',pasada)
    salida=tmp_path/'salida.json'

    colocadas=sparrow_worker.resolver(entrada,salida)

    assert chapas_usadas(colocadas)==4
    assert avisos_escritos(salida)==['Una de las vueltas de búsqueda falló: quedó el mejor resultado de las anteriores.']
    assert 'pasada 2' in capsys.readouterr().err


def test_un_mismo_aviso_no_se_repite(monkeypatch,tmp_path):
    """Vaciar chapas falla igual en las dos pasadas: un solo aviso."""
    entrada=entrada_de_cuadrados(4,lado=60,intentos=2,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    monkeypatch.setattr(sparrow_worker,'entra_en_una_chapa',rota)
    salida=tmp_path/'salida.json'

    sparrow_worker.resolver(entrada,salida)

    assert len(avisos_escritos(salida))==1


def test_lo_que_el_worker_da_por_mejor_es_lo_que_quedo_escrito(monkeypatch,tmp_path):
    """Si escribir el mejor falla, no se lo da por mejor: si no, uno peor
    que ese pero mejor que el escrito ya no se escribiría."""
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    reemplazar=Path.replace
    escrituras=[]
    salida=tmp_path/'salida.json'
    def replace(self,destino):
        # Se cuentan solo las escrituras del resultado: el worker también
        # reemplaza su archivo de avisos y el de progreso.
        if Path(destino)==salida:
            escrituras.append(1)
            if len(escrituras)==2: raise OSError('disco lleno de prueba')
        return reemplazar(self,destino)
    monkeypatch.setattr(Path,'replace',replace)

    colocadas=sparrow_worker.resolver(entrada,salida)

    assert colocadas==json.loads(salida.read_text(encoding='utf8'))


def worker_falso(tmp_path,codigo,avisos=(),registro=''):
    """Un worker que deja cada pieza sola en su chapa, escribe `avisos`,
    deja `registro` en su salida de errores y termina con `codigo`."""
    guion=tmp_path/'worker_falso.py'
    guion.write_text(
        'import json,sys\n'
        'from pathlib import Path\n'
        f'print({registro!r},file=sys.stderr)\n'
        'data=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))\n'
        'salida=Path(sys.argv[2])\n'
        'salida.write_text(json.dumps([{"id":p["id"],"sheet":n,"rotation":0,"tx":data["borde"],"ty":data["borde"]} for n,p in enumerate(data["items"])]),encoding="utf8")\n'
        f'salida.with_suffix(".avisos.json").write_text(json.dumps({list(avisos)!r}),encoding="utf8")\n'
        f'sys.exit({codigo})\n',
        encoding='utf8',
    )
    return guion


def con_worker(monkeypatch,guion):
    from app.services.nesting import sparrow
    abrir=sparrow.subprocess.Popen
    monkeypatch.setattr(sparrow.subprocess,'Popen',lambda args,**kw:abrir([args[0],str(guion),*args[-2:]],**kw))


def test_los_avisos_del_worker_llegan_al_resultado(monkeypatch,tmp_path):
    con_worker(monkeypatch,worker_falso(tmp_path,0,['No se pudo terminar de vaciar chapas (prueba).']))

    resultado=anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20))

    assert 'No se pudo terminar de vaciar chapas (prueba).' in resultado.advertencias


@pytest.mark.parametrize('contenido',['','["cortado'])
def test_un_archivo_de_avisos_que_no_se_puede_leer_no_pierde_el_anidado(monkeypatch,tmp_path,contenido):
    """Si el worker se corta mientras escribe un aviso (por tiempo, o con
    el disco lleno), el archivo queda vacío o a medias: el anidado de
    `salida.json` igual vale."""
    guion=worker_falso(tmp_path,0)
    guion.write_text(
        guion.read_text(encoding='utf8').replace(
            'salida.with_suffix(".avisos.json").write_text(json.dumps([]),encoding="utf8")',
            f'salida.with_suffix(".avisos.json").write_text({contenido!r},encoding="utf8")',
        ),
        encoding='utf8',
    )
    con_worker(monkeypatch,guion)

    resultado=anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20))

    assert resultado.planchas_usadas==2
    assert any('No se pudieron leer los avisos' in aviso for aviso in resultado.advertencias)


def test_avisar_no_deja_el_archivo_de_avisos_a_medias(monkeypatch,tmp_path):
    """Se escribe aparte y se reemplaza de una vez, como el resultado."""
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    monkeypatch.setattr(sparrow_worker,'entra_en_una_chapa',rota)
    escribir=Path.write_text
    def write_text(self,texto,**kw):
        if self.name.endswith('.avisos.json'): raise AssertionError('el aviso se escribió directo sobre el archivo')
        return escribir(self,texto,**kw)
    monkeypatch.setattr(Path,'write_text',write_text)
    salida=tmp_path/'salida.json'

    sparrow_worker.resolver(entrada,salida)

    assert len(json.loads(ruta_de_avisos(salida).read_bytes()))==1


def test_si_el_worker_termina_con_error_vale_lo_que_dejo_escrito(monkeypatch, tmp_path, caplog):
    """Antes se descartaba el anidado de la primera pasada. El aviso no
    trae lo técnico: la causa queda en el registro del servidor."""
    con_worker(monkeypatch, worker_falso(tmp_path, 1, registro='Traceback...\nValueError: causa de prueba'))

    with caplog.at_level("WARNING", logger="carteleria"):
        resultado = anidar_sparrow(*datos(3), OpcionesSparrow(tiempo_maximo_s=20))

    assert resultado.planchas_usadas == 2
    assert "El cálculo se cortó antes de terminar: este es el mejor resultado completo que había encontrado." in resultado.advertencias
    assert "ValueError: causa de prueba" in caplog.text


def worker_que_falla(tmp_path,escribir_error):
    """Un worker que no deja ningún anidado: escribe su error con
    `escribir_error` (código Python) y termina con 1."""
    guion=tmp_path/'worker_que_falla.py'
    guion.write_text('import sys\n'+escribir_error+'\nsys.exit(1)\n',encoding='utf8')
    return guion


def test_un_error_del_worker_con_acentos_llega_entero(monkeypatch,tmp_path):
    """En Windows el worker escribía su error en cp1252 y se leía en UTF-8:
    la «í» de la carpeta `cartelería` en el traceback tapaba la causa con
    «'utf-8' codec can't decode byte 0xed»."""
    con_worker(monkeypatch,worker_que_falla(tmp_path,"print('ValueError: ninguna pieza entró en la chapa',file=sys.stderr)"))

    with pytest.raises(ValueError,match='ninguna pieza entró en la chapa'):
        anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20))


def test_un_registro_del_worker_que_no_es_utf8_no_tapa_el_error(monkeypatch,tmp_path):
    """Una biblioteca nativa puede escribir directo en la salida de errores,
    sin pasar por Python: un byte que no es UTF-8 no puede tapar la causa."""
    con_worker(monkeypatch,worker_que_falla(tmp_path,r"sys.stderr.buffer.write(b'causa de prueba \xed\n')"))

    with pytest.raises(ValueError,match='causa de prueba'):
        anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20))


def dos_piezas_una_girada(angulo):
    return [{'id':'1#0','sheet':0,'rotation':angulo,'tx':10,'ty':1},{'id':'1#1','sheet':0,'rotation':0,'tx':60,'ty':60}]


def test_con_giro_libre_acepta_cualquier_angulo():
    entry=preparar_entrada(*datos(),OpcionesSparrow(giro_libre=True))
    assert entry['rotations'] is None
    resultado=convertir_y_validar(entry,dos_piezas_una_girada(37))
    assert resultado.posiciones[0].angulo_libre_grados==D(37)


def test_con_giro_libre_un_angulo_negativo_queda_entre_0_y_360():
    entry=preparar_entrada(*datos(),OpcionesSparrow(giro_libre=True))
    resultado=convertir_y_validar(entry,dos_piezas_una_girada(-323))
    assert resultado.posiciones[0].angulo_libre_grados==D(37)


def test_con_veta_no_gira_libre_aunque_se_pida():
    pieces,g,plancha,_=datos()
    params=ParametrosCorte(D(0),D(0),D(0),RotacionPermitida.SOLO_0_180)
    entry=preparar_entrada(pieces,g,plancha,params,OpcionesSparrow(giro_libre=True))
    assert entry['rotations']==[0,180]
    with pytest.raises(ValueError,match='Rotación'):convertir_y_validar(entry,dos_piezas_una_girada(37))


def test_giro_libre_esta_marcado_por_defecto():
    assert OpcionesSparrow().giro_libre is True


def test_worker_real_con_giro_libre():
    result=anidar_sparrow(*datos(3),OpcionesSparrow(giro_libre=True,segundos_por_busqueda=1,tiempo_maximo_s=20,simplificacion_mm=0))
    assert len(result.posiciones)==2
    assert result.planchas_usadas==1


# Las piezas grandes (A11): las que no entran en la chapa a cualquier ángulo
# giran solo en los ángulos con los que entran enteras.
from shapely.geometry import Polygon
from app.services.nesting.sparrow import angulos_que_entran

#: El lugar útil de la chapa de Complejo («Calibre 22»).
UTIL=(1198,2418)


def rectangulo(ancho,alto):
    return [(0,0),(ancho,0),(ancho,alto),(0,alto)]


def test_una_letra_chica_gira_como_todas():
    assert angulos_que_entran(Polygon(rectangulo(650,650)),None,*UTIL) is None


def test_un_tramo_del_aro_va_derecho_o_dado_vuelta():
    # Inclinado 1° ya mide 1234 mm de ancho.
    assert angulos_que_entran(Polygon(rectangulo(1193,2361)),None,*UTIL)==[0,180]


def test_una_pieza_algo_mas_chica_que_la_chapa_se_puede_inclinar_un_poco():
    angulos=angulos_que_entran(Polygon(rectangulo(1150,400)),None,*UTIL)
    # A 8° mide 1194,5 de ancho; a 19° llega a 1217, el máximo.
    assert {0,8,90,352}<=set(angulos)
    assert 9 not in angulos and 19 not in angulos and 161 not in angulos


def test_con_veta_una_pieza_grande_solo_da_media_vuelta():
    assert angulos_que_entran(Polygon(rectangulo(1150,400)),[0,180],*UTIL)==[0,180]


def test_sin_giro_libre_un_tramo_del_aro_no_se_pone_de_costado():
    assert angulos_que_entran(Polygon(rectangulo(1193,2361)),[0,90,180,270],*UTIL)==[0,180]


def tramo_y_letra():
    piezas=[Pieza('1',D(1193),D(2361)),Pieza('2',D(650),D(650),2)]
    g={'1':GeometriaPieza(D(1193),D(2361),rectangulo(1193,2361)),
       '2':GeometriaPieza(D(650),D(650),rectangulo(650,650))}
    return piezas,g,Plancha(D(1198),D(2418)),ParametrosCorte(D(0),D(0),D(0),RotacionPermitida.LIBRE_0_90)


def test_preparar_entrada_da_sus_angulos_solo_a_las_piezas_grandes():
    entry=preparar_entrada(*tramo_y_letra(),OpcionesSparrow(giro_libre=True))
    por_id={p['id']:p for p in entry['items']}
    assert por_id['1#0']['rotations']==[0,180]
    assert 'rotations' not in por_id['2#0'] and 'rotations' not in por_id['2#1']
    assert entry['rotations'] is None
    assert entry['piezas_grandes']==['1']


def test_sin_giro_libre_las_piezas_grandes_no_se_anotan_para_el_aviso():
    entry=preparar_entrada(*tramo_y_letra(),OpcionesSparrow(giro_libre=False))
    assert entry['items'][0]['rotations']==[0,180]
    assert entry['piezas_grandes']==[]


def test_sparrow_recibe_los_angulos_de_cada_pieza_grande(monkeypatch):
    import spyrrow
    recibidos={};item=spyrrow.Item
    def anotar(id,forma,demanda,angulos):
        recibidos[id]=angulos
        return item(id,forma,demanda,angulos)
    monkeypatch.setattr(spyrrow,'Item',anotar)
    entry=preparar_entrada(*tramo_y_letra(),OpcionesSparrow(giro_libre=True,segundos_por_busqueda=1,simplificacion_mm=0))
    originales,formas=sparrow_worker.formas(entry)

    sparrow_worker.franja(list(formas),originales,formas,entry)

    assert recibidos=={'1#0':[0,180],'2#0':None,'2#1':None}


from app.mensajes import Aviso

AVISO_GRANDES="Estas piezas son casi del tamaño de la chapa: se giran solo en los ángulos con los que entran enteras:"

#: El tramo solo en una chapa y las dos letras en otra.
TRAMO_Y_LETRAS_UBICADOS=[{'id':'1#0','sheet':0,'rotation':180,'tx':1193,'ty':2361},
                         {'id':'2#0','sheet':1,'rotation':0,'tx':0,'ty':0},
                         {'id':'2#1','sheet':1,'rotation':0,'tx':0,'ty':700}]


def test_el_aviso_nombra_las_piezas_grandes():
    entry=preparar_entrada(*tramo_y_letra(),OpcionesSparrow(giro_libre=True))

    resultado=convertir_y_validar(entry,TRAMO_Y_LETRAS_UBICADOS)

    assert resultado.advertencias==[Aviso(AVISO_GRANDES,(1,))]


def test_sin_giro_libre_no_se_avisa_de_las_piezas_grandes():
    entry=preparar_entrada(*tramo_y_letra(),OpcionesSparrow(giro_libre=False))

    assert convertir_y_validar(entry,TRAMO_Y_LETRAS_UBICADOS).advertencias==[]


def test_worker_real_con_una_pieza_casi_del_ancho_de_la_chapa():
    resultado=anidar_sparrow(*tramo_y_letra(),OpcionesSparrow(giro_libre=True,segundos_por_busqueda=1,tiempo_maximo_s=30,simplificacion_mm=0))

    tramo=next(q for q in resultado.posiciones if q.pieza_id=='1#0')
    assert tramo.angulo_libre_grados in (D(0),D(180))
    assert resultado.planchas_usadas==2
    assert Aviso(AVISO_GRANDES,(1,)) in resultado.advertencias


# El sobrante arriba, como bloque (A12): se anida con la chapa acostada y
# se endereza el resultado.
from app.services.nesting.material_usado import material_de_chapa
from app.services.nesting.validacion_manual import poligono_colocado,posicion_manual_desde_pieza


def sobrante_de_la_primera_chapa(resultado,geometrias,borde):
    poligonos=[poligono_colocado(posicion_manual_desde_pieza(q),geometrias[q.pieza_id.split('#')[0]])
               for q in resultado.posiciones if q.plancha_indice==0]
    return material_de_chapa(0,poligonos,100,100,borde,250).sobrante


def seis_rectangulos(rotaciones=RotacionPermitida.LIBRE_0_90):
    """Seis piezas de 20 x 30 en una chapa de 100 x 100 con kerf 3: ocupan
    un tercio de la chapa."""
    piezas=[Pieza('1',D(20),D(30),6)]
    g={'1':GeometriaPieza(D(20),D(30),[(0,0),(20,0),(20,30),(0,30)])}
    return piezas,g,Plancha(D(100),D(100)),ParametrosCorte(D(3),D(0),D(0),rotaciones)


def rapido(**opciones):
    return OpcionesSparrow(segundos_por_busqueda=1,tiempo_maximo_s=20,simplificacion_mm=0,**opciones)


def test_el_sobrante_vale_costado_si_no_se_dice():
    assert OpcionesSparrow().sobrante=='costado'


def test_con_el_sobrante_arriba_las_piezas_quedan_abajo_y_sobra_un_bloque():
    piezas,g,plancha,params=seis_rectangulos()

    resultado=anidar_sparrow(piezas,g,plancha,params,rapido(sobrante='arriba'))

    sobrante=sobrante_de_la_primera_chapa(resultado,g,1.5)
    assert sobrante.ancho_mm==100 and sobrante.alto_mm>40
    # Abajo de verdad, del lado de la `y` chica, como en el DXF: así el
    # bloque queda arriba en la chapa, en el archivo y en la pantalla.
    assert max(q.y_mm+q.alto_colocado_mm for q in resultado.posiciones)<60


def test_con_el_sobrante_al_costado_sobra_una_tira_como_hasta_ahora():
    piezas,g,plancha,params=seis_rectangulos()

    resultado=anidar_sparrow(piezas,g,plancha,params,rapido(sobrante='costado'))

    sobrante=sobrante_de_la_primera_chapa(resultado,g,1.5)
    assert sobrante.alto_mm==100 and sobrante.ancho_mm>40


def test_con_veta_y_el_sobrante_arriba_ninguna_pieza_queda_a_90():
    piezas,g,plancha,params=seis_rectangulos(RotacionPermitida.SOLO_0_180)

    resultado=anidar_sparrow(piezas,g,plancha,params,rapido(sobrante='arriba'))

    assert {q.angulo_libre_grados for q in resultado.posiciones}<={D(0),D(180)}
    assert all(round(q.alto_colocado_mm)==30 for q in resultado.posiciones)


def test_con_el_sobrante_arriba_huecos_y_piezas_grandes_termina_bien():
    resultado=anidar_sparrow(*tramo_y_letra(),OpcionesSparrow(sobrante='arriba',usar_anidado_en_huecos=True,giro_libre=True,
                                                              segundos_por_busqueda=1,tiempo_maximo_s=30,simplificacion_mm=0))

    tramo=next(q for q in resultado.posiciones if q.pieza_id=='1#0')
    assert resultado.planchas_usadas==2
    assert round(tramo.alto_colocado_mm)==2361
    assert Aviso(AVISO_GRANDES,(1,)) in resultado.advertencias


from app.services.nesting.sparrow import ruta_de_progreso


def progreso_escrito(salida):
    return json.loads(ruta_de_progreso(salida).read_text(encoding='utf8'))


def test_el_worker_anota_la_pasada_al_empezarla(monkeypatch,tmp_path):
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60,vaciar_chapas=False)
    salida=tmp_path/'salida.json'
    vistos=[]
    def pasada(data):
        vistos.append(progreso_escrito(salida))
        return una_por_chapa(data)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',pasada)

    sparrow_worker.resolver(entrada,salida)

    assert vistos==[{'fase':'pasada','pasada':1,'pasadas':1,'mejor_chapas':None}]


def test_el_worker_anota_el_mejor_resultado_y_la_etapa_de_vaciar(monkeypatch,tmp_path):
    """La primera etapa deja cuatro chapas y vaciar chapas las junta en una."""
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    salida=tmp_path/'salida.json'

    sparrow_worker.resolver(entrada,salida)

    assert progreso_escrito(salida)=={'fase':'vaciar','pasada':1,'pasadas':1,'mejor_chapas':1}


def test_el_avance_se_anota_aunque_windows_no_deje_reemplazarlo_enseguida(monkeypatch,tmp_path,capsys):
    """El supervisor lee el progreso mientras el worker lo reemplaza, y
    Windows no deja reemplazar un archivo abierto («Acceso denegado»).
    Medido con tres anidados a la vez, el 2026-10-23."""
    entrada=entrada_de_cuadrados(4,intentos=1,tiempo_maximo_s=60)
    monkeypatch.setattr(sparrow_worker,'resolver_una_pasada',una_por_chapa)
    reemplazar=Path.replace;rechazos=[]
    def replace(self,destino):
        if Path(destino).name.endswith('.progreso.json') and len(rechazos)<2:
            rechazos.append(destino)
            raise PermissionError(13,'Acceso denegado')
        return reemplazar(self,destino)
    monkeypatch.setattr(Path,'replace',replace)
    salida=tmp_path/'salida.json'

    sparrow_worker.resolver(entrada,salida)

    assert len(rechazos)==2
    assert 'avanzar:' not in capsys.readouterr().err
    assert progreso_escrito(salida)=={'fase':'vaciar','pasada':1,'pasadas':1,'mejor_chapas':1}


def worker_que_avanza(tmp_path,progreso,espera=1.5):
    """Un worker que escribe `progreso` (texto, tal cual) como su archivo de
    progreso, espera y recién después deja cada pieza sola en su chapa."""
    guion=tmp_path/'worker_que_avanza.py'
    guion.write_text(
        'import json,sys,time\n'
        'from pathlib import Path\n'
        'data=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))\n'
        'salida=Path(sys.argv[2])\n'
        f'salida.with_suffix(".progreso.json").write_text({progreso!r},encoding="utf8")\n'
        f'time.sleep({espera})\n'
        'salida.write_text(json.dumps([{"id":p["id"],"sheet":n,"rotation":0,"tx":data["borde"],"ty":data["borde"]} for n,p in enumerate(data["items"])]),encoding="utf8")\n',
        encoding='utf8',
    )
    return guion


def test_el_supervisor_informa_lo_que_anota_el_worker(monkeypatch,tmp_path):
    anotado={'fase':'pasada','pasada':2,'pasadas':3,'mejor_chapas':7}
    con_worker(monkeypatch,worker_que_avanza(tmp_path,json.dumps(anotado)))
    avances=[]

    anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20),al_avanzar=avances.append)

    assert any({k:a.get(k) for k in anotado}==anotado for a in avances)
    assert all(a['maximo']==20 and 0<=a['segundos']<=20 for a in avances)


def test_un_progreso_a_medias_no_frena_el_anidado_ni_la_barra(monkeypatch,tmp_path):
    """Si el archivo está cortado, el tiempo se informa igual."""
    con_worker(monkeypatch,worker_que_avanza(tmp_path,'{"fase": "pas'))
    avances=[]

    resultado=anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20),al_avanzar=avances.append)

    assert resultado.planchas_usadas==2
    assert avances and all(set(a)=={'segundos','maximo'} for a in avances)


from app.services.nesting.sparrow import (
    CalculoInterrumpido,
    PiezaSinContorno,
    PiezasQueNoEntran,
    ResultadoQueNoPasaElControl,
    SinLugarUtil,
    TiempoAgotado,
)


def test_una_pieza_que_no_entra_dice_cual_es():
    piezas, geometrias, _, params = datos()

    with pytest.raises(PiezasQueNoEntran) as error:
        preparar_entrada(piezas, geometrias, Plancha(D(15), D(15)), params, OpcionesSparrow())

    assert error.value.ids == ["1"]


def test_una_pieza_sin_contorno_dice_cual_es():
    piezas, _, plancha, params = datos()

    with pytest.raises(PiezaSinContorno) as error:
        preparar_entrada(piezas, {}, plancha, params, OpcionesSparrow())

    assert error.value.pieza_id == "1"


def test_una_chapa_sin_lugar_util_tiene_nombre():
    piezas, geometrias, _, _ = datos()
    params = ParametrosCorte(D(0), D(10), D(0), RotacionPermitida.LIBRE_0_90)

    with pytest.raises(SinLugarUtil):
        preparar_entrada(piezas, geometrias, Plancha(D(20), D(20)), params, OpcionesSparrow())


def test_sin_tiempo_dice_cuantos_segundos_tenia():
    with pytest.raises(TiempoAgotado) as error:
        anidar_sparrow(*datos(), OpcionesSparrow(segundos_por_busqueda=10, tiempo_maximo_s=0.01))

    assert error.value.segundos == 0.01


def test_un_resultado_que_no_pasa_el_control_lleva_el_motivo():
    entrada = preparar_entrada(*datos(), OpcionesSparrow())
    q = {'id': '1#0', 'sheet': 0, 'rotation': 0, 'tx': 0, 'ty': 0}

    with pytest.raises(ResultadoQueNoPasaElControl) as error:
        convertir_y_validar(entrada, [q, q])

    assert "duplicadas" in error.value.motivo


def test_un_worker_que_se_corta_lleva_su_registro(monkeypatch, tmp_path):
    con_worker(monkeypatch, worker_que_falla(tmp_path, "print('ValueError: causa de prueba', file=sys.stderr)"))

    with pytest.raises(CalculoInterrumpido) as error:
        anidar_sparrow(*datos(3), OpcionesSparrow(tiempo_maximo_s=20))

    assert "causa de prueba" in error.value.registro


from app.mensajes import Aviso


def test_el_aviso_de_huecos_unidos_nombra_las_piezas_y_ya_no_hay_aviso_fijo():
    p, g, plancha, params = datos()
    g['1'].agujeros_local_mm.extend([[(2, 2), (6, 2), (6, 6), (2, 6)], [(4, 4), (8, 4), (8, 8), (4, 8)]])
    entrada = preparar_entrada(p, g, plancha, params, OpcionesSparrow())
    colocadas = [{'id': '1#0', 'sheet': 0, 'rotation': 0, 'tx': 0, 'ty': 0}, {'id': '1#1', 'sheet': 0, 'rotation': 0, 'tx': 40, 'ty': 0}]

    resultado = convertir_y_validar(entrada, colocadas)

    assert resultado.advertencias == [Aviso(
        "Estas piezas tenían huecos que se pisaban y se calcularon con los huecos unidos (el dibujo guardado no cambia):",
        (1,),
    )]


def test_sin_avisos_si_no_hubo_nada_que_avisar():
    resultado = anidar_sparrow(*datos(3), OpcionesSparrow(segundos_por_busqueda=1, tiempo_maximo_s=20, simplificacion_mm=0))

    assert not any("Sparrow" in str(a) for a in resultado.advertencias)


# --- Aprovechar huecos primero (A10) -----------------------------------------
from app.services.nesting.sparrow import ruta_de_progreso, _leer_progreso


def cuadrado_d(lado, desde=0):
    return [(D(desde), D(desde)), (D(desde + lado), D(desde)), (D(desde + lado), D(desde + lado)), (D(desde), D(desde + lado))]


def entrada_aro_y_cuadrado(huecos, **opciones):
    """Un aro de 90 con un hueco de 60 y un cuadrado de 50, en una chapa de
    100 x 100 con kerf 2: juntos no entran, salvo con el cuadrado adentro."""
    piezas = [Pieza('1', D(90), D(90)), Pieza('2', D(50), D(50))]
    g = {'1': GeometriaPieza(D(90), D(90), cuadrado_d(90), [cuadrado_d(60, 15)]),
         '2': GeometriaPieza(D(50), D(50), cuadrado_d(50))}
    params = ParametrosCorte(D(2), D(0), D(0), RotacionPermitida.LIBRE_0_90)
    return preparar_entrada(piezas, g, Plancha(D(100), D(100)), params, OpcionesSparrow(
        segundos_por_busqueda=1, simplificacion_mm=0, tiempo_maximo_s=30, usar_anidado_en_huecos=huecos, **opciones))


def test_con_huecos_el_cuadrado_va_adentro_y_alcanza_una_chapa():
    entrada = entrada_aro_y_cuadrado(True)
    colocadas = sparrow_worker.resolver(entrada)
    assert chapas_usadas(colocadas) == 1
    assert convertir_y_validar(entrada, colocadas).planchas_usadas == 1


def test_sin_huecos_usa_dos_chapas():
    assert chapas_usadas(sparrow_worker.resolver(entrada_aro_y_cuadrado(False))) == 2


def test_sin_ningun_hueco_no_avisa_nada(tmp_path):
    entrada = entrada_de_cuadrados(4, usar_anidado_en_huecos=True, tiempo_maximo_s=30)
    salida = tmp_path / 'salida.json'
    colocadas = sparrow_worker.resolver(entrada, salida)
    assert chapas_usadas(colocadas) == 1
    assert not ruta_de_avisos(salida).exists()


def test_el_aviso_dice_cuantas_van_adentro(tmp_path):
    salida = tmp_path / 'salida.json'
    sparrow_worker.resolver(entrada_aro_y_cuadrado(True), salida)
    assert avisos_escritos(salida) == ['1 pieza va adentro del hueco de otra: no ocupa lugar propio en la chapa.']


def test_la_barra_pasa_por_la_fase_de_huecos(tmp_path, monkeypatch):
    salida = tmp_path / 'salida.json'
    leido = []

    def falso(*args, al_avanzar, seguir, **kwargs):
        al_avanzar(1, 1)
        leido.append(json.loads(ruta_de_progreso(salida).read_text(encoding='utf8')))
        return []

    monkeypatch.setattr(sparrow_worker, 'meter_en_huecos', falso)
    sparrow_worker.resolver(entrada_aro_y_cuadrado(True), salida)
    [progreso] = leido
    assert (progreso['fase'], progreso['huecos'], progreso['huecos_total']) == ('huecos', 1, 1)


def test_leer_progreso_deja_pasar_los_huecos(tmp_path):
    salida = tmp_path / 'salida.json'
    ruta_de_progreso(salida).write_text(json.dumps({'fase': 'huecos', 'huecos': 3, 'huecos_total': 9}), encoding='utf8')
    assert _leer_progreso(salida) == {'fase': 'huecos', 'huecos': 3, 'huecos_total': 9}


@pytest.mark.parametrize('maximo,sigue', [(240, True), (0, False)])
def test_el_paso_de_huecos_para_a_la_mitad_del_tiempo(monkeypatch, maximo, sigue):
    visto = []

    def falso(*args, al_avanzar, seguir, **kwargs):
        visto.append(seguir())
        return []

    monkeypatch.setattr(sparrow_worker, 'meter_en_huecos', falso)
    sparrow_worker.resolver(entrada_de_cuadrados(1, usar_anidado_en_huecos=True, tiempo_maximo_s=maximo))
    assert visto == [sigue]


def test_si_el_paso_de_huecos_falla_se_acomoda_sin_huecos_y_se_avisa(tmp_path, monkeypatch, capsys):
    """La casilla viene marcada por defecto: una falla del paso nuevo no
    puede tirar un anidado que sin huecos sale bien (revisión de A10). La
    causa va al registro del worker, no al aviso."""
    def falla(*args, **kwargs):
        raise ValueError('falla de prueba')

    monkeypatch.setattr(sparrow_worker, 'meter_en_huecos', falla)
    entrada = entrada_aro_y_cuadrado(True)
    salida = tmp_path / 'salida.json'

    colocadas = sparrow_worker.resolver(entrada, salida)

    assert chapas_usadas(colocadas) == 2
    assert convertir_y_validar(entrada, colocadas).planchas_usadas == 2
    assert avisos_escritos(salida) == ['No se pudieron meter piezas en los huecos: se acomodó sin aprovecharlos.']
    assert 'falla de prueba' in capsys.readouterr().err
