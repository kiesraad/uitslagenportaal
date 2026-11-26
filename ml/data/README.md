# ML data

Data for training and evaluating the OCR models. Every directory here is tracked with DVC and stored in the
`uitslagenportaal-mlops` bucket; git only holds its `.dvc` file. See
[pv-ocr.md](../../docs/pv-ocr.md#access-to-the-dvc-remote) for access to the remote.

DVC runs in the `ml` compose service, from `ml/`:

```bash
docker compose exec ml dvc pull                                 # everything
docker compose exec ml dvc pull data/testdata/GR2026/0228-ede   # part of a directory
```

| Path                | Contents                                                   | Made by          |
|---------------------|------------------------------------------------------------|------------------|
| `testdata/`         | PVs, mostly scanned, with the 510b EMLs                    | hand, `dvc add`  |
| `tocs.json`         | The table of contents of each PV in `testdata/`, or `null` | `toc` stage      |
| `orientations.json` | The rotation of each vote page of the OCR models           | `orientations`   |
| `crops/`            | A crop of each handwritten number, with its 510b value     | `extract_crops`  |
| `split/`            | The crops for training, validation and testing             | `split`          |
| `evaluation/`       | The scores of each number reader on the test split         | `evaluate`       |

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

Turning a page upright takes Tesseract's orientation check, over a third of the time of `extract_crops`, so the
`orientations` stage stores the rotation of each page in `orientations.json`, and a change to the detectors reruns only
`extract_crops`. A page missing from it, as in a trial run with another `--glob`, is checked on the spot.

`crops.csv` lists each crop with its PV, model, page, field and `label`, the value in the 510b. That is the first 510b,
which holds the counts the gemeentelijk stembureau set; for a corrigendum (Na 14-1, Na 14-2 Bijlage 1) it is the last
`_correctie<n>`, if any. Some gemeenten attach the original N 10 PV to a Na 14-1; its pages, recognised by the model in
their footer, are labelled from the first 510b as that N 10 model, or left out where the N 10 PV is in `testdata/` too.
`blank` says whether the area holds no writing. On N 10 and Na 31-2 Bijlage 1 a blank area means 0; a corrigendum
leaves a count blank when it did not change, so a blank crop of a corrigendum says nothing about its label. For a
corrigendum, `changed` says whether the count differs from the `_origineel`. A label can still differ from what is
written, where the PV and the 510b disagree: with centrale stemopneming (N 10-2) the gemeentelijk stembureau counts
the votes again, and the 510b holds its count. A crop covers its row or field, and a third of its height below it, as
many write on the bottom line; part of a neighbouring number can show at the top or bottom.

`crops.csv` lists every crop found, but only the ones with `saved` true are on disk, as many would go unused: the
changed crops of a corrigendum, the written crops of the other models, and a share of their blank ones, `extract_crops.blank`
in `params.yaml`, chosen by a hash of the path so a rerun saves the same ones. It must leave enough blank crops for
`split.blank`. The unsaved rows stay in the CSV, as `split` needs them.

Pages where the fields cannot be placed reliably are skipped, and a PV where many counts that are not 0 come out blank is
left out: it was matched to the wrong stembureau, or holds pages of another model. Both are logged. Crops stop at the
"Bijlage voor een experiment met een nieuw stembiljet" (Noordoostpolder), whose layout differs. For a trial run on a
few PVs, with each page drawn with its areas:

```bash
docker compose exec ml python -m scripts.extract_crops data/testdata data/tocs.json data/orientations.json /tmp/crops \
    --glob "GR2026/0059-achtkarspelen/*SB1.pdf" --debug /tmp/debug
```

To check crops by hand, browse them with their labels in [FiftyOne](https://docs.voxel51.com/), filter on model, field,
label or `blank`, and tag the wrong ones. FiftyOne needs OpenCV 4, so it runs on the host in an environment of its own,
from the repository root:

```bash
uv run ml/scripts/browse_crops.py --sample 5000     # http://localhost:5151; --browser opens it
uv run ml/scripts/browse_crops.py                   # the same crops again, with their tags
uv run ml/scripts/browse_crops.py --all             # with the crops left out of every split
uv run ml/scripts/browse_crops.py --export-tags tagged.csv
```

The dataset is kept between starts; after `extract_crops` has run again, `--reload` loads the crops it saved.

Once `split` has run, each crop has a `split` field, `train`, `validate` or `test`, or empty when `split` left it out,
and each split has a saved view of that name, kept in step on every start, so these names can't hold a selection.
The browser then opens the `train` view. The crops `split` leaves out keep the label of their 510b, also where the
crop does not show it, as with the counts of an original PV that its corrigendum corrected (see [split](#split)). `--all` shows them too, and `--split` limits the crops of a `--view` to one split.

To measure how many labels are wrong, check a fixed random set: `--view` saves it under a name in the dataset, and
prints how many of its crops carry each tag. The same name opens it again, with the tags given; `--reload` drops both,
and the same options then select the same crops again.

```bash
uv run ml/scripts/browse_crops.py --view n10-2-check --model N10-2 --content votes-cast --written --take 200
uv run ml/scripts/browse_crops.py --view n10-2-check
uv run ml/scripts/browse_crops.py --view test-check --split test --written --take 500
```

## split

The `split` stage writes `train.csv`, `validate.csv` and `test.csv`, listing crops as `crops.csv` does, in the shares
of `params.yaml`. It splits by gemeente, so no handwriting is in two splits, and puts each model in every split. Half
the crops are blank, nearly all 0, so only `split.blank` of them is kept, as a share of the written crops.

A corrigendum is filled in only where a count changed, and its other fields may well be empty or show stray marks
`blank` misses, so only its `changed` crops are kept; with a single 510b none are. Where a count changed, the
`_origineel` holds the count from before the correction, which the original PV of that stembureau says, so its crop is
kept. Where the counts are equal, or there is a single 510b, the first 510b may hold the correction already, as when the
gemeentelijk stembureau made the corrigendum before setting its counts, so an original PV of the same stembureau,
attached or on its own, leaves out the fields its corrigendum filled in.

The votes-cast and differences crops of N 10-2 are in `train` only: the 510b holds the recount of the gemeentelijk
stembureau, which differs from what the stembureau wrote in about 5% of them, nearly always by 1 or 2.

## evaluation

The `evaluate` stage runs each reader in `evaluate.readers` of `params.yaml` over the test split, and writes its scores
to `evaluation/<reader>/`. It reads a sample of `evaluate.pages` whole pages, spread evenly over the models. A model
with fewer pages than its share, such as the corrigenda, is read whole; `null` reads the whole split. A reader that reads nothing scores
as 0, which is what a blank area means outside the corrigenda.

| File              | Contents                                                                                  |
|-------------------|-------------------------------------------------------------------------------------------|
| `metrics.json`    | The scores per model, pooled (`all`), and as the mean over the models (`macro`)           |
| `per_group.csv`   | The same scores as a table, a row per model, `all` and `macro`                            |
| `misreads.csv`    | Each crop read wrongly, with its label, the reading and its confidence, surest first      |
| `calibration.csv` | Per model and confidence bin, the crops, their mean confidence and their accuracy         |
| `confusion.csv`   | Per model, how often each digit is read as each other one; `∅` is a missed or extra digit |

The scores are `exact_match`, the share of numbers read right, also for the blank and written crops apart;
`page_exact_match`, the share of pages with every number of the split right, which holds only a few of their blank
crops; `digit_error_rate`, `confusion_1_7` and `confusion_7_1` from the confusion matrix of the written crops; and
`ece`, the expected calibration error. Compare readers on `macro`, the unweighted mean over the models: the pooled
scores lean towards the models with most numbers per page, such as Na 31-2 Bijlage 1. A model with fewer crops in the
sample than `evaluate.macro-min-crops` is scored, but left out of `macro`; `models` says how many count. The same scores, files and a heatmap of
each confusion matrix are logged to MLflow, in the experiment `number-readers`.
