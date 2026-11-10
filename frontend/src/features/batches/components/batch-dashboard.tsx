"use client";

import { Inbox } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { DataTableSkeleton } from "@/shared/components/ui/data-table";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Notice, WakingNotice } from "@/shared/components/ui/notice";
import { StatCard, StatRow, StatRowSkeleton } from "@/shared/components/ui/stat-card";
import { VerdictBreakdown } from "@/shared/components/ui/verdict-breakdown";
import { shareLabel } from "@/shared/lib/format";
import { fieldLabel } from "@/shared/lib/reference-fields";
import type { BatchDetail } from "../types";
import { useBatchDetail } from "../use-batch-detail";
import { AddWorksLink } from "./add-works-link";
import { BatchExportButton } from "./batch-export-button";
import { DeleteBatchButton } from "./delete-batch-button";
import { EditBatchButton } from "./edit-batch-button";
import { BatchRiskTable } from "./batch-risk-table";

const BACK_LINK = { href: "/docente/lotes", label: "Lotes" };
const EYEBROW = "Tablero del lote";

/**
 * Acciones del tablero en el celular: la principal y la destructiva a todo el ancho, las
 * otras dos en una fila. Desde md, todas en una sola fila.
 */
const ACTION_FULL = "basis-full md:basis-auto";
const ACTION_HALF = "grow basis-2/5 md:grow-0 md:basis-auto";

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
    <div aria-live="polite" className="flex flex-col gap-2 empty:hidden">
      {inProgress > 0 ? (
        <Notice>
          {finished} de {totalWorks}{" "}
          {totalWorks === 1 ? "trabajo terminado" : "trabajos terminados"}. Las cifras se actualizan
          automáticamente.
        </Notice>
      ) : null}
      {failed > 0 ? (
        <Notice tone="warning">
          {failed === 1
            ? "1 trabajo no se pudo analizar y no cuenta en las cifras."
            : `${failed} trabajos no se pudieron analizar y no cuentan en las cifras.`}
        </Notice>
      ) : null}
      {queryErrors > 0 ? (
        <Notice tone="warning">
          {queryErrors === 1
            ? "1 referencia quedó sin verificar porque una fuente no respondió."
            : `${queryErrors} referencias quedaron sin verificar porque una fuente no respondió.`}
        </Notice>
      ) : null}
    </div>
  );
}

/** El tablero con sus datos: indicadores y trabajos ordenados por riesgo (maqueta 16). */
type BatchDashboardViewProps = {
  batch: BatchDetail;
  /** Tras editar el lote o eliminar un trabajo, el tablero se vuelve a pedir. */
  onChanged?: () => void;
};

export function BatchDashboardView({ batch, onChanged }: BatchDashboardViewProps) {
  const alerts = batch.counts.contradiccion + batch.counts.discrepancia;
  const hasReferences = batch.references > 0;

  return (
    <PageSection
      eyebrow={EYEBROW}
      title={batch.name}
      description={batch.period ?? undefined}
      back={BACK_LINK}
      wideActions
      actions={
        <div className="flex w-full flex-wrap gap-2 md:w-auto">
          <AddWorksLink batchId={batch.id} totalWorks={batch.totalWorks} className={ACTION_FULL} />
          {onChanged ? (
            <EditBatchButton batch={batch} onSaved={onChanged} className={ACTION_HALF} />
          ) : null}
          <BatchExportButton
            batchId={batch.id}
            disabled={batch.totalWorks === 0}
            className={ACTION_HALF}
          />
          {onChanged ? <DeleteBatchButton batch={batch} className={ACTION_FULL} /> : null}
        </div>
      }
    >
      {batch.totalWorks === 0 ? (
        <EmptyState
          icon={Inbox}
          title="Este lote no tiene trabajos"
          description="Agrega los PDF del curso, o elimina el lote si ya no lo necesitas."
        >
          <AddWorksLink batchId={batch.id} totalWorks={batch.totalWorks} primary />
        </EmptyState>
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
            <StatCard
              value={String(alerts)}
              label="Alertas"
              tone={alerts > 0 ? "danger" : "default"}
            />
          </StatRow>
          <BatchNotices batch={batch} />
          {hasReferences ? <BatchBreakdown batch={batch} /> : null}
          <section aria-labelledby="titulo-riesgo" className="flex flex-col gap-3">
            <h2 id="titulo-riesgo" className="text-small font-semibold tracking-normal text-ink">
              Trabajos ordenados por riesgo
            </h2>
            <BatchRiskTable batchId={batch.id} works={batch.works} onDeleted={onChanged} />
          </section>
        </>
      )}
    </PageSection>
  );
}

/** Pide el tablero del lote de la dirección y muestra la carga, los datos o el motivo. */
export function BatchDashboard() {
  const { loteId } = useParams<{ loteId: string }>();
  const [version, setVersion] = useState(0);
  const state = useBatchDetail(loteId, version);

  if (state.kind === "loading") {
    return (
      <PageSectionSkeleton back action>
        {state.slow ? <WakingNotice /> : null}
        <StatRowSkeleton count={4} />
        <DataTableSkeleton columns={5} rows={5} cardsOnMobile />
      </PageSectionSkeleton>
    );
  }
  if (state.kind === "error") {
    return (
      <PageSection eyebrow={EYEBROW} title="Lote no disponible" back={BACK_LINK}>
        <Notice tone="error">{state.message}</Notice>
      </PageSection>
    );
  }
  return (
    <BatchDashboardView
      batch={state.batch}
      onChanged={() => setVersion((current) => current + 1)}
    />
  );
}
