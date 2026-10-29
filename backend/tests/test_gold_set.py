"""Estándar de oro: archivos, validación, acuerdo entre anotadores y alteraciones (T09)."""

import json
from pathlib import Path

import httpx
import pytest

from app.benchmark.gold_set import (
    ALTERATIONS,
    FIELDS,
    GoldReference,
    agreement,
    cohen_kappa,
    make_alterations,
    read_csv,
    strata,
    to_database_row,
    validate,
    write_csv,
)
from app.repositories.gold_set import SupabaseGoldSetRepository
from scripts.gold_set import main
from tests.pdf_factory import PageSpec, make_pdf

# Al leer la planilla, cada campo está presente aunque quede vacío.
EMPTY = dict.fromkeys(FIELDS, "")
APA_TEXT = (
    "Pérez, M. y López Vera, J. A. (2021). Redes neuronales en la educación superior. "
    "Revista Andina, 8(1), 10–25. https://doi.org/10.1234/ra.2021.8"
)
APA_FIELDS = {
    **EMPTY,
    "autores": "Pérez, M.; López Vera, J. A.",
    "anio": "2021",
    "titulo": "Redes neuronales en la educación superior",
    "contenedor": "Revista Andina",
    "volumen": "8",
    "numero": "1",
    "paginas": "10-25",  # en la planilla con guion corto; el PDF trae "–"
    "doi": "10.1234/ra.2021.8",
}
IEEE_TEXT = (
    '[1] A. Rivas y L. Moreira, "Evaluación de fuentes académicas," Rev. Ciencia, '
    "vol. 14, no. 2, pp. 45–60, 2020, doi: 10.5678/rc.2020.14."
)
IEEE_FIELDS = {
    **EMPTY,
    "autores": "Rivas, A.; Moreira, L.",
    "anio": "2020",
    "titulo": "Evaluación de fuentes académicas",
    "contenedor": "Rev. Ciencia",
    "volumen": "14",
    "numero": "2",
    "paginas": "45-60",
    "doi": "10.5678/rc.2020.14",
}


def apa(reference_id: str = "R001", **changes: str) -> GoldReference:
    return GoldReference(
        reference_id, APA_TEXT, "APA", "articulo", {**APA_FIELDS, **changes}, "Miguel"
    )


def ieee(reference_id: str = "R002") -> GoldReference:
    return GoldReference(reference_id, IEEE_TEXT, "IEEE", "articulo", IEEE_FIELDS, "Jackson")


# --- Archivos y validación ------------------------------------------------------------------


def test_el_csv_conserva_todo_al_guardar_y_leer(tmp_path: Path) -> None:
    path = tmp_path / "estandar.csv"
    write_csv(path, [apa(), ieee()])

    assert read_csv(path) == [apa(), ieee()]


def test_lee_el_csv_de_excel_en_espanol_con_punto_y_coma(tmp_path: Path) -> None:
    path = tmp_path / "excel.csv"
    path.write_bytes(
        "id;texto;norma;tipo_obra;anio\nR001;Rivas, A. (2020). Título.;apa;Libro;2020\n".encode(
            "cp1252"
        )
    )

    [reference] = read_csv(path)

    assert (reference.norm, reference.work_type, reference.value("anio")) == (
        "APA",
        "libro",
        "2020",
    )


def test_una_anotacion_correcta_no_tiene_problemas() -> None:
    assert validate([apa(), ieee()]) == []


@pytest.mark.parametrize(
    ("reference", "problem"),
    [
        pytest.param(apa(anio="21"), "anio '21' debe tener 4 dígitos", id="año"),
        pytest.param(
            apa(titulo="Redes neuronales en educación"),
            "titulo 'Redes neuronales en educación' no aparece tal cual",
            id="título mal copiado",
        ),
        pytest.param(
            apa(autores="Peres, M."), "el apellido 'Peres' no aparece", id="apellido mal copiado"
        ),
        pytest.param(GoldReference("R009", APA_TEXT, "MLA", "articulo"), "norma 'MLA'", id="norma"),
    ],
)
def test_detecta_errores_de_anotacion(reference: GoldReference, problem: str) -> None:
    assert any(problem in item for item in validate([reference]))


def test_detecta_ids_repetidos() -> None:
    assert "R001: id repetido 2 veces" in validate([apa(), apa()])


def test_cuenta_las_referencias_reales_por_estrato() -> None:
    counts = strata([apa(), apa("R003"), ieee()])

    assert counts[("APA", "articulo")] == 2
    assert counts[("IEEE", "articulo")] == 1
    assert counts[("IEEE", "web")] == 0


# --- Acuerdo entre anotadores ---------------------------------------------------------------


def test_kappa_de_cohen() -> None:
    assert cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    # Ejemplo clásico: 70 % de acuerdo observado y 50 % esperado por azar, kappa 0.4.
    first = ["si"] * 20 + ["si"] * 5 + ["no"] * 10 + ["no"] * 15
    second = ["si"] * 20 + ["no"] * 5 + ["si"] * 10 + ["no"] * 15
    assert cohen_kappa(first, second) == pytest.approx(0.4)


def test_acuerdo_entre_dos_anotadores() -> None:
    miguel = [apa(), ieee()]
    jackson = [apa(paginas="10"), ieee(), apa("R099")]  # R099 solo la anotó uno

    result = agreement(miguel, jackson)

    assert result.common == 2
    assert result.by_field["paginas"] == 0.5
    assert result.by_field["titulo"] == 1.0
    assert result.kappa["norma"] == 1.0
    assert result.differences == ["R001 · paginas: '10-25' / '10'"]


# --- Alteraciones ---------------------------------------------------------------------------


def real_set() -> list[GoldReference]:
    references = []
    for number in range(1, 21):
        surname = f"Apellido{chr(64 + number)}"
        title = f"Estudio número {number} sobre fuentes"
        year = str(2000 + number)
        doi = f"10.1234/obra.{number:03d}"
        text = (
            f"{surname}, M. ({year}). {title}. Revista Andina, 8(1), 10-25. https://doi.org/{doi}"
        )
        fields = {"autores": f"{surname}, M.", "anio": year, "titulo": title, "doi": doi}
        references.append(GoldReference(f"R{number:03d}", text, "APA", "articulo", fields))
    return references


def test_las_alteraciones_son_reproducibles_y_equilibradas() -> None:
    first = make_alterations(real_set(), total=12)
    second = make_alterations(real_set(), total=12)

    assert first == second  # misma semilla, mismas alteradas
    assert len(first) == 12
    assert {kind: sum(ref.alteration == kind for ref in first) for kind in ALTERATIONS} == {
        "anio": 3,
        "autor": 3,
        "titulo": 3,
        "doi": 3,
    }
    assert len({ref.source_id for ref in first}) == 12  # cada real se altera una sola vez


def test_cada_alteracion_cambia_un_solo_dato_en_el_texto_y_en_sus_campos() -> None:
    originals = {reference.id: reference for reference in real_set()}

    for altered in make_alterations(real_set(), total=8):
        original = originals[altered.source_id]
        changed = [name for name in original.fields if altered.value(name) != original.value(name)]
        assert altered.altered and altered.id == f"{original.id}-alt-{altered.alteration}"
        assert changed == ["autores" if altered.alteration == "autor" else altered.alteration]
        assert altered.text != original.text
        assert validate([altered]) == []  # el campo alterado aparece en el texto alterado


def test_el_doi_alterado_conserva_la_forma_de_un_doi() -> None:
    originals = {reference.id: reference for reference in real_set()}
    [altered] = [ref for ref in make_alterations(real_set(), total=4) if ref.alteration == "doi"]

    assert altered.value("doi").startswith("10.1234/obra.")
    assert altered.value("doi") != originals[altered.source_id].value("doi")


# --- Base de datos y comandos ---------------------------------------------------------------


def test_la_fila_conserva_su_uuid_al_recargar() -> None:
    row = to_database_row(apa())

    assert row["id"] == to_database_row(apa())["id"]
    assert row["norma"] == "APA" and row["es_alterada"] is False
    campos = row["campos_anotados"]
    assert isinstance(campos, dict)
    assert campos["id_planilla"] == "R001" and campos["tipo_obra"] == "articulo"


def test_cargar_reemplaza_el_estandar_completo() -> None:
    seen: list[tuple[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, json.loads(request.content) if request.content else None))
        return httpx.Response(204 if request.method == "DELETE" else 201)

    repository = SupabaseGoldSetRepository(
        "https://proyecto.supabase.co/rest/v1", httpx.Client(transport=httpx.MockTransport(handler))
    )
    repository.replace_all([to_database_row(apa())])

    assert [method for method, _ in seen] == ["DELETE", "POST"]


def test_flujo_completo_de_la_herramienta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf = tmp_path / "trabajo.pdf"
    pdf.write_bytes(
        make_pdf(
            [PageSpec(["Texto del trabajo con suficientes caracteres.", "Referencias", APA_TEXT])]
        )
    )
    base, annotated, final = tmp_path / "base.csv", tmp_path / "anotado.csv", tmp_path / "final.csv"

    assert main(["preparar", str(pdf), "--salida", str(base)]) == 0
    [prepared] = read_csv(base)
    assert prepared.text.startswith("Pérez, M.") and prepared.norm == "APA"
    assert prepared.fields == {name: "" for name in prepared.fields}  # sin precargar

    write_csv(annotated, [apa(), ieee()])
    assert main(["validar", str(annotated)]) == 0
    assert main(["alterar", str(annotated), "--salida", str(final)]) == 0
    assert len(read_csv(final)) > 2
    assert "faltan" in capsys.readouterr().out  # aún no se cumple la meta por estrato
