"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { KeyboardEvent, ReactNode } from "react";

type Tab = { id: string; label: string; content: ReactNode };

const TAB_PARAM = "pestana";

/** Pestañas accesibles del Laboratorio; la elegida viaja en la dirección (?pestana=benchmark). */
export function LabTabs({ tabs }: { tabs: Tab[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requested = searchParams.get(TAB_PARAM);
  const active = tabs.find((tab) => tab.id === requested)?.id ?? tabs[0].id;

  function choose(id: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set(TAB_PARAM, id);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    const index = tabs.findIndex((tab) => tab.id === active);
    const step = event.key === "ArrowRight" ? 1 : -1;
    const next = tabs[(index + step + tabs.length) % tabs.length].id;
    choose(next);
    document.getElementById(`tab-${next}`)?.focus();
  }

  return (
    <div className="flex flex-col gap-5">
      <div
        role="tablist"
        aria-label="Laboratorio de extracción"
        onKeyDown={handleKeyDown}
        className="flex gap-1 self-start rounded-pill border border-hairline bg-canvas p-1"
      >
        {tabs.map((tab) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => choose(tab.id)}
              className={`rounded-pill px-4 py-1.5 text-small font-semibold ${
                selected ? "bg-action text-on-action" : "text-body hover:text-ink"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {tabs.map((tab) => (
        <div
          key={tab.id}
          id={`panel-${tab.id}`}
          role="tabpanel"
          aria-labelledby={`tab-${tab.id}`}
          hidden={tab.id !== active}
          className="flex flex-col gap-4"
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
