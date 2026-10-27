import { ChevronDown } from "lucide-react";
import { PageSection } from "@/shared/components/page-section";
import { VerdictBadge } from "@/shared/components/ui/verdict-badge";
import { VERDICT_ORDER, VERDICTS } from "@/shared/lib/verdicts";

const QUESTIONS = [
  {
    question: "¿Qué documentos puedo subir?",
    answer:
      "Archivos PDF de hasta 10 MB con texto seleccionable y referencias en APA o IEEE en español.",
  },
  {
    question: "¿Con qué fuentes se comparan mis referencias?",
    answer:
      "Con los datos registrados en Crossref y, si no aparecen ahí, en OpenAlex. Las obras que ninguna de las dos registra se marcan como no verificables: confirma sus datos en la obra original.",
  },
  {
    question: "¿Un veredicto negativo significa que hice plagio?",
    answer:
      "No. CheckUrRef revisa que las referencias existan y estén bien escritas; no detecta plagio. El docente decide con base en el informe.",
  },
  {
    question: "¿Quién puede ver mis trabajos?",
    answer: "Solo tú y, si el trabajo forma parte de un lote, el docente que lo creó.",
  },
];

/**
 * Ayuda: cómo leer los veredictos y preguntas frecuentes (HU-14).
 * Un solo contenido para todos los roles; cada sección lo muestra desde su
 * propia ruta (/estudiante/ayuda, /docente/ayuda) para conservar su barra.
 */
export function HelpContent() {
  return (
    <PageSection eyebrow="Ayuda" title="Cómo leer tu informe">
      <section aria-labelledby="titulo-veredictos" className="flex flex-col gap-3">
        <h2 id="titulo-veredictos" className="text-small font-semibold tracking-normal text-ink">
          Los cinco veredictos
        </h2>
        <ul className="flex flex-col gap-3">
          {VERDICT_ORDER.map((verdict) => (
            <li
              key={verdict}
              className="flex flex-col gap-2 rounded-card border border-hairline bg-canvas px-5 py-3 md:flex-row md:items-center md:gap-6"
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
          Algunas revistas en español no están en Crossref ni en OpenAlex: revisa la referencia y
          consulta a tu docente.
        </p>
      </section>

      <section aria-labelledby="titulo-formato" className="flex flex-col gap-3">
        <h2 id="titulo-formato" className="text-small font-semibold tracking-normal text-ink">
          Hallazgos de formato
        </h2>
        <p className="text-small">
          Aparte del veredicto, CheckUrRef revisa que cada referencia esté bien escrita según la
          norma que elegiste (APA 7 o IEEE): por ejemplo, que incluya el DOI o que el año vaya entre
          paréntesis. Cada hallazgo muestra cómo está escrita la referencia y cómo debería ir.
        </p>
        <p className="text-small">
          <strong className="text-ink">El formato no cambia el veredicto ni el índice.</strong> Una
          referencia puede estar verificada y tener errores de formato: la obra existe, pero está
          mal escrita.
        </p>
      </section>

      <section aria-labelledby="titulo-preguntas" className="flex flex-col gap-3">
        <h2 id="titulo-preguntas" className="text-small font-semibold tracking-normal text-ink">
          Preguntas frecuentes
        </h2>
        <div className="flex flex-col gap-2">
          {QUESTIONS.map((item) => (
            <details
              key={item.question}
              className="group rounded-card border border-hairline bg-canvas px-5 py-3 text-small"
            >
              {/* Sin el triángulo del navegador: una flecha a la derecha que gira al abrir. */}
              <summary className="flex list-none items-center justify-between gap-3 font-semibold text-ink [&::-webkit-details-marker]:hidden">
                {item.question}
                <ChevronDown
                  aria-hidden="true"
                  className="size-5 shrink-0 text-body transition-transform duration-(--cr-duration-fast) group-open:rotate-180"
                />
              </summary>
              <p className="pt-2">{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </PageSection>
  );
}
