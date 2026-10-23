export interface Punto {
  x: number;
  y: number;
}

export function mmAPx(mm: number, escalaPxPorMm: number): number {
  return mm * escalaPxPorMm;
}

export function pxAMm(px: number, escalaPxPorMm: number): number {
  return px / escalaPxPorMm;
}

/** La altura de un punto de la chapa en la pantalla. En la chapa (y en el
 * DXF) la altura crece hacia arriba; en la pantalla, hacia abajo. Sin
 * darla vuelta, Ajuste mostraba la chapa de cabeza (2026-10-23). */
export function yEnPantalla(yMm: number, altoPlanchaMm: number, escalaPxPorMm: number): number {
  return (altoPlanchaMm - yMm) * escalaPxPorMm;
}

/** La inversa de `yEnPantalla`: de un punto de la pantalla a la altura en la chapa. */
export function yDesdePantalla(yPx: number, altoPlanchaMm: number, escalaPxPorMm: number): number {
  return altoPlanchaMm - yPx / escalaPxPorMm;
}

/** Rota `punto` alrededor de `centro` por `anguloGrados`, sentido
 * antihorario (convención matemática estándar; el SVG invierte Y en
 * pantalla, pero esta función trabaja en el espacio mm, no en píxeles
 * de pantalla — la inversión de eje la hace `yEnPantalla`, al dibujar). */
export function rotarPunto(punto: Punto, centro: Punto, anguloGrados: number): Punto {
  const radianes = (anguloGrados * Math.PI) / 180;
  const coseno = Math.cos(radianes);
  const seno = Math.sin(radianes);
  const dx = punto.x - centro.x;
  const dy = punto.y - centro.y;
  return {
    x: centro.x + dx * coseno - dy * seno,
    y: centro.y + dx * seno + dy * coseno,
  };
}
