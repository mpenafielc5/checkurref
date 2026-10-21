import { Check } from "lucide-react";
import { VerdictBadge } from "@/shared/components/ui/verdict-badge";
import type { Verdict } from "@/shared/lib/verdicts";
import type { ProgressStep } from "../types";

type AnalysisProgressProps = {
  steps: ProgressStep[];
  verified: number;
  total: number;
  latest: ReadonlyArray<{ label: string; verdict: Verdict }>;
};

function StepMarker({ step, position }: { step: ProgressStep; position: number }) {
  if (step.state === "done") {
    return (
      <span className="flex size-avatar shrink-0 items-center justify-center rounded-pill bg-verdict-verified text-surface">
        <Check aria-hidden="true" className="size-5" />
      </span>
    );
  }
  return (
    <span
      className={`flex size-avatar shrink-0 items-center justify-center rounded-pill bg-surface text-small font-semibold ${
        step.state === "current"
          ? "border-2 border-primary text-accent-text"
          : "border border-hairline-strong text-muted"
      }`}
    >
      {position}
    </span>
  );
}

/** Etapas del análisis y últimas referencias verificadas (maqueta 11). */
export function AnalysisProgress({ steps, verified, total, latest }: AnalysisProgressProps) {
  const percent = Math.round((verified / total) * 100);

  return (
    <div className="flex flex-col gap-8 lg:flex-row">
      <ol className="flex flex-1 flex-col gap-5">
        {steps.map((step, index) => (
          <li key={step.title} className="flex items-start gap-4">
            <StepMarker step={step} position={index + 1} />
            <div className="flex flex-1 flex-col gap-1">
              <p
                className={`text-title font-semibold ${step.state === "pending" ? "text-muted" : "text-ink"}`}
              >
                {step.title}
              </p>
              <p className={`text-small ${step.state === "pending" ? "text-muted" : ""}`}>
                {step.detail}
              </p>
              {step.state === "current" ? (
                <div
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={percent}
                  aria-label="Avance de la verificación"
                  className="mt-1 flex h-3 overflow-hidden rounded-pill bg-hairline-soft"
                >
                  <span className="bg-primary" style={{ width: `${percent}%` }} />
                </div>
              ) : null}
            </div>
          </li>
        ))}
      </ol>

      <section aria-labelledby="titulo-ultimas" className="flex flex-col gap-3 lg:w-80">
        <h2 id="titulo-ultimas" className="text-small font-semibold tracking-normal text-ink">
          Últimas verificadas
        </h2>
        <ul className="flex flex-col gap-2">
          {latest.map((item) => (
            <li
              key={item.label}
              className="flex flex-col items-start gap-2 rounded-card border border-hairline px-4 py-3 text-small text-ink"
            >
              {item.label}
              <VerdictBadge verdict={item.verdict} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
