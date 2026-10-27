import { buttonStyles } from "@/shared/components/ui/button-styles";
import {
  DataTable,
  numericClass,
  tableHeadClass,
  tdClass,
  thClass,
} from "@/shared/components/ui/data-table";
import { StatCard, StatRow } from "@/shared/components/ui/stat-card";
import { formatDecimal } from "@/shared/lib/format";
import type { SAMPLE_BENCHMARK } from "../sample-data";

/** F1 por campo de AnyStyle y spaCy contra el conjunto de oro (maqueta 18). */
export function BenchmarkPanel({ benchmark }: { benchmark: typeof SAMPLE_BENCHMARK }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-hairline bg-canvas px-5 py-3">
        <p className="flex flex-col text-small">
          <span className="font-semibold text-ink">Conjunto de oro: {benchmark.goldSet}</span>
          <span>{benchmark.goldDetail}</span>
        </p>
        <button type="button" disabled className={`${buttonStyles({ fullWidth: true })} md:w-auto`}>
          Ejecutar benchmark
        </button>
      </div>

      <StatRow>
        {benchmark.summary.map((item) => (
          <StatCard key={item.label} value={item.value} label={item.label} />
        ))}
      </StatRow>

      <DataTable caption="F1 por campo de cada motor">
        <thead className={tableHeadClass}>
          <tr>
            <th scope="col" className={thClass}>
              Campo
            </th>
            <th scope="col" className={`${thClass} ${numericClass}`}>
              F1 AnyStyle
            </th>
            <th scope="col" className={`${thClass} ${numericClass}`}>
              F1 spaCy
            </th>
            <th scope="col" className={thClass}>
              Mejor
            </th>
          </tr>
        </thead>
        <tbody>
          {benchmark.rows.map((row) => {
            const best = row.anystyle >= row.spacy ? "AnyStyle" : "spaCy";
            return (
              <tr key={row.field}>
                <td className={tdClass}>{row.field}</td>
                <td className={`${tdClass} ${numericClass}`}>{formatDecimal(row.anystyle)}</td>
                <td className={`${tdClass} ${numericClass}`}>{formatDecimal(row.spacy)}</td>
                <td className={`${tdClass} font-semibold text-verdict-verified-text`}>{best}</td>
              </tr>
            );
          })}
        </tbody>
      </DataTable>
    </div>
  );
}
