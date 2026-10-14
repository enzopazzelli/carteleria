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


def test_una_pasada_que_falla_despues_de_la_primera_no_pierde_lo_encontrado(monkeypatch,tmp_path):
    """De 60 entra uno por chapa, y por área podrían ser dos: el worker
    prueba una segunda pasada. Si esa falla, vale la primera."""
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
    [aviso]=avisos_escritos(salida)
    assert 'pánico de prueba' in aviso


def test_una_pasada_posterior_que_no_valida_no_pierde_lo_encontrado(monkeypatch,tmp_path):
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
    [aviso]=avisos_escritos(salida)
    assert 'pasada 2' in aviso


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


def test_si_el_worker_termina_con_error_vale_lo_que_dejo_escrito(monkeypatch,tmp_path):
    """Antes se descartaba el anidado de la primera pasada. El aviso dice
    la causa: el registro del worker se borra con su carpeta."""
    con_worker(monkeypatch,worker_falso(tmp_path,1,registro='Traceback...\nValueError: causa de prueba'))

    resultado=anidar_sparrow(*datos(3),OpcionesSparrow(tiempo_maximo_s=20))

    assert resultado.planchas_usadas==2
    [aviso]=[a for a in resultado.advertencias if 'terminó con un error' in a]
    assert 'ValueError: causa de prueba' in aviso


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
