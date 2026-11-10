import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LabTabs } from "./lab-tabs";

const route = vi.hoisted(() => ({ search: "", replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin/laboratorio",
  useRouter: () => ({ replace: route.replace }),
  useSearchParams: () => new URLSearchParams(route.search),
}));

const TABS = [
  { id: "comparar", label: "Comparar", content: <p>Panel de comparar</p> },
  { id: "benchmark", label: "Benchmark", content: <p>Panel de benchmark</p> },
];

function selected(): string | undefined {
  return (
    screen.getAllByRole("tab").find((tab) => tab.getAttribute("aria-selected") === "true")
      ?.textContent ?? undefined
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  route.search = "";
});

describe("LabTabs", () => {
  it("sin parámetro o con uno desconocido abre la primera pestaña", () => {
    route.search = "pestana=otra";
    render(<LabTabs tabs={TABS} />);

    expect(selected()).toBe("Comparar");
  });

  it("abre la pestaña de la dirección: un enlace o una recarga no la pierde", () => {
    route.search = "pestana=benchmark";
    render(<LabTabs tabs={TABS} />);

    expect(selected()).toBe("Benchmark");
  });

  it("elegir una pestaña la guarda en la dirección", () => {
    render(<LabTabs tabs={TABS} />);

    fireEvent.click(screen.getByRole("tab", { name: "Benchmark" }));

    expect(route.replace).toHaveBeenCalledWith("/admin/laboratorio?pestana=benchmark", {
      scroll: false,
    });
  });

  it("con las flechas cambia de pestaña y mueve el foco", () => {
    render(<LabTabs tabs={TABS} />);

    fireEvent.keyDown(screen.getByRole("tablist"), { key: "ArrowRight" });

    expect(route.replace).toHaveBeenCalledWith("/admin/laboratorio?pestana=benchmark", {
      scroll: false,
    });
    expect(document.activeElement?.textContent).toBe("Benchmark");
  });
});
