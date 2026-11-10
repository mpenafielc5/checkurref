"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { Pagination } from "@/shared/components/ui/pagination";
import { PAGE_PARAM, parsePage } from "@/shared/lib/pagination";
import type { BatchSummary } from "../types";
import { useBatches, type BatchesState } from "../use-batches";
import { BatchList, BatchListSkeleton } from "./batch-list";

const LIST_ID = "lotes";
const EMPTY_MESSAGE =
  "Todavía no has creado lotes. Crea uno con Nueva auditoría para revisar los trabajos de un curso.";

/** Cuántos lotes muestra el inicio; el resto está en Lotes. */
const RECENT_COUNT = 3;

type BatchesBodyProps = {
  state: BatchesState;
  skeletonRows: number;
  children: (batches: BatchSummary[]) => React.ReactNode;
};

/** Lo común a las dos listas: la carga, el error y el mensaje sin lotes. */
function BatchesBody({ state, skeletonRows, children }: BatchesBodyProps) {
  if (state.kind === "loading") {
    return (
      <div className="flex flex-col gap-4">
        <p role="status" className="sr-only">
          Cargando los lotes…
        </p>
        {state.slow ? (
          <p className="text-small">
            Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.
          </p>
        ) : null}
        <BatchListSkeleton rows={skeletonRows} />
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <p role="alert" className="text-small text-verdict-contradiction-text">
        {state.message}
      </p>
    );
  }
  if (state.page.total === 0) return <p className="text-small">{EMPTY_MESSAGE}</p>;
  return children(state.page.items);
}

/** Lotes del docente, de 20 en 20, con la página en la dirección (HU-08). */
export function BatchesLoader() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const state = useBatches(parsePage(searchParams.get(PAGE_PARAM)));

  return (
    <div id={LIST_ID} className="flex scroll-mt-6 flex-col gap-4">
      <BatchesBody state={state} skeletonRows={3}>
        {(batches) => (
          <>
            <BatchList batches={batches} />
            {state.kind === "ready" ? (
              <Pagination
                slice={state.page}
                pathname={pathname}
                query={searchParams.toString()}
                noun="lotes"
                anchorId={LIST_ID}
              />
            ) : null}
          </>
        )}
      </BatchesBody>
    </div>
  );
}

/** Los lotes más recientes, para el inicio del docente. */
export function RecentBatchesLoader() {
  const state = useBatches(1);
  return (
    <BatchesBody state={state} skeletonRows={RECENT_COUNT}>
      {(batches) => <BatchList batches={batches.slice(0, RECENT_COUNT)} />}
    </BatchesBody>
  );
}
