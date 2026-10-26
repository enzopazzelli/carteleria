import { Outlet } from "react-router-dom";
import Barra from "../components/Barra";

/** Todas las pantallas van debajo de la barra fija (A16). */
export default function ConBarra() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <Barra />
      <Outlet />
    </div>
  );
}
