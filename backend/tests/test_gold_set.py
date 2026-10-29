"""Estándar de oro: archivos, validación, acuerdo entre anotadores y alteraciones (T09)."""

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from app.benchmark.gold_set import (
    ALTERATIONS,
    FIELDS,
    MAX_PER_DOCUMENT,
    PARTITIONS,
    REAL_PER_NORM,
    RESERVE_NOTE,
    RESERVE_PER_NORM,
    GoldReference,
    agreement,
    cohen_kappa,
    composition,
    final_set,
    make_alterations,
    read_csv,
    same_value,
    select_sample,
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


def test_cuenta_las_referencias_reales_por_norma_y_tipo() -> None:
    counts = composition([apa(), apa("R003"), ieee()])

    assert counts[("APA", "articulo")] == 2
    assert counts[("IEEE", "articulo")] == 1
    assert counts[("IEEE", "web")] == 0


def test_detecta_demasiadas_referencias_de_un_mismo_documento() -> None:
    references = [
        GoldReference(f"R{n:03d}", APA_TEXT, "APA", "articulo", APA_FIELDS, document="tesis-1")
        for n in range(MAX_PER_DOCUMENT + 1)
    ]

    assert f"tesis-1: 4 referencias, el máximo es {MAX_PER_DOCUMENT}" in validate(references)


# --- Sorteo ---------------------------------------------------------------------------------


def candidates() -> list[GoldReference]:
    # 120 APA repartidas en 60 tesis y 10 IEEE de una sola tesis.
    apa_candidates = [
        GoldReference("", f"APA {n}", "APA", "", document=f"tesis-{n // 2}") for n in range(120)
    ]
    ieee_candidates = [
        GoldReference("", f"IEEE {n}", "IEEE", "", document="tesis-ieee") for n in range(10)
    ]
    return apa_candidates + ieee_candidates + [GoldReference("", "Sin norma", "", "")]


def test_el_sorteo_es_reproducible_y_respeta_los_limites() -> None:
    sample = select_sample(candidates())

    assert sample == select_sample(candidates())  # misma semilla, mismo sorteo
    apa_rows = [reference for reference in sample if reference.norm == "APA"]
    assert len(apa_rows) == REAL_PER_NORM + RESERVE_PER_NORM
    assert [reference.notes == RESERVE_NOTE for reference in apa_rows].count(True) == 15
    # Las 10 IEEE salen de una sola tesis: solo entran 3.
    assert sum(reference.norm == "IEEE" for reference in sample) == MAX_PER_DOCUMENT
    assert all(reference.norm in ("APA", "IEEE") for reference in sample)
    assert [reference.id for reference in sample[:2]] == ["R001", "R002"]
    # Las que se anotan van antes que las de reserva.
    first_reserve = next(n for n, ref in enumerate(sample) if ref.notes == RESERVE_NOTE)
    assert all(ref.notes == RESERVE_NOTE for ref in sample[first_reserve:])


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


def test_la_puntuacion_del_borde_no_es_un_desacuerdo() -> None:
    assert same_value("titulo", "Planificación de rutas,", "Planificación de rutas")
    assert same_value("doi", "10.1109/ICEI.2019.00087.", "10.1109/ICEI.2019.00087")
    assert same_value("autores", "Zarchan ; Musoff", "Zarchan; Musoff")
    assert not same_value("autores", "Parra Valencia", "Parra")
    assert not same_value("autores", "Jie; Jasser, Ajibade", "Jie; Jasser; Ajibade")


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
    first = make_alterations(real_set(), total=10)
    second = make_alterations(real_set(), total=10)

    assert first == second  # misma semilla, mismas alteradas
    assert len(first) == 10
    assert {kind: sum(ref.alteration == kind for ref in first) for kind in ALTERATIONS} == {
        "anio": 2,
        "autor": 2,
        "titulo": 2,
        "doi": 2,
        "inventada": 2,
    }
    assert len({ref.source_id for ref in first}) == 10  # si alcanzan, cada real se altera una vez


def test_solo_se_alteran_las_reales_con_doi() -> None:
    without_doi = [replace(ref, fields={**ref.fields, "doi": ""}) for ref in real_set()[:15]]

    altered = make_alterations(without_doi + real_set()[15:], total=10)

    assert {ref.source_id for ref in altered} <= {"R016", "R017", "R018", "R019", "R020"}
    # Si no alcanzan, una real se repite, pero nunca con el mismo tipo de alteración.
    assert len(altered) == 10
    assert len({(ref.source_id, ref.alteration) for ref in altered}) == 10


def test_cada_alteracion_cambia_solo_sus_datos_en_el_texto_y_en_los_campos() -> None:
    originals = {reference.id: reference for reference in real_set()}
    expected = {
        "anio": ["anio"],
        "autor": ["autores"],
        "titulo": ["titulo"],
        "doi": ["doi"],
        "inventada": ["autores", "anio", "titulo"],  # piezas de otras referencias
    }

    for altered in make_alterations(real_set(), total=10):
        original = originals[altered.source_id]
        changed = [name for name in original.fields if altered.value(name) != original.value(name)]
        assert altered.altered and altered.id == f"{original.id}-alt-{altered.alteration}"
        assert changed == expected[altered.alteration]
        assert altered.text != original.text
        assert validate([altered]) == []  # el campo alterado aparece en el texto alterado


def test_el_anio_cambia_al_menos_dos_y_no_dentro_del_doi() -> None:
    references = [
        replace(ieee(f"R{n:03d}"), fields={**IEEE_FIELDS, "doi": f"10.5678/rc.2020.{n}"})
        for n in range(1, 6)
    ]
    references = [
        replace(ref, text=IEEE_TEXT.replace("rc.2020.14", ref.value("doi").split("/")[1]))
        for ref in references
    ]

    [altered] = [ref for ref in make_alterations(references, total=1) if ref.alteration == "anio"]

    assert 2 <= abs(int(altered.value("anio")) - 2020) <= 5
    assert "rc.2020." in altered.text  # el DOI conserva su año
    assert f"pp. 45–60, {altered.value('anio')}, doi" in altered.text


def test_cada_real_y_sus_alteradas_quedan_en_la_misma_particion() -> None:
    real = real_set()
    altered = make_alterations(real, total=10)
    final = final_set(real, altered)

    by_source = {ref.source_id: ref.partition for ref in altered}
    assert {ref.partition for ref in altered} == set(PARTITIONS)
    assert sum(ref.partition == "calibracion" for ref in altered) == 4  # 40 %
    for reference in final:
        if not reference.altered:
            assert reference.partition == by_source.get(reference.id, "")


def test_el_doi_alterado_conserva_la_forma_de_un_doi() -> None:
    originals = {reference.id: reference for reference in real_set()}
    [altered] = [ref for ref in make_alterations(real_set(), total=5) if ref.alteration == "doi"]

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

    assert main(["preparar", "--apa", str(pdf), "--salida", str(base)]) == 0
    [prepared] = read_csv(base)
    assert prepared.text.startswith("Pérez, M.") and prepared.norm == "APA"
    assert (prepared.id, prepared.document) == ("R001", "trabajo")
    assert prepared.fields == {name: "" for name in prepared.fields}  # sin precargar

    # La misma referencia APA dentro de un trabajo de la carpeta IEEE no entra.
    assert main(["preparar", "--ieee", str(pdf), "--salida", str(base)]) == 0
    assert read_csv(base) == []

    write_csv(annotated, [apa(), ieee()])
    assert main(["validar", str(annotated)]) == 0
    assert main(["alterar", str(annotated), "--salida", str(final)]) == 0
    assert len(read_csv(final)) > 2
    assert "APA: 1 de 50 (faltan 49)" in capsys.readouterr().out
