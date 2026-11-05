"""Resultado de la verificación de un análisis (PostgREST de Supabase).

Guarda una fila de verificaciones por referencia con veredicto, lo que respondió
el NLI por campo (inferencias_nli), los hallazgos de veracidad y el índice de
veracidad del análisis. Una referencia con error de consulta no tiene fila en
verificaciones: solo su hallazgo informativo.
"""

from typing import Any, Protocol
from uuid import UUID

import httpx

from app.repositories.supabase_http import send
from app.verification.decision import CheckedField, NliCheck, Verification
from app.verification.findings import findings_for

# NUMERIC(8,3): la relevancia de OpenAlex puede pasar de lo que cabe.
MAX_SCORE = 99_999.999


class VerificationRepository(Protocol):
    def save(
        self,
        analysis_id: UUID,
        verifications: dict[str, Verification | None],
        index: float | None,
    ) -> None:
        """Guarda la verificación de cada referencia (por su id; None si falló por un
        error interno) y el índice de veracidad del análisis."""
        ...


class SupabaseVerificationRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._rest_url = rest_url
        self._client = client

    def save(
        self,
        analysis_id: UUID,
        verifications: dict[str, Verification | None],
        index: float | None,
    ) -> None:
        with_verdict = {
            reference_id: verification
            for reference_id, verification in verifications.items()
            if verification and not verification.query_failed
        }
        rows = [_verification_row(ref_id, item) for ref_id, item in with_verdict.items()]
        saved = (
            self._send(
                "POST",
                "verificaciones",
                json=rows,
                headers={"Prefer": "return=representation"},
                params={"select": "id,referencia_id"},
            )
            if rows
            else []
        )
        ids = {row["referencia_id"]: row["id"] for row in saved}

        inferences = [
            _inference_row(ids[reference_id], check)
            for reference_id, verification in with_verdict.items()
            for check in verification.nli
        ]
        if inferences:
            self._send("POST", "inferencias_nli", json=inferences)

        findings = [
            {
                "referencia_id": reference_id,
                "tipo": "veracidad",
                "codigo": finding.code,
                "severidad": finding.severity.value,
                "campo": finding.field.value if finding.field else None,
                "valor_dado": finding.given,
                "valor_oficial": finding.official,
                "mensaje": finding.message,
            }
            for reference_id, verification in verifications.items()
            for finding in findings_for(verification)
        ]
        if findings:
            self._send("POST", "hallazgos", json=findings)

        self._send(
            "PATCH",
            "analisis",
            params={"id": f"eq.{analysis_id}"},
            json={"indice_veracidad": index},
        )

    def _send(self, method: str, table: str, **options: Any) -> list[dict[str, Any]]:
        return send(self._client, method, f"{self._rest_url}/{table}", **options)


def _verification_row(reference_id: str, verification: Verification) -> dict[str, Any]:
    record = verification.record
    title = verification.check(CheckedField.TITLE)
    authors = verification.check(CheckedField.AUTHORS)
    year = verification.check(CheckedField.YEAR)
    score = record.score if record else None
    return {
        "referencia_id": reference_id,
        # Las obras con DOI ya están en registros_crossref: la búsqueda las guarda.
        "crossref_doi": record.doi if record else None,
        "estrategia": verification.strategy.value,
        "score_crossref": round(score, 3) if score is not None and score <= MAX_SCORE else None,
        "sim_titulo": round(title.similarity, 3) if title else None,
        "sim_autores": round(authors.similarity, 3) if authors else None,
        "coincide_anio": year.matches if year else None,
        "veredicto": verification.verdict.value if verification.verdict else None,
    }


def _inference_row(verification_id: str, check: NliCheck) -> dict[str, Any]:
    return {
        "verificacion_id": verification_id,
        "campo": check.field.value,
        "premisa": check.premise,
        "hipotesis": check.hypothesis,
        "p_implicacion": round(check.scores.entailment, 4),
        "p_neutral": round(check.scores.neutral, 4),
        "p_contradiccion": round(check.scores.contradiction, 4),
    }
