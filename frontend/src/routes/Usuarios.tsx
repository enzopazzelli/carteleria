import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import type { Usuario } from "../api/usuarios";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../components/Mensaje/contenido";
import { administraUsuarios } from "../auth/permisos";
import { useSesion } from "../auth/SesionContext";
import {
  useActualizarUsuario,
  useCrearUsuario,
  useDarDeAlta,
  useDarDeBaja,
  useRestablecerContrasena,
  useUsuarios,
} from "../hooks/useUsuarios";
import { validarUsuarioNuevo } from "./usuariosForm";

const CAMPO = "border border-line rounded px-2 py-1 bg-paper";
const BOTON = "rounded px-3 py-1 text-sm border border-line disabled:opacity-50";

/** La contraseña temporal, **una sola vez**: después solo se puede restablecer. */
interface ContrasenaParaAnotar {
  usuario: string;
  contrasena: string;
}

function AvisoDeContrasena({ aviso, alCerrar }: { aviso: ContrasenaParaAnotar; alCerrar: () => void }) {
  return (
    <div className="mb-4 border border-bronze rounded p-4" role="status">
      <p className="text-sm">
        Contraseña temporal de <strong>{aviso.usuario}</strong>:
      </p>
      <p className="my-2 font-mono text-lg select-all">{aviso.contrasena}</p>
      <p className="text-sm text-ink/70">
        Anotala ahora y pasásela: no se vuelve a mostrar. Va a tener que elegir otra al entrar.
      </p>
      <button type="button" className={`${BOTON} mt-2`} onClick={alCerrar}>
        Ya la anoté
      </button>
    </div>
  );
}

function AltaDePersona({
  alCrear,
  alCancelar,
}: {
  alCrear: (aviso: ContrasenaParaAnotar) => void;
  alCancelar: () => void;
}) {
  const crear = useCrearUsuario();
  const [usuario, setUsuario] = useState("");
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [puedeAprobar, setPuedeAprobar] = useState(false);
  const [administra, setAdministra] = useState(false);
  const [error, setError] = useState<QueMostrar | null>(null);

  async function alEnviar(evento: FormEvent) {
    evento.preventDefault();
    const problema = validarUsuarioNuevo({ usuario, nombre, email });
    if (problema) {
      setError(problema);
      return;
    }
    setError(null);
    try {
      const creado = await crear.mutateAsync({
        usuario: usuario.trim(),
        nombre: nombre.trim(),
        email: email.trim() || null,
        puede_aprobar: puedeAprobar,
        administra_usuarios: administra,
      });
      alCrear({ usuario: creado.usuario, contrasena: creado.contrasena_temporal });
    } catch (e) {
      setError(falla(e, "No se pudo dar de alta a la persona."));
    }
  }

  return (
    <form onSubmit={alEnviar} className="mb-6 border border-line rounded p-4 space-y-3" aria-label="Dar de alta">
      <h2 className="font-medium">Dar de alta a una persona</h2>
      {error && <Mensaje variante="error" que={error} />}
      <div className="flex flex-wrap gap-3">
        <label className="text-sm">
          Usuario
          <input className={`${CAMPO} block`} value={usuario} autoFocus onChange={(e) => setUsuario(e.target.value)} />
        </label>
        <label className="text-sm">
          Nombre
          <input className={`${CAMPO} block`} value={nombre} onChange={(e) => setNombre(e.target.value)} />
        </label>
        <label className="text-sm">
          Email (opcional)
          <input className={`${CAMPO} block`} value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
      </div>
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={puedeAprobar} onChange={(e) => setPuedeAprobar(e.target.checked)} />
          Puede aprobar presupuestos
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={administra} onChange={(e) => setAdministra(e.target.checked)} />
          Puede administrar usuarios
        </label>
      </div>
      <p className="text-sm text-ink/70">El sistema genera una contraseña temporal y te la muestra una sola vez.</p>
      <div className="flex gap-2">
        <button type="submit" className="bg-cut text-negro rounded px-3 py-1 text-sm disabled:opacity-50" disabled={crear.isPending}>
          Dar de alta
        </button>
        <button type="button" className={BOTON} onClick={alCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

function EdicionDeFila({
  persona,
  alTerminar,
  alFallar,
}: {
  persona: Usuario;
  alTerminar: () => void;
  alFallar: (error: QueMostrar) => void;
}) {
  const actualizar = useActualizarUsuario();
  const [nombre, setNombre] = useState(persona.nombre);
  const [email, setEmail] = useState(persona.email ?? "");
  const [puedeAprobar, setPuedeAprobar] = useState(persona.puede_aprobar);
  const [administra, setAdministra] = useState(persona.administra_usuarios);

  async function guardar() {
    try {
      await actualizar.mutateAsync({
        id: persona.id,
        cambios: {
          nombre: nombre.trim(),
          email: email.trim() || null,
          puede_aprobar: puedeAprobar,
          administra_usuarios: administra,
        },
      });
      alTerminar();
    } catch (e) {
      alFallar(falla(e, "No se pudo guardar el cambio."));
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 py-2">
      <input className={CAMPO} aria-label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
      <input className={CAMPO} aria-label="Email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <label className="flex items-center gap-1 text-sm">
        <input type="checkbox" checked={puedeAprobar} onChange={(e) => setPuedeAprobar(e.target.checked)} />
        Aprueba
      </label>
      <label className="flex items-center gap-1 text-sm">
        <input type="checkbox" checked={administra} onChange={(e) => setAdministra(e.target.checked)} />
        Administra
      </label>
      <button type="button" className="bg-cut text-negro rounded px-3 py-1 text-sm disabled:opacity-50" disabled={actualizar.isPending} onClick={() => void guardar()}>
        Guardar
      </button>
      <button type="button" className={BOTON} onClick={alTerminar}>
        Cancelar
      </button>
    </div>
  );
}

function permisosDe(persona: Usuario): string {
  const permisos = [persona.puede_aprobar && "aprueba", persona.administra_usuarios && "administra"].filter(Boolean);
  return permisos.length > 0 ? permisos.join(" y ") : "diseña";
}

/** La pantalla de usuarios (1.1, diseño §4.5): solo la ve quien administra usuarios. */
export default function Usuarios() {
  const { yo } = useSesion();
  const { data: personas = [], isLoading } = useUsuarios();
  const restablecer = useRestablecerContrasena();
  const darDeBaja = useDarDeBaja();
  const darDeAlta = useDarDeAlta();
  const [dandoDeAlta, setDandoDeAlta] = useState(false);
  const [editando, setEditando] = useState<number | null>(null);
  const [aviso, setAviso] = useState<ContrasenaParaAnotar | null>(null);
  const [error, setError] = useState<QueMostrar | null>(null);

  if (!administraUsuarios(yo)) return <Navigate to="/" replace />;

  async function alRestablecer(persona: Usuario) {
    if (!window.confirm(`¿Restablecer la contraseña de ${persona.nombre}? Se le cierran las sesiones abiertas.`)) return;
    setError(null);
    try {
      const { contrasena_temporal } = await restablecer.mutateAsync(persona.id);
      setAviso({ usuario: persona.usuario, contrasena: contrasena_temporal });
    } catch (e) {
      setError(falla(e, "No se pudo restablecer la contraseña."));
    }
  }

  async function alCambiarElAcceso(persona: Usuario) {
    if (persona.activo && !window.confirm(`¿Dar de baja a ${persona.nombre}? Deja de poder entrar al instante.`)) return;
    setError(null);
    try {
      await (persona.activo ? darDeBaja : darDeAlta).mutateAsync(persona.id);
    } catch (e) {
      // Por ejemplo, el aviso de que tiene que quedar al menos un administrador: el servidor lo dice.
      setError(falla(e, "No se pudo cambiar el acceso."));
    }
  }

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-8 py-8">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Usuarios</h1>
        {!dandoDeAlta && (
          <button type="button" className="bg-cut text-negro rounded px-3 py-1 text-sm" onClick={() => setDandoDeAlta(true)}>
            Dar de alta
          </button>
        )}
      </div>

      {aviso && <AvisoDeContrasena aviso={aviso} alCerrar={() => setAviso(null)} />}
      {error && (
        <div className="mb-4">
          <Mensaje variante="error" que={error} />
        </div>
      )}
      {dandoDeAlta && (
        <AltaDePersona
          alCrear={(nuevo) => {
            setAviso(nuevo);
            setDandoDeAlta(false);
          }}
          alCancelar={() => setDandoDeAlta(false)}
        />
      )}

      {isLoading ? (
        <p className="text-ink/70">Cargando…</p>
      ) : (
        <ul className="divide-y divide-line border border-line rounded">
          {personas.map((persona) => (
            <li key={persona.id} className={`px-4 ${persona.activo ? "" : "bg-line/30 text-ink/60"}`}>
              {editando === persona.id ? (
                <EdicionDeFila persona={persona} alTerminar={() => setEditando(null)} alFallar={setError} />
              ) : (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3">
                  <span className="font-medium">{persona.nombre}</span>
                  <span className="font-mono text-sm">{persona.usuario}</span>
                  <span className="text-sm">{permisosDe(persona)}</span>
                  {persona.email && <span className="text-sm">{persona.email}</span>}
                  {!persona.activo && <span className="text-sm">de baja</span>}
                  {persona.activo && persona.debe_cambiar_contrasena && (
                    <span className="text-sm text-bronze">todavía no eligió su contraseña</span>
                  )}
                  <span className="ml-auto flex gap-2">
                    <button type="button" className={BOTON} onClick={() => setEditando(persona.id)}>
                      Editar
                    </button>
                    {persona.activo && (
                      <button type="button" className={BOTON} disabled={restablecer.isPending} onClick={() => void alRestablecer(persona)}>
                        Restablecer contraseña
                      </button>
                    )}
                    <button type="button" className={BOTON} onClick={() => void alCambiarElAcceso(persona)}>
                      {persona.activo ? "Dar de baja" : "Dar de alta"}
                    </button>
                  </span>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
