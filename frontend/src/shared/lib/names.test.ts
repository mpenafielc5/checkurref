import { describe, expect, it } from "vitest";
import { displayFullName } from "./names";

describe("displayFullName", () => {
  it("pasa los nombres en mayúsculas a mayúscula inicial", () => {
    expect(displayFullName("LUCÍA ÁVILA PEÑA MORA")).toBe("Lucía Ávila Peña Mora");
  });

  it("deja en minúscula las partículas de los apellidos, salvo al inicio", () => {
    expect(displayFullName("ANA DE LA TORRE Y VERA")).toBe("Ana de la Torre y Vera");
    expect(displayFullName("de la Cruz Luis")).toBe("De la Cruz Luis");
  });

  it("ignora los espacios de más", () => {
    expect(displayFullName("  luis   vera ")).toBe("Luis Vera");
  });
});
