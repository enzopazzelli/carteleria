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
    entry=preparar_entrada(*datos(),OpcionesSparrow())
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
