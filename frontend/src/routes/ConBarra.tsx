import { Outlet } from "react-router-dom";
import AvisoDeConsultas from "../components/AvisoDeConsultas";
import Barra from "../components/Barra";

/** Todas las pantallas van debajo de la barra fija (A16), y del aviso de lo
 * que no pudo cargar (A17). */
export default function ConBarra() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <Barra />
      <AvisoDeConsultas />
      <Outlet />
    </div>
  );
}
