import { CircleCheck, FileUp, Globe, Lightbulb, ListChecks, Users } from "lucide-react";
import Link from "next/link";
import { AccessCard } from "@/features/auth/components/access-card";
import { VerdictBadge } from "@/features/reports/components/verdict-badge";
import { VERDICT_ORDER, VERDICTS } from "@/features/reports/verdicts";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { Eyebrow } from "@/shared/components/ui/eyebrow";
import { Wordmark } from "@/shared/components/ui/wordmark";

/** Página pública: propuesta de valor y acceso (maqueta 01, HU-03). */
export default function HomePage() {
  return (
    <div className="flex flex-1 flex-col bg-surface">
      <header className="border-b border-hairline">
        <div className="mx-auto flex min-h-nav w-full max-w-content flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 md:px-8">
          <Wordmark />
          <nav aria-label="Secciones">
            <ul className="flex items-center gap-6">
              <li>
                <a href="#como-funciona" className="text-small text-body hover:text-ink">
                  Cómo funciona
                </a>
              </li>
              <li>
                <a href="#para-docentes" className="text-small text-body hover:text-ink">
                  Para docentes
                </a>
              </li>
            </ul>
          </nav>
        </div>
      </header>

      <main className="flex flex-1 flex-col">
        <section
          aria-labelledby="titulo-principal"
          className="mx-auto flex w-full max-w-content flex-col gap-10 px-4 py-12 md:px-8 md:py-20 lg:flex-row lg:items-center"
        >
          <div className="flex flex-1 flex-col gap-5">
            <Eyebrow>Auditoría de referencias con IA</Eyebrow>
            <h1 id="titulo-principal" className="text-display-md md:text-display-lg">
              ¿Tus referencias existen de verdad?
            </h1>
            <p className="max-w-xl text-title font-normal">
              Sube el PDF de tu trabajo y CheckUrRef coteja cada referencia con su fuente oficial
              antes de que la revise tu tutor.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/inicio" className={buttonStyles()}>
                Revisar mi trabajo
              </Link>
              <a href="#como-funciona" className={buttonStyles({ variant: "secondary" })}>
                Cómo funciona
              </a>
            </div>
            <ul className="flex flex-wrap gap-x-6 gap-y-2 text-small">
              <li className="flex items-center gap-2">
                <CircleCheck aria-hidden="true" className="size-5 text-verdict-verified" />
                APA e IEEE
              </li>
              <li className="flex items-center gap-2">
                <Globe aria-hidden="true" className="size-5 text-body" />
                Crossref
              </li>
              <li className="flex items-center gap-2">
                <Lightbulb aria-hidden="true" className="size-5 text-body" />
                IA en español
              </li>
            </ul>
          </div>

          <AccessCard />
        </section>

        <section
          id="como-funciona"
          aria-labelledby="titulo-como-funciona"
          className="border-t border-hairline bg-canvas"
        >
          <div className="mx-auto flex w-full max-w-content flex-col gap-8 px-4 py-12 md:px-8 md:py-20">
            <div className="flex flex-col gap-2">
              <Eyebrow>Cómo funciona</Eyebrow>
              <h2 id="titulo-como-funciona" className="text-display-sm md:text-display-md">
                Tres pasos, un informe por referencia
              </h2>
            </div>

            <ol className="flex flex-col gap-4 md:flex-row">
              <li className="flex flex-1 flex-col gap-2 rounded-card border border-hairline bg-surface p-6">
                <FileUp aria-hidden="true" className="size-6 text-primary" />
                <h3 className="text-title font-semibold tracking-normal">1. Sube tu PDF</h3>
                <p className="text-small">Hasta 10 MB, con referencias en APA o IEEE en español.</p>
              </li>
              <li className="flex flex-1 flex-col gap-2 rounded-card border border-hairline bg-surface p-6">
                <ListChecks aria-hidden="true" className="size-6 text-primary" />
                <h3 className="text-title font-semibold tracking-normal">
                  2. Verificamos cada una
                </h3>
                <p className="text-small">
                  Separamos sus campos, los buscamos en Crossref y los comparamos con un modelo de
                  inteligencia artificial en español.
                </p>
              </li>
              <li className="flex flex-1 flex-col gap-2 rounded-card border border-hairline bg-surface p-6">
                <CircleCheck aria-hidden="true" className="size-6 text-primary" />
                <h3 className="text-title font-semibold tracking-normal">3. Recibe tu informe</h3>
                <p className="text-small">
                  Cada referencia recibe un veredicto y el dato registrado para corregirla.
                </p>
              </li>
            </ol>

            <ul aria-label="Veredictos" className="flex flex-col gap-3">
              {VERDICT_ORDER.map((verdict) => (
                <li
                  key={verdict}
                  className="flex flex-col gap-2 rounded-card border border-hairline bg-surface px-5 py-3 md:flex-row md:items-center md:gap-6"
                >
                  <span className="flex md:w-48 md:shrink-0">
                    <VerdictBadge verdict={verdict} />
                  </span>
                  <p className="text-small">{VERDICTS[verdict].description}</p>
                </li>
              ))}
            </ul>
            <p className="text-small">
              <strong className="text-ink">
                &ldquo;Sin respaldo&rdquo; no significa &ldquo;falsa&rdquo;.
              </strong>{" "}
              Muchas obras en español no tienen DOI: el sistema señala y el docente decide.
            </p>
          </div>
        </section>

        <section
          id="para-docentes"
          aria-labelledby="titulo-para-docentes"
          className="border-t border-hairline"
        >
          <div className="mx-auto flex w-full max-w-content flex-col gap-6 px-4 py-12 md:flex-row md:items-center md:px-8 md:py-20">
            <div className="flex flex-1 flex-col gap-2">
              <Eyebrow>Para docentes</Eyebrow>
              <h2 id="titulo-para-docentes" className="text-display-sm md:text-display-md">
                Revisa los trabajos de un curso a la vez
              </h2>
              <p className="max-w-xl">
                Sube los PDF de un paralelo en un lote y revisa primero los que tienen más
                problemas. Especialmente útil para acompañar los trabajos de titulación.
              </p>
            </div>
            <ul className="flex flex-1 flex-col gap-3 text-small">
              <li className="flex items-center gap-3">
                <Users aria-hidden="true" className="size-5 text-primary" />
                Lotes por curso y periodo académico
              </li>
              <li className="flex items-center gap-3">
                <ListChecks aria-hidden="true" className="size-5 text-primary" />
                Trabajos ordenados por riesgo
              </li>
              <li className="flex items-center gap-3">
                <FileUp aria-hidden="true" className="size-5 text-primary" />
                Exportación de resultados en CSV
              </li>
            </ul>
          </div>
        </section>
      </main>

      <footer className="border-t border-hairline">
        <p className="mx-auto w-full max-w-content px-4 py-6 text-small text-muted md:px-8">
          Universidad Estatal de Milagro · Ingeniería de Software
        </p>
      </footer>
    </div>
  );
}
