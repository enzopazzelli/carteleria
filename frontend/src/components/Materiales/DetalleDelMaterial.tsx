import { useState } from "react";
import type { Formato } from "../../api/catalogo";
import type { EspesorDelCatalogo, MaterialDelCatalogo, MedidaDelCatalogo } from "../../api/materiales";
import { useCrearRetazo, useQuitarFormato } from "../../hooks/useCatalogo";
import { useCambiarSeAnida, useMarcarProveedor } from "../../hooks/useMateriales";
import { mostrarImporte } from "../../routes/TrabajoWorkspace/importes";
import { MEDIDA_MAXIMA_DE_RETAZO_MM, medida, medidaDeRetazo } from "../ListaDeFormatos/filas";
import Mensaje from "../Mensaje/Mensaje";
import { falla, type QueMostrar } from "../Mensaje/contenido";
import CorteDelEspesor from "./CorteDelEspesor";
import LoQueDiceLaPlanilla from "./LoQueDiceLaPlanilla";
import { marcasDeLaMedida, nombreParaMostrar } from "./arbol";

// Un material que se corta, a la derecha de la pantalla de Materiales (A18,
// diseño §5.6, boceto C).

const SECCION = "text-xs uppercase tracking-wider text-ink/60 font-semibold mt-5 mb-2";
const BOTON_CHICO = "border border-line bg-white rounded px-2 py-0.5 text-xs hover:bg-line/40 disabled:opacity-40";

function Marca({ texto }: { texto: string }) {
  return <span className="ml-1.5 inline-block rounded border border-bronze/50 bg-bronze/10 px-1 font-sans text-[11px] text-bronze">{texto}</span>;
}

/** Todo lo que cambia algo pasa por acá, para mostrar el error arriba. */
type Hacer = (accion: () => Promise<unknown>, siFalla: string) => Promise<void>;

export default function DetalleDelMaterial({ material }: { material: MaterialDelCatalogo }) {
  const [error, setError] = useState<QueMostrar | null>(null);
  const cambiarSeAnida = useCambiarSeAnida();

  const hacer: Hacer = async (accion, siFalla) => {
    setError(null);
    try {
      await accion();
    } catch (e) {
      setError(falla(e, siFalla));
    }
  };

  const medidas = material.espesores.flatMap((espesor) => espesor.medidas);
  const articulos = medidas.flatMap((m) => m.proveedores.map((p) => p.articulo));
  const proveedores = [...new Set(articulos.filter((a) => a.en_ultima_planilla).map((a) => a.proveedor))];
  // «Se anida» se guarda por espesor: la casilla los cambia todos juntos.
  const seAnidan = material.espesores.filter((espesor) => espesor.material.nesteable_por_area).length;
  const todosSeAnidan = seAnidan === material.espesores.length;

  return (
    <article className="rounded border border-line bg-white p-4 sm:p-5">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-lg font-semibold">{nombreParaMostrar(material.nombre)}</h2>
        <span className="text-sm text-ink/60">{proveedores.length > 0 ? proveedores.join(" · ") : "sin proveedor en la planilla"}</span>
        <label className="ml-auto flex items-center gap-1.5 text-sm">
          <input
            type="checkbox"
            checked={todosSeAnidan}
            ref={(nodo) => {
              if (nodo) nodo.indeterminate = seAnidan > 0 && !todosSeAnidan;
            }}
            disabled={cambiarSeAnida.isPending}
            onChange={(e) => {
              const valor = e.target.checked;
              void hacer(async () => {
                for (const espesor of material.espesores) {
                  await cambiarSeAnida.mutateAsync({ materialId: espesor.material.id, valor });
                }
              }, "No se pudo cambiar si se anida.");
            }}
          />
          Se anida
        </label>
      </header>

      {error && (
        <div className="mt-3">
          <Mensaje variante="error" que={error} />
        </div>
      )}

      <h3 className={SECCION}>Corte (se cambia acá)</h3>
      <div>
        {material.espesores.map((espesor) => (
          <CorteDelEspesor key={espesor.material.id} espesor={espesor} todos={material.espesores} />
        ))}
      </div>

      <h3 className={SECCION}>Medidas</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-ink/60 border-b border-line">
              <th className="py-1.5 pr-3 font-medium">Espesor</th>
              <th className="pr-3 font-medium">Medida (mm)</th>
              <th className="pr-3 font-medium">Código</th>
              <th className="pr-3 font-medium">Proveedor</th>
              <th className="pr-3 font-medium text-right">Costo por m²</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {material.espesores.flatMap((espesor) =>
              espesor.medidas.map((m) => <RenglonesDeLaMedida key={m.formato.id} espesor={espesor} medida={m} hacer={hacer} />),
            )}
          </tbody>
        </table>
      </div>
      {medidas.length === 0 && <p className="text-sm text-ink/60 mt-2">No tiene medidas cargadas.</p>}

      <LoQueDiceLaPlanilla articulos={articulos} />
    </article>
  );
}

function RenglonesDeLaMedida({ espesor, medida: m, hacer }: { espesor: EspesorDelCatalogo; medida: MedidaDelCatalogo; hacer: Hacer }) {
  const marcar = useMarcarProveedor();
  const quitar = useQuitarFormato();
  const [agregando, setAgregando] = useState(false);
  const { formato } = m;
  const queCuenta = m.proveedores.find((p) => p.cuenta) ?? m.proveedores[0];
  const otros = m.proveedores.filter((p) => p !== queCuenta);
  const sePuedeElegir = !m.ya_no_esta && m.proveedores.length > 1;
  const celda = "py-1.5 pr-3 align-top";

  function alQuitar(retazo: Formato) {
    if (!window.confirm(`¿Quitar el retazo de ${medida(retazo)} mm?`)) return;
    void hacer(() => quitar.mutateAsync({ formatoId: retazo.id, materialId: retazo.material_id }), "No se pudo quitar el retazo.");
  }

  return (
    <>
      <tr className="border-t border-line/60">
        <td className={celda}>{espesor.material.espesor ?? "—"}</td>
        <td className={`${celda} font-mono whitespace-nowrap`}>{medida(formato)}</td>
        <td className={`${celda} font-mono`}>{formato.codigo ?? "—"}</td>
        <td className={celda}>
          {queCuenta?.proveedor ?? "—"}
          {sePuedeElegir && <span className="ml-1.5 text-xs text-cut font-medium">el que cuenta</span>}
          {sePuedeElegir && m.proveedor_a_mano !== null && (
            <button
              type="button"
              className="ml-2 text-xs underline text-ink/70"
              disabled={marcar.isPending}
              onClick={() =>
                void hacer(() => marcar.mutateAsync({ formatoId: formato.id, proveedor: null }), "No se pudo volver a automático.")
              }
            >
              Volver a automático
            </button>
          )}
        </td>
        <td className={`${celda} text-right`}>
          {formato.costo_unidad_venta !== null && (
            <span className="font-mono whitespace-nowrap">{mostrarImporte(formato.costo_unidad_venta, formato.moneda ?? "ARS")}</span>
          )}
          {marcasDeLaMedida(m).map((marca) => (
            <Marca key={marca} texto={marca} />
          ))}
        </td>
        <td className={`${celda} text-right whitespace-nowrap`}>
          {!formato.es_retazo && (
            <button type="button" className={BOTON_CHICO} onClick={() => setAgregando(true)} disabled={agregando}>
              + Retazo
            </button>
          )}
        </td>
      </tr>

      {otros.map((otro) => (
        <tr key={otro.proveedor} className="text-ink/70">
          <td className={celda}></td>
          <td className={celda}></td>
          <td className={celda}></td>
          <td className={celda}>{otro.proveedor}</td>
          <td className={`${celda} text-right whitespace-nowrap font-mono`}>
            {otro.articulo.costo_unidad_venta === null ? <Marca texto="sin precio" /> : mostrarImporte(otro.articulo.costo_unidad_venta, "ARS")}
          </td>
          <td className={`${celda} text-right`}>
            {sePuedeElegir && (
              <button
                type="button"
                className={BOTON_CHICO}
                disabled={marcar.isPending}
                onClick={() =>
                  void hacer(
                    () => marcar.mutateAsync({ formatoId: formato.id, proveedor: otro.proveedor }),
                    "No se pudo cambiar el proveedor.",
                  )
                }
              >
                Usar este
              </button>
            )}
          </td>
        </tr>
      ))}

      {m.retazos.map((retazo) => (
        <tr key={retazo.id} className="bg-paper/60 text-ink/70 text-xs">
          <td className={celda}></td>
          <td className={`${celda} whitespace-nowrap`} colSpan={2}>
            Retazo <span className="font-mono">{medida(retazo)}</span>
          </td>
          <td className={celda}></td>
          <td className={`${celda} text-right font-mono`}>
            {retazo.costo_unidad_venta !== null && mostrarImporte(retazo.costo_unidad_venta, retazo.moneda ?? "ARS")}
          </td>
          <td className={`${celda} text-right whitespace-nowrap`}>
            {retazo.disponible ? (
              <button type="button" className="underline" disabled={quitar.isPending} onClick={() => alQuitar(retazo)}>
                Quitar
              </button>
            ) : (
              <span title="Se quitó, pero el grupo de un trabajo lo sigue usando">quitado, en uso</span>
            )}
          </td>
        </tr>
      ))}

      {agregando && <NuevoRetazo formato={formato} alTerminar={() => setAgregando(false)} hacer={hacer} />}
    </>
  );
}

/** «+ Retazo»: el ancho y el alto, como en la lista de formatos (A8). */
function NuevoRetazo({ formato, alTerminar, hacer }: { formato: Formato; alTerminar: () => void; hacer: Hacer }) {
  const crear = useCrearRetazo();
  const [ancho, setAncho] = useState("");
  const [alto, setAlto] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);

  function alAgregar() {
    const anchoMm = medidaDeRetazo(ancho);
    const altoMm = medidaDeRetazo(alto);
    if (anchoMm === null || altoMm === null) {
      setAviso(`Ancho y alto en mm: números mayores que 0 y hasta ${MEDIDA_MAXIMA_DE_RETAZO_MM.toLocaleString("es-AR")}.`);
      return;
    }
    setAviso(null);
    void hacer(async () => {
      await crear.mutateAsync({ formatoId: formato.id, anchoMm, altoMm, materialId: formato.material_id });
      alTerminar();
    }, "No se pudo agregar el retazo.");
  }

  return (
    <tr className="bg-paper/60 text-xs">
      <td className="py-1.5"></td>
      <td className="py-1.5 pr-3" colSpan={5}>
        <span className="inline-flex flex-wrap items-center gap-1.5">
          Retazo de
          <input
            className="border border-line rounded p-0.5 w-16 bg-white"
            aria-label="Ancho del retazo (mm)"
            placeholder="ancho"
            value={ancho}
            onChange={(e) => setAncho(e.target.value)}
          />
          ×
          <input
            className="border border-line rounded p-0.5 w-16 bg-white"
            aria-label="Alto del retazo (mm)"
            placeholder="alto"
            value={alto}
            onChange={(e) => setAlto(e.target.value)}
          />
          mm
          <button type="button" className="underline ml-1" disabled={crear.isPending} onClick={alAgregar}>
            Agregar
          </button>
          <button type="button" className="underline" onClick={alTerminar}>
            Cancelar
          </button>
          {aviso && <span className="text-conflict">{aviso}</span>}
        </span>
      </td>
    </tr>
  );
}
