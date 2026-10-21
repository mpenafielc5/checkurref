import { describe, expect, it } from "vitest";
import {
  errorCodeFromOAuthFailure,
  homePathForRole,
  initialsOf,
  isInstitutionalEmail,
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
    expect(shortDisplayName("MIGUEL ANGEL PEÑAFIEL CADENA")).toBe("Miguel P.");
    expect(initialsOf("MIGUEL ANGEL PEÑAFIEL CADENA")).toBe("MP");
  });

  it("funciona con nombres de dos y tres palabras", () => {
    expect(shortDisplayName("Ana Torres")).toBe("Ana T.");
    expect(shortDisplayName("Jackson Reyes Ibarra")).toBe("Jackson R.");
    expect(initialsOf("Ana Torres")).toBe("AT");
  });

  it("funciona con una sola palabra", () => {
    expect(shortDisplayName("mpenafielc5")).toBe("Mpenafielc5");
    expect(initialsOf("mpenafielc5")).toBe("M");
  });
});

describe("isInstitutionalEmail", () => {
  it("acepta correos @unemi.edu.ec sin importar mayúsculas ni espacios", () => {
    expect(isInstitutionalEmail("mpenafielc5@unemi.edu.ec")).toBe(true);
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
