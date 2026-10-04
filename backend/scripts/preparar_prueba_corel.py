"""Copia local de la prueba: verifica escala por bboxes del CDR y conserva el original."""
import json
import struct
import sys
import zipfile
import argparse
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.modelos.base import inicializar, Sesion
from app.modelos.trabajo import Trabajo, GrupoDeCorte, Pieza

parser = argparse.ArgumentParser(description="Verifica la corrección de escala ×10 contra un Corel y crea una copia del trabajo.")
parser.add_argument("archivo", type=Path, help="Archivo CDR con contenedor ZIP")
parser.add_argument("--trabajo-id", type=int, required=True)
args = parser.parse_args()
archivo = args.archivo
with zipfile.ZipFile(archivo) as z:
    root = z.read("content/root.dat")
    streams = [z.read("content/data/" + n) for n in z.read("content/dataFileList.dat").decode().splitlines()]
    medidas = []
    def recorrer(lo, hi):
        while lo + 8 <= hi:
            tag = root[lo:lo+4]
            n = struct.unpack_from("<I", root, lo+4)[0]
            fin = lo+8+n
            if fin > hi:
                raise ValueError("RIFF truncado")
            if tag in (b"RIFF", b"LIST"):
                recorrer(lo+12, fin)
            elif tag == b"bbox" and n == 16:
                stream, largo, offset, _ = struct.unpack_from("<4I", root, lo+8)
                if stream < len(streams) and largo >= 16:
                    x0,y0,x1,y1 = struct.unpack_from("<4i", streams[stream], offset)
                    # libcdr CommonParser: coordenada /254000 pulgadas;
                    # convertir a mm equivale a dividir por 10000.
                    medidas.append((abs(x1-x0)/10000, abs(y1-y0)/10000))
            lo = fin + n % 2
    recorrer(0, len(root))

inicializar()
with Sesion() as s:
    origen = s.get(Trabajo, args.trabajo_id)
    if origen is None:
        raise ValueError("No existe el trabajo indicado")
    coincidencias = []
    for p in origen.piezas:
        w,h = float(p.ancho_mm)*10,float(p.alto_mm)*10
        if any(abs(w-a)<.002 and abs(h-b)<.002 for a,b in medidas):
            coincidencias.append({"pieza_id":p.id,"cdr_mm":[w,h],"dxf_mm":[float(p.ancho_mm),float(p.alto_mm)]})
    if len(coincidencias) < 10:
        raise ValueError("No hay suficientes coincidencias para confirmar la escala")
    nombre = origen.nombre + " · escala Corel verificada"
    nuevo = s.scalar(select(Trabajo).where(Trabajo.nombre == nombre))
    if nuevo is None:
        nuevo = Trabajo(nombre=nombre, archivo_origen=origen.archivo_origen,
            archivo_guardado=origen.archivo_guardado, escala_a_mm=(origen.escala_a_mm or Decimal(1))*10)
        s.add(nuevo);s.flush()
        grupos = {}
        for g in origen.grupos:
            clon = GrupoDeCorte(trabajo_id=nuevo.id,nombre=g.nombre,formato_id=g.formato_id,orden=g.orden,parametros_usados=g.parametros_usados)
            s.add(clon);s.flush();grupos[g.id]=clon.id
        def escalar(anillo):
            return [[float(Decimal(str(x))*10),float(Decimal(str(y))*10)] for x,y in anillo]
        for p in origen.piezas:
            s.add(Pieza(trabajo_id=nuevo.id,grupo_id=grupos.get(p.grupo_id),id_origen=p.id_origen,
                cantidad=p.cantidad,ancho_mm=p.ancho_mm*10,alto_mm=p.alto_mm*10,
                contorno_mm=escalar(p.contorno_mm),agujeros_mm=[escalar(a) for a in p.agujeros_mm],
                descartada=p.descartada,contorno_recto=p.contorno_recto))
        s.commit()
    salida = Path(__file__).resolve().parents[1]/"local"/"verificacion-escala-corel.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps({"archivo":str(archivo),"factor":10,"trabajo_original":origen.id,
        "trabajo_corregido":nuevo.id,"coincidencias":coincidencias},ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({"trabajo_id":nuevo.id,"grupos":[g.id for g in nuevo.grupos],"piezas":len(nuevo.piezas),"coincidencias":len(coincidencias)}))
