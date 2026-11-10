import { useCallback, useEffect, useState } from "react";
import { fetchUsers, type UsersOutcome } from "./api";
import type { RoleCounts, RoleFilter } from "./types";

export type UsersState = { kind: "loading"; slow: boolean } | UsersOutcome;

/**
 * Una página de usuarios según la búsqueda y el filtro. Tras un cambio, reload
 * vuelve a consultar sin ocultar la tabla: la fila puede haber salido del filtro y
 * los totales por rol cambian. Los totales ya conocidos se conservan mientras carga.
 */
export function useUsers(page: number, search: string, role: RoleFilter) {
  const key = `${page}|${role}|${search}`;
  const [result, setResult] = useState<{ key: string; outcome: UsersOutcome } | null>(null);
  const [slowKey, setSlowKey] = useState<string | null>(null);
  const [counts, setCounts] = useState<RoleCounts | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    fetchUsers(page, search, role, () => {
      if (active) setSlowKey(key);
    }).then((outcome) => {
      if (!active) return;
      setResult({ key, outcome });
      if (outcome.kind === "ready") setCounts(outcome.users.counts);
    });
    return () => {
      active = false;
    };
  }, [key, page, role, search, version]);

  const reload = useCallback(() => setVersion((current) => current + 1), []);
  const state: UsersState =
    result?.key === key ? result.outcome : { kind: "loading", slow: slowKey === key };

  return { state, counts, reload };
}
