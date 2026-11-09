import { NavLink } from "react-router-dom";
import { administraUsuarios } from "../auth/permisos";
import { useSesion } from "../auth/SesionContext";

// La barra fija de arriba, en todas las pantallas (A16, diseño §5.1).
// Cada lugar tiene su pantalla: Materiales desde A18 y Presupuestos desde A19.

const LUGAR = "h-12 flex items-center px-1 border-b-2 text-sm";

function claseDelLugar({ isActive }: { isActive: boolean }): string {
  return `${LUGAR} ${isActive ? "border-cut text-cut font-medium" : "border-transparent hover:text-cut"}`;
}

export default function Barra() {
  const { yo, salir } = useSesion();
  return (
    <header className="sticky top-0 z-20 h-12 bg-paper border-b border-line">
      <nav className="h-full max-w-6xl mx-auto px-4 sm:px-8 flex items-center gap-6" aria-label="Secciones">
        <span className="font-semibold mr-4">Cotizador</span>
        <NavLink to="/" end className={claseDelLugar}>
          Inicio
        </NavLink>
        {/* Sin `end`: dentro de un trabajo también queda marcado Trabajos. */}
        <NavLink to="/trabajos" className={claseDelLugar}>
          Trabajos
        </NavLink>
        <NavLink to="/presupuestos" className={claseDelLugar}>
          Presupuestos
        </NavLink>
        <NavLink to="/materiales" className={claseDelLugar}>
          Materiales
        </NavLink>
        {/* Solo para quien administra usuarios (1.1). */}
        {administraUsuarios(yo) && (
          <NavLink to="/usuarios" className={claseDelLugar}>
            Usuarios
          </NavLink>
        )}
        {/* A la derecha: quién entró, su cuenta y salir (1.1). */}
        {yo && (
          <div className="ml-auto flex items-center gap-4 text-sm">
            <NavLink to="/cuenta" className={claseDelLugar} title="Mi cuenta">
              {yo.nombre}
            </NavLink>
            <button type="button" className="underline hover:text-cut" onClick={() => void salir()}>
              Cerrar sesión
            </button>
          </div>
        )}
      </nav>
    </header>
  );
}
