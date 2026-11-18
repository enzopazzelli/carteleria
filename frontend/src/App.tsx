import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import ConBarra from "./routes/ConBarra";
import Inicio from "./routes/Inicio";
import Materiales from "./routes/Materiales";
import Trabajos from "./routes/Trabajos";
import WorkspaceLayout from "./routes/TrabajoWorkspace/WorkspaceLayout";
import PiezasTab from "./routes/TrabajoWorkspace/PiezasTab";
import GruposTab from "./routes/TrabajoWorkspace/GruposTab";
import AnidadoTab from "./routes/TrabajoWorkspace/AnidadoTab";
import ChapasTab from "./routes/TrabajoWorkspace/ChapasTab";

const AL_INICIO = <Navigate to="/" replace />;

const router = createBrowserRouter([
  {
    // Todo va debajo de la barra fija (A16). Sin login desde A26: la app entra directo.
    element: <ConBarra />,
    children: [
      { path: "/", element: <Inicio /> },
      // El login y el presupuesto ya no están (A26): un enlace viejo lleva al inicio.
      { path: "/entrar", element: AL_INICIO },
      { path: "/cuenta", element: AL_INICIO },
      { path: "/usuarios", element: AL_INICIO },
      { path: "/presupuestos", element: AL_INICIO },
      { path: "/trabajos", element: <Trabajos /> },
      { path: "/materiales", element: <Materiales /> },
      {
        path: "/trabajos/:trabajoId",
        element: <WorkspaceLayout />,
        children: [
          { index: true, element: <Navigate to="piezas" replace /> },
          { path: "piezas", element: <PiezasTab /> },
          { path: "grupos", element: <GruposTab /> },
          { path: "anidado", element: <AnidadoTab /> },
          { path: "chapas", element: <ChapasTab /> },
          // Ajuste pasó a ser Chapas (A14): un enlace viejo lleva ahí.
          { path: "ajuste", element: <Navigate to="../chapas" replace /> },
          // Sin presupuesto (A26), el recorrido termina en Chapas: el costeo lleva ahí.
          { path: "costeo", element: <Navigate to="../chapas" replace /> },
        ],
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
