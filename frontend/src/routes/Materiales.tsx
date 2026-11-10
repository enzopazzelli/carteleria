import { useEffect, useRef, useState } from "react";
import type { Catalogo, Revision } from "../api/materiales";
import DetalleDelInsumo from "../components/Materiales/DetalleDelInsumo";
import DetalleDelMaterial from "../components/Materiales/DetalleDelMaterial";
import ListaDeCategorias from "../components/Materiales/ListaDeCategorias";
import RevisionDePlanilla from "../components/Materiales/RevisionDePlanilla";
import { diaDeLaPlanilla, filtrarCatalogo, primeraEleccion, type Eleccion } from "../components/Materiales/arbol";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../components/Mensaje/contenido";
import { cuantos } from "../components/Tarjeta/formato";
import { useCatalogo, useRevisarPlanilla } from "../hooks/useMateriales";

// La pantalla de Materiales (A18, diseño §5.6, boceto C): a la izquierda las
// categorías; a la derecha, lo elegido entero. Con una planilla subida, la
// revisión ocupa su lugar hasta aplicarla o cancelarla (§5.4).

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
    if (material) {
      return (
        <DetalleDelMaterial
          key={`${eleccion.categoria}-${material.nombre}`}
          material={material}
          hayPlanilla={catalogo.ultima_carga !== null}
        />
      );
    }
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
  const revisar = useRevisarPlanilla();
  const [revision, setRevision] = useState<Revision | null>(null);
  const [errorAlLeer, setErrorAlLeer] = useState<QueMostrar | null>(null);
  const [listo, setListo] = useState<string | null>(null);
  const elegirArchivo = useRef<HTMLInputElement>(null);

  // La revisión y la vuelta a las dos columnas empiezan arriba de todo.
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [revision]);

  async function alElegirArchivo(archivo: File | undefined) {
    if (!archivo) return;
    setErrorAlLeer(null);
    setListo(null);
    try {
      setRevision(await revisar.mutateAsync(archivo));
    } catch (e) {
      setErrorAlLeer(falla(e, "No se pudo leer la planilla."));
    }
  }

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

  if (revision !== null) {
    return (
      <main className="max-w-6xl mx-auto px-4 sm:px-8 py-8">
        <RevisionDePlanilla
          revision={revision}
          alCancelar={() => setRevision(null)}
          alTerminar={(aplicada) => {
            setRevision(null);
            setListo(`Listo: se aplicó la planilla ${aplicada.archivo}.`);
          }}
        />
      </main>
    );
  }

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
              className="bg-cut text-negro rounded px-3 py-1.5 font-medium disabled:opacity-50 disabled:cursor-wait"
              disabled={revisar.isPending}
              onClick={() => elegirArchivo.current?.click()}
            >
              {revisar.isPending ? "Leyendo la planilla…" : "Actualizar desde la planilla"}
            </button>
            <input
              ref={elegirArchivo}
              type="file"
              accept=".xlsx"
              className="hidden"
              aria-label="Planilla de precios (.xlsx)"
              onChange={(e) => {
                void alElegirArchivo(e.target.files?.[0]);
                // Para poder elegir el mismo archivo otra vez.
                e.target.value = "";
              }}
            />
          </div>
        )}
      </div>

      {listo && (
        <p role="status" className="mb-4 rounded border border-cut/40 bg-cut/10 px-3 py-2 text-sm text-cuttext">
          {listo}
        </p>
      )}
      {errorAlLeer && (
        <div className="mb-4">
          <Mensaje variante="error" que={errorAlLeer} />
        </div>
      )}
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
