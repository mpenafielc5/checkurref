import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { paginate } from "@/shared/lib/pagination";
import { Pagination } from "./pagination";

const ITEMS = Array.from({ length: 58 }, (_, index) => index);
const PATH = "/estudiante/trabajos/a7f3";

describe("Pagination", () => {
  it("muestra el rango y enlaza a la página anterior y la siguiente", () => {
    render(<Pagination slice={paginate(ITEMS, 2, 10)} pathname={PATH} noun="referencias" />);

    expect(screen.getByText("Mostrando 11–20 de 58 referencias")).toBeTruthy();
    expect(screen.getByText("Página 2 de 6")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Anterior" }).getAttribute("href")).toBe(
      `${PATH}?pagina=1`,
    );
    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe(
      `${PATH}?pagina=3`,
    );
  });

  it("con anchorId, cada enlace vuelve al inicio de la lista", () => {
    render(
      <Pagination
        slice={paginate(ITEMS, 2, 10)}
        pathname={PATH}
        noun="referencias"
        anchorId="referencias"
      />,
    );

    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe(
      `${PATH}?pagina=3#referencias`,
    );
  });

  it("en la primera página no enlaza hacia atrás", () => {
    render(<Pagination slice={paginate(ITEMS, 1, 10)} pathname={PATH} noun="referencias" />);

    expect(screen.queryByRole("link", { name: "Anterior" })).toBeNull();
    expect(screen.getByRole("link", { name: "Siguiente" })).toBeTruthy();
  });

  it("con una sola página solo muestra el rango", () => {
    render(<Pagination slice={paginate([1, 2, 3], 1, 10)} pathname={PATH} noun="referencias" />);

    expect(screen.getByText("Mostrando 1–3 de 3 referencias")).toBeTruthy();
    expect(screen.queryByText(/Página/)).toBeNull();
  });
});
