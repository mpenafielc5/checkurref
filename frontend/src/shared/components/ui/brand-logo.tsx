/**
 * Isotipo: una hoja con la esquina doblada y un check grande. Sin líneas de
 * texto, para que no se confunda con los íconos de documento del menú (el
 * mismo dibujo está en app/icon.svg). La hoja toma el color del texto con un
 * trazo apenas más firme que el de los íconos del menú; el check, naranja y un
 * poco más grueso, es lo que destaca.
 */
function LogoIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
      <path d="m8.5 14 2.5 2.5 5-5.5" className="text-primary" strokeWidth="2" />
    </svg>
  );
}

type BrandLogoProps = {
  /** collapsed: solo el isotipo (barra lateral contraída); expanded: isotipo y nombre. */
  variant: "expanded" | "collapsed";
  /** Clases extra para el nombre; la barra lateral lo usa para mostrarlo al desplegarse. */
  nameClass?: string;
};

/** Logotipo de CheckUrRef. El naranja queda solo en el check; el nombre va en tinta. */
export function BrandLogo({ variant, nameClass = "" }: BrandLogoProps) {
  if (variant === "collapsed") {
    return (
      <span role="img" aria-label="CheckUrRef" className="flex text-ink">
        <LogoIcon className="size-7" />
      </span>
    );
  }

  return (
    <span className="flex items-center gap-2 text-title font-bold tracking-wordmark text-ink">
      <LogoIcon className="size-7 shrink-0" />
      <span className={`whitespace-nowrap ${nameClass}`}>CheckUrRef</span>
    </span>
  );
}
