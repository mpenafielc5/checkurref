import type { Verdict } from "@/shared/lib/verdicts";

/** Veredictos acumulados de los análisis terminados. */
type VerdictTotals = {
  counts: Record<Verdict, number>;
  /** Referencias sin veredicto porque una fuente no respondió. */
  queryErrors: number;
};

export type StudentStatistics = VerdictTotals & {
  role: "estudiante";
  works: number;
  references: number;
  averageIndex: number | null;
  mostDifferentField: string | null;
};

export type TeacherStatistics = VerdictTotals & {
  role: "docente";
  batches: number;
  works: number;
  references: number;
  highRiskWorks: number;
};

export type AdminStatistics = VerdictTotals & {
  role: "admin";
  users: { estudiante: number; docente: number; admin: number };
  documents: number;
  references: number;
};

export type Statistics = StudentStatistics | TeacherStatistics | AdminStatistics;
