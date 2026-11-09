import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { cambiarContrasena } from "../api/acceso";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../components/Mensaje/contenido";
import { useSesion } from "../auth/SesionContext";
import { validarCambioDeContrasena } from "../auth/cuenta";

const CAMPO = "border border-line rounded px-2 py-1 bg-paper w-full max-w-xs";

/** «Mi cuenta» (1.1): quién sos y cambiar tu contraseña. Quien entró con una temporal no puede ir a otro lado
 * hasta elegir la suya (`RutaProtegida`). */
export default function MiCuenta() {
  const { yo, recargar } = useSesion();
  const navegar = useNavigate();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState<QueMostrar | null>(null);
  const [listo, setListo] = useState(false);
  const [guardando, setGuardando] = useState(false);

  if (!yo) return null;
  const obligatorio = yo.debe_cambiar_contrasena;

  async function alEnviar(evento: FormEvent) {
    evento.preventDefault();
    setListo(false);
    const problema = validarCambioDeContrasena(actual, nueva, repetida);
    if (problema) {
      setError(problema);
      return;
    }
    setError(null);
    setGuardando(true);
    try {
      await cambiarContrasena(actual, nueva);
      setActual("");
      setNueva("");
      setRepetida("");
      await recargar();
      setListo(true);
      if (obligatorio) navegar("/", { replace: true });
    } catch (e) {
      setError(falla(e, "No se pudo cambiar la contraseña."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-8 py-8">
      <h1 className="text-xl font-semibold mb-1">Mi cuenta</h1>
      <p className="text-sm text-ink/70 mb-6">
        {yo.nombre} · <span className="font-mono">{yo.usuario}</span>
        {yo.email ? ` · ${yo.email}` : ""}
      </p>

      {obligatorio && (
        <div className="mb-4">
          <Mensaje variante="aviso" que="Entraste con una contraseña temporal: elegí la tuya para seguir." />
        </div>
      )}

      <form onSubmit={alEnviar} className="space-y-3 max-w-sm">
        <h2 className="font-medium">Cambiar la contraseña</h2>
        {error && <Mensaje variante="error" que={error} />}
        {listo && <p className="text-sm text-bronze">Listo: tu contraseña quedó cambiada.</p>}
        <label className="block text-sm">
          Contraseña actual
          <input className={CAMPO} type="password" value={actual} autoComplete="current-password" onChange={(e) => setActual(e.target.value)} />
        </label>
        <label className="block text-sm">
          Contraseña nueva
          <input className={CAMPO} type="password" value={nueva} autoComplete="new-password" onChange={(e) => setNueva(e.target.value)} />
        </label>
        <label className="block text-sm">
          Repetí la contraseña nueva
          <input className={CAMPO} type="password" value={repetida} autoComplete="new-password" onChange={(e) => setRepetida(e.target.value)} />
        </label>
        <button type="submit" className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50" disabled={guardando}>
          Cambiar la contraseña
        </button>
      </form>
    </main>
  );
}
