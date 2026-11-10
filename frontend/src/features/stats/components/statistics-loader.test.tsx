import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchStatistics } from "../api";
import type { AdminStatistics, StudentStatistics, TeacherStatistics } from "../types";
import { StatisticsLoader } from "./statistics-loader";

vi.mock("../api", () => ({ fetchStatistics: vi.fn() }));

const fetchMock = vi.mocked(fetchStatistics);

const COUNTS = {
  verificada: 6,
  discrepancia: 2,
  contradiccion: 1,
  sin_respaldo: 1,
  no_verificable: 0,
};

const STUDENT: StudentStatistics = {
  role: "estudiante",
  works: 2,
  references: 11,
  averageIndex: 72.456,
  mostDifferentField: "anio",
  counts: COUNTS,
  queryErrors: 1,
};

const TEACHER: TeacherStatistics = {
  role: "docente",
  batches: 3,
  works: 8,
  references: 10,
  highRiskWorks: 2,
  counts: COUNTS,
  queryErrors: 0,
};

const ADMIN: AdminStatistics = {
  role: "admin",
  users: { estudiante: 7, docente: 2, admin: 1 },
  documents: 12,
  references: 13,
  counts: COUNTS,
  queryErrors: 3,
};

function card(label: string): string {
  return screen.getByText(label).parentElement?.textContent ?? "";
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("StatisticsLoader", () => {
  it("el estudiante ve sus trabajos, referencias, índice promedio y campo con más diferencias", async () => {
    fetchMock.mockResolvedValue({ kind: "ready", statistics: STUDENT });
    render(<StatisticsLoader />);

    await screen.findByText("Veredictos acumulados");
    expect(card("Trabajos analizados")).toContain("2");
    expect(card("Referencias revisadas")).toContain("11");
    expect(card("Índice de veracidad promedio")).toContain("72,5");
    expect(card("Campo con más diferencias")).toContain("Año");
    expect(screen.getByText(/1 referencia quedó sin verificar/)).toBeTruthy();
  });

  it("el docente ve lotes, trabajos, referencias y los trabajos de riesgo alto", async () => {
    fetchMock.mockResolvedValue({ kind: "ready", statistics: TEACHER });
    render(<StatisticsLoader />);

    await screen.findByText("Veredictos de tus lotes");
    expect(card("Lotes")).toContain("3");
    expect(card("Trabajos analizados")).toContain("8");
    expect(card("Referencias")).toContain("10");
    expect(card("De riesgo alto")).toContain("2");
    expect(screen.getByText("60 % (6)")).toBeTruthy();
  });

  it("el administrador ve usuarios por rol, documentos, referencias y errores de consulta", async () => {
    fetchMock.mockResolvedValue({ kind: "ready", statistics: ADMIN });
    render(<StatisticsLoader />);

    await screen.findByText("Veredictos globales");
    expect(card("Estudiantes")).toContain("7");
    expect(card("Docentes")).toContain("2");
    expect(card("Administradores")).toContain("1");
    expect(card("Documentos analizados")).toContain("12");
    expect(card("Referencias procesadas")).toContain("13");
    expect(card("Errores de consulta a las fuentes")).toContain("3");
  });

  it("sin análisis terminados no muestra porcentajes vacíos", async () => {
    fetchMock.mockResolvedValue({
      kind: "ready",
      statistics: { ...TEACHER, works: 0, references: 0 },
    });
    render(<StatisticsLoader />);

    expect(await screen.findByText(/cuando termine el primer análisis/)).toBeTruthy();
    expect(screen.queryByText("Veredictos de tus lotes")).toBeNull();
  });

  it("sin promedio ni campo, muestra una raya en lugar de un cero", async () => {
    fetchMock.mockResolvedValue({
      kind: "ready",
      statistics: { ...STUDENT, averageIndex: null, mostDifferentField: null },
    });
    render(<StatisticsLoader />);

    await screen.findByText("Veredictos acumulados");
    expect(card("Índice de veracidad promedio")).toContain("—");
    expect(card("Campo con más diferencias")).toContain("—");
  });

  it("si falla, muestra el motivo", async () => {
    fetchMock.mockResolvedValue({ kind: "error", message: "No se pudo cargar." });
    render(<StatisticsLoader />);

    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar.");
  });

  it("en modo discreto no ocupa lugar si falla o si no hay análisis", async () => {
    fetchMock.mockResolvedValueOnce({ kind: "error", message: "No se pudo cargar." });
    const failed = render(<StatisticsLoader quiet />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("alert")).toBeNull();
    failed.unmount();

    fetchMock.mockResolvedValueOnce({
      kind: "ready",
      statistics: { ...STUDENT, works: 0, references: 0 },
    });
    const { container } = render(<StatisticsLoader quiet />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(container.textContent).toBe("");
  });
});
