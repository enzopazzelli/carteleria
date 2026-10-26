import { expect, it } from "vitest";
import { urlMiniatura } from "./inicio";

it("la miniatura cambia de dirección cuando se toca el trabajo", () => {
  // Si la dirección no cambia, el navegador muestra la que tenía guardada.
  expect(urlMiniatura(4, "2026-10-24T19:14:00Z")).toBe(
    "http://localhost:8000/trabajos/4/miniatura?v=2026-10-24T19%3A14%3A00Z",
  );
});
