import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchOriginalPdfUrl } from "../api";
import { OriginalPdfButton, OriginalPdfProvider, PageLink } from "./original-pdf";

vi.mock("../api", () => ({ fetchOriginalPdfUrl: vi.fn() }));

const fetchMock = vi.mocked(fetchOriginalPdfUrl);
const URL_PDF = "https://storage.ejemplo.test/object/sign/documentos/u/d.pdf?token=t";

function renderWithPdf() {
  return render(
    <OriginalPdfProvider analysisId="a1">
      <OriginalPdfButton />
      <PageLink page={87} />
    </OriginalPdfProvider>,
  );
}

describe("PDF original", () => {
  beforeEach(() => fetchMock.mockReset());

  it("con enlace, el botón y la página abren el PDF en otra pestaña", async () => {
    fetchMock.mockResolvedValue(URL_PDF);
    renderWithPdf();

    const button = await screen.findByRole("link", { name: /Ver PDF original/ });
    expect(button.getAttribute("href")).toBe(URL_PDF);
    expect(button.getAttribute("target")).toBe("_blank");
    expect(button.getAttribute("rel")).toBe("noopener noreferrer");
    const page = screen.getByRole("link", { name: /Página 87/ });
    expect(page.getAttribute("href")).toBe(`${URL_PDF}#page=87`);
    expect(fetchMock).toHaveBeenCalledWith("a1");
  });

  it("sin enlace no hay botón y la página es solo texto", async () => {
    fetchMock.mockResolvedValue(null);
    renderWithPdf();

    expect(await screen.findByText("Página 87")).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();
  });
});
