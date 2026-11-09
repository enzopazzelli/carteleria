import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../components/Mensaje/contenido";
import { useSesion } from "../auth/SesionContext";

const CAMPO = "border border-line rounded px-2 py-1 bg-paper w-full";

/** La pantalla de entrada (1.1): usuario, contraseña y si se deja la sesión abierta en este dispositivo.
 * Un error de entrada dice siempre lo mismo, sin aclarar si el usuario existe. */
export default function Entrar() {
  const { yo, cargando, errorDeConexion, entrar } = useSesion();
  const navegar = useNavigate();
  const [usuario, setUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [mantener, setMantener] = useState(false);
  const [error, setError] = useState<QueMostrar | null>(null);
  const [entrando, setEntrando] = useState(false);

  if (yo) return <Navigate to="/" replace />;

  async function alEnviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEntrando(true);
    try {
      await entrar(usuario, contrasena, mantener);
      navegar("/", { replace: true });
    } catch (e) {
      setError(falla(e, "No se pudo entrar."));
      setContrasena("");
    } finally {
      setEntrando(false);
    }
  }

  return (
    <main className="min-h-screen bg-paper text-ink flex items-center justify-center px-4">
      <form onSubmit={alEnviar} className="w-full max-w-sm border border-line rounded p-6 space-y-4">
        <h1 className="font-display italic font-extrabold uppercase tracking-wide text-2xl">Cotizador</h1>
        <p className="text-sm text-ink/70">Entrá con tu usuario y tu contraseña.</p>

        {(error || errorDeConexion) && <Mensaje variante="error" que={(error ?? errorDeConexion)!} />}

        <label className="block text-sm">
          Usuario
          <input
            className={CAMPO}
            value={usuario}
            autoFocus
            autoComplete="username"
            autoCapitalize="none"
            onChange={(e) => setUsuario(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          Contraseña
          <input
            className={CAMPO}
            type="password"
            value={contrasena}
            autoComplete="current-password"
            onChange={(e) => setContrasena(e.target.value)}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={mantener} onChange={(e) => setMantener(e.target.checked)} />
          Mantener la sesión abierta en este dispositivo
        </label>
        <button
          type="submit"
          className="w-full bg-cut text-negro rounded px-3 py-2 text-sm disabled:opacity-50"
          disabled={entrando || cargando || !usuario.trim() || !contrasena}
        >
          Entrar
        </button>
      </form>
    </main>
  );
}
