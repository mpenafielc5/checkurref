import Link from "next/link";

/** Nombre del sistema como logotipo de texto. */
export function Wordmark({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="text-title font-bold tracking-wordmark text-ink">
      CheckUrRef
    </Link>
  );
}
