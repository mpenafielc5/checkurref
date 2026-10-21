import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Profile } from "../types";
import { ReviewWorkAction } from "./landing-access";

const signInWithOAuth = vi.fn();
const getCurrentProfile = vi.fn<() => Promise<Profile | null>>();

vi.mock("@/shared/lib/supabase/client", () => ({
  createSupabaseBrowserClient: () => ({ auth: { signInWithOAuth } }),
}));

vi.mock("../api", () => ({
  getCurrentProfile: () => getCurrentProfile(),
}));

const STUDENT: Profile = {
  id: "1",
  fullName: "Ana Torres",
  email: "atorres@unemi.edu.ec",
  role: "estudiante",
  career: null,
  active: true,
  avatarUrl: null,
};

describe("ReviewWorkAction", () => {
  beforeEach(() => {
    signInWithOAuth.mockReset().mockResolvedValue({ error: null });
    getCurrentProfile.mockReset();
  });

  it("sin sesión, abre el acceso con Google en un solo clic", async () => {
    getCurrentProfile.mockResolvedValue(null);
    render(await ReviewWorkAction({ children: "Revisar mi trabajo" }));

    fireEvent.click(screen.getByRole("button", { name: "Revisar mi trabajo" }));

    await waitFor(() => expect(signInWithOAuth).toHaveBeenCalledTimes(1));
    expect(signInWithOAuth.mock.calls[0][0]).toMatchObject({
      provider: "google",
      options: { queryParams: { hd: "unemi.edu.ec" } },
    });
  });

  it("con sesión, lleva al inicio del rol", async () => {
    getCurrentProfile.mockResolvedValue(STUDENT);
    render(await ReviewWorkAction({ children: "Revisar mi trabajo" }));

    expect(screen.getByRole("link", { name: "Revisar mi trabajo" }).getAttribute("href")).toBe(
      "/estudiante",
    );
    expect(signInWithOAuth).not.toHaveBeenCalled();
  });
});
