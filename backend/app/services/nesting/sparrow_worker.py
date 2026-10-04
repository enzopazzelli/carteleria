"""Worker aislado: franjas Sparrow -> chapas completas, sin cortar piezas."""
import json,sys,time,math
from pathlib import Path
from shapely.geometry import Polygon
from shapely import affinity
from .geometria_material import poligono_material

def resolver_una_pasada(data):
    import spyrrow
    opts=data['options'];width,height=data['width'],data['height']
    reserva=data['gap']/2
    originals={p['id']:poligono_material(p['shell'],p['holes']) for p in data['items']}
    shapes={}
    for p in data['items']:
        shell=Polygon(p['shell']);tol=opts['simplificacion_mm']
        candidate=shell.buffer(tol).simplify(tol,preserve_topology=True) if tol else shell
        fits=False
        for a in data['rotations']:
            b=affinity.rotate(candidate,a,origin=(0,0)).bounds
            fits |= b[2]-b[0]<=width+1e-8 and b[3]-b[1]<=height+1e-8
        shape=candidate if candidate.geom_type=='Polygon' and candidate.covers(shell) and fits else shell
        # La operación nativa de offset falla con algunos contornos muy
        # pequeños. Reservar aquí medio gap por lado es equivalente y
        # conservador; los contornos originales se validan al terminar.
        shapes[p['id']]=shape.buffer(reserva,join_style=2) if reserva else shape
    pending=list(shapes);placed=[];sheet=0
    while pending:
        items=[spyrrow.Item(k,list(shapes[k].exterior.coords),1,data['rotations']) for k in pending]
        config=spyrrow.StripPackingConfig(total_computation_time=opts['segundos_por_busqueda'],num_workers=opts['workers'],seed=opts['semilla'],early_termination=False,min_items_separation=None)
        sol=spyrrow.StripPackingInstance('Carteleria',height+2*reserva+0.001,items).solve(config)
        parts=[(pi,affinity.translate(affinity.rotate(originals[pi.id],pi.rotation,origin=(0,0)),pi.translation[0],pi.translation[1]-reserva)) for pi in sol.placed_items]
        bounds=[g.bounds for _,g in parts]
        best=[];offset=0;score=(-1,-1)
        for x in [b[0] for b in bounds]:
            group=[(pi,g) for (pi,g),b in zip(parts,bounds) if b[0]>=x-0.001 and b[2]<=x+width+0.001]
            value=(sum(g.area for _,g in group),len(group))
            if value>score:best=group;offset=x;score=value
        if not best:raise ValueError('No hay piezas completas que entren en una chapa.')
        for pi,g in best:placed.append({'id':pi.id,'sheet':sheet,'rotation':pi.rotation,'tx':pi.translation[0]-offset+data['borde'],'ty':pi.translation[1]-reserva+data['borde']})
        selected={pi.id for pi,_ in best};pending=[k for k in pending if k not in selected];sheet+=1
    return placed


def puntaje(placed, data):
    """Menos planchas primero; empate: menor zona ocupada para conservar retazos."""
    shapes={p['id']:Polygon(p['shell']) for p in data['items']}
    bounds={}
    for p in placed:
        g=affinity.translate(affinity.rotate(shapes[p['id']],p['rotation'],origin=(0,0)),p['tx'],p['ty'])
        b=g.bounds
        old=bounds.get(p['sheet'],b)
        bounds[p['sheet']]=(min(old[0],b[0]),min(old[1],b[1]),max(old[2],b[2]),max(old[3],b[3]))
    return len(bounds),sum((b[2]-b[0])*(b[3]-b[1]) for b in bounds.values())


def resolver(data, salida=None):
    from .sparrow import convertir_y_validar
    inicio=time.monotonic(); best=None; score=None
    # Cota física por área exterior: Sparrow reserva las siluetas completas.
    area=sum(Polygon(p['shell']).area for p in data['items'])
    minimo=max(1,math.ceil(area/(data['width']*data['height'])))
    for intento in range(data['options'].get('intentos',3)):
        if intento and time.monotonic()-inicio >= data['options']['tiempo_maximo_s']-1: break
        prueba={**data,'options':{**data['options'],'semilla':(data['options']['semilla']+104729*intento)%2147483648}}
        candidato=resolver_una_pasada(prueba)
        convertir_y_validar(data,candidato)  # Nunca guardar demanda parcial o colocaciones inválidas.
        rank=puntaje(candidato,data)
        if score is None or rank<score:
            best=candidato;score=rank
            if salida:
                temporal=salida.with_suffix('.tmp')
                temporal.write_text(json.dumps(best),encoding='utf8');temporal.replace(salida)
        if score[0]==minimo: break
    return best

if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
    resolver(data,Path(sys.argv[2]))
