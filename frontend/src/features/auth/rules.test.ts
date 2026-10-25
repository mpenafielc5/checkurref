import { describe, expect, it } from "vitest";
import {
  accountPathForRole,
  displayFullName,
  errorCodeFromOAuthFailure,
  homePathForRole,
  initialsOf,
  isInstitutionalEmail,
  isNavItemActive,
  loginErrorMessage,
  navItemsForRole,
  safeAvatarUrl,
  shortDisplayName,
} from "./rules";

describe("safeAvatarUrl", () => {
  it("acepta fotos https servidas por Google", () => {
    const photo = "https://lh3.googleusercontent.com/a/ACg8ocK=s96-c";
    expect(safeAvatarUrl(photo)).toBe(photo);
  });

  it("descarta otros dominios, http y valores que no son texto", () => {
    expect(safeAvatarUrl("https://ejemplo.com/foto.png")).toBeNull();
    expect(safeAvatarUrl("https://googleusercontent.com.ejemplo.com/a.png")).toBeNull();
    expect(safeAvatarUrl("http://lh3.googleusercontent.com/a/x")).toBeNull();
    expect(safeAvatarUrl("no es una url")).toBeNull();
    expect(safeAvatarUrl(undefined)).toBeNull();
    expect(safeAvatarUrl(42)).toBeNull();
  });
});

describe("nombre corto e iniciales", () => {
  it("usa el primer nombre y la inicial del primer apellido", () => {
    expect(shortDisplayName("MARÍA JOSÉ ÑAUPARI CASTRO")).toBe("María Ñ.");
    expect(initialsOf("MARÍA JOSÉ ÑAUPARI CASTRO")).toBe("MÑ");
  });

  it("funciona con nombres de dos y tres palabras", () => {
    expect(shortDisplayName("Ana Torres")).toBe("Ana T.");
    expect(shortDisplayName("Carlos Mendoza Vera")).toBe("Carlos M.");
    expect(initialsOf("Ana Torres")).toBe("AT");
  });

  it("funciona con una sola palabra", () => {
    expect(shortDisplayName("atorres9")).toBe("Atorres9");
    expect(initialsOf("atorres9")).toBe("A");
  });
});

describe("isInstitutionalEmail", () => {
  it("acepta correos @unemi.edu.ec sin importar mayúsculas ni espacios", () => {
    expect(isInstitutionalEmail("atorres9@unemi.edu.ec")).toBe(true);
    expect(isInstitutionalEmail("  Docente@UNEMI.EDU.EC ")).toBe(true);
  });

  it("rechaza otros dominios y dominios que solo se parecen", () => {
    expect(isInstitutionalEmail("alguien@gmail.com")).toBe(false);
    expect(isInstitutionalEmail("alguien@unemi.edu.ec.com")).toBe(false);
    expect(isInstitutionalEmail("alguien@falsounemi.edu.ec")).toBe(false);
  });

  it("rechaza valores vacíos", () => {
    expect(isInstitutionalEmail(null)).toBe(false);
    expect(isInstitutionalEmail("")).toBe(false);
  });
});

describe("homePathForRole", () => {
  it("lleva a cada rol a su propia página de inicio", () => {
    expect(homePathForRole("estudiante")).toBe("/estudiante");
    expect(homePathForRole("docente")).toBe("/docente");
    expect(homePathForRole("admin")).toBe("/admin");
  });
});

describe("navItemsForRole", () => {
  it("muestra el menú acordado para cada rol", () => {
    expect(navItemsForRole("estudiante").map((item) => item.label)).toEqual([
      "Inicio",
      "Mis trabajos",
      "Ayuda",
    ]);
    expect(navItemsForRole("docente").map((item) => item.label)).toEqual([
      "Inicio",
      "Lotes",
      "Ayuda",
    ]);
    expect(navItemsForRole("admin").map((item) => item.label)).toEqual([
      "Inicio",
      "Laboratorio",
      "Usuarios",
    ]);
  });

  it("cada rol enlaza a la ayuda dentro de su propia sección", () => {
    const helpHref = (role: "estudiante" | "docente") =>
      navItemsForRole(role).find((item) => item.label === "Ayuda")?.href;
    expect(helpHref("estudiante")).toBe("/estudiante/ayuda");
    expect(helpHref("docente")).toBe("/docente/ayuda");
  });
});

describe("displayFullName", () => {
  it("pasa el nombre de Google de mayúsculas a mayúscula inicial", () => {
    expect(displayFullName("JOSÉ IVÁN MUÑOZ PEÑA")).toBe("José Iván Muñoz Peña");
  });

  it("quita los espacios sobrantes", () => {
    expect(displayFullName("  ana   torres ")).toBe("Ana Torres");
  });
});

describe("accountPathForRole", () => {
  it("ubica Mi cuenta dentro de la sección de cada rol", () => {
    expect(accountPathForRole("estudiante")).toBe("/estudiante/cuenta");
    expect(accountPathForRole("docente")).toBe("/docente/cuenta");
    expect(accountPathForRole("admin")).toBe("/admin/cuenta");
  });
});

describe("isNavItemActive", () => {
  it("marca la sección también en sus páginas internas", () => {
    expect(isNavItemActive("/docente/lotes/is-7a", "/docente/lotes", "/docente")).toBe(true);
  });

  it("marca Inicio solo en su propia página", () => {
    expect(isNavItemActive("/docente", "/docente", "/docente")).toBe(true);
    expect(isNavItemActive("/docente/lotes", "/docente", "/docente")).toBe(false);
  });

  it("no confunde rutas que solo empiezan igual", () => {
    expect(isNavItemActive("/admin/usuarios-extra", "/admin/usuarios", "/admin")).toBe(false);
  });
});

describe("mensajes de error del inicio de sesión", () => {
  it("traduce los códigos conocidos e ignora los desconocidos", () => {
    expect(loginErrorMessage("dominio")).toContain("@unemi.edu.ec");
    expect(loginErrorMessage("otro")).toBeNull();
    expect(loginErrorMessage(null)).toBeNull();
  });

  it("identifica el rechazo del dominio en la base de datos", () => {
    expect(errorCodeFromOAuthFailure("Database error saving new user")).toBe("dominio");
    expect(errorCodeFromOAuthFailure("access_denied")).toBe("oauth");
    expect(errorCodeFromOAuthFailure(null)).toBe("oauth");
  });
});
