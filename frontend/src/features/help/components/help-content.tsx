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
      "Con los metadatos registrados en Crossref y, si no aparecen ahí, en OpenAlex. Los libros, tesis y sitios web sin registro se marcan como no verificables.",
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
          Muchas obras en español no tienen DOI: revisa la referencia y consulta a tu docente.
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
              className="rounded-card border border-hairline bg-canvas px-5 py-3 text-small"
            >
              <summary className="cursor-pointer font-semibold text-ink">{item.question}</summary>
              <p className="pt-2">{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </PageSection>
  );
}
