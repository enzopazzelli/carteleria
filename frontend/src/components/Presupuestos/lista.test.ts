import { describe, expect, it } from "vitest";
import type { PresupuestoResumido } from "../../api/inicio";
import { filtrarPresupuestos } from "./lista";

const presupuesto = (id: number, codigo: string, cliente: string, trabajo: string | null): PresupuestoResumido => ({
  id,
  codigo,
  cliente,
  trabajo_id: trabajo === null ? null : id,
  trabajo,
  total: "1000.00",
  moneda: "ARS",
  estado: "BORRADOR",
  creado_en: "2026-11-07T15:00:00Z",
  por_debajo: 0,
});

const LISTA = [
  presupuesto(1, "P-2026-0001", "Peña", "Parador"),
  presupuesto(2, "P-2026-0002", "Megacarteles", "Complejo"),
  presupuesto(3, "P-2026-0003", "Rosa Coronel", null),
];

const ids = (lista: PresupuestoResumido[]) => lista.map((p) => p.id);

describe("filtrarPresupuestos", () => {
  it("con el texto vacío devuelve la lista tal cual", () => {
    expect(filtrarPresupuestos(LISTA, "")).toBe(LISTA);
    expect(filtrarPresupuestos(LISTA, "  ")).toBe(LISTA);
  });

  it("busca por código", () => {
    expect(ids(filtrarPresupuestos(LISTA, "0002"))).toEqual([2]);
  });

  it("busca por cliente, con o sin tilde y sin mayúsculas", () => {
    expect(ids(filtrarPresupuestos(LISTA, "pena"))).toEqual([1]);
    expect(ids(filtrarPresupuestos(LISTA, "PEÑA"))).toEqual([1]);
  });

  it("busca por trabajo", () => {
    expect(ids(filtrarPresupuestos(LISTA, "complejo"))).toEqual([2]);
  });

  it("uno sin trabajo se encuentra por los otros campos y no rompe", () => {
    expect(ids(filtrarPresupuestos(LISTA, "coronel"))).toEqual([3]);
    expect(ids(filtrarPresupuestos(LISTA, "parador"))).toEqual([1]);
  });

  it("sin coincidencias, vacía", () => {
    expect(filtrarPresupuestos(LISTA, "zzz")).toEqual([]);
  });
});
