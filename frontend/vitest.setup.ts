import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Desmonta lo renderizado después de cada prueba para que no se acumule en el DOM.
afterEach(() => {
  cleanup();
});

// Fuera de Next.js no existe el enrutador: se simula con valores neutros.
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));
