import { NavLink } from "react-router-dom";

// La barra fija de arriba, en todas las pantallas (A16, diseño §5.1).
// Cada lugar tiene su pantalla (Materiales desde A18). Desde A26, sin login ni
// presupuesto: no hay usuario, «Mi cuenta», «Cerrar sesión» ni «Presupuestos».

const LUGAR = "h-12 flex items-center px-1 border-b-[3px] pt-[3px] text-sm";

function claseDelLugar({ isActive }: { isActive: boolean }): string {
  return `${LUGAR} ${isActive ? "border-cut text-paper font-medium" : "border-transparent text-paper/70 hover:text-paper"}`;
}

export default function Barra() {
  return (
    <header className="sticky top-0 z-20 h-12 bg-negro text-paper">
      <nav className="h-full max-w-6xl mx-auto px-4 sm:px-8 flex items-center gap-6" aria-label="Secciones">
        <span className="font-display italic font-extrabold uppercase tracking-wide text-[17px] mr-4">Cartelería</span>
        <NavLink to="/" end className={claseDelLugar}>
          Inicio
        </NavLink>
        {/* Sin `end`: dentro de un trabajo también queda marcado Trabajos. */}
        <NavLink to="/trabajos" className={claseDelLugar}>
          Trabajos
        </NavLink>
        <NavLink to="/materiales" className={claseDelLugar}>
          Materiales
        </NavLink>
      </nav>
    </header>
  );
}
