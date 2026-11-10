"use client";

import { useParams } from "next/navigation";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { DataTableSkeleton } from "@/shared/components/ui/data-table";
import { StatCard, StatRow, StatRowSkeleton } from "@/shared/components/ui/stat-card";
import { VerdictBreakdown } from "@/shared/components/ui/verdict-breakdown";
import { shareLabel } from "@/shared/lib/format";
import { fieldLabel } from "@/shared/lib/reference-fields";
import type { BatchDetail } from "../types";
import { useBatchDetail } from "../use-batch-detail";
import { BatchExportButton } from "./batch-export-button";
import { BatchRiskTable } from "./batch-risk-table";

const BACK_LINK = { href: "/docente/lotes", label: "Lotes" };
const EYEBROW = "Tablero del lote";

/** Cuántos campos se muestran; el resto casi no aporta a la revisión del lote. */
const TOP_FIELDS = 5;

function referencesLabel(count: number): string {
  return `${count} ${count === 1 ? "referencia" : "referencias"}`;
}

/** Porcentaje por veredicto y campos con más diferencias (RF20-CA01). */
function BatchBreakdown({ batch }: { batch: BatchDetail }) {
  const fields = batch.mostDifferentFields.slice(0, TOP_FIELDS);

  return (
    <div className="flex flex-col gap-6 rounded-panel border border-hairline bg-canvas px-6 py-4 md:flex-row">
      <section aria-labelledby="titulo-veredictos" className="flex flex-1 flex-col gap-3">
        <h2 id="titulo-veredictos" className="text-small font-semibold tracking-normal text-ink">
          Veredictos del lote
        </h2>
        <VerdictBreakdown counts={batch.counts} total={batch.references} />
      </section>

      <section aria-labelledby="titulo-campos" className="flex flex-1 flex-col gap-3">
        <h2 id="titulo-campos" className="text-small font-semibold tracking-normal text-ink">
          Campos con más diferencias
        </h2>
        {fields.length > 0 ? (
          <ul className="flex flex-col gap-1 text-small">
            {fields.map((item) => (
              <li key={item.field} className="flex justify-between gap-2">
                <span className="text-ink">{fieldLabel(item.field)}</span>
                <span className="tabular-nums">{referencesLabel(item.references)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-small">No se registraron diferencias con las fuentes.</p>
        )}
      </section>
    </div>
  );
}

/** Lo que falta para que los indicadores cubran todo el lote. */
function BatchNotices({ batch }: { batch: BatchDetail }) {
  const { inProgress, failed, finished, totalWorks, queryErrors } = batch;
  return (
    <div aria-live="polite" className="flex flex-col gap-1 text-small empty:hidden">
      {inProgress > 0 ? (
        <p>
          {finished} de {totalWorks} trabajos terminados. Los indicadores incluyen solo los
          terminados y se actualizan automáticamente.
        </p>
      ) : null}
      {failed > 0 ? (
        <p>
          {failed === 1
            ? "1 trabajo no se pudo analizar y no cuenta en los indicadores."
            : `${failed} trabajos no se pudieron analizar y no cuentan en los indicadores.`}
        </p>
      ) : null}
      {queryErrors > 0 ? (
        <p>
          {queryErrors === 1
            ? "1 referencia no se pudo verificar porque una fuente no respondió."
            : `${queryErrors} referencias no se pudieron verificar porque una fuente no respondió.`}
        </p>
      ) : null}
    </div>
  );
}

/** El tablero con sus datos: indicadores y trabajos ordenados por riesgo (maqueta 16). */
export function BatchDashboardView({ batch }: { batch: BatchDetail }) {
  const alerts = batch.counts.contradiccion + batch.counts.discrepancia;
  const hasReferences = batch.references > 0;

  return (
    <PageSection
      eyebrow={EYEBROW}
      title={batch.name}
      description={batch.period ?? undefined}
      back={BACK_LINK}
      actions={<BatchExportButton batchId={batch.id} disabled={batch.totalWorks === 0} />}
    >
      {batch.totalWorks === 0 ? (
        <p className="text-small">Este lote aún no tiene trabajos.</p>
      ) : (
        <>
          <StatRow>
            <StatCard value={String(batch.totalWorks)} label="Trabajos" />
            <StatCard value={String(batch.references)} label="Referencias" />
            <StatCard
              value={shareLabel(batch.counts.verificada, batch.references)}
              label="Verificadas"
              tone="success"
            />
            <StatCard value={String(alerts)} label="Alertas" tone="danger" />
          </StatRow>
          <BatchNotices batch={batch} />
          {hasReferences ? <BatchBreakdown batch={batch} /> : null}
          <section aria-labelledby="titulo-riesgo" className="flex flex-col gap-3">
            <h2 id="titulo-riesgo" className="text-small font-semibold tracking-normal text-ink">
              Trabajos ordenados por riesgo
            </h2>
            <BatchRiskTable batchId={batch.id} works={batch.works} />
          </section>
        </>
      )}
    </PageSection>
  );
}

/** Pide el tablero del lote de la dirección y muestra la carga, los datos o el motivo. */
export function BatchDashboard() {
  const { loteId } = useParams<{ loteId: string }>();
  const state = useBatchDetail(loteId);

  if (state.kind === "loading") {
    return (
      <PageSectionSkeleton back action>
        {state.slow ? (
          <p className="text-small">
            Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.
          </p>
        ) : null}
        <StatRowSkeleton count={4} />
        <DataTableSkeleton columns={5} rows={5} cardsOnMobile />
      </PageSectionSkeleton>
    );
  }
  if (state.kind === "error") {
    return (
      <PageSection eyebrow={EYEBROW} title="Lote no disponible" back={BACK_LINK}>
        <p role="alert" className="text-small text-verdict-contradiction-text">
          {state.message}
        </p>
      </PageSection>
    );
  }
  return <BatchDashboardView batch={state.batch} />;
}
