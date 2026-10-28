"""Motor Sparrow experimental con proceso aislado y validación original."""
from __future__ import annotations
import json, math, os, subprocess, sys, tempfile, time
from pathlib import Path
from decimal import Decimal
from dataclasses import dataclass, replace
import numpy as np
from shapely.geometry import Polygon, box
from shapely import affinity
from ... import config
from ...mensajes import Aviso, ErrorPrevisto
from ...registro import registro
from .models import Plancha, ResultadoAnidado, PosicionPieza, RotacionPermitida
from .geometria_material import poligono_material
from .huecos_primero import AREA_MINIMA_HUECO_MM2

class ErrorGeometriaSparrow(ValueError):
    def __init__(self, ids):
        self.piezas_invalidas = ids
        super().__init__(f"Sparrow no puede comparar: {len(ids)} pieza(s) tienen contornos o agujeros inválidos (IDs: {', '.join(ids)}). Revisá las piezas indicadas y corregí el DXF; no se omitió ninguna pieza.")

# Las fallas del cálculo, con nombre propio y los datos que hacen falta
# para decirlas (A9). Su texto es técnico: va al detalle. La ruta, que
# conoce los nombres del dibujo, arma el mensaje para el usuario
# (`app/api/traducir_errores.py`).

class PiezasQueNoEntran(ValueError):
    def __init__(self, ids):
        self.ids = [str(i) for i in ids]
        super().__init__('Piezas que no entran con el kerf y margen actuales: ' + ', '.join(self.ids) + '.')


class PiezaSinContorno(ValueError):
    def __init__(self, pieza_id):
        self.pieza_id = str(pieza_id)
        super().__init__(f'La pieza {pieza_id} no tiene contorno.')


class SinLugarUtil(ValueError):
    def __init__(self):
        super().__init__('Los parámetros no dejan un formato útil válido.')


class TiempoAgotado(ValueError):
    def __init__(self, segundos):
        self.segundos = segundos
        super().__init__(f'Sparrow excedió el tiempo máximo ({segundos} s) sin un anidado completo.')


class ResultadoQueNoPasaElControl(ValueError):
    def __init__(self, motivo):
        self.motivo = motivo
        super().__init__(motivo)


class CalculoInterrumpido(ValueError):
    def __init__(self, registro):
        self.registro = registro
        super().__init__('Sparrow no pudo calcular: ' + registro)

@dataclass(frozen=True)
class OpcionesSparrow:
    semilla: int = 42
    segundos_por_busqueda: int = 2
    tiempo_maximo_s: int = 240
    workers: int = 2
    simplificacion_mm: float = 0.3
    intentos: int = 3
    #: Segunda etapa (`sparrow_reparto.py`): vaciar chapas repartiendo sus
    #: piezas en las demás, con el tiempo que sobra de `tiempo_maximo_s`.
    vaciar_chapas: bool = True
    #: Girar las piezas a cualquier ángulo, no solo de a cuartos de vuelta.
    #: Marcada por defecto (Enzo, 2026-10-14). Con veta no se aplica: el
    #: material solo gira media vuelta.
    giro_libre: bool = True
    #: Meter las piezas chicas en los huecos de las grandes antes de
    #: acomodar (A10, `huecos_primero.py`). El mismo nombre que en la API y
    #: en las corridas guardadas, para que pasen sin traducir.
    usar_anidado_en_huecos: bool = False
    #: Hacia qué lado queda el sobrante de cada chapa (A12): `"arriba"`,
    #: como bloque de todo el ancho, o `"costado"`, como tira de todo el
    #: alto. Si no se dice, al costado, como antes: la pantalla manda
    #: arriba, y la comparación de chapas siempre arriba.
    sobrante: str = "costado"

def ruta_de_avisos(salida):
    """Dónde deja el worker sus avisos, al lado de su resultado. Los escribe
    en el momento: si se lo corta por tiempo, ya están."""
    return Path(salida).with_suffix('.avisos.json')

def ruta_de_progreso(salida):
    """Dónde deja el worker cómo va (A7): pasada, fase y mejor resultado.
    Como los avisos, al lado del resultado y escrito de una vez."""
    return Path(salida).with_suffix('.progreso.json')

def _area_util(plancha, params):
    borde = float(params.margen_borde_mm + params.kerf_mm / 2)
    return borde, float(plancha.ancho_mm)-2*borde, float(plancha.alto_mm)-2*borde

def _rotaciones(params):
    return [0,180] if params.rotaciones_permitidas is RotacionPermitida.SOLO_0_180 else [0,90,180,270]

def _rotaciones_para_buscar(params, giro_libre):
    """Lo que se le pasa a Sparrow: `None` es cualquier ángulo. Con veta,
    siempre media vuelta."""
    if giro_libre and params.rotaciones_permitidas is not RotacionPermitida.SOLO_0_180:
        return None
    return _rotaciones(params)

def _entra(shell, rotations, width, height):
    for a in rotations:
        b=affinity.rotate(shell,a,origin=(0,0)).bounds
        if b[2]-b[0]<=width+1e-8 and b[3]-b[1]<=height+1e-8: return True
    return False

def angulos_que_entran(shell, rotations, width, height):
    """`None` si la pieza entra en el área útil a cualquier ángulo: gira como
    todas, con `rotations` (`None` es cualquier ángulo). Si no, es una pieza
    grande (A11): los ángulos de `rotations`, o de 0° a 359° de a 1° si gira
    libre, con los que entra entera. Sin esa lista, Sparrow la inclina en la
    franja, que solo limita el alto, y queda más ancha que la chapa."""
    puntos=np.asarray(shell.convex_hull.exterior.coords)
    # El largo de punta a punta es el mayor ancho que puede tomar al girar.
    largo=max(float(np.hypot(*(puntos-p).T).max()) for p in puntos)
    if largo<=min(width,height)+1e-8: return None
    return [a for a in (rotations or range(360)) if _entra(shell,[a],width,height)]

def entra_en_la_chapa(contorno_local_mm, plancha, params, giro_libre):
    """Si la silueta entra entera en el área útil con los giros del anidado
    (A17): con giro libre, a cualquier ángulo, de a 1°; con veta, media
    vuelta aunque se pida giro libre; si no, de a cuartos de vuelta. El
    mismo chequeo que `preparar_entrada` hace antes de buscar."""
    _, width, height = _area_util(plancha, params)
    angulos = angulos_que_entran(Polygon(contorno_local_mm), _rotaciones_para_buscar(params, giro_libre), width, height)
    return angulos is None or bool(angulos)

def piezas_que_no_entran(piezas, geometrias, plancha, params, giro_libre=False):
    """Las piezas cuya silueta no entra en el área útil con ningún giro
    permitido (`entra_en_la_chapa`). No se descartan: son las que habría
    que seccionar (A5) para usar este formato. Las que no tienen contorno
    las rechaza `preparar_entrada`."""
    return [p.id for p in piezas
            if (g := geometrias.get(p.id)) is not None and g.contorno_local_mm
            and not entra_en_la_chapa(g.contorno_local_mm, plancha, params, giro_libre)]

def preparar_entrada(piezas, geometrias, plancha, params, opciones):
    borde, width, height = _area_util(plancha, params)
    gap = float(params.kerf_mm + params.separacion_piezas_mm)
    if width <= 0 or height <= 0 or min(borde, gap) < 0:
        raise SinLugarUtil()
    para_buscar = _rotaciones_para_buscar(params, opciones.giro_libre)
    items=[]; blocked=[]; invalidas=[]; normalizadas=[]; grandes=[]
    for p in piezas:
        g=geometrias.get(p.id)
        if g is None or not g.contorno_local_mm:
            raise PiezaSinContorno(p.id)
        original=Polygon(g.contorno_local_mm,g.agujeros_local_mm)
        try:
            poly=poligono_material(g.contorno_local_mm,g.agujeros_local_mm)
        except ValueError:
            invalidas.append(p.id)
            continue
        if not original.is_valid:
            normalizadas.append(p.id)
        shell=Polygon(g.contorno_local_mm)
        # Con los giros del anidado (A17): una pieza que solo entra en
        # diagonal se acomoda inclinada, no se manda a seccionar.
        angulos=angulos_que_entran(shell, para_buscar, width, height)
        if angulos==[]:
            blocked.append(p.id)
            continue
        # Se avisa solo con giro libre: sin él, la casilla no prometía inclinarlas.
        if angulos is not None and para_buscar is None: grandes.append(p.id)
        propios={} if angulos is None else {'rotations':angulos}
        for n in range(p.cantidad):
            items.append({'id':f'{p.id}#{n}','shell':list(shell.exterior.coords),'holes':[list(r.coords) for r in original.interiors],**propios})
    if invalidas:
        raise ErrorGeometriaSparrow(invalidas)
    if blocked:
        raise PiezasQueNoEntran(blocked)
    if not items: raise ErrorPrevisto('No hay piezas para anidar.')
    return {'items':items,'width':width,'height':height,'borde':borde,'gap':gap,'rotations':para_buscar,'options':vars(opciones),'normalizadas':normalizadas,'piezas_grandes':grandes,'area_minima_hueco_mm2':AREA_MINIMA_HUECO_MM2}

def _piezas_del_aviso(ids):
    """Las piezas que la pantalla dibuja al lado de un aviso. El visor de
    `scripts/` nombra sus piezas con texto («aro»): esas no se dibujan, y
    el aviso sale igual."""
    return tuple(int(i) for i in ids if str(i).isdigit())

def convertir_y_validar(entrada, placed):
    expected={p['id'] for p in entrada['items']}
    ids=[p['id'] for p in placed]
    if len(ids)!=len(expected) or set(ids)!=expected:
        raise ResultadoQueNoPasaElControl('Sparrow devolvió piezas faltantes o duplicadas.')
    originals={p['id']:poligono_material(p['shell'],p['holes']) for p in entrada['items']}
    border=entrada['borde'];w=entrada['width'];h=entrada['height']
    container=box(border,border,border+w,border+h)
    polys=[]; positions=[]
    for q in placed:
        values=[q['tx'],q['ty'],q['rotation']]
        if not all(math.isfinite(v) for v in values) or not isinstance(q['sheet'],int) or q['sheet']<0:
            raise ResultadoQueNoPasaElControl('Colocación inválida devuelta por Sparrow.')
        q = dict(q)
        angle = q['rotation'] % 360
        if entrada['rotations'] is None:
            q['rotation'] = angle  # giro libre: cualquier ángulo, entre 0 y 360
        else:
            allowed = min(entrada['rotations'], key=lambda a: abs((angle-a+180)%360-180))
            if abs((angle-allowed+180)%360-180)>0.001:
                raise ResultadoQueNoPasaElControl('Rotación no permitida devuelta por Sparrow.')
            q['rotation'] = allowed
        original=originals[q['id']]
        rotated=affinity.rotate(original,q['rotation'],origin=(0,0))
        poly=affinity.translate(rotated,q['tx'],q['ty'])
        x0,y0,x1,y1=poly.bounds
        # Solo corrige deriva submilimétrica de traslación; valida de nuevo luego.
        dx=max(border-x0,min(0,border+w-x1));dy=max(border-y0,min(0,border+h-y1))
        if abs(dx)>0.002 or abs(dy)>0.002:
            raise ResultadoQueNoPasaElControl('Una pieza sale del formato útil.')
        poly=affinity.translate(poly,dx,dy)
        if poly.difference(container).area>0.01: raise ResultadoQueNoPasaElControl('Una pieza invade el margen/kerf del borde.')
        bounds=poly.bounds
        for other, otherq, otherbounds in polys:
            if otherq['sheet']!=q['sheet']: continue
            gap=entrada['gap']
            if (bounds[0]-otherbounds[2]>gap or otherbounds[0]-bounds[2]>gap or
                bounds[1]-otherbounds[3]>gap or otherbounds[1]-bounds[3]>gap):
                continue
            if poly.intersection(other).area>0.01 or poly.distance(other)<entrada['gap']-0.01:
                raise ResultadoQueNoPasaElControl('El resultado viola la separación o superpone piezas.')
        polys.append((poly,q,bounds));x0,y0,x1,y1=bounds
        ox0,oy0,ox1,oy1=original.bounds
        cx,cy=(ox0+ox1)/2,(oy0+oy1)/2
        rad=math.radians(q['rotation'])
        centerx=cx*math.cos(rad)-cy*math.sin(rad)+q['tx']+dx
        centery=cx*math.sin(rad)+cy*math.cos(rad)+q['ty']+dy
        positions.append(PosicionPieza(q['id'],q['sheet'],Decimal(str(x0)),Decimal(str(y0)),Decimal(str(x1-x0)),Decimal(str(y1-y0)),False,Decimal(str(q['rotation'])),Decimal(str(centerx)),Decimal(str(centery))))
    sheets={p.plancha_indice for p in positions}
    if sheets!=set(range(len(sheets))):raise ResultadoQueNoPasaElControl('Índices de chapa inconsistentes.')
    avisos = []
    if entrada.get('normalizadas'):
        avisos.append(Aviso(
            "Estas piezas tenían huecos que se pisaban y se calcularon con los huecos unidos (el dibujo guardado no cambia):",
            _piezas_del_aviso(entrada['normalizadas']),
        ))
    if entrada.get('piezas_grandes'):
        avisos.append(Aviso(
            "Estas piezas son casi del tamaño de la chapa: se giran solo en los ángulos con los que entran enteras:",
            _piezas_del_aviso(entrada['piezas_grandes']),
        ))
    return ResultadoAnidado(positions, len(sheets), avisos)

def _lo_que_dejo_el_worker(entrada,out,*avisos):
    """El mejor anidado que dejó escrito el worker, validado, con los avisos
    que escribió él y los que agrega el supervisor."""
    result=convertir_y_validar(entrada,json.loads(out.read_text(encoding='utf8')))
    ruta=ruta_de_avisos(out)
    try:
        del_worker=json.loads(ruta.read_text(encoding='utf8')) if ruta.exists() else []
        if not isinstance(del_worker,list) or not all(isinstance(a,str) for a in del_worker):
            raise ValueError('avisos sin forma de lista de textos')
    except (OSError,ValueError):
        # Los avisos no valen el anidado: el resultado ya está validado.
        del_worker=['No se pudieron leer los avisos del cálculo: el anidado es válido, pero puede faltar algún aviso.']
    return ResultadoAnidado(result.posiciones,result.planchas_usadas,[*result.advertencias,*del_worker,*avisos])

#: Cada cuánto el supervisor lee el progreso del worker: la barra no
#: necesita más, y así no se lee el archivo en cada vuelta.
_LEER_PROGRESO_CADA_S=0.5

def _leer_progreso(out):
    """Lo que dejó escrito el worker sobre cómo va, o `None` si todavía no
    está o está a medias: la barra de progreso no vale un error."""
    try:
        datos=json.loads(ruta_de_progreso(out).read_text(encoding='utf8'))
    except (OSError,ValueError):
        return None
    if not isinstance(datos,dict): return None
    return {k:datos[k] for k in ('fase','pasada','pasadas','mejor_chapas','huecos','huecos_total') if k in datos}

def _acostar(g):
    """La pieza girada un cuarto de vuelta en sentido horario, corrida
    para que quede en positivo: cada punto `(x, y)` pasa a `(y, ancho − x)`."""
    def girar(anillo):
        return [(float(y),float(g.ancho_mm)-float(x)) for x,y in anillo]
    return replace(g,ancho_mm=g.alto_mm,alto_mm=g.ancho_mm,
                   contorno_local_mm=girar(g.contorno_local_mm) if g.contorno_local_mm else g.contorno_local_mm,
                   agujeros_local_mm=[girar(a) for a in g.agujeros_local_mm])

def _enderezar(resultado,ancho_mm):
    """De la chapa acostada a la real: `(x, y)` pasa a `(ancho − y, x)`, un
    cuarto de vuelta antihorario. Las piezas, que Sparrow juntó contra el
    borde de la `x` chica, quedan abajo (la `y` chica, como en el DXF) y el
    sobrante arriba. El ángulo no cambia: este cuarto de vuelta cancela el
    de `_acostar`, y por eso la veta se respeta."""
    ancho=Decimal(ancho_mm)
    return replace(resultado,posiciones=[replace(p,
        x_mm=ancho-(p.y_mm+p.alto_colocado_mm),y_mm=p.x_mm,
        ancho_colocado_mm=p.alto_colocado_mm,alto_colocado_mm=p.ancho_colocado_mm,
        centro_libre_x_mm=ancho-p.centro_libre_y_mm,centro_libre_y_mm=p.centro_libre_x_mm,
    ) for p in resultado.posiciones])

def anidar_sparrow(piezas,geometrias,plancha,params,opciones=None,cancelada=lambda:False,al_avanzar=None,nombre='el cálculo'):
    """`nombre` dice en el registro de qué es lo que escribió Sparrow: «el
    anidado #14», «la comparación (1220×2440 mm)» (A17)."""
    opciones=opciones or OpcionesSparrow()
    if opciones.sobrante=='arriba':
        # Sparrow llena una franja del alto de la chapa, contra un borde de
        # los cortos. Para que las piezas se junten a lo largo del lado
        # largo y el sobrante quede como bloque de todo el ancho, se anida
        # con la chapa y las piezas acostadas, y se endereza (A12).
        acostadas={k:_acostar(g) for k,g in geometrias.items()}
        resultado=anidar_sparrow(piezas,acostadas,Plancha(plancha.alto_mm,plancha.ancho_mm),params,
                                 replace(opciones,sobrante='costado'),cancelada,al_avanzar,nombre)
        return _enderezar(resultado,plancha.ancho_mm)
    entrada=preparar_entrada(piezas,geometrias,plancha,params,opciones)
    with tempfile.TemporaryDirectory(prefix='carteleria-sparrow-',dir=config.carpeta_temporal()) as d:
        inp,out=Path(d)/'entrada.json',Path(d)/'salida.json'
        inp.write_text(json.dumps(entrada),encoding='utf8')
        # En Windows el worker escribiría su error en cp1252, y la «í» de
        # `cartelería` en el traceback rompía la lectura y tapaba la causa.
        # `replace`: lo que escriba una biblioteca nativa sin pasar por
        # Python tampoco puede taparla.
        with (Path(d)/'worker.log').open('w+',encoding='utf8',errors='replace') as log:
            proc=subprocess.Popen([sys.executable,'-m','app.services.nesting.sparrow_worker',str(inp),str(out)],stdout=log,stderr=log,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
            start=time.monotonic()
            # Lo último que se leyó bien del progreso: si el archivo está a
            # medias, queda esto y el tiempo se informa igual.
            leido={};ultima_lectura=None
            try:
                while proc.poll() is None:
                    if cancelada():raise ErrorPrevisto('Anidado cancelado.')
                    ahora=time.monotonic()
                    if ahora-start>opciones.tiempo_maximo_s:
                        if out.exists():
                            proc.kill(); proc.wait()
                            return _lo_que_dejo_el_worker(entrada,out,'Se usó todo el tiempo de búsqueda: este es el mejor resultado que encontró. Con más tiempo puede salir mejor.')
                        raise TiempoAgotado(opciones.tiempo_maximo_s)
                    if al_avanzar is not None and (ultima_lectura is None or ahora-ultima_lectura>=_LEER_PROGRESO_CADA_S):
                        ultima_lectura=ahora
                        leido=_leer_progreso(out) or leido
                        al_avanzar({**leido,'segundos':round(ahora-start,1),'maximo':opciones.tiempo_maximo_s})
                    time.sleep(0.1)
                if proc.returncode!=0:
                    # Si ya había escrito un anidado, una falla posterior
                    # no lo tira: el worker escribe solo resultados validados.
                    log.seek(0);escrito=log.read()
                    if out.exists():
                        # La causa no va en el aviso: queda en el registro del servidor (abajo).
                        return _lo_que_dejo_el_worker(entrada,out,'El cálculo se cortó antes de terminar: este es el mejor resultado completo que había encontrado.')
                    raise CalculoInterrumpido(escrito[-2000:])
                return _lo_que_dejo_el_worker(entrada,out)
            finally:
                if proc.poll() is None:proc.kill()
                proc.wait()
                # Lo técnico de los avisos (y de cualquier falla) no va a la
                # pantalla: queda acá, en el registro del servidor (A9).
                log.seek(0);escrito=log.read().strip()
                if escrito:registro().warning('Lo que escribió Sparrow en %s:\n%s',nombre,escrito[-4000:])
