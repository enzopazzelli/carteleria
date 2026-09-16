import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGrupos } from "../../hooks/useGrupos";
import { usePiezas } from "../../hooks/usePiezas";
import { useEjecucionesDeGrupo, useColocaciones, useAjustarColocacion } from "../../hooks/useNesting";
import { urlPlano, urlDxf } from "../../api/nesting";
import { useFormato } from "../../hooks/useCatalogo";
import PlanoEditor from "../../components/PlanoEditor/PlanoEditor";
import Banner from "../../components/Banner";

export default function AjusteTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: grupos } = useGrupos(id);
  const { data: piezas } = usePiezas(id);
  const [grupoId, setGrupoId] = useState<number | null>(null);
  const { data: historial } = useEjecucionesDeGrupo(grupoId ?? -1);
  const ejecucionDefinitiva = historial?.find((e) => e.es_definitiva) ?? historial?.[0];
  const { data: colocaciones } = useColocaciones(ejecucionDefinitiva?.id ?? null);
  const ajustar = useAjustarColocacion(ejecucionDefinitiva?.id ?? -1);
  const [plancha, setPlancha] = useState(0);
  const [seleccionada, setSeleccionada] = useState<number | null>(null);
  // Guarda el resultado completo de cada ajuste (no solo el motivo) para
  // poder decidir "es inválida" por el booleano `valida` que ya manda el
  // backend con ese propósito, no por si el string de motivo vino vacío.
  const [resultadosAjuste, setResultadosAjuste] = useState<Map<number, { valida: boolean; motivo: string | null }>>(
    new Map()
  );

  const grupoActivo = grupos?.find((g) => g.id === grupoId);
  // Las medidas reales de la plancha salen del catálogo (mapeado del
  // Excel real del cliente, ver B-02 en REGISTRO.md) — nunca un valor
  // de prueba: sin esto el editor dibujaría a una escala inventada.
  const { data: formato } = useFormato(grupoActivo?.formato_id ?? null);

  async function alMover(colocacionId: number, centroXMm: number, centroYMm: number) {
    const resultado = await ajustar.mutateAsync({
      colocacionId,
      datos: { centro_x_mm: centroXMm, centro_y_mm: centroYMm },
    });
    setResultadosAjuste((prev) =>
      new Map(prev).set(colocacionId, { valida: resultado.valida, motivo: resultado.motivo })
    );
  }

  async function alRotar(colocacionId: number, anguloGrados: number) {
    const resultado = await ajustar.mutateAsync({ colocacionId, datos: { angulo_grados: anguloGrados } });
    setResultadosAjuste((prev) =>
      new Map(prev).set(colocacionId, { valida: resultado.valida, motivo: resultado.motivo })
    );
  }

  const invalidas = new Set(
    Array.from(resultadosAjuste.entries())
      .filter(([, resultado]) => !resultado.valida)
      .map(([id]) => id)
  );

  const colocacionesDePlancha = colocaciones?.filter((c) => c.plancha_indice === plancha) ?? [];
  const colocacionSeleccionada = colocacionesDePlancha.find((c) => c.id === seleccionada) ?? null;

  function alRotarSeleccionada(deltaGrados: number) {
    if (!colocacionSeleccionada) return;
    const anguloActual = Number(colocacionSeleccionada.angulo_grados);
    const nuevoAngulo = ((anguloActual + deltaGrados) % 360 + 360) % 360;
    alRotar(colocacionSeleccionada.id, nuevoAngulo);
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Ajuste del plano</h1>

      <select
        className="border border-line rounded px-2 py-1 mb-4 bg-paper"
        value={grupoId ?? ""}
        onChange={(e) => setGrupoId(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Elegí un grupo...</option>
        {grupos?.map((g) => (
          <option key={g.id} value={g.id}>
            {g.nombre}
          </option>
        ))}
      </select>

      {ejecucionDefinitiva?.estado === "lista" && grupoActivo && piezas && (
        <>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-sm">
              Plancha {plancha + 1} de {ejecucionDefinitiva.planchas_usadas}
            </span>
            <button
              className="text-xs underline"
              disabled={plancha === 0}
              onClick={() => setPlancha((p) => p - 1)}
            >
              anterior
            </button>
            <button
              className="text-xs underline"
              disabled={plancha + 1 >= (ejecucionDefinitiva.planchas_usadas ?? 1)}
              onClick={() => setPlancha((p) => p + 1)}
            >
              siguiente
            </button>
            <a
              className="text-xs underline ml-4"
              href={urlPlano(ejecucionDefinitiva.id, plancha)}
              target="_blank"
              rel="noreferrer"
            >
              Ver plano imprimible
            </a>
            <a className="text-xs underline" href={urlDxf(ejecucionDefinitiva.id, plancha)}>
              Descargar DXF de corte
            </a>
          </div>

          {[...resultadosAjuste.values()].some((r) => !r.valida) && (
            <div className="mb-3">
              <Banner variante="aviso">Hay colocaciones marcadas en rojo — pasá el cursor para ver el motivo.</Banner>
            </div>
          )}

          {colocacionSeleccionada && (
            <div className="flex items-center gap-2 mb-3 text-sm">
              <span className="text-ink/60">Pieza seleccionada — rotar:</span>
              <button
                className="border border-line rounded px-2 py-1 hover:bg-line/40"
                onClick={() => alRotarSeleccionada(-90)}
              >
                -90°
              </button>
              <button
                className="border border-line rounded px-2 py-1 hover:bg-line/40"
                onClick={() => alRotarSeleccionada(-15)}
              >
                -15°
              </button>
              <button
                className="border border-line rounded px-2 py-1 hover:bg-line/40"
                onClick={() => alRotarSeleccionada(15)}
              >
                +15°
              </button>
              <button
                className="border border-line rounded px-2 py-1 hover:bg-line/40"
                onClick={() => alRotarSeleccionada(90)}
              >
                +90°
              </button>
            </div>
          )}

          {formato ? (
            <PlanoEditor
              anchoPlanchaMm={Number(formato.ancho_mm)}
              altoPlanchaMm={Number(formato.alto_mm)}
              piezas={piezas}
              colocaciones={colocacionesDePlancha}
              onMover={alMover}
              onRotar={alRotar}
              colocacionesInvalidas={invalidas}
              seleccionada={seleccionada}
              onSeleccionar={setSeleccionada}
            />
          ) : (
            <p className="text-sm text-ink/60">Cargando el formato del grupo...</p>
          )}
        </>
      )}
    </div>
  );
}
