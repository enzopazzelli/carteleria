import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // strictPort: los enlaces y el proxy suponen siempre el mismo puerto. Si estuviera ocupado, Vite se
  // corría solo al 5174 y la app cargaba pero nada funcionaba como se espera: mejor que no arranque.
  server: {
    port: 5173,
    strictPort: true,
    // La pantalla habla con un solo origen (1.1): todo pedido a `/api/...` se reenvía al servidor sacando
    // el prefijo, igual que lo hace el proxy en producción. Así la cookie de sesión viaja sola y el
    // servidor no necesita permitir pedidos de otros orígenes.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (ruta) => ruta.replace(/^\/api/, ""),
      },
    },
  },
  test: { environment: "node" },
});
