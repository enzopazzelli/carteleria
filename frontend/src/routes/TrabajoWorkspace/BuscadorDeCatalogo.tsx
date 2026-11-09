import { useEffect, useState } from "react";
import type { ArticuloDelCatalogo } from "../../api/presupuestos";
import Mensaje from "../../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../../components/Mensaje/contenido";
import { useAgregarDelCatalogo, useBuscarEnElCatalogo } from "../../hooks/usePresupuestos";
import { avisoDeResultados, precioDelArticulo, unidadDeLaCantidad } from "./catalogo";
import { leerCantidad } from "./importes";

const RUBROS = [
  ["INSUMO", "Insumo"],
  ["MANO_DE_OBRA", "Mano de obra"],
  ["FLETE", "Flete"],
  ["INSTALACION", "Instalación"],
  ["OTRO", "Otro"],
] as const;

/** Un momento después de que se deja de escribir, para no pedir al servidor en cada letra. */
function useDespuesDeEscribir(valor: string, ms = 250): string {
  const [lento, setLento] = useState(valor);
  useEffect(() => {
    const espera = setTimeout(() => setLento(valor), ms);
    return () => clearTimeout(espera);
  }, [valor, ms]);
  return lento;
}

/** «Agregar del catálogo» (A23, `docs/historico/A23-materiales-en-el-presupuesto/diseno.md §6`):
 * se busca un artículo de la planilla (corrugado, vinilos, pintura, tornillos, diseño,
 * montaje…), se escribe la cantidad y se agrega como una línea del presupuesto, con el
 * margen de la planilla para el precio sugerido. */
export default function BuscadorDeCatalogo({ presupuestoId }: { presupuestoId: number }) {
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const [categoria, setCategoria] = useState("");
  const [elegido, setElegido] = useState<ArticuloDelCatalogo | null>(null);
  const [cantidad, setCantidad] = useState("1");
  const [rubro, setRubro] = useState("INSUMO");
  const [agregado, setAgregado] = useState<string | null>(null);
  const [error, setError] = useState<QueMostrar | null>(null);

  const consulta = useDespuesDeEscribir(texto);
  const { data, isFetching, isError } = useBuscarEnElCatalogo(consulta, categoria, abierto);
  const agregar = useAgregarDelCatalogo(presupuestoId);

  if (!abierto) {
    return (
      <div className="mb-6">
        <button type="button" className="border border-line rounded px-3 py-1 text-sm hover:bg-line/40" onClick={() => setAbierto(true)}>
          Agregar del catálogo
        </button>
      </div>
    );
  }

  const articulos = data?.articulos ?? [];
  const aviso = data ? avisoDeResultados(articulos.length, data.total) : null;

  function cerrar() {
    setAbierto(false);
    setElegido(null);
    setAgregado(null);
    setError(null);
  }

  function elegir(articulo: ArticuloDelCatalogo) {
    setElegido(articulo);
    setCantidad("1");
    setAgregado(null);
    setError(null);
  }

  async function alAgregar() {
    if (!elegido) return;
    const cuanto = leerCantidad(cantidad);
    if (cuanto === null || Number(cuanto) <= 0) {
      setError("La cantidad tiene que ser un número mayor que 0, como 2 o 1,5.");
      return;
    }
    setError(null);
    try {
      await agregar.mutateAsync({ articulo_id: elegido.id, cantidad: cuanto, rubro });
      setAgregado(`Se agregó «${elegido.descripcion}».`);
      setElegido(null);
    } catch (e) {
      setError(falla(e, "No se pudo agregar el artículo."));
    }
  }

  return (
    <section className="mb-6 border border-line rounded p-3" aria-label="Agregar del catálogo">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <input
          className="border border-line rounded px-2 py-1 bg-paper text-sm flex-1 min-w-48"
          placeholder="Buscar por código o descripción…"
          aria-label="Buscar en el catálogo"
          value={texto}
          autoFocus
          onChange={(e) => {
            setTexto(e.target.value);
            setElegido(null);
          }}
        />
        <select
          className="border border-line rounded px-2 py-1 bg-paper text-sm"
          aria-label="Categoría"
          value={categoria}
          onChange={(e) => {
            setCategoria(e.target.value);
            setElegido(null);
          }}
        >
          <option value="">Todas las categorías</option>
          {data?.categorias.map((c) => (
            <option key={c.valor} value={c.valor}>
              {c.nombre}
            </option>
          ))}
        </select>
        <button type="button" className="text-sm underline" onClick={cerrar}>
          Cerrar
        </button>
      </div>

      {agregado && <p className="text-sm text-cuttext mb-2">{agregado}</p>}
      {error && (
        <div className="mb-2">
          <Mensaje variante="error" que={error} />
        </div>
      )}
      {isError && <p className="text-sm text-conflict mb-2">No se pudo buscar en el catálogo.</p>}

      <ul className={`max-h-64 overflow-auto border border-line rounded divide-y divide-line text-sm ${isFetching ? "opacity-70" : ""}`}>
        {articulos.map((articulo) => (
          <li key={articulo.id}>
            <button
              type="button"
              className={`w-full text-left px-2 py-1.5 flex flex-wrap items-baseline gap-x-3 hover:bg-line/40 ${
                elegido?.id === articulo.id ? "bg-line/60" : ""
              }`}
              onClick={() => elegir(articulo)}
            >
              <span className="font-mono text-xs text-ink/60">{articulo.codigo}</span>
              <span className="flex-1 min-w-48">{articulo.descripcion}</span>
              <span className={`font-mono text-xs whitespace-nowrap ${articulo.costo_unidad_venta === null ? "text-bronze" : ""}`}>
                {precioDelArticulo(articulo)}
              </span>
            </button>
          </li>
        ))}
        {data && articulos.length === 0 && <li className="px-2 py-2 text-ink/60">No hay artículos que cumplan la búsqueda.</li>}
      </ul>
      {aviso && <p className="text-xs text-ink/60 mt-1">{aviso}</p>}

      {elegido && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="font-medium">{elegido.descripcion}</span>
          <label className="flex items-center gap-1">
            Cantidad
            <input
              className="border border-line rounded px-2 py-1 bg-paper w-20 font-mono"
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
            />
            {unidadDeLaCantidad(elegido.unidad_venta)}
          </label>
          <label className="flex items-center gap-1">
            Rubro
            <select className="border border-line rounded px-2 py-1 bg-paper" value={rubro} onChange={(e) => setRubro(e.target.value)}>
              {RUBROS.map(([valor, nombre]) => (
                <option key={valor} value={valor}>
                  {nombre}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="bg-cut text-negro rounded px-3 py-1 disabled:opacity-50"
            disabled={agregar.isPending}
            onClick={() => void alAgregar()}
          >
            Agregar
          </button>
          <button type="button" className="underline" onClick={() => setElegido(null)}>
            Cancelar
          </button>
          {elegido.costo_unidad_venta === null && (
            <span className="text-bronze text-xs">La planilla no trae precio: tendrás que ponerle un valor a mano.</span>
          )}
        </div>
      )}
    </section>
  );
}
