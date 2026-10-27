import { describe, expect, it } from "vitest";
import { pageHref, paginate, parsePage } from "./pagination";

const ITEMS = Array.from({ length: 58 }, (_, index) => index + 1);

describe("parsePage", () => {
  it("acepta enteros positivos", () => {
    expect(parsePage("3")).toBe(3);
  });

  it("devuelve la página 1 ante valores ausentes o inválidos", () => {
    for (const raw of [null, undefined, "", "0", "-2", "1.5", "abc"]) {
      expect(parsePage(raw)).toBe(1);
    }
  });
});

describe("pageHref", () => {
  it("cambia la página y conserva los demás parámetros", () => {
    expect(pageHref("/informe", "veredicto=discrepancia&pagina=1", 2)).toBe(
      "/informe?veredicto=discrepancia&pagina=2",
    );
  });

  it("agrega el ancla del inicio de la lista", () => {
    expect(pageHref("/informe", "", 3, "referencias")).toBe("/informe?pagina=3#referencias");
  });
});

describe("paginate", () => {
  it("corta la página pedida y calcula el rango mostrado", () => {
    const slice = paginate(ITEMS, 2, 10);
    expect(slice.items).toEqual([11, 12, 13, 14, 15, 16, 17, 18, 19, 20]);
    expect(slice).toMatchObject({ page: 2, totalPages: 6, total: 58, first: 11, last: 20 });
  });

  it("la última página puede venir incompleta", () => {
    expect(paginate(ITEMS, 6, 10)).toMatchObject({ first: 51, last: 58 });
  });

  it("una página fuera de rango muestra la última", () => {
    expect(paginate(ITEMS, 99, 10).page).toBe(6);
  });

  it("una lista vacía tiene una sola página y nada que mostrar", () => {
    expect(paginate([], 1, 10)).toMatchObject({ page: 1, totalPages: 1, first: 0, last: 0 });
  });
});
