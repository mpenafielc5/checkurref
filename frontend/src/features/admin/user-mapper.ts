/* Traduce la respuesta de GET /usuarios (UsersPage del backend) a los tipos de la pantalla. */
import type { UserRole, UserRow, UsersPage } from "./types";

type UserDto = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  active: boolean;
};

type UsersPageDto = {
  items: UserDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  counts: Record<UserRole | "todos", number>;
};

const ROLES: UserRole[] = ["estudiante", "docente", "admin"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isUserDto(value: unknown): value is UserDto {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    typeof value.email === "string" &&
    typeof value.active === "boolean" &&
    ROLES.some((role) => role === value.role)
  );
}

function isUsersPageDto(body: unknown): body is UsersPageDto {
  return (
    isRecord(body) &&
    Array.isArray(body.items) &&
    body.items.every(isUserDto) &&
    typeof body.page === "number" &&
    typeof body.page_size === "number" &&
    typeof body.total === "number" &&
    typeof body.total_pages === "number" &&
    isRecord(body.counts)
  );
}

function toUserRow(dto: UserDto): UserRow {
  return { id: dto.id, name: dto.name, email: dto.email, role: dto.role, active: dto.active };
}

/** Página de usuarios; null si la respuesta no es la esperada. */
export function toUsersPage(body: unknown): UsersPage | null {
  if (!isUsersPageDto(body)) return null;
  const first = body.items.length > 0 ? (body.page - 1) * body.page_size + 1 : 0;
  return {
    slice: {
      items: body.items.map(toUserRow),
      page: body.page,
      totalPages: body.total_pages,
      total: body.total,
      first,
      last: first > 0 ? first + body.items.length - 1 : 0,
    },
    counts: body.counts,
  };
}
