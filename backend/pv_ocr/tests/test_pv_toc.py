import json
from io import BytesIO, StringIO
from unittest import mock

import pypdfium2 as pdfium
import pytest
from django.core.management import CommandError, call_command
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject

from file_import.utils.named_bytes_io import NamedBytesIO
from pv_ocr.management.commands.determine_pv_toc import pdf_model
from pv_ocr.tests.classified_pvs import BLANK_PDF
from pv_ocr.utils.pv_classifier import MODELS, PDF_METADATA_KEYS, PvClassifier
from pv_ocr.utils.pv_toc import (
    HEADER_FRACTION,
    MODEL_CONTENTS,
    Heading,
    PageContent,
    PvDetermineTOC,
    TableOfContents,
    TocEntry,
    infer_list_numbers,
)
from pv_ocr.utils.rendering import DPI, render_scale

HEADING_CASES = [
    ("Inhoudsopgave\nDeel 1 - Verslag van de zitting\nDeel 2 - Telresultaten", Heading(PageContent.TABLE_OF_CONTENTS)),
    ("Deel 1 -- Verslag van de zitting\n1.1 Presentielijst", Heading(PageContent.SESSION_REPORT)),
    ("Deel 2 -- Telresultaten Stembureau 1\n2.1 Toegelaten kiezers", Heading(PageContent.ADMITTED_VOTERS)),
    (
        "2.2 Uitgebrachte stemmen Stembureau 1\n2.2.1 Beoordeel de stembiljetten\nE.1 Totaal lijst 1 -- CDA",
        Heading(PageContent.VOTES_CAST),
    ),
    # Three misread letters, within the budget of three for this title.
    ("Deel 2 - Telresultaten\n2.2 Uilgebrochte slemmen", Heading(PageContent.VOTES_CAST)),
    ("B1 - 3.3 Verschillen tussen aantal kiezers en uitgebrachte stemmen", Heading(PageContent.DIFFERENCES)),
    (
        "Deel 2 Telresultaten Slembureou I\n2.4 Stemmen per lijsl en per kqndidoot\n"
        "tijst 1 Ons Belong Slemmen Kondldool",
        Heading(PageContent.CANDIDATE_VOTES, 1, True),
    ),
    (
        "Gemeente 0059 Achtkarspelen Stembureau 1\n Lijst 2 - FNP   Stemmen  Kandidaat",
        Heading(PageContent.CANDIDATE_VOTES, 2, True),
    ),
    ("Lijst 3 VVD", Heading(PageContent.CANDIDATE_VOTES, 3, True)),
    ("Lijst 10-BBB", Heading(PageContent.CANDIDATE_VOTES, 10, True)),
    ("Vervolg lijst 3 VVD", Heading(PageContent.CANDIDATE_VOTES_CONTINUED, 3, True)),
    ("vervolg lijst 3 VVD", Heading(PageContent.CANDIDATE_VOTES_CONTINUED, 3, True)),
    ("Bijlage 1\nLijst & CDA", Heading(PageContent.CANDIDATE_VOTES, None, True)),
    # The section title alone starts no list.
    (
        "Deel 3 -- Ondertekening Gemeente 1945 Berg en Dal\n[2.4 Stemmen per lijst en per kandidaat",
        Heading(PageContent.CANDIDATE_VOTES),
    ),
    (
        "Deel 1 - Verschillen met telresultaten stembureau Gemeente 1945 Berg en Dal\n1.3 Lijsten met verschillen",
        Heading(PageContent.LIST_DIFFERENCES),
    ),
    # The part title in the running header does not beat the section heading.
    (
        "Deel 1 - Onderzoek naar telresultaten Gemeente 0356 Nieuwegein\n1.3 Lijsten met verschillen",
        Heading(PageContent.LIST_DIFFERENCES),
    ),
    ("Stembureau 1\nGemeentehuis\nOver deze bijlage", Heading(PageContent.ABOUT_ATTACHMENT)),
    ("Aantal kiesgerechtigden", Heading(PageContent.ELECTORATE)),
    ("Kiesdeler", Heading(PageContent.SEAT_ALLOCATION)),
    ("Toewijzing van zetels aan kandidaten Lijst 3 VVD", Heading(PageContent.SEAT_ALLOCATION)),
    ("Gekozen kandidaten in alfabetische volgorde", Heading(PageContent.ELECTED_CANDIDATES)),
    (
        "Stembureau 101\nDeze pagina is expres leeg\n"
        "Zo komt het handtekeningen-blad altijd op een losse pagina, ook als het verslag dubbelzijdig is geprint.",
        Heading(PageContent.EMPTY_PAGE),
    ),
    # The part title in the running header does not decide an empty page.
    (
        "Deel 3 - Ondertekening Gemeente 1945 Berg en Dal\nDeze pagina is expres leeg\n"
        "Zo komt het handtekeningen-blad altijd op een losse pagina",
        Heading(PageContent.EMPTY_PAGE),
    ),
    # A part title is no heading.
    ("Deel 1 - Verslag van de zitting Schagen - Stembureau 17", Heading(PageContent.UNKNOWN)),
    ("Deel 3 - Ondertekening Schagen - Stembureau 17", Heading(PageContent.UNKNOWN)),
    ("B1 - 2 Verschillen met telresultaten stembureau", Heading(PageContent.UNKNOWN)),
    ("Deel 1 - Onderzoek naar telresultaten", Heading(PageContent.UNKNOWN)),
    ("", Heading(PageContent.UNKNOWN)),
    # Four misread letters, one over the budget of three for this title.
    ("Uilgebrochle slemmen", Heading(PageContent.UNKNOWN)),
    # A short title allows one misread letter.
    ("Kiasdaler", Heading(PageContent.UNKNOWN)),
    ("Kiasdeler", Heading(PageContent.SEAT_ALLOCATION)),
]


@pytest.mark.parametrize(("text", "expected"), HEADING_CASES)
def test_identify_heading_from_header_text(text, expected):
    assert PvDetermineTOC.identify_heading(text) == expected


PART_CASES = [
    ("Deel 1 - Verslag van de zitting Schagen - Stembureau 17", PageContent.SESSION_REPORT),
    ("Deel 3 - Ondertekening Schagen - Stembureau 17", PageContent.SIGNATURES),
    ("B1 - 2 Verschillen met telresultaten stembureau", PageContent.INVESTIGATION),
    ("Deel 1 - Onderzoek naar telresultaten", PageContent.INVESTIGATION),
    # "Ede Stembureau" is no title of the session report.
    ("Bijlage 1 Gemeente 0228 Ede Stembureau 24 Stembureau Wijkcentrum De Velder", PageContent.UNKNOWN),
    ("Stembureau 18", PageContent.UNKNOWN),
    ("", PageContent.UNKNOWN),
]


@pytest.mark.parametrize(("text", "content"), PART_CASES)
def test_identify_part_from_header_text(text, content):
    assert PvDetermineTOC.identify_part(text) == content


def test_identify_heading_takes_the_first_title_found():
    text = "2.2 Uitgebrachte stemmen Stembureau 1\n2.1 Toegelaten kiezers"

    assert PvDetermineTOC.identify_heading(text)[:2] == (PageContent.VOTES_CAST, None)


def test_identify_part_is_unknown_for_a_heading_only_text():
    assert PvDetermineTOC.identify_part("2.2 Uitgebrachte stemmen") == PageContent.UNKNOWN


def test_identify_part_takes_a_running_header_part_title_as_admitted_voters():
    text = "Deel 2 - Gecorrigeerde telresultaten Gemeente 0228 Ede"

    assert PvDetermineTOC.identify_part(text) == PageContent.ADMITTED_VOTERS


def test_identify_heading_leaves_an_unreadable_continued_list_number_unknown():
    assert PvDetermineTOC.identify_heading("Vervolg lijst & VVD")[:2] == (PageContent.CANDIDATE_VOTES_CONTINUED, None)


def start(number: int | None) -> TocEntry:
    """A candidate votes page with a list heading, whose number may be unreadable."""
    return TocEntry(0, PageContent.CANDIDATE_VOTES, number, has_list_heading=True)


def cont(number: int | None) -> TocEntry:
    return TocEntry(0, PageContent.CANDIDATE_VOTES_CONTINUED, number)


def other() -> TocEntry:
    return TocEntry(0, PageContent.SIGNATURES)


def empty_page() -> TocEntry:
    return TocEntry(0, PageContent.EMPTY_PAGE)


def section_title() -> TocEntry:
    """A candidate votes page headed by the section title only, without a list heading."""
    return TocEntry(0, PageContent.CANDIDATE_VOTES)


# Each case: the entries as read, the list numbers after inference, and the positions flagged as inferred.
INFER_CASES = [
    pytest.param([start(5), start(None), start(7)], [5, 6, 7], [1], id="unreadable-number-between-neighbours"),
    pytest.param([start(5), start(5), start(7)], [5, 6, 7], [1], id="repeated-number"),
    pytest.param([start(5), start(3), start(7)], [5, 6, 7], [1], id="number-below-the-previous-list"),
    pytest.param([start(5), start(None), start(8)], [5, None, 8], [], id="wider-gap-is-left-unknown"),
    pytest.param([start(4), start(None)], [4, None], [], id="no-list-after-is-left-unknown"),
    pytest.param([start(5), cont(None)], [5, 5], [1], id="continuation-without-number-follows-the-list"),
    pytest.param(
        [start(5), start(5), cont(5), start(7)], [5, 6, 6, 7], [1, 2], id="continuation-follows-a-corrected-list"
    ),
    pytest.param([start(5), section_title(), start(7)], [5, None, 7], [], id="section-title-page-gets-no-number"),
    pytest.param([start(5), other(), start(None), start(7)], [5, None, None, 7], [], id="non-list-page-breaks-run"),
    pytest.param([start(5), empty_page(), start(None), start(7)], [5, None, None, 7], [], id="empty-page-breaks-run"),
    pytest.param([start(1), start(2), start(4)], [1, 2, 4], [], id="skipped-list-is-not-corrected"),
    pytest.param([start(1), cont(1), start(2), cont(2)], [1, 1, 2, 2], [], id="correct-continuations-are-untouched"),
    pytest.param([cont(4), start(5)], [4, 5], [], id="run-starting-with-a-continuation-keeps-its-number"),
    pytest.param(
        [start(3), cont(4), start(None), start(6)],
        [3, 3, None, 6],
        [1],
        id="continuation-follows-its-list-and-a-wide-gap-stays-unknown",
    ),
    pytest.param([start(8), start(2), start(None), start(4)], [8, 2, 3, 4], [2], id="misread-high-first-number"),
    pytest.param(
        [start(5), start(None), cont(6), start(8)],
        [5, 6, 6, 8],
        [1],
        id="unreadable-start-takes-the-continuation-number",
    ),
    pytest.param(
        [start(5), start(None), cont(None), start(7)], [5, 6, 6, 7], [1, 2], id="two-page-unreadable-list-is-inferred"
    ),
    pytest.param(
        [start(5), start(9), cont(6), start(8)],
        [5, 6, 6, 8],
        [1],
        id="untrusted-number-does-not-spread-to-a-fitting-continuation",
    ),
    pytest.param(
        [start(8), cont(2), start(3)], [2, 2, 3], [0], id="misread-high-first-list-is-corrected-by-its-continuation"
    ),
    pytest.param(
        [start(5), start(None), cont(None), cont(6), start(8)],
        [5, 6, 6, 6, 8],
        [1, 2],
        id="correcting-a-list-start-fills-its-earlier-numberless-continuations",
    ),
]


@pytest.mark.parametrize(("entries", "numbers", "inferred"), INFER_CASES)
def test_infer_list_numbers(entries, numbers, inferred):
    infer_list_numbers(entries)

    assert [e.list_number for e in entries] == numbers
    assert [i for i, e in enumerate(entries) if e.list_number_inferred] == inferred


@pytest.mark.parametrize(("width", "height"), [(595, 842), (842, 595)], ids=["portrait", "landscape"])
def test_render_scale_is_the_dpi_scale_for_a4(width, height):
    assert render_scale(width, height) == pytest.approx(DPI / 72, rel=0.01)


def test_render_scale_is_none_for_a_page_over_a3():
    assert render_scale(2000, 3000) is None


def test_render_scale_is_lower_for_a_page_between_a4_and_a3():
    scale = render_scale(842, 1191)

    assert scale is not None
    assert scale < DPI / 72


HEADERLESS = "Gemeente Ede Stembureau 1"


def determine(
    texts: list[str | None],
    model: str | None = None,
    empty: frozenset[int] = frozenset(),
    asked: list[list[int]] | None = None,
) -> list[TocEntry]:
    """Run determine with one fake header image per page, None for a page without image.

    `empty` is what `empty_bodies` reports; the pages it is asked about are appended to `asked`.
    """

    def empty_bodies(pages):
        if asked is not None:
            asked.append(list(pages))
        return set(empty)

    images = [None if text is None else object() for text in texts]
    ocr_texts = iter(text for text in texts if text is not None)
    with (
        mock.patch.object(PvDetermineTOC, "header_images", return_value=iter(images)),
        mock.patch.object(PvDetermineTOC, "empty_bodies", side_effect=empty_bodies),
        mock.patch.object(PvClassifier, "ocr", side_effect=lambda _: next(ocr_texts)),
    ):
        return PvDetermineTOC(NamedBytesIO(BLANK_PDF, "pv.pdf"), model=model).determine().entries


def test_determine_makes_an_unrecognized_first_page_the_cover():
    entries = determine(["Gemeente Ede\nVerkiezing", "Inhoudsopgave"])

    assert [e.content for e in entries] == [PageContent.COVER, PageContent.TABLE_OF_CONTENTS]
    assert [e.page for e in entries] == [1, 2]


def test_determine_keeps_the_header_text_in_the_entry():
    assert determine(["Kiesdeler"])[0].text == "Kiesdeler"


def test_determine_lets_an_unrecognized_page_continue_the_previous_list():
    entries = determine(["Cover", "Lijst 4 - SP", "Gemeente Ede Stembureau 1"])

    assert (entries[2].content, entries[2].list_number) == (PageContent.CANDIDATE_VOTES_CONTINUED, 4)


def test_determine_lets_a_running_header_continue_the_list_instead_of_the_part_title():
    texts = ["Cover", "Lijst 3 - VVD", "Deel 2 - Gecorrigeerde telresultaten Gemeente 0228 Ede"]

    entries = determine(texts)

    assert (entries[2].content, entries[2].list_number) == (PageContent.CANDIDATE_VOTES_CONTINUED, 3)


def test_determine_ends_the_list_at_a_signatures_page():
    entries = determine(["Cover", "Lijst 9 - CU", "Deel 3 - Ondertekening Schagen - Stembureau 17"])

    assert (entries[2].content, entries[2].list_number) == (PageContent.SIGNATURES, None)


def test_determine_does_not_continue_a_list_on_an_empty_page():
    texts = [
        "Lijst 6 - CU",
        "Stembureau 101\nDeze pagina is expres leeg\nZo komt het handtekeningen-blad altijd op een losse pagina",
        "Deel 3 - Ondertekening Gemeente 1945 Landgraaf",
    ]

    entries = determine(texts)

    assert [(e.content, e.list_number) for e in entries] == [
        (PageContent.CANDIDATE_VOTES, 6),
        (PageContent.EMPTY_PAGE, None),
        (PageContent.SIGNATURES, None),
    ]


def test_determine_uses_the_part_title_when_no_list_precedes():
    entries = determine(["Cover", "Deel 2 - Gecorrigeerde telresultaten Gemeente 0228 Ede"])

    assert entries[1].content == PageContent.ADMITTED_VOTERS


def test_determine_continues_a_list_without_number_and_infers_it():
    texts = ["Cover", "Lijst 5 - A", "Lijst & CDA", HEADERLESS, "Lijst 7 - B", HEADERLESS]

    entries = determine(texts)

    assert [(e.content, e.list_number, e.list_number_inferred) for e in entries[2:]] == [
        (PageContent.CANDIDATE_VOTES, 6, True),
        (PageContent.CANDIDATE_VOTES_CONTINUED, 6, True),
        (PageContent.CANDIDATE_VOTES, 7, False),
        (PageContent.CANDIDATE_VOTES_CONTINUED, 7, False),
    ]


def test_determine_keeps_a_page_without_text_unknown():
    entries = determine(["Cover", "Lijst 4 - SP", "  \n"])

    assert entries[2].content == PageContent.UNKNOWN


def test_determine_keeps_a_first_page_without_text_unknown():
    assert determine([""])[0].content == PageContent.UNKNOWN


def test_determine_leaves_a_page_without_image_unknown_and_does_not_read_it():
    entries = determine(["Cover", "Lijst 4 - SP", None])

    assert (entries[2].content, entries[2].text) == (PageContent.UNKNOWN, "")


def test_determine_keeps_an_unrecognized_page_unknown_after_other_content():
    entries = determine(["Cover", "Kiesdeler", "Stembureau 18"])

    assert entries[2].content == PageContent.UNKNOWN


def test_to_json_lists_page_and_content_and_the_list_number_only_when_known_or_inferred():
    toc = TableOfContents(
        [
            TocEntry(1, PageContent.COVER, text="ignored"),
            TocEntry(2, PageContent.CANDIDATE_VOTES, 5),
            TocEntry(3, PageContent.CANDIDATE_VOTES, 6, list_number_inferred=True),
            TocEntry(4, PageContent.CANDIDATE_VOTES, None),
        ]
    )

    assert toc.to_json() == [
        {"page": 1, "content": "cover"},
        {"page": 2, "content": "candidate-votes", "list_number": 5},
        {"page": 3, "content": "candidate-votes", "list_number": 6, "list_number_inferred": True},
        {"page": 4, "content": "candidate-votes"},
    ]


def test_model_contents_has_every_classifier_model():
    assert set(MODEL_CONTENTS) == set(MODELS)


@pytest.mark.parametrize("model", sorted(MODEL_CONTENTS))
def test_model_contents_always_include_cover_empty_page_and_unknown(model):
    assert {PageContent.COVER, PageContent.EMPTY_PAGE, PageContent.UNKNOWN} <= MODEL_CONTENTS[model]


def test_identify_heading_ignores_a_list_heading_the_model_lacks():
    heading = PvDetermineTOC.identify_heading("Lijst 3 VVD", MODEL_CONTENTS["N 10-2"])

    assert heading == Heading(PageContent.UNKNOWN)


SESSION_TEXT = (
    "Deel 1 — Verslag van de zitting Gemeente 0986 Voerendaal\n1.2 Getelde stembureaus\n"
    "… Als er extra onderzoeken hebben plaatsgevonden …"
)


def test_identify_heading_ignores_a_title_the_model_lacks():
    heading = PvDetermineTOC.identify_heading(SESSION_TEXT, MODEL_CONTENTS["Na 31-2"])

    assert heading.content == PageContent.UNKNOWN


def test_identify_part_names_the_part_when_the_heading_is_a_content_the_model_lacks():
    assert PvDetermineTOC.identify_part(SESSION_TEXT, MODEL_CONTENTS["Na 31-2"]) == PageContent.SESSION_REPORT


def test_identify_heading_without_a_model_finds_the_investigation_title():
    assert PvDetermineTOC.identify_heading(SESSION_TEXT).content == PageContent.INVESTIGATION


def test_identify_heading_takes_the_seat_allocation_title_without_a_list_number():
    text = (
        "Deel 2 — Uitslag en zetelverdeling Centraal stembureau Drechterland\nLijst 1 CDA\nAantal zetels: 5\n"
        "Met voorkeursstemmen gekozen kandidaten"
    )

    assert PvDetermineTOC.identify_heading(text) == Heading(PageContent.SEAT_ALLOCATION)


def test_identify_heading_takes_the_control_protocol_title_as_checks_and_corrections():
    text = "Deel 2 — Uitslag en zetelverdeling\n2.11 Uitkomst controleprotocol"

    assert PvDetermineTOC.identify_heading(text).content == PageContent.CHECKS_AND_CORRECTIONS


OBJECTION_TEXTS = ["Cover", "Lijst 5 - A", "Bijlage 2 - bezwaren van kiezers Gemeente 1680 Aa en Hunze"]


def test_determine_with_a_model_leaves_a_page_of_a_content_the_model_lacks_unknown():
    entries = determine(OBJECTION_TEXTS, "Na 31-2 Bijlage 1")

    assert [(e.content, e.list_number) for e in entries] == [
        (PageContent.COVER, None),
        (PageContent.CANDIDATE_VOTES, 5),
        (PageContent.UNKNOWN, None),
    ]


def test_determine_without_a_model_reads_the_objections_page_as_session_report():
    assert determine(OBJECTION_TEXTS)[2].content == PageContent.SESSION_REPORT


def test_determine_does_not_continue_a_list_in_a_model_without_continued_pages():
    entries = determine(["Cover", "Lijst 4 - SP", HEADERLESS], "N 10-2")

    assert [e.content for e in entries] == [PageContent.COVER, PageContent.UNKNOWN, PageContent.UNKNOWN]


def test_determine_continues_a_list_in_a_model_with_continued_pages():
    texts = ["Cover", "Lijst 5 - A", "Gemeente 0088 Schiermonnikoog Stembureau 1"]

    entries = determine(texts, "N 10-1")

    assert [(e.content, e.list_number) for e in entries] == [
        (PageContent.COVER, None),
        (PageContent.CANDIDATE_VOTES, 5),
        (PageContent.CANDIDATE_VOTES_CONTINUED, 5),
    ]


def test_pv_determine_toc_rejects_an_unknown_model():
    with pytest.raises(ValueError, match="Unknown model"):
        PvDetermineTOC(NamedBytesIO(BLANK_PDF, "pv.pdf"), model="X 99")


def pdf_with_model(path, model: str | None):
    """Write a blank PDF to the path, with /PvModel in its document information when a model is given."""
    writer = PdfWriter(clone_from=BytesIO(BLANK_PDF))
    if model:
        writer.add_metadata({PDF_METADATA_KEYS["model"]: model})
    with open(path, "wb") as f:
        writer.write(f)


def test_pdf_model_reads_the_model_from_the_metadata(tmp_path):
    pdf_with_model(tmp_path / "a.pdf", "Na31-2-B1")

    assert pdf_model(tmp_path / "a.pdf") == "Na31-2-B1"


def test_pdf_model_is_none_without_the_metadata(tmp_path):
    pdf_with_model(tmp_path / "a.pdf", None)

    assert pdf_model(tmp_path / "a.pdf") is None


def run_command_models(tmp_path, models: dict[str, str | None], *args) -> tuple[list, str]:
    """The `allowed` set each file was determined with, and the output; each file has its /PvModel from `models`."""
    for name, model in models.items():
        pdf_with_model(tmp_path / name, model)
    stdout = StringIO()
    allowed = []

    def determine(self):
        allowed.append(self.allowed)
        return TableOfContents([TocEntry(1, PageContent.COVER)])

    with mock.patch.object(PvDetermineTOC, "determine", autospec=True, side_effect=determine):
        call_command("determine_pv_toc", tmp_path, *args, stdout=stdout)
    return allowed, stdout.getvalue()


MODELLED_FILES = {"a.pdf": "Na31-2-B1", "b.pdf": "N10-1"}


def test_determine_pv_toc_takes_the_model_from_each_files_metadata(tmp_path):
    allowed, _ = run_command_models(tmp_path, MODELLED_FILES)

    assert allowed == [MODEL_CONTENTS["Na 31-2 Bijlage 1"], MODEL_CONTENTS["N 10-1"]]


def test_determine_pv_toc_passes_the_model_option_for_every_file(tmp_path):
    allowed, _ = run_command_models(tmp_path, {"a.pdf": None, "b.pdf": "Na31-2-B1"}, "--model", "N 10-1")

    assert allowed == [MODEL_CONTENTS["N 10-1"]] * 2


def test_determine_pv_toc_reads_unrestricted_with_no_model(tmp_path):
    allowed, output = run_command_models(tmp_path, {"a.pdf": None, "b.pdf": "N10-1"}, "--no-model")

    assert allowed == [None, None]
    assert "a.pdf  unrestricted  " in output
    assert "skipped" not in output.replace("0 skipped", "")


def test_determine_pv_toc_rejects_model_with_no_model(tmp_path):
    pdfs_in(tmp_path, "a.pdf")

    with pytest.raises(CommandError, match="--model and --no-model cannot be combined"):
        call_command("determine_pv_toc", tmp_path, "--model", "N 10-1", "--no-model")


def test_determine_pv_toc_shows_the_model_per_file(tmp_path):
    _, output = run_command_models(tmp_path, MODELLED_FILES)

    assert "a.pdf  Na 31-2 Bijlage 1  " in output
    assert "b.pdf  N 10-1  " in output


def test_determine_pv_toc_skips_a_file_without_a_model_and_counts_it(tmp_path):
    allowed, output = run_command_models(tmp_path, {"a.pdf": None, "b.pdf": "N10-1"})

    assert allowed == [MODEL_CONTENTS["N 10-1"]]
    assert "skipped: no /PvModel" in output
    assert "1 pages in 1 files, 1 skipped, 0 errors" in output


def test_determine_pv_toc_skips_a_file_with_an_unknown_model(tmp_path):
    allowed, output = run_command_models(tmp_path, {"a.pdf": "X99"})

    assert allowed == []
    assert "skipped: unknown /PvModel 'X99'" in output


def test_header_images_render_only_the_header_fraction():
    file = NamedBytesIO(BLANK_PDF, "pv.pdf")
    [header] = list(PvDetermineTOC(file, 0.5).header_images())
    pdf = pdfium.PdfDocument(BLANK_PDF)
    full = pdf[0].render(scale=DPI / 72, grayscale=True).to_pil()
    pdf.close()

    assert header.size[0] == full.size[0]
    assert header.size[1] == pytest.approx(full.size[1] * 0.5, abs=2)


def test_header_images_default_to_the_header_fraction_constant():
    [header] = list(PvDetermineTOC(NamedBytesIO(BLANK_PDF, "pv.pdf")).header_images())

    assert header.size[1] == pytest.approx(DPI * HEADER_FRACTION, abs=2)


def test_header_images_yield_none_for_an_oversized_page():
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(2384, 3370)  # A0
    pdf.new_page(595, 842)  # A4
    out = NamedBytesIO(b"", "big.pdf")
    pdf.save(out)
    pdf.close()

    images = list(PvDetermineTOC(out).header_images())

    assert images[0] is None
    assert images[1] is not None


def pdfs_in(tmp_path, *names):
    """Blank PDFs of the model N 10-1, which the command reads and skips none of."""
    for name in names:
        pdf_with_model(tmp_path / name, "N10-1")
    return [tmp_path / name for name in names]


def test_determine_pv_toc_carries_on_after_a_failed_file(tmp_path):
    pdfs_in(tmp_path, "a.pdf", "b.pdf")
    stdout = StringIO()
    toc = TableOfContents([TocEntry(1, PageContent.COVER)])
    with mock.patch.object(PvDetermineTOC, "determine", side_effect=[RuntimeError("boom"), toc]) as determine_mock:
        call_command("determine_pv_toc", tmp_path, stdout=stdout)

    output = stdout.getvalue()
    assert determine_mock.call_count == 2
    assert "error RuntimeError('boom')" in output
    assert "1 cover" in output
    assert "1 pages in 1 files, 0 skipped, 1 errors" in output


def test_determine_pv_toc_prints_json(tmp_path):
    [pdf] = pdfs_in(tmp_path, "a.pdf")
    stdout = StringIO()
    toc = TableOfContents([TocEntry(1, PageContent.COVER), TocEntry(2, PageContent.CANDIDATE_VOTES, 5)])
    with mock.patch.object(PvDetermineTOC, "determine", return_value=toc):
        call_command("determine_pv_toc", pdf, "--json", stdout=stdout)

    json_line = next(line for line in stdout.getvalue().splitlines() if line.strip().startswith("["))
    assert json.loads(json_line) == toc.to_json()


def test_determine_pv_toc_merges_equal_neighbours_in_the_compact_line(tmp_path):
    [pdf] = pdfs_in(tmp_path, "a.pdf")
    stdout = StringIO()
    toc = TableOfContents([TocEntry(n, PageContent.CANDIDATE_VOTES, 3) for n in (1, 2, 3)])
    with mock.patch.object(PvDetermineTOC, "determine", return_value=toc):
        call_command("determine_pv_toc", pdf, stdout=stdout)

    output = stdout.getvalue()
    assert "1-3 candidate-votes lijst 3" in output
    assert "  3 vote-count pages" in output
    assert "vote-count pages: 3" in output


def test_determine_pv_toc_marks_an_inferred_list_number_in_the_compact_line(tmp_path):
    [pdf] = pdfs_in(tmp_path, "a.pdf")
    stdout = StringIO()
    toc = TableOfContents(
        [
            TocEntry(1, PageContent.CANDIDATE_VOTES, 5),
            TocEntry(2, PageContent.CANDIDATE_VOTES, 6, list_number_inferred=True),
        ]
    )
    with mock.patch.object(PvDetermineTOC, "determine", return_value=toc):
        call_command("determine_pv_toc", pdf, stdout=stdout)

    output = stdout.getvalue()
    assert "1 candidate-votes lijst 5 | 2 candidate-votes lijst 6?" in output


def test_determine_pv_toc_passes_the_crop_fraction_on(tmp_path):
    [pdf] = pdfs_in(tmp_path, "a.pdf")
    toc = TableOfContents([TocEntry(1, PageContent.COVER)])
    fractions = []

    def determine(self):
        fractions.append(self.header_fraction)
        return toc

    with mock.patch.object(PvDetermineTOC, "determine", autospec=True, side_effect=determine):
        call_command("determine_pv_toc", pdf, "--crop-fraction", "0.3", stdout=StringIO())

    assert fractions == [0.3]


@pytest.mark.parametrize("fraction", ["0", "1.5", "-0.1"])
def test_determine_pv_toc_rejects_an_invalid_crop_fraction(tmp_path, fraction):
    [pdf] = pdfs_in(tmp_path, "a.pdf")

    with pytest.raises(CommandError, match="--crop-fraction must be above 0 and at most 1"):
        call_command("determine_pv_toc", pdf, "--crop-fraction", fraction)


def test_determine_pv_toc_accepts_a_crop_fraction_of_one(tmp_path):
    [pdf] = pdfs_in(tmp_path, "a.pdf")
    toc = TableOfContents([TocEntry(1, PageContent.COVER)])
    with mock.patch.object(PvDetermineTOC, "determine", return_value=toc):
        call_command("determine_pv_toc", pdf, "--crop-fraction", "1", stdout=StringIO())


def grey_image(pixels: dict[tuple[int, int], int] | None = None, fill: int = 255) -> Image.Image:
    """A 100x280 body image (28 strips of 10 rows) of one grey level, with single pixels set from `pixels`."""
    image = Image.new("L", (100, 280), fill)
    for xy, value in (pixels or {}).items():
        image.putpixel(xy, value)
    return image


def test_body_is_empty_for_a_white_image():
    assert PvDetermineTOC.body_is_empty(grey_image())


def test_body_is_empty_for_a_few_scattered_dark_pixels():
    assert PvDetermineTOC.body_is_empty(grey_image({(x, 5): 0 for x in (3, 40, 90)}))


def test_body_is_empty_for_faint_grey_above_the_ink_level():
    assert PvDetermineTOC.body_is_empty(grey_image(fill=210))


def test_body_is_not_empty_for_grey_below_the_ink_level():
    assert not PvDetermineTOC.body_is_empty(grey_image(fill=150))


def test_body_is_not_empty_for_a_short_block_in_one_strip():
    image = grey_image()
    image.paste(0, (10, 10, 20, 20))  # One strip, 10% inked; 0.36% of the whole band, under the limit.

    assert not PvDetermineTOC.body_is_empty(image)


def pdf_with_content(*streams: bytes) -> NamedBytesIO:
    """An A4 PDF with a page per content stream (PDF drawing operators; empty for a blank page)."""
    writer = PdfWriter()
    for content in streams:
        page = writer.add_blank_page(595, 842)
        stream = DecodedStreamObject()
        stream.set_data(content)
        page.replace_contents(stream)
    out = BytesIO()
    writer.write(out)
    return NamedBytesIO(out.getvalue(), "pv.pdf")


# PDF points are measured from the bottom; the header is above y=716 and the footer below y=126 (15% of 842).
BLANK_PAGE = b""
BODY_INK = b"0 g 100 300 300 100 re f"
HEADER_INK = b"0 g 100 740 300 60 re f"
FOOTER_INK = b"0 g 100 40 300 60 re f"
# Punch holes: mid-height, within the 8% side margin (47 pt of 595).
SIDE_INK = b"0 g 5 300 35 200 re f"


@pytest.mark.parametrize("ink", [HEADER_INK, FOOTER_INK, SIDE_INK], ids=["header", "footer", "side-margin"])
def test_empty_bodies_ignores_ink_in_the_header_footer_and_side_margin(ink):
    assert PvDetermineTOC(pdf_with_content(ink)).empty_bodies([1]) == {1}


def test_empty_bodies_only_returns_the_requested_pages():
    toc = PvDetermineTOC(pdf_with_content(BLANK_PAGE, BODY_INK, BLANK_PAGE))

    assert toc.empty_bodies([2, 3]) == {3}


def test_determine_only_checks_the_bodies_of_inherited_pages():
    texts = ["Cover", "Lijst 4 - SP", "Vervolg lijst 4 - SP", HEADERLESS, "Lijst 5 - B"]
    asked = []

    entries = determine(texts, empty=frozenset({4}), asked=asked)

    assert asked == [[4]]
    assert [e.content for e in entries[1:3]] == [PageContent.CANDIDATE_VOTES, PageContent.CANDIDATE_VOTES_CONTINUED]


def test_determine_does_not_check_bodies_when_no_page_inherited():
    asked = []

    determine(["Cover", "Lijst 4 - SP", "Vervolg lijst 4 - SP"], asked=asked)

    assert asked == []


def test_determine_does_not_let_an_empty_page_end_the_list_for_the_pages_after_it():
    asked = []

    entries = determine(["Cover", "Lijst 3 - VVD", HEADERLESS, HEADERLESS], empty=frozenset({3}), asked=asked)

    assert asked == [[3, 4]]
    assert [(e.content, e.list_number) for e in entries] == [
        (PageContent.COVER, None),
        (PageContent.CANDIDATE_VOTES, 3),
        (PageContent.EMPTY_PAGE, None),
        (PageContent.CANDIDATE_VOTES_CONTINUED, 3),
    ]


def test_determine_infers_a_list_number_across_blank_pages_and_leaves_them_unnumbered():
    texts = ["Lijst 5 - A", HEADERLESS, "Lijst & CDA", HEADERLESS, "Lijst 7 - B"]

    entries = determine(texts, empty=frozenset({2, 4}))

    assert [(e.content, e.list_number, e.list_number_inferred) for e in entries] == [
        (PageContent.CANDIDATE_VOTES, 5, False),
        (PageContent.EMPTY_PAGE, None, False),
        (PageContent.CANDIDATE_VOTES, 6, True),
        (PageContent.EMPTY_PAGE, None, False),
        (PageContent.CANDIDATE_VOTES, 7, False),
    ]
