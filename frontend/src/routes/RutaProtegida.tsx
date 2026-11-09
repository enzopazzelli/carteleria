import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSesion } from "../auth/SesionContext";

/** Todo lo que no es «Entrar» exige haber entrado (1.1). Sin sesión lleva a «Entrar»; si la persona tiene que
 * elegir otra contraseña (la temporal con la que se la dio de alta), no la deja pasar de «Mi cuenta». */
export default function RutaProtegida() {
  const { yo, cargando } = useSesion();
  const { pathname } = useLocation();

  if (cargando) return <p className="p-8 text-ink/70">Cargando…</p>;
  if (!yo) return <Navigate to="/entrar" replace />;
  if (yo.debe_cambiar_contrasena && pathname !== "/cuenta") return <Navigate to="/cuenta" replace />;
  return <Outlet />;
}
