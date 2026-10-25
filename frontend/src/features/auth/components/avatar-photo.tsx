"use client";

import Image from "next/image";
import { useEffect, useRef, useState, type ReactNode } from "react";

type AvatarPhotoProps = {
  src: string;
  /** Lo que se muestra si la foto no carga (las iniciales). */
  fallback: ReactNode;
  /** Tamaño; por omisión, el del avatar de la barra lateral. */
  sizeClass?: string;
};

/**
 * Foto de perfil de Google con respaldo.
 *
 * - unoptimized: el navegador la pide directo a Google; el servidor no la
 *   descarga ni guarda copias.
 * - no-referrer: Google a veces rechaza las fotos pedidas desde otra página;
 *   sin el dato de origen las entrega, y además no se informa qué sitio se visita.
 * - Si aun así falla, se muestran las iniciales en lugar de una imagen rota.
 *   Se revisa también al montar, porque el error puede ocurrir antes de que la
 *   página termine de cargar y entonces el aviso onError no llega.
 */
export function AvatarPhoto({ src, fallback, sizeClass = "size-avatar" }: AvatarPhotoProps) {
  const [failed, setFailed] = useState(false);
  const image = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const element = image.current;
    if (element?.complete && element.naturalWidth === 0) setFailed(true);
  }, []);

  if (failed) return fallback;

  return (
    <Image
      ref={image}
      src={src}
      alt=""
      width={40}
      height={40}
      unoptimized
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className={`${sizeClass} shrink-0 rounded-pill object-cover`}
    />
  );
}
