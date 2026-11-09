import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { SesionProvider } from "./auth/SesionContext";
import ConBarra from "./routes/ConBarra";
import Entrar from "./routes/Entrar";
import Inicio from "./routes/Inicio";
import Materiales from "./routes/Materiales";
import MiCuenta from "./routes/MiCuenta";
import Presupuestos from "./routes/Presupuestos";
import RutaProtegida from "./routes/RutaProtegida";
import Trabajos from "./routes/Trabajos";
import Usuarios from "./routes/Usuarios";
import WorkspaceLayout from "./routes/TrabajoWorkspace/WorkspaceLayout";
import PiezasTab from "./routes/TrabajoWorkspace/PiezasTab";
import GruposTab from "./routes/TrabajoWorkspace/GruposTab";
import AnidadoTab from "./routes/TrabajoWorkspace/AnidadoTab";
import CosteoTab from "./routes/TrabajoWorkspace/CosteoTab";
import ChapasTab from "./routes/TrabajoWorkspace/ChapasTab";

const router = createBrowserRouter([
  // «Entrar» va afuera: es lo único que se ve sin haber entrado (1.1).
  { path: "/entrar", element: <Entrar /> },
  {
    // Todo lo demás exige sesión (1.1)…
    element: <RutaProtegida />,
    children: [
      {
        // …y va debajo de la barra fija (A16).
        element: <ConBarra />,
        children: [
          { path: "/", element: <Inicio /> },
          { path: "/cuenta", element: <MiCuenta /> },
          // Solo la ve quien administra usuarios; sin el permiso lleva al inicio.
          { path: "/usuarios", element: <Usuarios /> },
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
    ],
  },
]);

export default function App() {
  return (
    <SesionProvider>
      <RouterProvider router={router} />
    </SesionProvider>
  );
}
