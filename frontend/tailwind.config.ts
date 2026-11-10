import type { Config } from "tailwindcss";

// La marca (propuesta aprobada el 2026-11-09): barra negra, naranja para lo que se toca, contenido claro.
// Los nombres de los colores se conservan: casi todas las pantallas los usan por nombre.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Fondo, letra y divisiones.
        paper: "#F4F4F2",
        ink: "#1A1A1A",
        line: "#DCDCD8",
        // El negro de la marca: la barra de arriba y la letra de los botones naranjas. Con letra blanca el
        // naranja da contraste 3,1 (no alcanza); con este negro, 6,3.
        negro: "#0D0D0D",
        // El naranja de la marca, para fondos, bordes y lo seleccionado. Nunca para letra sobre fondo claro.
        cut: "#FF5D00",
        // El naranja para letra y enlaces sobre fondo claro (contraste 5,8 sobre blanco).
        cuttext: "#B83A00",
        // Avisos y «en curso»: ámbar oscuro, legible como letra y como fondo con letra clara.
        bronze: "#8A6100",
        conflict: "#C8102E",
        // «Listo», «hecho», «aprobado»: el verde de los estados. El naranja queda para las acciones.
        ok: "#1F7A3D",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
        // La letra de la marca (cursiva ancha, como el logo): solo el nombre de la barra y los títulos de entrada.
        display: ["Exo 2", "IBM Plex Sans", "system-ui", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "8px",
      },
    },
  },
  plugins: [],
} satisfies Config;
