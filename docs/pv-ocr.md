## PV test set (OCR)

The OCR test set pairs PV scans with the 510b EMLs they should match, organised as
`<election>/<code>-<slug>/`. Handwritten models we have no scans
of are made by generating the form from the template and EML, then filling it in by hand and
scanning it.

- **Models.** Only the Kiesraad models of November 2025 count. Download templates from
  kiesraad.nl.
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
