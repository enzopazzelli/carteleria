import { describe, expect, it } from "vitest";
import { giroLibreSeAplica } from "./giroLibre";

describe("giroLibreSeAplica", () => {
  it("no, con veta: el material solo gira media vuelta", () => {
    expect(giroLibreSeAplica("SOLO_0_180")).toBe(false);
  });

  it("sí, sin veta", () => {
    expect(giroLibreSeAplica("LIBRE_0_90")).toBe(true);
  });

  it("sí, mientras no se sabe: el servidor igual no gira libre con veta", () => {
    expect(giroLibreSeAplica(undefined)).toBe(true);
  });
});
