import { createBrowserRouter, RouterProvider } from "react-router-dom";
import TrabajosLista from "./routes/TrabajosLista";

const router = createBrowserRouter([{ path: "/", element: <TrabajosLista /> }]);

export default function App() {
  return <RouterProvider router={router} />;
}
