"""Referencias separadas de un análisis y la norma detectada (PostgREST de Supabase)."""

from typing import Any, Protocol
from uuid import UUID

import httpx

from app.pipeline.segmentation import Segmentation
from app.repositories.supabase_http import send

# Hallazgo informativo de una entrada cuya separación no se pudo confirmar. No es
# un error del estudiante: también puede venir de la lectura del PDF.
UNCONFIRMED_SPLIT_CODE = "SEPARACION_NO_CONFIRMADA"


class ReferenceRepository(Protocol):
    def save_segmentation(self, analysis_id: UUID, segmentation: Segmentation) -> dict[int, str]:
        """Guarda las referencias y la norma; devuelve el id de cada una por su orden."""
        ...


class SupabaseReferenceRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._rest_url = rest_url
        self._client = client

    def save_segmentation(self, analysis_id: UUID, segmentation: Segmentation) -> dict[int, str]:
        # Si el análisis se repite, se reemplaza lo anterior (sus hallazgos se borran en cascada).
        self._send("DELETE", "referencias", params={"analisis_id": f"eq.{analysis_id}"})
        rows = [
            {
                "analisis_id": str(analysis_id),
                "orden": reference.order,
                "texto_crudo": reference.text,
                "pagina": reference.page,
                "norma": reference.norm.value,
            }
            for reference in segmentation.references
        ]
        saved = (
            self._send(
                "POST",
                "referencias",
                json=rows,
                headers={"Prefer": "return=representation"},
                params={"select": "id,orden"},
            )
            if rows
            else []
        )
        ids = {row["orden"]: row["id"] for row in saved}

        findings = [
            {
                "referencia_id": ids[reference.order],
                "tipo": "formato",
                "codigo": UNCONFIRMED_SPLIT_CODE,
                "severidad": "info",
                "valor_dado": reference.text,
                "mensaje": reference.issue,
            }
            for reference in segmentation.references
            if reference.issue
        ]
        if findings:
            self._send("POST", "hallazgos", json=findings)

        self._send(
            "PATCH",
            "analisis",
            params={"id": f"eq.{analysis_id}"},
            json={
                "norma_detectada": segmentation.norm.value,
                "total_referencias": len(segmentation.references),
            },
        )
        return ids

    def _send(self, method: str, table: str, **options: Any) -> list[dict[str, Any]]:
        return send(self._client, method, f"{self._rest_url}/{table}", **options)
