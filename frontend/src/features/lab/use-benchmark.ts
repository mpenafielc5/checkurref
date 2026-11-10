import { useEffect, useState } from "react";
import { fetchBenchmark, runBenchmark, type BenchmarkOutcome } from "./api";

export type BenchmarkState = { kind: "loading" } | BenchmarkOutcome;

/** El panel del benchmark. Si una medición falla, lo ya medido sigue a la vista. */
export function useBenchmark() {
  const [state, setState] = useState<BenchmarkState>({ kind: "loading" });
  const [slow, setSlow] = useState(false);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchBenchmark(() => {
      if (active) setSlow(true);
    }).then((outcome) => {
      if (!active) return;
      setState(outcome);
      setSlow(false);
    });
    return () => {
      active = false;
    };
  }, []);

  async function run() {
    setRunning(true);
    setRunError(null);
    const outcome = await runBenchmark(() => setSlow(true));
    setRunning(false);
    setSlow(false);
    if (outcome.kind === "ready") setState(outcome);
    else setRunError(outcome.message);
  }

  return { state, slow, running, runError, run };
}
