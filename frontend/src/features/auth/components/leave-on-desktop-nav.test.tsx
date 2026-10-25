import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LeaveOnDesktopNav } from "./leave-on-desktop-nav";

const replace = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

/** jsdom no trae matchMedia: se simula con el resultado que necesita cada prueba. */
function mockDesktopNav(matches: boolean) {
  vi.stubGlobal("matchMedia", () => ({
    matches,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
}

describe("LeaveOnDesktopNav", () => {
  afterEach(() => {
    replace.mockReset();
    vi.unstubAllGlobals();
  });

  it("con la navegación de escritorio, vuelve al inicio del rol", () => {
    mockDesktopNav(true);
    render(<LeaveOnDesktopNav href="/docente" />);
    expect(replace).toHaveBeenCalledWith("/docente");
  });

  it("con la navegación del celular, se queda en la pantalla", () => {
    mockDesktopNav(false);
    render(<LeaveOnDesktopNav href="/docente" />);
    expect(replace).not.toHaveBeenCalled();
  });
});
