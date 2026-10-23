"""Worker aislado: franjas Sparrow -> chapas completas, sin cortar piezas."""
import json,sys,time,math
from pathlib import Path
from shapely.geometry import Polygon
from shapely import affinity
from .geometria_material import poligono_material
from .huecos_primero import AREA_MINIMA_HUECO_MM2, expandir, meter_en_huecos

def formas(data):
    """`(originales, de_busqueda)` por id: el material real de cada pieza,
    con el que se coloca y se valida, y la silueta con la que busca Sparrow."""
    opts=data['options'];width,height=data['width'],data['height']
    reserva=data['gap']/2
    originals={p['id']:poligono_material(p['shell'],p['holes']) for p in data['items']}
    shapes={}
    for p in data['items']:
        shell=Polygon(p['shell']);tol=opts['simplificacion_mm']
        candidate=shell.buffer(tol).simplify(tol,preserve_topology=True) if tol else shell
        fits=False
        # Con giro libre (`None`) se prueba con cuartos de vuelta, como al
        # decidir si la pieza entra en la chapa.
        for a in data['rotations'] or [0,90,180,270]:
            b=affinity.rotate(candidate,a,origin=(0,0)).bounds
            fits |= b[2]-b[0]<=width+1e-8 and b[3]-b[1]<=height+1e-8
        shape=candidate if candidate.geom_type=='Polygon' and candidate.covers(shell) and fits else shell
        # La operación nativa de offset falla con algunos contornos muy
        # pequeños. Reservar aquí medio gap por lado es equivalente y
        # conservador; los contornos originales se validan al terminar.
        shapes[p['id']]=shape.buffer(reserva,join_style=2) if reserva else shape
    return originals,shapes

def franja(ids,originals,shapes,data):
    """Una búsqueda de Sparrow con esas piezas, en una franja del alto de la
    chapa: `[(colocación de Sparrow, material real ya ubicado)]`."""
    import spyrrow
    opts=data['options'];reserva=data['gap']/2
    items=[spyrrow.Item(k,list(shapes[k].exterior.coords),1,data['rotations']) for k in ids]
    config=spyrrow.StripPackingConfig(total_computation_time=opts['segundos_por_busqueda'],num_workers=opts['workers'],seed=opts['semilla'],early_termination=False,min_items_separation=None)
    sol=spyrrow.StripPackingInstance('Carteleria',data['height']+2*reserva+0.001,items).solve(config)
    return [(pi,affinity.translate(affinity.rotate(originals[pi.id],pi.rotation,origin=(0,0)),pi.translation[0],pi.translation[1]-reserva)) for pi in sol.placed_items]

def colocacion(pi,izquierda,data):
    """Dónde queda una pieza en su chapa, tomando `izquierda` (medido en la
    franja) como el borde útil de la chapa."""
    return {'id':pi.id,'rotation':pi.rotation,'tx':pi.translation[0]-izquierda+data['borde'],'ty':pi.translation[1]-data['gap']/2+data['borde']}

def entra_en_una_chapa(ids,originals,shapes,data):
    """Las colocaciones si esas piezas entran juntas en una chapa, o `None`.
    Un `None` no prueba que no entren: Sparrow no lo encontró en
    `segundos_por_busqueda`."""
    parts=franja(ids,originals,shapes,data)
    izquierda=min(g.bounds[0] for _,g in parts)
    if max(g.bounds[2] for _,g in parts)-izquierda>data['width']+0.001:return None
    return [colocacion(pi,izquierda,data) for pi,_ in parts]

def resolver_una_pasada(data):
    width=data['width']
    originals,shapes=formas(data)
    pending=list(shapes);placed=[];sheet=0
    while pending:
        parts=franja(pending,originals,shapes,data)
        bounds=[g.bounds for _,g in parts]
        best=[];offset=0;score=(-1,-1)
        for x in [b[0] for b in bounds]:
            group=[(pi,g) for (pi,g),b in zip(parts,bounds) if b[0]>=x-0.001 and b[2]<=x+width+0.001]
            value=(sum(g.area for _,g in group),len(group))
            if value>score:best=group;offset=x;score=value
        if not best:raise ValueError('No hay piezas completas que entren en una chapa.')
        for pi,g in best:placed.append({**colocacion(pi,offset,data),'sheet':sheet})
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


def por_chapa(placed):
    """Las colocaciones agrupadas por chapa y sin `sheet`, como las recibe
    `vaciar_chapas`."""
    chapas={}
    for q in placed:chapas.setdefault(q['sheet'],[]).append({k:v for k,v in q.items() if k!='sheet'})
    return [chapas[s] for s in sorted(chapas)]

def resolver(data, salida=None):
    from .sparrow import convertir_y_validar, ruta_de_avisos, ruta_de_progreso
    from .sparrow_reparto import vaciar_chapas
    opts=data['options']
    inicio=time.monotonic(); best=None; score=None; duracion=0
    limite=inicio+opts['tiempo_maximo_s']-1
    avisos=[]
    def avisar(texto):
        # Se escriben en el momento: si el supervisor corta por tiempo, ya
        # están. Aparte y de una vez, como el resultado: un archivo a medias
        # no se puede leer. Uno que ya está no se repite.
        if texto in avisos: return
        avisos.append(texto)
        if not salida: return
        ruta=ruta_de_avisos(salida);temporal=ruta.with_suffix('.tmp')
        try:
            temporal.write_text(json.dumps(avisos),encoding='utf8');temporal.replace(ruta)
        except OSError as error:
            print('avisar:',error,file=sys.stderr)  # El aviso es lo de menos: el anidado sigue.
    avance={'fase':None,'pasada':None,'pasadas':opts.get('intentos',3),'mejor_chapas':None}
    def avanzar(**cambios):
        # Para la barra de progreso (A7). Aparte y de una vez, como los
        # avisos; si no se puede escribir, el anidado sigue.
        avance.update(cambios)
        if not salida: return
        ruta=ruta_de_progreso(salida);temporal=ruta.with_suffix('.tmp')
        try:
            temporal.write_text(json.dumps(avance),encoding='utf8');temporal.replace(ruta)
        except OSError as error:
            print('avanzar:',error,file=sys.stderr)
    adentro=[]
    if opts.get('usar_anidado_en_huecos'):
        # Antes de acomodar, las piezas chicas a los huecos de las grandes
        # (A10): lo que entra no ocupa lugar propio. Hasta la mitad del
        # tiempo, para que quede tiempo para acomodar.
        tope=inicio+opts['tiempo_maximo_s']/2
        avanzar(fase='huecos',huecos=0,huecos_total=None)
        try:
            adentro=meter_en_huecos(data['items'],data['gap'],data['rotations'],data.get('area_minima_hueco_mm2',AREA_MINIMA_HUECO_MM2),
                al_avanzar=lambda hechos,total:avanzar(huecos=hechos,huecos_total=total),
                seguir=lambda:time.monotonic()<tope)
        except (KeyboardInterrupt,SystemExit):raise
        except BaseException as error:
            # Viene marcado por defecto: una falla de este paso no tira un
            # anidado que sin huecos sale bien. La causa queda en el
            # registro del worker; el aviso, para quien anida.
            print('meter_en_huecos:',repr(error),file=sys.stderr)
            avisar('No se pudieron meter piezas en los huecos: se acomodó sin aprovecharlos.')
            adentro=[]
        if len(adentro)==1:avisar('1 pieza va adentro del hueco de otra: no ocupa lugar propio en la chapa.')
        elif adentro:avisar(f'{len(adentro)} piezas van adentro de huecos de otras: no ocupan lugar propio en la chapa.')
    # Sparrow acomoda los bloques: cada pieza que quedó afuera, con lo que
    # tiene adentro. Lo de adentro vuelve con `expandir` antes de validar.
    de_adentro={a.id for a in adentro}
    bloques={**data,'items':[p for p in data['items'] if p['id'] not in de_adentro]}
    # Cota física por área exterior: Sparrow reserva las siluetas completas.
    area=sum(Polygon(p['shell']).area for p in bloques['items'])
    minimo=max(1,math.ceil(area/(data['width']*data['height'])))
    def considerar(candidato):
        nonlocal best,score
        completo=expandir(candidato,adentro)
        convertir_y_validar(data,completo)  # Nunca guardar demanda parcial o colocaciones inválidas.
        rank=puntaje(completo,data)
        if score is None or rank<score:
            # Primero se escribe y después se lo da por mejor: si escribir
            # falla, uno peor que este pero mejor que el escrito todavía
            # tiene que poder escribirse.
            if salida:
                temporal=salida.with_suffix('.tmp')
                temporal.write_text(json.dumps(completo),encoding='utf8');temporal.replace(salida)
            best=completo;score=rank
            avanzar(mejor_chapas=score[0])
    for intento in range(opts.get('intentos',3)):
        # No empezar una pasada que no va a terminar antes del límite.
        if intento and time.monotonic()+duracion>=limite: break
        prueba={**bloques,'options':{**opts,'semilla':(opts['semilla']+104729*intento)%2147483648}}
        avanzar(fase='pasada',pasada=intento+1)
        t0=time.monotonic()
        try:
            candidato=resolver_una_pasada(prueba)
            duracion=time.monotonic()-t0
            considerar(candidato)
        except (KeyboardInterrupt,SystemExit):raise
        except BaseException as error:
            # Una pasada que falla o no valida después de la primera no tira
            # lo que ya se encontró. Si falla la primera, no hay nada que
            # conservar.
            if best is None: raise
            print(f'pasada {intento+1}:',repr(error),file=sys.stderr)
            avisar('Una de las vueltas de búsqueda falló: quedó el mejor resultado de las anteriores.')
            break
        if score[0]==minimo: break
        if opts.get('vaciar_chapas',True):
            avanzar(fase='vaciar')
            originals,shapes=formas(prueba);reserva=data['gap']/2
            try:
                for chapas in vaciar_chapas(
                    por_chapa(candidato),
                    lambda k:shapes[k].area,
                    (data['width']+2*reserva)*(data['height']+2*reserva),
                    lambda ids:entra_en_una_chapa(ids,originals,shapes,prueba),
                    lambda:time.monotonic()+opts['segundos_por_busqueda']<limite,
                ):
                    considerar([{**q,'sheet':s} for s,chapa in enumerate(chapas) for q in chapa])
                    if score[0]==minimo: break
            except (KeyboardInterrupt,SystemExit):raise
            except BaseException as error:
                # La etapa es una mejora: si falla o entrega algo que no
                # valida, vale el mejor resultado ya guardado. Se ataja
                # `BaseException` porque spyrrow avisa sus fallas internas
                # con `PanicException`, que no desciende de `Exception`.
                print('vaciar_chapas:',error,file=sys.stderr)
                avisar('No se pudo terminar de vaciar chapas: este es el mejor resultado completo que encontró.')
            if score[0]==minimo: break
    return best

if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
    resolver(data,Path(sys.argv[2]))
