import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchReport } from "../api";
import { ReportLoader } from "./report-loader";

const replace = vi.fn();

vi.mock("../api", () => ({ fetchReport: vi.fn() }));
vi.mock("next/navigation", () => ({
  useParams: () => ({ analisisId: "a1" }),
  useRouter: () => ({ replace }),
}));

const fetchMock = vi.mocked(fetchReport);

describe("ReportLoader", () => {
  beforeEach(() => {
    replace.mockReset();
    fetchMock.mockReset();
  });

  it("un análisis en curso lleva solo a su progreso, sin aviso ni botón", async () => {
    fetchMock.mockResolvedValue({ kind: "in_progress" });
    render(<ReportLoader listHref="/estudiante/trabajos" />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/estudiante/trabajos/a1/progreso"));
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("sin pantalla de progreso explica la espera y ofrece volver", async () => {
    fetchMock.mockResolvedValue({ kind: "in_progress" });
    render(
      <ReportLoader
        listHref="/docente/lotes/l1"
        backLabel="Volver al tablero del lote"
        hasProgressPage={false}
      />,
    );

    expect(await screen.findByText("El análisis aún no termina")).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "Volver al tablero del lote" }).getAttribute("href"),
    ).toBe("/docente/lotes/l1");
    expect(replace).not.toHaveBeenCalled();
  });

  it("un error muestra el motivo y el regreso a la lista", async () => {
    fetchMock.mockResolvedValue({ kind: "error", message: "No se encontró este informe." });
    render(<ReportLoader listHref="/estudiante/trabajos" />);

    expect((await screen.findByRole("alert")).textContent).toContain(
      "No se encontró este informe.",
    );
    expect(screen.getByRole("link", { name: "Volver a mis trabajos" }).getAttribute("href")).toBe(
      "/estudiante/trabajos",
    );
  });
});
