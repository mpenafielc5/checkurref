"use client";

import { useSearchParams } from "next/navigation";
import { loginErrorMessage } from "../rules";
import { Notice } from "@/shared/components/ui/notice";

/** Muestra el motivo por el que no se pudo iniciar sesión (?error=…). */
export function LoginError() {
  const message = loginErrorMessage(useSearchParams().get("error"));

  if (!message) return null;

  return <Notice tone="error">{message}</Notice>;
}
