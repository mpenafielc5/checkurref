import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Desmonta lo renderizado después de cada prueba para que no se acumule en el DOM.
afterEach(() => {
  cleanup();
});
