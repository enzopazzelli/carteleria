// Cuentas puras del dibujo de una lectura (cómo leyó el sistema un DXF,
// antes de cargarlo). Sin React: se prueban solas.

import type { Correcciones, FormaLeida, Lectura } from "../../api/piezasYgrupos";

export interface Caja {
  minX: number;
  minY: number;
  ancho: number;
  alto: number;
}

/**
 * La caja que contiene a todas las formas, en mm del dibujo.
 *
 * Sin formas, o con una sola línea sin ancho, devuelve una caja de al
 * menos 1 × 1: un `viewBox` de lado cero no dibuja nada.
 */
export function cajaDelDibujo(formas: FormaLeida[]): Caja {
  const puntos = formas.flatMap((forma) => forma.contorno_mm);
  if (puntos.length === 0) return { minX: 0, minY: 0, ancho: 1, alto: 1 };
  const xs = puntos.map(([x]) => x);
  const ys = puntos.map(([, y]) => y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  return { minX, minY, ancho: Math.max(Math.max(...xs) - minX, 1), alto: Math.max(Math.max(...ys) - minY, 1) };
}

const centesimas = (valor: number) => Math.round(valor * 100) / 100;

/**
 * El `d` de un `<path>` con el contorno de la forma y sus huecos,
 * medido desde la esquina de arriba a la izquierda de la caja.
 *
 * La Y se da vuelta: en el DXF crece hacia arriba y en la pantalla,
 * hacia abajo. Sin eso el dibujo sale cabeza abajo. Con
 * `fillRule="evenodd"` los huecos quedan vacíos.
 */
export function trazo(forma: FormaLeida, caja: Caja): string {
  const arriba = caja.minY + caja.alto;
  return [forma.contorno_mm, ...forma.agujeros_mm]
    .filter((anillo) => anillo.length > 2)
    .map(
      (anillo) =>
        anillo
          .map(([x, y], i) => `${i === 0 ? "M" : "L"}${centesimas(x - caja.minX)} ${centesimas(arriba - y)}`)
          .join(" ") + " Z",
    )
    .join(" ");
}

/** «17 piezas a cortar · 2 entran descartadas · 15 no van». Lo que vale
 * cero no se nombra, salvo las piezas a cortar. */
export function resumenDeLectura(lectura: Pick<Lectura, "a_cortar" | "descartadas" | "no_van">): string {
  const partes = [lectura.a_cortar === 1 ? "1 pieza a cortar" : `${lectura.a_cortar} piezas a cortar`];
  if (lectura.descartadas > 0) {
    partes.push(lectura.descartadas === 1 ? "1 entra descartada" : `${lectura.descartadas} entran descartadas`);
  }
  if (lectura.no_van > 0) partes.push(lectura.no_van === 1 ? "1 no va" : `${lectura.no_van} no van`);
  return partes.join(" · ");
}

/** Sin nada para cortar no se carga: cargar reemplaza las piezas del
 * trabajo, y eso lo dejaría vacío. */
export function sePuedeCargar(lectura: Pick<Lectura, "a_cortar">): boolean {
  return lectura.a_cortar > 0;
}

/**
 * El nombre de una forma como se muestra: su número en el archivo, sin
 * el nombre del archivo. «trabajo-1-497» es «497»; lo que sigue a una
 * barra se conserva («39/unida», «39/hueco7»).
 */
export function nombreCorto(idOrigen: string): string {
  const [base, ...resto] = idOrigen.split("/");
  return [base.split("-").pop(), ...resto].join("/");
}

/**
 * La lista de correcciones después de tocar una forma.
 *
 * Tocar una forma sin corregir la fuerza a lo contrario de lo que se ve:
 * la que se corta pasa a «no va»; la que no se corta, a «cortar». Otro
 * clic sobre la que se forzó a cortar la saca («no va»): es el camino
 * para un recorte que no era un hueco, como la mitad de una letra
 * dibujada dos veces. Tocar una que se sacó le quita la corrección, y
 * vuelve a decidir el sistema.
 *
 * Una forma que se ve «no va» y no tiene marca es de un dibujo anterior
 * al último clic (el segundo de un doble clic rápido): devuelve la misma
 * lista, sin tocar.
 */
export function alTocar(correcciones: Correcciones, forma: Pick<FormaLeida, "id_origen" | "estado">): Correcciones {
  const marca = correcciones[forma.id_origen];
  if (marca === "no_va") return sinCorreccion(correcciones, forma.id_origen);
  if (marca === "cortar") return { ...correcciones, [forma.id_origen]: "no_va" };
  if (forma.estado === "no_va") return correcciones;
  return { ...correcciones, [forma.id_origen]: forma.estado === "se_corta" ? "no_va" : "cortar" };
}

/** La lista sin la corrección de esa forma. */
export function sinCorreccion(correcciones: Correcciones, idOrigen: string): Correcciones {
  return Object.fromEntries(Object.entries(correcciones).filter(([id]) => id !== idOrigen));
}

const MARCA_EN_PALABRAS = { cortar: "se corta", no_va: "no va" };

/**
 * Las correcciones como se listan debajo del dibujo: «497 no va»,
 * «519 se corta». Solo las de formas que están en la lectura que se ve:
 * la pieza unida no existe en la lectura sin unir, y nombrarla ahí no
 * diría nada. Su corrección no se pierde, vuelve al cambiar de lectura.
 */
export function correccionesALaVista(
  correcciones: Correcciones,
  formas: Pick<FormaLeida, "id_origen">[],
): { id: string; texto: string }[] {
  const aLaVista = new Set(formas.map((forma) => forma.id_origen));
  return Object.entries(correcciones)
    .filter(([id]) => aLaVista.has(id))
    .map(([id, marca]) => ({ id, texto: `${nombreCorto(id)} ${MARCA_EN_PALABRAS[marca]}` }));
}

function medida(forma: FormaLeida): { ancho: number; alto: number } {
  const { ancho, alto } = cajaDelDibujo([forma]);
  return { ancho, alto };
}

/**
 * Las formas en el orden en que hay que dibujarlas; la última queda
 * arriba y recibe el clic.
 *
 * Primero, al fondo, las que no van: así el rayado no tapa lo que se
 * corta, y de dos formas dibujadas en el mismo lugar (una chapa sobre
 * un contorno) la que se sacó deja a la otra a la vista y a mano.
 * Dentro de cada grupo, de la más grande a la más chica: se puede tocar
 * una letra que está adentro de un contorno.
 */
export function enOrdenDeDibujo(formas: FormaLeida[]): FormaLeida[] {
  const area = (forma: FormaLeida) => {
    const { ancho, alto } = medida(forma);
    return ancho * alto;
  };
  const alFondo = (forma: FormaLeida) => (forma.estado === "no_va" ? 0 : 1);
  return [...formas].sort((a, b) => alFondo(a) - alFondo(b) || area(b) - area(a));
}

const ESTADO_EN_PALABRAS = { se_corta: "se corta", descartada: "entra descartada", no_va: "no va" };

/** Lo que se lee al pasar el mouse por una forma: «497 · 1203 × 506 mm ·
 * no va: lo marcó quien carga». */
export function descripcion(forma: FormaLeida): string {
  const { ancho, alto } = medida(forma);
  const estado = ESTADO_EN_PALABRAS[forma.estado] + (forma.motivo ? `: ${forma.motivo}` : "");
  return `${nombreCorto(forma.id_origen)} · ${Math.round(ancho)} × ${Math.round(alto)} mm · ${estado}`;
}

// --- Acercar y mover ---------------------------------------------------------
//
// La vista es el recuadro del dibujo que se ve, en las mismas unidades que
// `trazo`: milímetros desde la esquina de arriba a la izquierda de la caja.

/** `PAR-53`. Cuánto se puede acercar el dibujo. Es donde el detalle con
 * que viaja (`PAR-52`) llega a un píxel de error. */
export const AUMENTO_MAXIMO = 20;

export interface Vista {
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

/** El dibujo entero, con un margen del 2 % de su lado mayor. */
export function vistaEntera(caja: Caja): Vista {
  const margen = Math.max(caja.ancho, caja.alto) * 0.02;
  return { x: -margen, y: -margen, ancho: caja.ancho + 2 * margen, alto: caja.alto + 2 * margen };
}

const entre = (valor: number, minimo: number, maximo: number) => Math.min(Math.max(valor, minimo), maximo);

function adentro(vista: Vista, entera: Vista): Vista {
  return {
    ...vista,
    x: entre(vista.x, entera.x, entera.x + entera.ancho - vista.ancho),
    y: entre(vista.y, entera.y, entera.y + entera.alto - vista.alto),
  };
}

/**
 * La vista acercada `factor` veces (menos de 1 aleja), dejando quieto el
 * punto (x, y) del dibujo, que es donde está el puntero. No acerca más
 * que `AUMENTO_MAXIMO` ni muestra más que el dibujo entero.
 */
export function acercar(vista: Vista, entera: Vista, factor: number, x: number, y: number): Vista {
  const ancho = entre(vista.ancho / factor, entera.ancho / AUMENTO_MAXIMO, entera.ancho);
  if (ancho === entera.ancho) return entera;
  const alto = (ancho * entera.alto) / entera.ancho;
  const queda = ancho / vista.ancho;
  return adentro({ x: x - (x - vista.x) * queda, y: y - (y - vista.y) * queda, ancho, alto }, entera);
}

/**
 * La vista corrida al arrastrar (dx, dy) milímetros del dibujo: el
 * dibujo sigue a la mano, así que la vista va para el otro lado. No se
 * sale del dibujo entero.
 */
export function mover(vista: Vista, entera: Vista, dx: number, dy: number): Vista {
  return adentro({ ...vista, x: vista.x - dx, y: vista.y - dy }, entera);
}

/** Soltar a menos de 4 píxeles de donde se apretó es un clic; más lejos,
 * se estaba arrastrando el dibujo. */
export function fueUnClic(dxPx: number, dyPx: number): boolean {
  return Math.hypot(dxPx, dyPx) < 4;
}

/**
 * Si la lectura que se pidió es la del archivo y la escala que hay
 * ahora en pantalla. Cambiar cualquiera de los dos la deja vieja: lo
 * que se ve ya no es lo que se cargaría.
 */
export function esLaLecturaDe(
  lectura: { archivo: File; escala: string } | null,
  archivo: File | null,
  escala: string | null,
): boolean {
  return lectura !== null && lectura.archivo === archivo && lectura.escala === escala;
}
