import type { Catalogo, MaterialDelCatalogo } from "../../api/materiales";
import { articulosDe, nombreParaMostrar, type Eleccion } from "./arbol";

// La columna de la izquierda de Materiales: el buscador y las categorías, que
// se abren y se cierran (A18, diseño §5.6, boceto C).

interface ListaDeCategoriasProps {
  /** Ya filtrado por la búsqueda. */
  catalogo: Catalogo;
  busqueda: string;
  alBuscar: (texto: string) => void;
  abiertas: Set<string>;
  alAbrirOCerrar: (categoria: string) => void;
  eleccion: Eleccion | null;
  alElegir: (eleccion: Eleccion) => void;
}

const ITEM = "w-full flex items-baseline justify-between gap-2 py-1 pr-3 text-left text-sm border-l-4";
const elegido = (si: boolean) =>
  si ? `${ITEM} pl-5 border-cut bg-cut/10 text-cuttext font-medium` : `${ITEM} pl-5 border-transparent text-ink/80 hover:bg-line/30`;

const medidasDe = (material: MaterialDelCatalogo) => material.espesores.reduce((total, espesor) => total + espesor.medidas.length, 0);

export default function ListaDeCategorias({
  catalogo, busqueda, alBuscar, abiertas, alAbrirOCerrar, eleccion, alElegir,
}: ListaDeCategoriasProps) {
  // Buscando, se ve todo lo que coincide sin tener que abrir nada.
  const buscando = busqueda.trim() !== "";
  // Sin planilla no hay artículos que contar: todas dirían 0.
  const conPlanilla = catalogo.ultima_carga !== null;

  return (
    <nav className="rounded border border-line bg-white py-2" aria-label="Categorías de materiales">
      <div className="px-3 pb-2">
        <input
          type="search"
          className="w-full border border-line rounded px-2 py-1.5 text-sm bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-cut"
          placeholder="Buscar…"
          aria-label="Buscar por código o descripción"
          value={busqueda}
          onChange={(e) => alBuscar(e.target.value)}
        />
      </div>
      {catalogo.categorias.length === 0 && (
        <p className="px-3 py-1 text-sm text-ink/60">{buscando ? "Nada coincide con la búsqueda." : "Todavía no hay materiales."}</p>
      )}
      <ul>
        {catalogo.categorias.map((categoria) => {
          const abierta = buscando || abiertas.has(categoria.nombre);
          return (
            <li key={categoria.nombre}>
              <button
                type="button"
                className="w-full flex items-baseline justify-between gap-2 px-3 py-1.5 text-left text-sm font-semibold hover:bg-line/30"
                aria-expanded={abierta}
                onClick={() => alAbrirOCerrar(categoria.nombre)}
                disabled={buscando}
              >
                <span>
                  <span className="inline-block w-3 text-ink/50" aria-hidden>
                    {abierta ? "▾" : "▸"}
                  </span>{" "}
                  {categoria.nombre}
                </span>
                {conPlanilla && <span className="text-xs font-normal text-ink/50">{articulosDe(categoria)}</span>}
              </button>
              {abierta && (
                <ul>
                  {categoria.materiales.map((material) => {
                    const si =
                      eleccion?.tipo === "material" && eleccion.categoria === categoria.nombre && eleccion.nombre === material.nombre;
                    return (
                      <li key={material.nombre}>
                        <button
                          type="button"
                          className={elegido(si)}
                          aria-current={si ? "true" : undefined}
                          onClick={() => alElegir({ tipo: "material", categoria: categoria.nombre, nombre: material.nombre })}
                        >
                          <span>{nombreParaMostrar(material.nombre)}</span>
                          <span className="text-xs">{medidasDe(material)}</span>
                        </button>
                      </li>
                    );
                  })}
                  {categoria.insumos.map((insumo) => {
                    const si = eleccion?.tipo === "insumo" && eleccion.codigo === insumo.codigo && eleccion.proveedor === insumo.proveedor;
                    return (
                      <li key={`${insumo.codigo}-${insumo.proveedor}`}>
                        <button
                          type="button"
                          className={elegido(si)}
                          aria-current={si ? "true" : undefined}
                          onClick={() => alElegir({ tipo: "insumo", codigo: insumo.codigo, proveedor: insumo.proveedor })}
                        >
                          <span className="min-w-0 truncate" title={insumo.descripcion}>
                            {insumo.descripcion}
                          </span>
                          <span className="text-xs text-ink/50 shrink-0">{insumo.proveedor}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
