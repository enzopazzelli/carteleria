import { Link } from "react-router-dom";
import { urlMiniatura, type EstadoPaso, type Tarjeta } from "../../api/inicio";
import { fechaDeTarjeta, renglonesDeChapas, rutaDelDestino, textoDelPresupuesto } from "./formato";

// La tarjeta de un trabajo (A16, diseño §5.3): la miniatura del diseño
// pintado, en qué paso quedó, las chapas y el presupuesto. Entera lleva al
// paso que sigue.

const PASOS = [
  { clave: "piezas", nombre: "Piezas" },
  { clave: "grupos", nombre: "Grupos" },
  { clave: "anidado", nombre: "Anidado" },
  { clave: "presupuesto", nombre: "Presupuesto" },
] as const;

const COLOR: Record<EstadoPaso, string> = {
  hecho: "bg-cut",
  a_medias: "bg-bronze",
  error: "bg-conflict",
  pendiente: "bg-line",
};

const EN_PALABRAS: Record<EstadoPaso, string> = {
  hecho: "hecho",
  a_medias: "a medias",
  error: "con error",
  pendiente: "pendiente",
};

function BarraDePasos({ pasos }: { pasos: Tarjeta["pasos"] }) {
  return (
    <ol className="grid grid-cols-4 gap-1 mt-3" aria-label="Pasos">
      {PASOS.map((paso) => (
        <li key={paso.clave}>
          <div className={`h-1.5 rounded-full ${COLOR[pasos[paso.clave]]}`} />
          <span className="block text-[11px] text-ink/60 mt-1">
            {paso.nombre}
            <span className="sr-only">: {EN_PALABRAS[pasos[paso.clave]]}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

export default function TarjetaTrabajo({ tarjeta, ahora }: { tarjeta: Tarjeta; ahora: Date }) {
  return (
    <Link
      to={rutaDelDestino(tarjeta.id, tarjeta.destino)}
      className="block rounded border border-line bg-white overflow-hidden hover:border-cut focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cut"
    >
      <img
        src={urlMiniatura(tarjeta.id, tarjeta.tocado_en)}
        alt=""
        className="block w-full aspect-[16/10] border-b border-line"
      />
      <div className="p-3">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="font-medium truncate">{tarjeta.nombre}</h3>
          <span className="text-xs text-ink/60 shrink-0">{fechaDeTarjeta(tarjeta.tocado_en, ahora)}</span>
        </div>
        <BarraDePasos pasos={tarjeta.pasos} />
        <p className="text-sm font-medium mt-2">{tarjeta.frase}</p>
        <ul className={`text-xs mt-2 ${tarjeta.chapas.length ? "text-ink/70" : "text-ink/40"}`}>
          {renglonesDeChapas(tarjeta.chapas).map((renglon) => (
            <li key={renglon} className="truncate">
              {renglon}
            </li>
          ))}
        </ul>
        <p className={`text-xs mt-1 truncate ${tarjeta.presupuesto ? "text-ink/70" : "text-ink/40"}`}>
          {tarjeta.presupuesto ? textoDelPresupuesto(tarjeta.presupuesto) : "Sin presupuesto"}
        </p>
      </div>
    </Link>
  );
}
