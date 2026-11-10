import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerdictBreakdown } from "./verdict-breakdown";

const COUNTS = {
  verificada: 3,
  discrepancia: 1,
  contradiccion: 0,
  sin_respaldo: 0,
  no_verificable: 0,
};

describe("VerdictBreakdown", () => {
  it("cada veredicto lleva su nombre, porcentaje y cantidad", () => {
    render(<VerdictBreakdown counts={COUNTS} total={4} />);

    expect(screen.getByText("Verificada")).toBeTruthy();
    expect(screen.getByText("75 % (3)")).toBeTruthy();
    expect(screen.getByText("Contradicción")).toBeTruthy();
    expect(screen.getAllByText("0 % (0)")).toHaveLength(3);
  });

  it("la barra solo dibuja los veredictos presentes, en proporción", () => {
    const { container } = render(<VerdictBreakdown counts={COUNTS} total={4} />);

    const segments = container.querySelectorAll<HTMLElement>('[aria-hidden="true"] > span');
    expect(segments).toHaveLength(2);
    expect(segments[0].style.flexGrow).toBe("3");
    expect(segments[1].style.flexGrow).toBe("1");
  });
});
