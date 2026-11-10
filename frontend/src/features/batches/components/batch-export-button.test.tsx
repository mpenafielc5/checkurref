import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { downloadTextFile } from "@/shared/lib/download";
import { fetchBatchExport } from "../api";
import { BatchExportButton } from "./batch-export-button";

vi.mock("../api", () => ({ fetchBatchExport: vi.fn() }));
vi.mock("@/shared/lib/download", () => ({ downloadTextFile: vi.fn() }));

const fetchMock = vi.mocked(fetchBatchExport);
const downloadMock = vi.mocked(downloadTextFile);

function exportButton(): HTMLButtonElement {
  return screen.getByRole<HTMLButtonElement>("button");
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("BatchExportButton", () => {
  it("descarga el archivo con el nombre del lote", async () => {
    fetchMock.mockResolvedValue({ kind: "ready", batch: { name: "Metodología 5B", works: [] } });
    render(<BatchExportButton batchId="lote-1" disabled={false} />);

    fireEvent.click(exportButton());

    await waitFor(() => expect(downloadMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith("lote-1");
    const [fileName, content, type] = downloadMock.mock.calls[0];
    expect(fileName).toBe("resultados-metodologia-5b.csv");
    expect(content.charCodeAt(0)).toBe(0xfeff);
    expect(type).toBe("text/csv;charset=utf-8");
  });

  it("si falla, muestra el motivo, no descarga y se puede reintentar", async () => {
    fetchMock.mockResolvedValue({ kind: "error", message: "No se pudo preparar el archivo." });
    render(<BatchExportButton batchId="lote-1" disabled={false} />);

    fireEvent.click(exportButton());

    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo preparar el archivo.");
    expect(downloadMock).not.toHaveBeenCalled();
    expect(exportButton().disabled).toBe(false);
  });

  it("un lote sin trabajos no se puede exportar", () => {
    render(<BatchExportButton batchId="lote-1" disabled />);

    expect(exportButton().disabled).toBe(true);
  });
});
