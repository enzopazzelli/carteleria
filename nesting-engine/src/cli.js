#!/usr/bin/env node
/**
 * CLI del motor: JSON por stdin, JSON por stdout.
 *
 * Es a propósito la interfaz más tonta posible. En la Fase 0 lo que importa es
 * poder medir el motor, no la infraestructura: un proceso por corrida, sin
 * servidor, sin puertos, sin Docker. El wrapper HTTP (Fastify) es la Fase 1, y
 * recién se justifica si esto rinde.
 *
 * El progreso va por stderr para no ensuciar el JSON de stdout.
 *
 *   node src/cli.js < payload.json > resultado.json
 *   node src/cli.js --entrada payload.json --salida resultado.json
 */
"use strict";

const fs = require("node:fs");
const { nest } = require("./index");

function leerArgumento(nombre) {
  const i = process.argv.indexOf(nombre);
  return i !== -1 ? process.argv[i + 1] : null;
}

function leerEntrada() {
  const ruta = leerArgumento("--entrada");
  if (ruta) return fs.readFileSync(ruta, "utf8");
  if (process.stdin.isTTY) {
    throw new Error("Sin entrada. Usar `--entrada archivo.json` o pasar el JSON por stdin.");
  }
  return fs.readFileSync(0, "utf8");
}

function main() {
  const silencioso = process.argv.includes("--silencioso");
  let ultimaFase = null;

  const alProgresar = silencioso
    ? null
    : (fase, fraccion) => {
        if (fase !== ultimaFase) {
          if (ultimaFase) process.stderr.write("\n");
          process.stderr.write(`[${fase}] `);
          ultimaFase = fase;
        }
        if (fraccion >= 0) process.stderr.write(`${Math.round(fraccion * 100)}% `);
      };

  const entrada = JSON.parse(leerEntrada());
  const resultado = nest(entrada, alProgresar);

  if (!silencioso && ultimaFase) process.stderr.write("\n");

  const salida = JSON.stringify(resultado, null, 2);
  const rutaSalida = leerArgumento("--salida");
  if (rutaSalida) {
    fs.writeFileSync(rutaSalida, salida + "\n");
    process.stderr.write(`Resultado en ${rutaSalida}\n`);
  } else {
    process.stdout.write(salida + "\n");
  }
}

try {
  main();
} catch (error) {
  process.stderr.write(`ERROR: ${error.message}\n`);
  process.exit(1);
}
