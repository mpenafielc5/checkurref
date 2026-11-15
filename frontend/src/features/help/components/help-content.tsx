import { ChevronDown } from "lucide-react";
import { PageSection } from "@/shared/components/page-section";
import { StatusChip } from "@/shared/components/ui/status-chip";
import { VerdictBadge } from "@/shared/components/ui/verdict-badge";
import { INDEX_LEVEL_ORDER, INDEX_LEVEL_RANGES, INDEX_LEVELS } from "@/shared/lib/truthfulness";
import { type Verdict, VERDICT_ORDER, VERDICTS } from "@/shared/lib/verdicts";
import { cardStyles } from "@/shared/components/ui/card-styles";

/** Un caso típico de cada veredicto (HU-14 CA01). */
const EXAMPLES: Record<Verdict, string> = {
  verificada:
    "La referencia cita el título, los autores, el año y el DOI tal como figuran en el registro de la obra.",
  discrepancia:
    "La referencia indica el año 2019 y el registro de la obra indica 2021, o le falta el subtítulo.",
  contradiccion:
    "El DOI citado lleva a un artículo de otros autores y sobre otro tema que el de la referencia.",
  sin_respaldo:
    "Un artículo de una revista que no registra sus publicaciones en Crossref ni en OpenAlex, o una referencia con el título tan alterado que no se encuentra la obra.",
  no_verificable:
    "Una tesis de grado, una ley publicada en el Registro Oficial o una página web: ninguna de las dos fuentes registra estas obras.",
};

const QUESTIONS = [
  {
    question: "¿Qué documentos puedo subir?",
    answer:
      "Archivos PDF de hasta 10 MB con texto seleccionable y referencias en APA o IEEE en español.",
  },
  {
    question: "¿Con qué fuentes se comparan mis referencias?",
    answer:
      "Con los datos registrados en Crossref y, cuando no figuran allí, en OpenAlex. Las obras que ninguna de las dos registra se marcan como no verificables: confirma sus datos en la obra original.",
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
 * Ayuda: cómo leer los veredictos, el índice de veracidad y preguntas frecuentes (HU-14).
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
              className={`flex flex-col gap-2 ${cardStyles()} px-5 py-3 md:flex-row md:items-start md:gap-6`}
            >
              <span className="flex md:w-48 md:shrink-0">
                <VerdictBadge verdict={verdict} />
              </span>
              <div className="flex flex-col gap-2">
                <p className="text-small">{VERDICTS[verdict].description}</p>
                <p className="flex flex-col gap-1 text-small text-body">
                  <span className="font-mono text-caption text-accent-text uppercase">Ejemplo</span>
                  {EXAMPLES[verdict]}
                </p>
              </div>
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

      <section aria-labelledby="titulo-indice" className="flex flex-col gap-3">
        <h2 id="titulo-indice" className="text-small font-semibold tracking-normal text-ink">
          El índice de veracidad
        </h2>
        <p className="text-small">
          Es el porcentaje de referencias verificadas entre las que se pudieron comprobar: las
          verificadas, con discrepancias, con contradicción y sin respaldo. Por ejemplo, si 17 de 20
          están verificadas, el índice es 85. Las no verificables (tesis, leyes, páginas web) no
          cuentan, porque las fuentes no registran ese tipo de obra: citar una tesis no baja el
          índice.
        </p>
        <ul className="flex flex-col gap-3">
          {INDEX_LEVEL_ORDER.map((level) => (
            <li
              key={level}
              className={`flex flex-col gap-2 ${cardStyles()} px-5 py-3 md:flex-row md:items-start md:gap-6`}
            >
              <span className="flex md:w-48 md:shrink-0">
                <StatusChip tone={INDEX_LEVELS[level].tone}>{INDEX_LEVELS[level].label}</StatusChip>
              </span>
              <p className="flex flex-col gap-1 text-small">
                <span className="font-mono text-caption text-accent-text uppercase">
                  {INDEX_LEVEL_RANGES[level]}
                </span>
                {INDEX_LEVELS[level].advice}
              </p>
            </li>
          ))}
        </ul>
        <p className="text-small">
          <strong className="text-ink">El índice no es una calificación.</strong> Indica cuántas
          referencias coinciden con su registro; no evalúa la calidad del trabajo. En los lotes, el
          docente ve el mismo dato como riesgo: un índice bajo es riesgo alto, un índice medio es
          riesgo medio y un índice alto es riesgo bajo. Además, una sola contradicción basta para
          que el riesgo sea alto.
        </p>
      </section>

      <section aria-labelledby="titulo-formato" className="flex flex-col gap-3">
        <h2 id="titulo-formato" className="text-small font-semibold tracking-normal text-ink">
          Hallazgos de formato
        </h2>
        <p className="text-small">
          Aparte del veredicto, CheckUrRef revisa que cada referencia esté bien escrita según su
          norma (APA 7 o IEEE), que el sistema identifica automáticamente: por ejemplo, que incluya
          el DOI o que el año vaya entre paréntesis. Cada hallazgo muestra cómo está escrita la
          referencia y cómo debería ir.
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
            <details key={item.question} className={`group ${cardStyles()} px-5 py-3 text-small`}>
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
