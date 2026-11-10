"use client";

import { useParams } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { PdfDropzone, type RejectedPdf } from "@/shared/components/pdf-dropzone";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { MAX_FILES_PER_BATCH } from "@/shared/lib/pdf-rules";
import type { BatchDetail } from "../types";
import { useBatchDetail } from "../use-batch-detail";
import { useBatchUpload } from "../use-batch-upload";
import { BatchUploadProgress } from "./batch-upload-progress";
import { Notice } from "@/shared/components/ui/notice";

const EYEBROW = "Agregar trabajos";

function filesLabel(count: number): string {
  return `${count} ${count === 1 ? "archivo" : "archivos"}`;
}

/**
 * Agrega PDF a un lote que ya existe (por ejemplo, un trabajo olvidado), con la
 * misma subida y el mismo avance que al crear el lote. El lote admite 40 trabajos.
 */
export function AddWorksForm({ batch }: { batch: BatchDetail }) {
  const { uploads, sending, slow, addTo, retry, reset, batch: uploading } = useBatchUpload();
  const [files, setFiles] = useState<File[]>([]);
  const [rejected, setRejected] = useState<RejectedPdf[]>([]);
  const [dropzoneKey, setDropzoneKey] = useState(0);
  const remaining = MAX_FILES_PER_BATCH - batch.totalWorks;

  const busyRef = useRef(false);
  useEffect(() => {
    busyRef.current = sending;
  }, [sending]);

  // Next.js conserva la página oculta al navegar: al volver, empieza de cero salvo
  // que todavía se estén enviando archivos.
  useLayoutEffect(() => {
    return () => {
      if (busyRef.current) return;
      reset();
      setFiles([]);
      setRejected([]);
      setDropzoneKey((key) => key + 1);
    };
  }, [reset]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (files.length === 0) return;
    void addTo({ id: batch.id, name: batch.name, period: batch.period }, files, rejected);
  }

  if (uploading) {
    return (
      <BatchUploadProgress
        batch={uploading}
        uploads={uploads}
        sending={sending}
        slow={slow}
        onRetry={() => void retry()}
      />
    );
  }

  if (remaining <= 0) {
    return (
      <Notice tone="warning">
        El lote está completo: tiene {MAX_FILES_PER_BATCH} trabajos. Elimina alguno para agregar
        otros.
      </Notice>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <PdfDropzone
        key={dropzoneKey}
        multiple
        maxFiles={remaining}
        title="Arrastra aquí los PDF que faltan"
        hint={`Hasta ${remaining} PDF más en este lote · 10 MB cada uno · APA o IEEE`}
        onChange={setFiles}
        onRejected={setRejected}
      >
        <button
          type="submit"
          disabled={files.length === 0}
          className={`${buttonStyles({ fullWidth: true })} md:w-auto`}
        >
          {`Agregar al lote (${filesLabel(files.length)})`}
        </button>
      </PdfDropzone>
    </form>
  );
}

/** Pide el lote de la dirección y muestra el formulario, la carga o el motivo. */
export function AddWorksLoader() {
  const { loteId } = useParams<{ loteId: string }>();
  const state = useBatchDetail(loteId);
  const href = `/docente/lotes/${encodeURIComponent(loteId)}`;
  const back = { href, label: state.kind === "ready" ? state.batch.name : "el lote" };

  if (state.kind === "loading") {
    return (
      <PageSectionSkeleton back>
        <Skeleton className="h-dropzone w-full rounded-panel" />
      </PageSectionSkeleton>
    );
  }
  if (state.kind === "error") {
    return (
      <PageSection eyebrow={EYEBROW} title="Lote no disponible" back={back}>
        <Notice tone="error">{state.message}</Notice>
      </PageSection>
    );
  }
  return (
    <PageSection eyebrow={EYEBROW} title={state.batch.name} back={back}>
      <AddWorksForm batch={state.batch} />
    </PageSection>
  );
}
