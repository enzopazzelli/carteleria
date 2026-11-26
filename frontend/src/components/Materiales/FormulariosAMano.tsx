import { useState } from "react";
import type { Material } from "../../api/catalogo";
import type { Categoria, MaterialDelCatalogo } from "../../api/materiales";
import {
  useAgregarMedida,
  useBorrarMaterial,
  useCrearMaterial,
  useEditarMaterial,
} from "../../hooks/useMateriales";
import Mensaje from "../Mensaje/Mensaje";
import { falla, type QueMostrar } from "../Mensaje/contenido";
import { leerMedidaNueva } from "./aMano";
import { nombreParaMostrar } from "./arbol";

// Cargar materiales a mano (A30, docs/A30-materiales-a-mano/diseno.md): un
// material nuevo, otra medida u otro espesor, y cambiar o borrar lo que se
// cargó a mano. Lo que viene de la planilla no se toca: la próxima carga lo pisaría.

const CAMPO = "border border-line rounded px-2 py-1 bg-white text-sm";
const ETIQUETA = "flex flex-col gap-1 text-xs";
const BOTON = "bg-cut text-negro rounded px-3 py-1.5 text-sm font-medium disabled:opacity-50";
const BOTON_CHICO = "border border-line bg-white rounded px-2 py-0.5 text-xs hover:bg-line/40 disabled:opacity-40";

const AVISO_DEL_COSTO =
  "Sin costo por m² el anidado funciona igual, pero no se pueden guardar retazos de esta chapa.";

/** Los cuatro campos de una chapa: espesor, ancho, alto y costo por m². */
function CamposDeLaChapa({
  espesor, setEspesor, ancho, setAncho, alto, setAlto, precio, setPrecio, sinEspesor,
}: {
  espesor: string; setEspesor: (v: string) => void;
  ancho: string; setAncho: (v: string) => void;
  alto: string; setAlto: (v: string) => void;
  precio: string; setPrecio: (v: string) => void;
  sinEspesor?: boolean;
}) {
  return (
    <>
      {!sinEspesor && (
        <label className={ETIQUETA}>
          Espesor (opcional)
          <input className={`${CAMPO} w-28`} placeholder="5 mm" value={espesor} onChange={(e) => setEspesor(e.target.value)} />
        </label>
      )}
      <label className={ETIQUETA}>
        Ancho (mm)
        <input className={`${CAMPO} w-24`} inputMode="decimal" placeholder="1220" value={ancho} onChange={(e) => setAncho(e.target.value)} />
      </label>
      <label className={ETIQUETA}>
        Alto (mm)
        <input className={`${CAMPO} w-24`} inputMode="decimal" placeholder="2440" value={alto} onChange={(e) => setAlto(e.target.value)} />
      </label>
      <label className={ETIQUETA} title={AVISO_DEL_COSTO}>
        Costo por m² (opcional)
        <input className={`${CAMPO} w-32`} inputMode="decimal" placeholder="13720,5" value={precio} onChange={(e) => setPrecio(e.target.value)} />
      </label>
    </>
  );
}

/** «Nuevo material»: el material con su primera medida de chapa. */
export function NuevoMaterial({
  categorias, alCrear, alCancelar,
}: {
  categorias: Categoria[];
  alCrear: (material: Material) => void;
  alCancelar: () => void;
}) {
  const crear = useCrearMaterial();
  const [nombre, setNombre] = useState("");
  const [espesor, setEspesor] = useState("");
  const [ancho, setAncho] = useState("");
  const [alto, setAlto] = useState("");
  const [precio, setPrecio] = useState("");
  const [familia, setFamilia] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [error, setError] = useState<QueMostrar | null>(null);

  async function alGuardar() {
    const leido = leerMedidaNueva({ nombre, espesor, ancho, alto, precio }, true);
    if (!leido.ok) {
      setAviso(leido.aviso);
      return;
    }
    setAviso(null);
    setError(null);
    try {
      const material = await crear.mutateAsync({ ...leido.dato, familia: familia === "" ? null : familia });
      alCrear(material);
    } catch (e) {
      setError(falla(e, "No se pudo crear el material."));
    }
  }

  return (
    <section aria-label="Nuevo material" className="mb-6 rounded border border-line bg-white p-4">
      <h2 className="text-base font-semibold mb-1">Nuevo material</h2>
      <p className="text-sm text-ink/70 mb-3">
        Cargá el material con su primera medida de chapa. Después le podés sumar otras medidas y espesores, y cargarle el corte.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label className={ETIQUETA}>
          Nombre
          <input className={`${CAMPO} w-56`} placeholder="Acero corten" value={nombre} onChange={(e) => setNombre(e.target.value)} />
        </label>
        <CamposDeLaChapa
          espesor={espesor} setEspesor={setEspesor} ancho={ancho} setAncho={setAncho}
          alto={alto} setAlto={setAlto} precio={precio} setPrecio={setPrecio}
        />
        <label className={ETIQUETA}>
          Categoría
          <select className={CAMPO} value={familia} onChange={(e) => setFamilia(e.target.value)}>
            <option value="">Automática (según el nombre)</option>
            {categorias.filter((c) => c.se_corta).map((c) => (
              <option key={c.nombre} value={c.nombre}>{c.nombre}</option>
            ))}
          </select>
        </label>
        <button type="button" className={BOTON} disabled={crear.isPending} onClick={() => void alGuardar()}>
          {crear.isPending ? "Guardando…" : "Crear material"}
        </button>
        <button type="button" className="underline text-sm pb-1.5" onClick={alCancelar}>Cancelar</button>
      </div>
      <p className="mt-2 text-xs text-ink/60">{AVISO_DEL_COSTO}</p>
      {aviso && <p role="alert" className="mt-2 text-sm text-conflict">{aviso}</p>}
      {error && <div className="mt-2"><Mensaje variante="error" que={error} /></div>}
    </section>
  );
}

type Modo = "medida" | "espesor" | "editar" | null;

/** Lo que se hace a mano sobre un material, debajo de sus medidas. */
export function ArreglosAMano({
  material, familia, todoAMano, alCambiarDeNombre,
}: {
  material: MaterialDelCatalogo;
  familia: string;
  /** Todas sus medidas se cargaron a mano: solo así se puede editar o borrar. */
  todoAMano: boolean;
  alCambiarDeNombre: (nombre: string) => void;
}) {
  const [modo, setModo] = useState<Modo>(null);
  const [error, setError] = useState<QueMostrar | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const agregar = useAgregarMedida();
  const crear = useCrearMaterial();
  const editar = useEditarMaterial();
  const borrar = useBorrarMaterial();

  const [espesorElegido, setEspesorElegido] = useState(String(material.espesores[0]?.material.id ?? ""));
  const [espesor, setEspesor] = useState("");
  const [ancho, setAncho] = useState("");
  const [alto, setAlto] = useState("");
  const [precio, setPrecio] = useState("");
  const [nombre, setNombre] = useState(material.nombre);
  const [espesores, setEspesores] = useState<Record<number, string>>(
    Object.fromEntries(material.espesores.map((e) => [e.material.id, e.material.espesor ?? ""])),
  );

  function cerrar() {
    setModo(null);
    setAviso(null);
    setError(null);
    setEspesor("");
    setAncho("");
    setAlto("");
    setPrecio("");
  }

  async function intentar(accion: () => Promise<unknown>, siFalla: string) {
    setError(null);
    try {
      await accion();
      cerrar();
    } catch (e) {
      setError(falla(e, siFalla));
    }
  }

  function alAgregarMedida() {
    const leido = leerMedidaNueva({ espesor: "", ancho, alto, precio }, false);
    if (!leido.ok) return setAviso(leido.aviso);
    setAviso(null);
    void intentar(
      () => agregar.mutateAsync({ materialId: Number(espesorElegido), ancho: leido.dato.ancho, alto: leido.dato.alto, precio: leido.dato.precio }),
      "No se pudo agregar la medida.",
    );
  }

  function alAgregarEspesor() {
    const leido = leerMedidaNueva({ espesor, ancho, alto, precio }, false);
    if (!leido.ok) return setAviso(leido.aviso);
    if (leido.dato.espesor === null) return setAviso("Falta el espesor.");
    setAviso(null);
    void intentar(
      () => crear.mutateAsync({ nombre: material.nombre, familia, espesor: leido.dato.espesor, ancho: leido.dato.ancho, alto: leido.dato.alto, precio: leido.dato.precio }),
      "No se pudo agregar el espesor.",
    );
  }

  function alGuardarCambios() {
    const nombreNuevo = nombre.trim().replace(/\s+/g, " ").toUpperCase();
    if (nombreNuevo === "") return setAviso("El nombre no puede quedar vacío.");
    setAviso(null);
    const pedidos = material.espesores.flatMap((e) => {
      const cambios: { nombre?: string; espesor?: string | null } = {};
      if (nombreNuevo !== material.nombre) cambios.nombre = nombreNuevo;
      const espesorNuevo = (espesores[e.material.id] ?? "").trim().replace(/\s+/g, " ");
      if (espesorNuevo !== (e.material.espesor ?? "")) cambios.espesor = espesorNuevo === "" ? null : espesorNuevo;
      return Object.keys(cambios).length > 0 ? [{ materialId: e.material.id, cambios }] : [];
    });
    void intentar(async () => {
      await editar.mutateAsync(pedidos);
      if (nombreNuevo !== material.nombre) alCambiarDeNombre(nombreNuevo);
    }, "No se pudo guardar el cambio.");
  }

  function alBorrar() {
    const retazos = material.espesores.flatMap((e) => e.medidas.flatMap((m) => m.retazos));
    if (retazos.some((r) => r.disponible && r.estado === "en_uso")) {
      return setError("Tiene retazos en uso en algún trabajo: primero hay que terminar o borrar ese trabajo.");
    }
    if (!window.confirm(`¿Borrar «${nombreParaMostrar(material.nombre)}» con todas sus medidas? Los trabajos que ya lo usan avisan y frenan el borrado.`)) return;
    // De a un espesor: si un grupo usa una medida, el servidor frena y los demás espesores quedan como estaban.
    void (async () => {
      setError(null);
      try {
        for (const e of material.espesores) {
          const formatoIds = e.medidas.flatMap((m) => [m.formato.id, ...m.retazos.map((r) => r.id)]);
          await borrar.mutateAsync({ materialId: e.material.id, formatoIds });
        }
      } catch (e) {
        setError(falla(e, "No se pudo borrar el material."));
      }
    })();
  }

  const ocupado = agregar.isPending || crear.isPending || editar.isPending || borrar.isPending;

  return (
    <div className="mt-4 border-t border-line pt-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-xs uppercase tracking-wider text-ink/60 font-semibold mr-1">Cargar a mano</span>
        <button type="button" className={BOTON_CHICO} disabled={ocupado} onClick={() => { cerrar(); setModo("medida"); }}>
          + Medida
        </button>
        <button type="button" className={BOTON_CHICO} disabled={ocupado} onClick={() => { cerrar(); setModo("espesor"); }}>
          + Espesor
        </button>
        {todoAMano && (
          <>
            <button type="button" className={BOTON_CHICO} disabled={ocupado} onClick={() => { cerrar(); setModo("editar"); }}>
              Editar nombre y espesor
            </button>
            <button type="button" className={BOTON_CHICO} disabled={ocupado} onClick={alBorrar}>
              Borrar material
            </button>
          </>
        )}
      </div>

      {modo === "medida" && (
        <div className="mt-3 flex flex-wrap items-end gap-3">
          {material.espesores.length > 1 && (
            <label className={ETIQUETA}>
              Espesor
              <select className={CAMPO} value={espesorElegido} onChange={(e) => setEspesorElegido(e.target.value)}>
                {material.espesores.map((e) => (
                  <option key={e.material.id} value={e.material.id}>{e.material.espesor ?? "sin espesor"}</option>
                ))}
              </select>
            </label>
          )}
          <CamposDeLaChapa
            sinEspesor espesor="" setEspesor={() => undefined} ancho={ancho} setAncho={setAncho}
            alto={alto} setAlto={setAlto} precio={precio} setPrecio={setPrecio}
          />
          <button type="button" className={BOTON} disabled={ocupado} onClick={alAgregarMedida}>Agregar medida</button>
          <button type="button" className="underline text-sm pb-1.5" onClick={cerrar}>Cancelar</button>
        </div>
      )}

      {modo === "espesor" && (
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <CamposDeLaChapa
            espesor={espesor} setEspesor={setEspesor} ancho={ancho} setAncho={setAncho}
            alto={alto} setAlto={setAlto} precio={precio} setPrecio={setPrecio}
          />
          <button type="button" className={BOTON} disabled={ocupado} onClick={alAgregarEspesor}>Agregar espesor</button>
          <button type="button" className="underline text-sm pb-1.5" onClick={cerrar}>Cancelar</button>
        </div>
      )}

      {modo === "editar" && (
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className={ETIQUETA}>
            Nombre
            <input className={`${CAMPO} w-56`} value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </label>
          {material.espesores.map((e) => (
            <label key={e.material.id} className={ETIQUETA}>
              Espesor {e.material.espesor ? `«${e.material.espesor}»` : "(sin espesor)"}
              <input
                className={`${CAMPO} w-28`}
                value={espesores[e.material.id] ?? ""}
                onChange={(ev) => setEspesores({ ...espesores, [e.material.id]: ev.target.value })}
              />
            </label>
          ))}
          <button type="button" className={BOTON} disabled={ocupado} onClick={alGuardarCambios}>Guardar</button>
          <button type="button" className="underline text-sm pb-1.5" onClick={cerrar}>Cancelar</button>
        </div>
      )}

      {modo !== null && modo !== "editar" && <p className="mt-2 text-xs text-ink/60">{AVISO_DEL_COSTO}</p>}
      {aviso && <p role="alert" className="mt-2 text-sm text-conflict">{aviso}</p>}
      {error && <div className="mt-2"><Mensaje variante="error" que={error} /></div>}
      {!todoAMano && (
        <p className="mt-2 text-xs text-ink/60">
          Este material viene de la planilla: el nombre, el espesor y las medidas se cambian subiendo la planilla nueva.
        </p>
      )}
    </div>
  );
}
