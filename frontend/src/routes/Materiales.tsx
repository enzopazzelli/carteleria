import { useEffect, useState } from "react";
import type { Catalogo } from "../api/materiales";
import DetalleDelInsumo from "../components/Materiales/DetalleDelInsumo";
import DetalleDelMaterial from "../components/Materiales/DetalleDelMaterial";
import ListaDeCategorias from "../components/Materiales/ListaDeCategorias";
import { diaDeLaPlanilla, filtrarCatalogo, primeraEleccion, type Eleccion } from "../components/Materiales/arbol";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla } from "../components/Mensaje/contenido";
import { cuantos } from "../components/Tarjeta/formato";
import { useCatalogo } from "../hooks/useMateriales";

// La pantalla de Materiales (A18, diseño §5.6, boceto C): a la izquierda las
// categorías; a la derecha, lo elegido entero.

function categoriaDe(catalogo: Catalogo, eleccion: Eleccion): string | undefined {
  if (eleccion.tipo === "material") return eleccion.categoria;
  return catalogo.categorias.find((c) => c.insumos.some((i) => i.codigo === eleccion.codigo))?.nombre;
}

/** Lo elegido, buscado en el catálogo entero: la búsqueda no lo saca de la derecha. */
function LoElegido({ catalogo, eleccion }: { catalogo: Catalogo; eleccion: Eleccion | null }) {
  if (eleccion?.tipo === "material") {
    const material = catalogo.categorias
      .find((c) => c.nombre === eleccion.categoria)
      ?.materiales.find((m) => m.nombre === eleccion.nombre);
    if (material) return <DetalleDelMaterial key={`${eleccion.categoria}-${material.nombre}`} material={material} />;
  }
  if (eleccion?.tipo === "insumo") {
    const categoria = catalogo.categorias.find((c) => c.insumos.some((i) => i.codigo === eleccion.codigo));
    const articulos = categoria?.insumos.filter((i) => i.codigo === eleccion.codigo) ?? [];
    if (categoria && articulos.length > 0) return <DetalleDelInsumo articulos={articulos} categoria={categoria.nombre} />;
  }
  return <p className="text-sm text-ink/60">Elegí un material de la lista.</p>;
}

export default function Materiales() {
  const catalogo = useCatalogo();
  const [eleccion, setEleccion] = useState<Eleccion | null>(null);
  const [abiertas, setAbiertas] = useState<Set<string>>(() => new Set());
  const [busqueda, setBusqueda] = useState("");

  // Al llegar el catálogo: el primer material, con su categoría abierta.
  useEffect(() => {
    if (!catalogo.data || eleccion !== null) return;
    const primera = primeraEleccion(catalogo.data);
    if (primera === null) return;
    setEleccion(primera);
    const categoria = categoriaDe(catalogo.data, primera);
    if (categoria) setAbiertas(new Set([categoria]));
  }, [catalogo.data, eleccion]);

  function abrirOCerrar(categoria: string) {
    setAbiertas((antes) => {
      const ahora = new Set(antes);
      if (ahora.has(categoria)) ahora.delete(categoria);
      else ahora.add(categoria);
      return ahora;
    });
  }

  const carga = catalogo.data?.ultima_carga ?? null;

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-8 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h1 className="text-2xl font-semibold">Materiales</h1>
        {catalogo.data && (
          <div className="flex flex-wrap items-center justify-end gap-3 text-sm text-ink/70">
            <span>
              {carga ? (
                <>
                  Planilla: <b className="text-ink font-medium">{carga.archivo}</b>, cargada el {diaDeLaPlanilla(carga.cargada_en)} ·{" "}
                  {cuantos(carga.articulos, "artículo", "artículos")}
                </>
              ) : (
                "Todavía no se cargó la planilla de precios"
              )}
            </span>
            <button
              type="button"
              className="bg-cut text-paper rounded px-3 py-1.5 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              disabled
              title="Todavía no: llega con la revisión de la planilla"
            >
              Actualizar desde la planilla
            </button>
          </div>
        )}
      </div>

      {catalogo.isLoading && <p className="text-sm text-ink/60">Cargando…</p>}
      {catalogo.error && <Mensaje variante="error" que={falla(catalogo.error, "No se pudieron cargar los materiales.")} />}

      {catalogo.data && (
        <div className="grid gap-6 lg:grid-cols-[18rem_1fr] items-start">
          <div className="lg:sticky lg:top-16 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto">
            <ListaDeCategorias
              catalogo={filtrarCatalogo(catalogo.data, busqueda)}
              busqueda={busqueda}
              alBuscar={setBusqueda}
              abiertas={abiertas}
              alAbrirOCerrar={abrirOCerrar}
              eleccion={eleccion}
              alElegir={setEleccion}
            />
          </div>
          {/* `min-w-0`: sin esto, una tabla ancha estira la columna y la página entera. */}
          <div className="min-w-0">
            <LoElegido catalogo={catalogo.data} eleccion={eleccion} />
          </div>
        </div>
      )}
    </main>
  );
}
