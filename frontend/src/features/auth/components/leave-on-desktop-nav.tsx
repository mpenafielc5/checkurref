"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { DESKTOP_NAV_QUERY } from "@/shared/lib/media";

/**
 * Mi cuenta es parte de la navegación del celular. Si la pantalla pasa a la
 * navegación de escritorio (al agrandar la ventana o conectar un mouse), vuelve
 * al inicio del rol: ahí el pie de la barra lateral ya muestra lo mismo.
 */
export function LeaveOnDesktopNav({ href }: { href: string }) {
  const router = useRouter();

  useEffect(() => {
    const desktop = window.matchMedia(DESKTOP_NAV_QUERY);
    function leaveIfDesktop() {
      if (desktop.matches) router.replace(href);
    }
    leaveIfDesktop();
    desktop.addEventListener("change", leaveIfDesktop);
    return () => desktop.removeEventListener("change", leaveIfDesktop);
  }, [href, router]);

  return null;
}
