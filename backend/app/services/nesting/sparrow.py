"""Motor Sparrow experimental con proceso aislado y validación original."""
from __future__ import annotations
import json, math, subprocess, sys, tempfile, time
from pathlib import Path
from decimal import Decimal
from dataclasses import dataclass
from shapely.geometry import Polygon, box
from shapely import affinity
from .models import ResultadoAnidado, PosicionPieza, RotacionPermitida
from .geometria_material import poligono_material

class ErrorGeometriaSparrow(ValueError):
    def __init__(self, ids):
        self.piezas_invalidas = ids
        super().__init__(f"Sparrow no puede comparar: {len(ids)} pieza(s) tienen contornos o agujeros inválidos (IDs: {', '.join(ids)}). Revisá las piezas indicadas y corregí el DXF; no se omitió ninguna pieza.")

@dataclass(frozen=True)
class OpcionesSparrow:
    semilla: int = 42
    segundos_por_busqueda: int = 2
    tiempo_maximo_s: int = 120
    workers: int = 2
    simplificacion_mm: float = 0.3
    intentos: int = 3

def _area_util(plancha, params):
    borde = float(params.margen_borde_mm + params.kerf_mm / 2)
    return borde, float(plancha.ancho_mm)-2*borde, float(plancha.alto_mm)-2*borde

def _rotaciones(params):
    return [0,180] if params.rotaciones_permitidas is RotacionPermitida.SOLO_0_180 else [0,90,180,270]

def _entra(shell, rotations, width, height):
    for a in rotations:
        b=affinity.rotate(shell,a,origin=(0,0)).bounds
        if b[2]-b[0]<=width+1e-8 and b[3]-b[1]<=height+1e-8: return True
    return False

def piezas_que_no_entran(piezas, geometrias, plancha, params):
    """Las piezas cuya silueta no entra en el área útil con ninguna rotación
    permitida: el mismo chequeo que `preparar_entrada` hace antes de buscar.
    No se descartan: son las que habría que seccionar (A5) para usar este
    formato. Las que no tienen contorno las rechaza `preparar_entrada`."""
    _, width, height = _area_util(plancha, params)
    rotations = _rotaciones(params)
    return [p.id for p in piezas
            if (g := geometrias.get(p.id)) is not None and g.contorno_local_mm
            and not _entra(Polygon(g.contorno_local_mm), rotations, width, height)]

def preparar_entrada(piezas, geometrias, plancha, params, opciones):
    borde, width, height = _area_util(plancha, params)
    gap = float(params.kerf_mm + params.separacion_piezas_mm)
    if width <= 0 or height <= 0 or min(borde, gap) < 0:
        raise ValueError('Los parámetros no dejan un formato útil válido.')
    rotations = _rotaciones(params)
    items=[]; blocked=[]; invalidas=[]; normalizadas=[]
    for p in piezas:
        g=geometrias.get(p.id)
        if g is None or not g.contorno_local_mm:
            raise ValueError(f'La pieza {p.id} necesita un contorno real para Sparrow.')
        original=Polygon(g.contorno_local_mm,g.agujeros_local_mm)
        try:
            poly=poligono_material(g.contorno_local_mm,g.agujeros_local_mm)
        except ValueError:
            invalidas.append(p.id)
            continue
        if not original.is_valid:
            normalizadas.append(p.id)
        shell=Polygon(g.contorno_local_mm)
        if not _entra(shell, rotations, width, height): blocked.append(p.id)
        for n in range(p.cantidad):
            items.append({'id':f'{p.id}#{n}','shell':list(shell.exterior.coords),'holes':[list(r.coords) for r in original.interiors]})
    if invalidas:
        raise ErrorGeometriaSparrow(invalidas)
    if blocked:
        raise ValueError('Piezas que no entran con el kerf y margen actuales: '+', '.join(blocked)+'. Revisar formato o seccionado; no se omiten piezas.')
    if not items: raise ValueError('No hay piezas para anidar.')
    return {'items':items,'width':width,'height':height,'borde':borde,'gap':gap,'rotations':rotations,'options':vars(opciones),'normalizadas':normalizadas}

def convertir_y_validar(entrada, placed):
    expected={p['id'] for p in entrada['items']}
    ids=[p['id'] for p in placed]
    if len(ids)!=len(expected) or set(ids)!=expected:
        raise ValueError('Sparrow devolvió piezas faltantes o duplicadas.')
    originals={p['id']:poligono_material(p['shell'],p['holes']) for p in entrada['items']}
    border=entrada['borde'];w=entrada['width'];h=entrada['height']
    container=box(border,border,border+w,border+h)
    polys=[]; positions=[]
    for q in placed:
        values=[q['tx'],q['ty'],q['rotation']]
        if not all(math.isfinite(v) for v in values) or not isinstance(q['sheet'],int) or q['sheet']<0:
            raise ValueError('Colocación inválida devuelta por Sparrow.')
        q = dict(q)
        angle = q['rotation'] % 360
        allowed = min(entrada['rotations'], key=lambda a: abs((angle-a+180)%360-180))
        if abs((angle-allowed+180)%360-180)>0.001:
            raise ValueError('Rotación no permitida devuelta por Sparrow.')
        q['rotation'] = allowed
        original=originals[q['id']]
        rotated=affinity.rotate(original,q['rotation'],origin=(0,0))
        poly=affinity.translate(rotated,q['tx'],q['ty'])
        x0,y0,x1,y1=poly.bounds
        # Solo corrige deriva submilimétrica de traslación; valida de nuevo luego.
        dx=max(border-x0,min(0,border+w-x1));dy=max(border-y0,min(0,border+h-y1))
        if abs(dx)>0.002 or abs(dy)>0.002:
            raise ValueError('Una pieza sale del formato útil.')
        poly=affinity.translate(poly,dx,dy)
        if poly.difference(container).area>0.01: raise ValueError('Una pieza invade el margen/kerf del borde.')
        bounds=poly.bounds
        for other, otherq, otherbounds in polys:
            if otherq['sheet']!=q['sheet']: continue
            gap=entrada['gap']
            if (bounds[0]-otherbounds[2]>gap or otherbounds[0]-bounds[2]>gap or
                bounds[1]-otherbounds[3]>gap or otherbounds[1]-bounds[3]>gap):
                continue
            if poly.intersection(other).area>0.01 or poly.distance(other)<entrada['gap']-0.01:
                raise ValueError('El resultado viola la separación o superpone piezas.')
        polys.append((poly,q,bounds));x0,y0,x1,y1=bounds
        ox0,oy0,ox1,oy1=original.bounds
        cx,cy=(ox0+ox1)/2,(oy0+oy1)/2
        rad=math.radians(q['rotation'])
        centerx=cx*math.cos(rad)-cy*math.sin(rad)+q['tx']+dx
        centery=cx*math.sin(rad)+cy*math.cos(rad)+q['ty']+dy
        positions.append(PosicionPieza(q['id'],q['sheet'],Decimal(str(x0)),Decimal(str(y0)),Decimal(str(x1-x0)),Decimal(str(y1-y0)),False,Decimal(str(q['rotation'])),Decimal(str(centerx)),Decimal(str(centery))))
    sheets={p.plancha_indice for p in positions}
    if sheets!=set(range(len(sheets))):raise ValueError('Índices de chapa inconsistentes.')
    avisos=['Sparrow experimental: no anida dentro de agujeros; resultado validado con geometría original.']
    if entrada.get('normalizadas'):
        avisos.append(f"Se unificaron huecos superpuestos o tangentes para calcular {len(entrada['normalizadas'])} pieza(s) (IDs: {', '.join(entrada['normalizadas'])}). Se conservaron todas las piezas y los contornos guardados del DXF.")
    return ResultadoAnidado(positions,len(sheets),avisos)

def anidar_sparrow(piezas,geometrias,plancha,params,opciones=None,cancelada=lambda:False):
    opciones=opciones or OpcionesSparrow()
    entrada=preparar_entrada(piezas,geometrias,plancha,params,opciones)
    with tempfile.TemporaryDirectory(prefix='carteleria-sparrow-') as d:
        inp,out=Path(d)/'entrada.json',Path(d)/'salida.json'
        inp.write_text(json.dumps(entrada),encoding='utf8')
        with (Path(d)/'worker.log').open('w+',encoding='utf8') as log:
            proc=subprocess.Popen([sys.executable,'-m','app.services.nesting.sparrow_worker',str(inp),str(out)],stdout=log,stderr=log)
            start=time.monotonic()
            try:
                while proc.poll() is None:
                    if cancelada():raise ValueError('Anidado cancelado.')
                    if time.monotonic()-start>opciones.tiempo_maximo_s:
                        if out.exists():
                            proc.kill(); proc.wait()
                            result=convertir_y_validar(entrada,json.loads(out.read_text(encoding='utf8')))
                            return ResultadoAnidado(result.posiciones,result.planchas_usadas,[*result.advertencias,'Se alcanzó el límite de búsqueda: se conserva el mejor anidado completo y validado, sin omitir piezas.'])
                        raise ValueError('Sparrow excedió el tiempo máximo; no se guardó un plano parcial.')
                    time.sleep(0.1)
                if proc.returncode!=0:
                    log.seek(0);raise ValueError('Sparrow no pudo calcular: '+log.read()[-2000:])
                return convertir_y_validar(entrada,json.loads(out.read_text(encoding='utf8')))
            finally:
                if proc.poll() is None:proc.kill()
                proc.wait()
