import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // strictPort: el CORS del backend solo acepta http://localhost:5173.
  // Si el puerto está ocupado, Vite se corría solo al 5174 y la app
  // cargaba pero cada llamada a la API fallaba con un error de CORS que
  // no explica nada — mejor que no arranque.
  server: { port: 5173, strictPort: true },
  test: { environment: "node" },
});
