import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import ConBarra from "./routes/ConBarra";
import Inicio from "./routes/Inicio";
import Materiales from "./routes/Materiales";
import Presupuestos from "./routes/Presupuestos";
import Trabajos from "./routes/Trabajos";
import WorkspaceLayout from "./routes/TrabajoWorkspace/WorkspaceLayout";
import PiezasTab from "./routes/TrabajoWorkspace/PiezasTab";
import GruposTab from "./routes/TrabajoWorkspace/GruposTab";
import AnidadoTab from "./routes/TrabajoWorkspace/AnidadoTab";
import CosteoTab from "./routes/TrabajoWorkspace/CosteoTab";
import ChapasTab from "./routes/TrabajoWorkspace/ChapasTab";

const AL_INICIO = <Navigate to="/" replace />;

const router = createBrowserRouter([
  {
    // Todo va debajo de la barra fija (A16). Sin login desde A26: la app entra directo.
    element: <ConBarra />,
    children: [
      { path: "/", element: <Inicio /> },
      // Las pantallas del login ya no están (A26): un enlace viejo lleva al inicio.
      { path: "/entrar", element: AL_INICIO },
      { path: "/cuenta", element: AL_INICIO },
      { path: "/usuarios", element: AL_INICIO },
      { path: "/trabajos", element: <Trabajos /> },
      { path: "/materiales", element: <Materiales /> },
      { path: "/presupuestos", element: <Presupuestos /> },
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
          { path: "costeo", element: <CosteoTab /> },
        ],
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
