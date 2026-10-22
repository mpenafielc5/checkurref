import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AvatarPhoto } from "./avatar-photo";

const PHOTO = "https://lh3.googleusercontent.com/a/foto-de-prueba";

describe("AvatarPhoto", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("pide la foto a Google sin enviar la página de origen", () => {
    const { container } = render(<AvatarPhoto src={PHOTO} fallback={<span>MP</span>} />);
    const image = container.querySelector("img");

    expect(image?.getAttribute("src")).toBe(PHOTO);
    expect(image?.getAttribute("referrerpolicy")).toBe("no-referrer");
  });

  it("si la foto no carga, muestra las iniciales en lugar de una imagen rota", () => {
    const { container } = render(<AvatarPhoto src={PHOTO} fallback={<span>MP</span>} />);

    fireEvent.error(container.querySelector("img") as HTMLImageElement);

    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("MP")).toBeDefined();
  });

  it("detecta la foto que ya falló antes de que la página terminara de cargar", () => {
    // Una imagen que terminó de cargar sin ancho es una imagen que falló.
    vi.spyOn(HTMLImageElement.prototype, "complete", "get").mockReturnValue(true);
    vi.spyOn(HTMLImageElement.prototype, "naturalWidth", "get").mockReturnValue(0);

    const { container } = render(<AvatarPhoto src={PHOTO} fallback={<span>MP</span>} />);

    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("MP")).toBeDefined();
  });
});
