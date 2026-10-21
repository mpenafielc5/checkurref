"use client";

import { useSearchParams } from "next/navigation";
import { loginErrorMessage } from "../rules";

/** Muestra el motivo por el que no se pudo iniciar sesión (?error=…). */
export function LoginError() {
  const message = loginErrorMessage(useSearchParams().get("error"));

  if (!message) return null;

  return (
    <p
      role="alert"
      className="rounded-control border border-verdict-contradiction bg-surface px-4 py-3 text-small text-verdict-contradiction-text"
    >
      {message}
    </p>
  );
}
