"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState } from "react";
import { Pagination } from "@/shared/components/ui/pagination";
import { PAGE_PARAM, parsePage } from "@/shared/lib/pagination";
import { useHistory } from "../use-history";
import { WorkHistory, WorkListSkeleton, WorkSearch } from "./work-history";
import { Notice, WakingNotice } from "@/shared/components/ui/notice";

/** La búsqueda viaja en la dirección, como la página (?buscar=avance&pagina=2). */
export const SEARCH_PARAM = "buscar";

const LIST_ID = "trabajos";

/** Historial real del estudiante (HU-07): de 20 en 20, con página y búsqueda en la dirección. */
export function WorkHistoryLoader() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const page = parsePage(searchParams.get(PAGE_PARAM));
  const search = searchParams.get(SEARCH_PARAM) ?? "";
  const [version, setVersion] = useState(0);
  const state = useHistory(page, search, version);

  /** Una búsqueda nueva vuelve a la página 1. */
  const applySearch = useCallback(
    (value: string) => {
      const params = new URLSearchParams();
      if (value) params.set(SEARCH_PARAM, value);
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  return (
    <div id={LIST_ID} className="flex scroll-mt-6 flex-col gap-4">
      <WorkSearch search={search} onSearch={applySearch} />

      <div className="flex flex-col gap-4">
        {state.kind === "loading" ? (
          <>
            <p role="status" className="sr-only">
              Cargando tus trabajos…
            </p>
            {state.slow ? <WakingNotice /> : null}
            <WorkListSkeleton />
          </>
        ) : null}

        {state.kind === "error" ? <Notice tone="error">{state.message}</Notice> : null}

        {state.kind === "ready" ? (
          <>
            <WorkHistory
              works={state.page.items}
              searching={search !== ""}
              onDeleted={() => setVersion((current) => current + 1)}
            />
            {state.page.total > 0 ? (
              <Pagination
                slice={state.page}
                pathname={pathname}
                query={searchParams.toString()}
                noun="trabajos"
                nounOne="trabajo"
                anchorId={LIST_ID}
              />
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
