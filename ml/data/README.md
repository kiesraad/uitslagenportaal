# ML data

Data for training and evaluating the OCR models. Every directory here is tracked with DVC and stored in the
`uitslagenportaal-mlops` bucket; git only holds its `.dvc` file. See
[pv-ocr.md](../../docs/pv-ocr.md#access-to-the-dvc-remote) for access to the remote.

DVC runs in the `ml` compose service, from `ml/`:

```bash
docker compose exec ml dvc pull                                 # everything
docker compose exec ml dvc pull data/testdata/GR2026/0228-ede   # part of a directory
```

| Path        | Contents                                                   | Made by          |
|-------------|------------------------------------------------------------|------------------|
| `testdata/` | PVs, mostly scanned, with the 510b EMLs                    | hand, `dvc add`  |
| `tocs.json` | The table of contents of each PV in `testdata/`, or `null` | `toc` stage      |
| `crops/`    | A crop of each handwritten number, with its 510b value     | `extract_crops`  |

## testdata

Processen-verbaal (PVs), mostly scanned, for testing the OCR in two ways: reading the handwritten vote counts, checked
against the 510b EML of the gemeente, and determining the table of contents, i.e. what each page of a PV holds. Which
of the two a PV serves follows from its model (see [Purposes](#purposes)). Only the Kiesraad models of November 2025
are included. How the generated PVs are made is in [pv-ocr.md](../../docs/pv-ocr.md).

### Contents

| Model             | OCR | TOC | GR2026 | TK2025 |   PVs | Gemeenten |
|-------------------|:---:|:---:|-------:|-------:|------:|----------:|
| N 10-1            | Yes | Yes |    690 |        |   690 |        43 |
| N 10-2            | Yes |     |  1,467 |        | 1,467 |        67 |
| Na 14-1           | Yes | Yes |    130 |        |   130 |        23 |
| Na 14-2 Bijlage 1 | Yes | Yes |     24 |      4 |    28 |        13 |
| Na 31-2 Bijlage 1 | Yes | Yes |  1,263 |        | 1,263 |        58 |
| Na 14-2           |     | Yes |     14 |        |    14 |        14 |
| Na 31-1           |     | Yes |     44 |        |    44 |        44 |
| Na 31-2           |     | Yes |     55 |        |    55 |        55 |
| P 22-2            |     | Yes |    109 |        |   109 |       109 |
| **Total**         |     |     |  3,796 |      4 | 3,800 |       144 |

The TK2025 Na 14-2 Bijlage 1 PVs are generated from the template and the EMLs, and filled in by ourselves.

### Purposes

The model in a file name tells what a PV is for:

- **OCR** of handwritten vote counts (#520): the models whose counts are handwritten. The EML of the gemeente holds the
  numbers they should read.
- **TOC**, the table of contents of a PV (#513): the models with a page or more per list, printed or handwritten. They
  need no EML.

O 7, P 1f-1 and P 22-1 also have pages per list, but no PVs of their November 2025 layout exist yet. Select a purpose
by model in the file name, e.g. `classify_pvs ml/data/testdata --glob "**/GR2026_Na31-2_*.pdf"`. Printed models are PVs of a gemeentelijk
or centraal stembureau, so their names have no `_SB<n>`, and their folder may hold no EML.

### Layout

Files are grouped as `<election>/<code>-<slug>/` and each PV is named after the PV classifier's convention, e.g.
`GR2026_N10-2_0228-ede_SB1.pdf`. The 510b EMLs sit next to the PVs; corrected ones are named `_origineel`,
`_correctie1`, `_correctie2`, … in order. A generated PV has a txt listing, per page, each number written in.

### Adding PVs

Put the files in place following the layout, update the tables above, then:

```bash
docker compose exec ml dvc add data/testdata
docker compose exec ml dvc push
git add ml/data/testdata.dvc ml/data/README.md
```

The files are hardlinked to the DVC cache and read-only; run `dvc unprotect` on a file before changing it.

## crops

The `extract_crops` stage crops each handwritten number on the vote pages of the OCR models, as `tocs.json` finds them:
the counts A–J and the votes per candidate. `pv_ocr/utils/vote_tables.py` finds where they are written. Gemeenten fill
in the templates differently, so a page is first turned upright and then tries each layout: digit boxes in a ruled
table, then a gray or black column of candidate numbers. The counts are found by their printed description ("Blanco
stemmen", "Totaal lijst 3"), read with Tesseract. Crops are named `<election>/<pv>/p<page>_<field>.png`, the field
being `A`…`J`, `E.<list>` or `L<list>-<candidate>`.

`crops.csv` lists each crop with its PV, model, page, field and `label`, the value in the 510b. That is the first 510b,
which holds the counts the gemeentelijk stembureau set; for Na 14-2 Bijlage 1 it is the last `_correctie<n>`.
`blank` says whether the area holds no writing. On N 10 and Na 31-2 Bijlage 1 a blank area means 0; a corrigendum
leaves a count blank when it did not change, so a blank crop of a corrigendum says nothing about its label. For Na 14-2
Bijlage 1, `changed` says whether the count differs from the `_origineel`. A label can still differ from what is
written, where the PV and the 510b disagree. A crop covers its row or field only: a number written across the line
below it is cut there, and part of its neighbour can show.

Pages where the fields cannot be placed reliably are skipped, and a PV where many counts that are not 0 come out blank is
left out: it was matched to the wrong stembureau, or holds pages of another model. Both are logged. For a trial run on a
few PVs, with each page drawn with its areas:

```bash
docker compose exec ml python -m scripts.extract_crops data/testdata data/tocs.json /tmp/crops \
    --glob "GR2026/0059-achtkarspelen/*SB1.pdf" --debug /tmp/debug
```
