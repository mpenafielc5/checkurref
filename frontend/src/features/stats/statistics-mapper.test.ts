import { describe, expect, it } from "vitest";
import { toStatistics } from "./statistics-mapper";

const COUNTS = {
  verificada: 5,
  discrepancia: 0,
  contradiccion: 0,
  sin_respaldo: 1,
  no_verificable: 3,
  error_consulta: 2,
};

describe("toStatistics", () => {
  it("traduce las cifras del estudiante y separa los errores de consulta", () => {
    const statistics = toStatistics({
      role: "estudiante",
      works: 2,
      references: 11,
      average_index: 72.5,
      most_different_field: "anio",
      counts: COUNTS,
    });

    expect(statistics).toEqual({
      role: "estudiante",
      works: 2,
      references: 11,
      averageIndex: 72.5,
      mostDifferentField: "anio",
      counts: {
        verificada: 5,
        discrepancia: 0,
        contradiccion: 0,
        sin_respaldo: 1,
        no_verificable: 3,
      },
      queryErrors: 2,
    });
  });

  it("acepta un estudiante sin promedio ni campo", () => {
    const statistics = toStatistics({
      role: "estudiante",
      works: 0,
      references: 0,
      average_index: null,
      most_different_field: null,
      counts: {},
    });

    expect(statistics).toMatchObject({ averageIndex: null, mostDifferentField: null, works: 0 });
  });

  it("traduce las cifras del docente", () => {
    const statistics = toStatistics({
      role: "docente",
      batches: 3,
      works: 8,
      references: 20,
      high_risk_works: 2,
      counts: COUNTS,
    });

    expect(statistics).toMatchObject({ role: "docente", batches: 3, highRiskWorks: 2 });
  });

  it("traduce las cifras del administrador", () => {
    const statistics = toStatistics({
      role: "admin",
      users: { todos: 10, estudiante: 7, docente: 2, admin: 1 },
      documents: 12,
      references: 20,
      counts: COUNTS,
    });

    expect(statistics).toMatchObject({
      role: "admin",
      documents: 12,
      queryErrors: 2,
      users: { estudiante: 7, docente: 2, admin: 1 },
    });
  });

  it("una respuesta inesperada devuelve null", () => {
    expect(toStatistics({ role: "rector", references: 1, counts: {} })).toBeNull();
    expect(toStatistics({ role: "docente", references: 1, counts: {} })).toBeNull();
    expect(toStatistics(null)).toBeNull();
  });
});
