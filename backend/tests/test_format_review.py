"""Revisión de formato según APA 7 e IEEE (T25, HU-21): un caso por regla que la cumple
y otro que no, las reglas de la lista y lo que nunca debe cambiar."""

from dataclasses import replace

import pytest

from app.extraction.base import Author, ExtractedFields
from app.pipeline.norm_detection import Norm
from app.pipeline.segmentation import Segmentation, SegmentedReference
from app.sources.lookup import Strategy
from app.sources.records import Source, SourceRecord
from app.verification.decision import Verdict, Verification, truthfulness_index
from app.verification.format_review import CATALOG, review_list, review_norm, review_reference

APA_OK = (
    "Pérez, M. A., & López, J. (2021). Redes neuronales en la educación. "
    "Revista Andina, 12(3), 10-20. https://doi.org/10.1234/ra.2021.1"
)
IEEE_OK = (
    '[1] M. A. Pérez y J. López, "Redes neuronales en la educación," Revista Andina, '
    "vol. 12, no. 3, pp. 10-20, 2021, doi: 10.1234/ra.2021.1."
)
ARTICLE = ExtractedFields(
    authors=(Author("Pérez", "M. A."), Author("López", "J.")),
    year=2021,
    title="Redes neuronales en la educación",
    container="Revista Andina",
    volume="12",
    pages="10-20",
)
BOOK = ExtractedFields(authors=(Author("Pérez", "M."),), year=2021, title="Redes neuronales")
RECORD = SourceRecord(Source.CROSSREF, "10.1234/ra.2021.1", ARTICLE.title)
FOUND = Verification(Verdict.VERIFIED, Strategy.DIRECT_DOI, record=RECORD)


def codes(
    text: str,
    norm: Norm,
    fields: ExtractedFields | None = None,
    verification: Verification | None = None,
) -> list[str]:
    reference = SegmentedReference(1, 1, text, norm, None)
    return [item.code for item in review_reference(reference, norm, fields, verification)]


def one(
    code: str,
    text: str,
    norm: Norm,
    fields: ExtractedFields | None = None,
    verification: Verification | None = None,
) -> tuple[str | None, str | None]:
    reference = SegmentedReference(1, 1, text, norm, None)
    found = review_reference(reference, norm, fields, verification)
    [finding] = [item for item in found if item.code == code]
    return finding.given, finding.official


def listing(norm: Norm, *texts: str) -> Segmentation:
    return Segmentation(
        [SegmentedReference(i, 1, text, norm, None) for i, text in enumerate(texts, start=1)],
        norm,
    )


# --- Referencias bien escritas --------------------------------------------------------------


def test_una_referencia_apa_correcta_no_tiene_hallazgos() -> None:
    assert codes(APA_OK, Norm.APA, ARTICLE, FOUND) == []


def test_una_referencia_ieee_correcta_no_tiene_hallazgos() -> None:
    assert codes(IEEE_OK, Norm.IEEE, ARTICLE, FOUND) == []


# --- APA 7 ----------------------------------------------------------------------------------


def test_apa_doi_faltante_con_el_registro() -> None:
    text = "Pérez, M. (2021). Redes neuronales. Revista Andina, 12(3), 10-20."
    given, official = one("APA_DOI_FALTANTE", text, Norm.APA, ARTICLE, FOUND)
    assert (given, official) == ("Sin DOI", "https://doi.org/10.1234/ra.2021.1")
    assert codes(APA_OK, Norm.APA, ARTICLE, FOUND) == []


def test_apa_doi_faltante_no_se_dispara_si_el_registro_no_es_seguro() -> None:
    other_work = replace(RECORD, title="Otra obra distinta")
    search = Verification(Verdict.DISCREPANCY, Strategy.BIBLIOGRAPHIC_SEARCH, record=other_work)
    text = "Pérez, M. (2021). Redes neuronales. Revista Andina."
    assert "APA_DOI_FALTANTE" not in codes(text, Norm.APA, ARTICLE, search)
    assert "APA_DOI_FALTANTE" not in codes(text, Norm.APA, ARTICLE, None)


@pytest.mark.parametrize(
    ("written", "given"),
    [
        ("doi:10.1234/ab.1.", "doi:10.1234/ab.1"),
        ("DOI: 10.1234/ab.1", "DOI: 10.1234/ab.1"),
        ("10.1234/ab.1", "10.1234/ab.1"),
    ],
)
def test_apa_doi_que_no_es_enlace(written: str, given: str) -> None:
    text = f"Pérez, M. (2021). Redes. Revista Andina. {written}"
    assert one("APA_DOI_FORMATO", text, Norm.APA) == (given, "https://doi.org/10.1234/ab.1")


@pytest.mark.parametrize(
    "written",
    ["https://doi.org/10.1234/ab.1", "https://onlinelibrary.wiley.com/doi/10.1002/ab.1"],
)
def test_apa_un_doi_en_un_enlace_no_es_un_hallazgo(written: str) -> None:
    assert codes(f"Pérez, M. (2021). Redes. Revista Andina. {written}", Norm.APA) == []


def test_apa_anio_sin_parentesis() -> None:
    text = "Pérez, M. 2021. Redes neuronales. Revista Andina."
    assert one("APA_ANIO_PARENTESIS", text, Norm.APA) == ("2021", "(2021)")


@pytest.mark.parametrize(
    "date", ["(2021)", "(2021a)", "(2021, 3 de mayo)", "(07 de julio de 1985)", "(s. f.)", "(s.f.)"]
)
def test_apa_fechas_validas_entre_parentesis(date: str) -> None:
    assert codes(f"Pérez, M. {date}. Redes neuronales.", Norm.APA) == []


def test_apa_en_prensa_no_pide_anio() -> None:
    assert codes("Pérez, M. (en prensa). Redes neuronales.", Norm.APA) == []


def test_apa_texto_al_final_de_la_lista_no_pide_anio() -> None:
    text = "Y para que así conste, firmo la presente en Manta en octubre de 2025."
    assert codes(text, Norm.APA) == []


@pytest.mark.parametrize(
    ("authors", "given", "official"),
    [
        ("Pérez, Juan", "Pérez, Juan", "Pérez, J."),
        ("Pérez, Juan Carlos", "Pérez, Juan Carlos", "Pérez, J. C."),
        ("J. Pérez", "J. Pérez", "Pérez, J."),
        ("Pérez, M. A., & Vera, L", "Vera, L", "Vera, L."),
    ],
)
def test_apa_autor_mal_escrito(authors: str, given: str, official: str) -> None:
    text = f"{authors} (2021). Redes neuronales."
    assert one("APA_AUTOR_FORMATO", text, Norm.APA) == (given, official)


@pytest.mark.parametrize(
    "authors",
    [
        "Pérez, M.",
        "Delgado Quirós, M. A., y Rivas, L.",
        "De la Cruz, J.-M.",
        "Ministerio de Salud.",
        "Organización Mundial de la Salud.",
        # Un apellido sin iniciales seguido de otro autor (un solo nombre es válido).
        "Quispe, Mendoza, L. O., y Tapia, M. A.",
    ],
)
def test_apa_autores_validos(authors: str) -> None:
    assert codes(f"{authors} (2021). Redes neuronales.", Norm.APA) == []


def test_apa_un_titulo_antes_de_la_fecha_no_es_un_autor() -> None:
    text = "Posiciones, Sexos y Niveles. Nutrición, 16(6). Rivas, M. (2020). Otra obra."
    assert codes(text, Norm.APA) == []


def test_apa_et_al_en_la_lista() -> None:
    text = "Pérez, M., et al. (2021). Redes neuronales."
    given, official = one("APA_ET_AL_EN_LISTA", text, Norm.APA)
    assert given == "et al."
    assert official and "Hasta 20 autores" in official


def test_apa_et_al_de_una_obra_editada_es_valido() -> None:
    assert codes("Pérez, M., et al. (Eds.). (2021). Redes neuronales.", Norm.APA) == []


def test_apa_el_ultimo_editor_conserva_el_punto_de_su_inicial() -> None:
    text = "Vera, A. B., Rojas, L., & Mora, E. (Eds.). (2012). Manual de HMI. Editorial Andina."
    assert codes(text, Norm.APA) == []


def test_apa_et_al_en_el_titulo_no_cuenta() -> None:
    assert codes("Pérez, M. (2021). Una réplica de Smith et al. Revista.", Norm.APA) == []


def test_apa_recuperado_de() -> None:
    text = "Pérez, M. (2021). Redes. Recuperado de https://sitio.ec/redes."
    assert one("APA_RECUPERADO_DE", text, Norm.APA) == (
        "Recuperado de https://sitio.ec/redes.",
        "https://sitio.ec/redes",
    )


def test_apa_recuperado_con_fecha_es_valido() -> None:
    text = "Pérez, M. (2021). Redes. Recuperado el 3 de mayo de 2021 de https://sitio.ec/redes"
    assert codes(text, Norm.APA) == []


# --- IEEE -----------------------------------------------------------------------------------


def test_ieee_doi_faltante_con_el_registro() -> None:
    text = '[1] M. Pérez, "Redes neuronales," Revista Andina, vol. 12, pp. 10-20, 2021.'
    assert one("IEEE_DOI_FALTANTE", text, Norm.IEEE, ARTICLE, FOUND) == (
        "Sin DOI",
        "doi: 10.1234/ra.2021.1",
    )


def test_ieee_autor_con_el_apellido_primero() -> None:
    text = '[1] Pérez, M. A., y López, J., "Redes neuronales," Revista Andina, 2021.'
    given, official = one("IEEE_AUTOR_FORMATO", text, Norm.IEEE)
    assert (given, official) == ("Pérez, M. A.; López, J.", "M. A. Pérez; J. López")


def test_ieee_autores_con_el_nombre_completo() -> None:
    text = '[1] Juan Pérez y Ana López, "Redes neuronales," Revista Andina, 2021.'
    fields = ExtractedFields(authors=(Author("Pérez", "Juan"), Author("López", "Ana")))
    assert one("IEEE_AUTOR_FORMATO", text, Norm.IEEE, fields) == (
        "Juan Pérez; Ana López",
        "J. Pérez; A. López",
    )


def test_ieee_una_organizacion_no_es_un_nombre_completo() -> None:
    text = "[1] Amazon Web Services, Guía de uso. 2021. [En línea]."
    fields = ExtractedFields(authors=(Author("Services", "Amazon Web"),))
    assert codes(text, Norm.IEEE, fields) == []


def test_ieee_titulo_sin_comillas() -> None:
    text = "[1] M. Pérez, Redes neuronales en la educación, Revista Andina, vol. 12, 2021."
    title = "Redes neuronales en la educación"
    assert one("IEEE_TITULO_COMILLAS", text, Norm.IEEE, ARTICLE) == (title, f"“{title},”")


@pytest.mark.parametrize("quotes", ['"{}"', "“{}”", "«{}»"])
def test_ieee_titulo_entre_comillas_es_valido(quotes: str) -> None:
    text = f"[1] M. Pérez, {quotes.format('Redes neuronales')}, Revista Andina, 2021."
    assert "IEEE_TITULO_COMILLAS" not in codes(text, Norm.IEEE, ARTICLE)


def test_ieee_un_libro_va_sin_comillas() -> None:
    assert codes("[1] M. Pérez, Redes neuronales. Quito: UNEMI, 2021.", Norm.IEEE, BOOK) == []


def test_ieee_un_libro_segun_el_registro_va_sin_comillas() -> None:
    record = replace(RECORD, title=ARTICLE.title, work_type="book")
    book = Verification(Verdict.VERIFIED, Strategy.DIRECT_DOI, record=record)
    text = "[1] M. Pérez, Redes neuronales en la educación, Revista Andina, vol. 12, 2021."
    assert "IEEE_TITULO_COMILLAS" not in codes(text, Norm.IEEE, ARTICLE, book)


@pytest.mark.parametrize(
    ("written", "right"),
    [
        ("volumen 12", "vol. 12"),
        ("Vol. 12", "vol. 12"),
        ("núm. 3", "no. 3"),
        ("nº 3", "no. 3"),
        ("No. 3", "no. 3"),
        ("págs. 10-20", "pp. 10-20"),
        ("p. 10-20", "pp. 10-20"),
        ("pág. 846", "p. 846"),
        ("pp 10-20", "pp. 10-20"),
    ],
)
def test_ieee_abreviaturas_incorrectas(written: str, right: str) -> None:
    text = f'[1] M. Pérez, "Redes neuronales," Revista Andina, {written}, 2021.'
    assert one("IEEE_ABREVIATURAS", text, Norm.IEEE) == (written, right)


def test_ieee_abreviaturas_correctas() -> None:
    text = '[1] M. Pérez, "Redes," Revista Andina, vol. 12, no. 3, pp. 10-20, p. 5, 2021.'
    assert codes(text, Norm.IEEE) == []


def test_ieee_anio_antes_del_titulo() -> None:
    text = '[1] M. Pérez (2021). "Redes neuronales," Revista Andina.'
    given, official = one("IEEE_ANIO_POSICION", text, Norm.IEEE)
    assert given == "(2021)"
    assert official and official.endswith("2021.")


def test_ieee_un_anio_en_el_nombre_de_la_obra_no_cuenta() -> None:
    fields = ExtractedFields(title="Energy management systems")
    text = "[1] Organización. ISO 50001:2011. Energy management systems. Ginebra: ISO, 2011."
    assert "IEEE_ANIO_POSICION" not in codes(text, Norm.IEEE, fields)


# --- Reglas de la lista completa ------------------------------------------------------------


def test_lista_apa_en_orden_alfabetico_sin_hallazgos() -> None:
    assert (
        review_list(
            listing(
                Norm.APA,
                "Ávila, M. (2021). Una obra.",
                "Baque, J. (2020). Otra obra.",
                "Núñez, L. (2019). Tercera obra.",
                "Sand, P. R. (2018). Cuarta obra.",
                "Sanderson, A. R. (2018). Quinta obra.",
            )
        )
        == {}
    )


def test_lista_apa_desordenada_deja_un_hallazgo_en_el_primer_caso() -> None:
    found = review_list(
        listing(
            Norm.APA,
            "Bravo, M. (2021). Una obra.",
            "Zapata, J. (2020). Otra obra.",
            "Castro, L. (2019). Tercera obra.",
            "Diaz, A. (2018). Cuarta obra.",
            "Andrade, B. (2017). Quinta obra.",
        )
    )
    assert list(found) == [3]
    [finding] = found[3]
    assert finding.code == "APA_ORDEN_ALFABETICO"
    assert finding.given == "Castro aparece después de Zapata"
    assert finding.official == "Castro antes de Zapata"
    assert finding.message.endswith("Se encontraron 2 casos en la lista.")


def test_lista_apa_fragmentos_y_particulas_no_rompen_el_orden() -> None:
    assert (
        review_list(
            listing(
                Norm.APA,
                "Bravo, M. (2021). Una obra.",
                "De la Torre, L. (2020). Va en la T para APA y en la D para otros.",
                "Sports Medicine and Physical Fitness, 56(12), 1-10.",
                "Castro, L. (2019). Tercera obra.",
                "Van der Berg, A. (2018). Otra obra.",
                "Diaz, A. (2018). Cuarta obra.",
            )
        )
        == {}
    )


def test_lista_ieee_numerada_en_orden_sin_hallazgos() -> None:
    assert review_list(listing(Norm.IEEE, "[1] Una.", "[2] Otra.", "[3] Tercera.")) == {}


def test_lista_ieee_salto_de_numero_es_un_solo_caso() -> None:
    found = review_list(listing(Norm.IEEE, "[1] Una.", "[3] Otra.", "[4] Tercera."))
    [finding] = found[2]
    assert (finding.code, finding.given, finding.official) == ("IEEE_NUMERACION", "[3]", "[2]")
    assert "casos" not in finding.message


def test_lista_ieee_referencia_sin_numero() -> None:
    found = review_list(listing(Norm.IEEE, "[1] Una.", "M. Pérez, Otra.", "[3] Tercera."))
    [finding] = found[2]
    assert finding.given == "M. Pérez, Otra.…"
    assert finding.official == "[2]"


def test_lista_ieee_corchete_perdido_y_anexo_final_no_son_hallazgos() -> None:
    assert review_list(listing(Norm.IEEE, "[1] Una.", "2] Otra.", "[3] Tercera.", "Anexos")) == {}


def test_lista_mixta_avisa_en_la_primera_de_la_norma_con_menos_referencias() -> None:
    references = [
        SegmentedReference(1, 1, APA_OK, Norm.APA, None),
        SegmentedReference(2, 1, APA_OK, Norm.APA, None),
        SegmentedReference(3, 1, IEEE_OK, Norm.IEEE, None),
    ]
    found = review_list(Segmentation(references, Norm.MIXED))
    [finding] = found[3]
    assert finding.code == "NORMA_MIXTA"
    assert finding.given == "IEEE"
    assert finding.official == "APA, como las otras 2 referencias de la lista"
    assert finding.message.endswith("Es la única referencia en IEEE de la lista.")


def test_lista_mixta_con_varias_de_la_norma_minoritaria_dice_cuantas_son() -> None:
    references = [
        SegmentedReference(1, 1, APA_OK, Norm.APA, None),
        SegmentedReference(2, 1, IEEE_OK, Norm.IEEE, None),
        SegmentedReference(3, 1, APA_OK, Norm.APA, None),
        SegmentedReference(4, 1, IEEE_OK, Norm.IEEE, None),
        SegmentedReference(5, 1, APA_OK, Norm.APA, None),
    ]
    [finding] = review_list(Segmentation(references, Norm.MIXED))[2]
    assert finding.given == "IEEE"
    assert finding.official == "APA, como las otras 3 referencias de la lista"
    assert finding.message.endswith("Es la primera de las 2 referencias en IEEE.")


def test_lista_mixta_empatada_pide_una_sola_norma() -> None:
    references = [
        SegmentedReference(1, 1, APA_OK, Norm.APA, None),
        SegmentedReference(2, 1, IEEE_OK, Norm.IEEE, None),
    ]
    [finding] = review_list(Segmentation(references, Norm.MIXED))[2]
    assert finding.given == "IEEE"
    assert finding.official == "Una sola norma en toda la lista"
    assert finding.message.endswith("La lista tiene 1 en APA y 1 en IEEE.")


# --- Norma con la que se revisa -------------------------------------------------------------


def test_lista_de_norma_desconocida_no_se_revisa() -> None:
    reference = SegmentedReference(1, 1, "Pérez, Juan 2021. Redes.", Norm.UNKNOWN, None)
    assert review_reference(reference, Norm.UNKNOWN, None, None) == []
    assert review_list(Segmentation([reference], Norm.UNKNOWN)) == {}


def test_cada_referencia_se_revisa_con_su_norma_y_si_no_con_la_de_la_lista() -> None:
    assert review_norm(Norm.IEEE, Norm.APA) is Norm.IEEE
    assert review_norm(Norm.UNKNOWN, Norm.APA) is Norm.APA
    assert review_norm(Norm.UNKNOWN, Norm.MIXED) is None
    assert review_norm(Norm.UNKNOWN, Norm.UNKNOWN) is None


def test_una_referencia_de_una_lista_mixta_se_revisa_con_su_propia_norma() -> None:
    reference = SegmentedReference(1, 1, "Pérez, M., et al. (2021). Redes.", Norm.APA, None)
    found = review_reference(reference, Norm.MIXED, None, None)
    assert [item.code for item in found] == ["APA_ET_AL_EN_LISTA"]


def test_una_entrada_sin_separacion_confirmada_no_se_revisa() -> None:
    reference = SegmentedReference(1, 1, "Pérez, M., et al. (2021). Redes.", Norm.APA, "dudosa")
    assert review_reference(reference, Norm.APA, None, None) == []


# --- Lo que no debe cambiar -----------------------------------------------------------------


def test_el_formato_no_cambia_el_veredicto_ni_el_indice() -> None:
    text = "Pérez, Juan, et al. 2021. Redes. doi:10.1234/ra.2021.1"
    before = truthfulness_index([FOUND.verdict])
    assert review_reference(
        SegmentedReference(1, 1, text, Norm.APA, None), Norm.APA, ARTICLE, FOUND
    )
    assert FOUND.verdict is Verdict.VERIFIED
    assert truthfulness_index([FOUND.verdict]) == before


def test_el_catalogo_tiene_las_reglas_acordadas() -> None:
    assert set(CATALOG) == {
        "APA_DOI_FALTANTE",
        "APA_DOI_FORMATO",
        "APA_ANIO_PARENTESIS",
        "APA_AUTOR_FORMATO",
        "APA_ET_AL_EN_LISTA",
        "APA_RECUPERADO_DE",
        "APA_ORDEN_ALFABETICO",
        "IEEE_NUMERACION",
        "IEEE_AUTOR_FORMATO",
        "IEEE_TITULO_COMILLAS",
        "IEEE_ABREVIATURAS",
        "IEEE_ANIO_POSICION",
        "IEEE_DOI_FALTANTE",
        "NORMA_MIXTA",
    }
    assert all(len(code) <= 40 for code in CATALOG)  # t_hallazgos.codigo es VARCHAR(40)
