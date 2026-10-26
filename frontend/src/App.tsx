import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import ConBarra from "./routes/ConBarra";
import Inicio from "./routes/Inicio";
import TrabajosLista from "./routes/TrabajosLista";
import WorkspaceLayout from "./routes/TrabajoWorkspace/WorkspaceLayout";
import PiezasTab from "./routes/TrabajoWorkspace/PiezasTab";
import GruposTab from "./routes/TrabajoWorkspace/GruposTab";
import AnidadoTab from "./routes/TrabajoWorkspace/AnidadoTab";
import CosteoTab from "./routes/TrabajoWorkspace/CosteoTab";
import ChapasTab from "./routes/TrabajoWorkspace/ChapasTab";

const router = createBrowserRouter([
  {
    // Todas las pantallas, debajo de la barra fija (A16).
    element: <ConBarra />,
    children: [
      { path: "/", element: <Inicio /> },
      // Hasta la tarea 6 de A16, la lista de siempre.
      { path: "/trabajos", element: <TrabajosLista /> },
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
