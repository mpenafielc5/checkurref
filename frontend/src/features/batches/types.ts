export type BatchStatus = { kind: "alerts"; count: number } | { kind: "analyzing"; done: number };

export type BatchSummary = {
  id: string;
  name: string;
  works: number;
  period: string;
  status: BatchStatus;
};

export type RiskLevel = "alto" | "medio" | "bajo";

export type BatchWork = {
  analysisId: string;
  name: string;
  references: number;
  index: number;
  alerts: number;
  risk: RiskLevel;
};

export type UploadState =
  | { kind: "listo" }
  | { kind: "verificando"; done: number; total: number }
  | { kind: "error"; reason: string };

export type BatchUpload = {
  fileName: string;
  sizeBytes: number;
  state: UploadState;
};
