## PV test set (OCR)

The OCR test set pairs PV scans with the 510b EMLs they should match, organised as
`<election>/<code>-<slug>/`. Handwritten models we have no scans
of are made by generating the form from the template and EML, then filling it in by hand and
scanning it.

- **Models.** Only the Kiesraad models of November 2025 count. Download templates from
  kiesraad.nl. [pv-models.md](pv-models.md) lists which models hold handwritten vote counts.
- **Corrections.** The `uitslagenportaal-test-emls` repo has branches `auto-<election>-tel`.
  There, each `correctie_*.zip` follows the `definitieve-documenten_*.zip` it corrects, in
  commit order; the inner `Telling_*.zip` holds the 510b. Name the copies of the 510b
  `_origineel` and `_correctie1`, `_correctie2`, … in order.
- **Generating.** Overlay the template PDF with PyMuPDF rather than filling its ODT, which
  is built from absolutely positioned frames. Redact the blue `<…>` placeholders but keep
  their graphics, then draw text at their positions. Print what OSV would print and leave the
  handwritten fields empty; on a corrigendum (Na 14-2) that means names and Oorspronkelijk
  values printed and the Gecorrigeerd boxes empty. Write a txt per PV listing, per page, each
  number to write in. Print a PV complete, with every list, as real ones are. Put a
  "Geen officiële PV" watermark on page 1.
- **Layout.** Compare the result with real PVs of the model, page by page. A real Na 14-2
  Bijlage 1 gives "Is er een gecorrigeerde uitslag?" and the B1-2.4 heading a page of their
  own, prints I and J also when 0, and names the columns used in "Totaal lijst (kolom 1 + 2)".
  Removing the openbaar-lichaam variants of the template text needs the paragraph wrapped
  again.
- **Naming.** Name a generated PV as the PV classifier would, and check it with
  `classify_pvs`.
- **EML fields.** In a stembureau's `ReportingUnitVotes`, `Cast` holds the opgeroepenen, not
  H. E is `TotalCounted` and H is E + blanco + ongeldig. A–D are the `UncountedVotes`
  for geldige stempassen, volmachtbewijzen and kiezerspassen, and for toegelaten kiezers; I
  and J are the `UncountedVotes` for meer and minder getelde stembiljetten. List numbers within
  a kieskring can skip numbers. Candidate names come from the kieskring's 230b.
- **PyMuPDF.** Insert text under a font name that is not already used in the document, or
  pages built with `show_pdf_page` render garbled.
- **Checking.** Compare every printed value in the generated PDF's text layer with the EML
  before printing.

### Table of contents

`PvDetermineTOC` (`pv_ocr/utils/pv_toc.py`) determines what each page of a PV holds from the
headings alone. Only the top fifth (20%) of each page is rendered and read with Tesseract, and the
heading titles are matched fuzzily, since OCR misreads them heavily. A "Lijst N" heading gives a
candidate votes page its list number. A "Vervolg lijst N" heading, or a following page without a
heading, is a continued page (`candidate-votes-continued`) of that list. Such a continued page, or
any page left unknown, whose body (15-85% of the height) holds no ink is an empty page instead; an
unknown page with ink is read again down to 40%, as a block above its heading can push the heading
out of the top fifth, and, if still unknown, turned upright when Tesseract finds it scanned sideways
or upside down. A list number that OCR
misread or could not read is inferred from the neighbouring lists, only when exactly one number fits
between them, or from the number a continued page names; the command marks such a number with a "?".

`determine_pv_toc` runs it on files and prints a table of contents per file; nothing is written to
the database. `--crop-fraction` sets the share of the page read, `--json` prints the table as JSON
and `--show-text` the text of pages not recognized.

With a model, only the contents that model has are recognized (`MODEL_CONTENTS`). The command
takes the model from the `/PvModel` metadata the classifier writes, so the limits apply to classified
copies; a file without a known `/PvModel` is skipped. `--model` sets the model for every file without
reading the metadata, and `--no-model` reads every file unrestricted.

```bash
docker compose run --rm backend-scripts python manage.py determine_pv_toc <path> --limit 3
```
