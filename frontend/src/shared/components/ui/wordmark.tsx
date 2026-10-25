import Link from "next/link";
import { BrandLogo } from "./brand-logo";

/** Logotipo con enlace (página pública, ingreso y barra superior del celular). */
export function Wordmark({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="flex rounded-control">
      <BrandLogo variant="expanded" />
    </Link>
  );
}
