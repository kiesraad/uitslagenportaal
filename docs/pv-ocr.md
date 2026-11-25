## PV OCR

This document describes how test PVs are generated, how the table of contents of a PV is determined, and how to set
up DVC and get the data.

### Generating test PVs

The OCR test set in [ml/data/testdata](../ml/data/README.md) pairs PV scans with the 510b EMLs
they should match. Handwritten models we have no scans of are made by generating the form from
the template and EML, then filling it in by hand and scanning it.

- **Models.** Download the templates from kiesraad.nl. [pv-models.md](pv-models.md) lists which models hold handwritten vote counts.
- **Corrections.** The `uitslagenportaal-test-emls` repo has branches `auto-<election>-tel`.
  There, each `correctie_*.zip` follows the `definitieve-documenten_*.zip` it corrects, in
  commit order; the inner `Telling_*.zip` holds the 510b. Name the copies as the test set's
  [layout](../ml/data/README.md#layout) says.
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

### Machine learning

#### Preparation

DVC, MLflow and the other machine-learning dependencies are the `ml` dependency group of the backend, so the scripts
in `ml/scripts/` can use the backend's code and the production image leaves them out. They run in the `ml` compose
service, which has the repo mounted at `/project` and works from `/project/ml`:

```bash
docker compose up -d --build ml
docker compose exec ml dvc repro
```

The profile keeps the service out of a plain `docker compose up --build`, so rebuild it by name after a dependency
change. For the IDE only, `uv sync --all-groups` in `backend/` installs every group into `backend/.venv`; the
pipeline itself expects the container. The service extends `backend-scripts`, so Django's settings work as expected,
with the log level at INFO to keep DVC's libraries quiet.

Keep the container running between sessions. `up -d` recreates it whenever the image or its compose config changed,
which kills whatever runs in it, so check that it is idle first. DVC remembers file hashes by inode, and a recreated
container may see new inodes and hash all of `data/testdata` again. Run DVC only in the container, never on the host as
well: the two see different paths and keep invalidating each other's hashes. On Windows it can help to move the project
to a WSL folder, and run it from there.

#### Access to the DVC remote

The DVC remote `storage` is `s3://uitslagenportaal-mlops/dvc` on Scaleway Object Storage (`nl-ams`), set in
`ml/.dvc/config`. You need a Scaleway API key with read and write access to objects in that bucket; it needs no
delete rights. Store it in `ml/.dvc/config.local`, which git ignores:

```bash
docker compose exec ml dvc remote modify --local storage access_key_id <access key>
docker compose exec ml dvc remote modify --local storage secret_access_key <secret key>
```

Where nothing should be written to disk, such as CI or a GPU VM, set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
instead; the `ml` service passes them through from the host. Check access with
`docker compose exec ml dvc status --cloud`.

#### Data

All data lives in `ml/data/` and is tracked with DVC; [ml/data/README.md](../ml/data/README.md) describes each
directory. `docker compose exec ml dvc pull` fetches it, about 9 GB for the test set alone.

#### Pipeline

`ml/dvc.yaml` defines the stages, each rerun only when its dependencies or params changed; paths are in `ml/data/`:

| Stage           | Reads                                         | Writes              |
|-----------------|-----------------------------------------------|---------------------|
| `toc`           | `testdata/`, the TOC code                     | `tocs.json`         |
| `orientations`  | `testdata/`, `tocs.json`                      | `orientations.json` |
| `extract_crops` | `testdata/`, `tocs.json`, `orientations.json` | `crops/`            |
| `split`         | `crops/`                                      | `split/`            |

`toc` is a full table-of-contents pass over the test set; it depends on `pv_toc.py` and `pv_classifier.py` in the
backend, so changing those reruns it. `orientations` stores the rotation of each page `extract_crops` reads, found
with Tesseract's orientation detection (`pv_ocr/utils/orientation.py`). That takes about a third of the time of
`extract_crops`, and doesn't depend on the detectors in `vote_tables.py`, so changing those reruns only
`extract_crops` and `split`. `ml/params.yaml` holds the params, such as `jobs`, the number of worker processes.

Any change in `testdata/` reruns `toc`, also a new or replaced 510b, which it doesn't read. Where no PV changed,
`dvc commit toc` records the new state without running it.

A full run takes hours.

```bash
docker compose exec ml dvc repro                  # every stage that is out of date
docker compose exec ml dvc repro extract_crops    # up to this stage
docker compose exec ml dvc status                 # what would rerun, and why
docker compose exec ml python -m scripts.determine_tocs data/testdata/GR2026/0050-zeewolde /tmp/tocs.json
```

The last runs a script on its own, outside DVC, on part of the data: handy while developing it. Run the scripts as
modules with `-m`: `scripts/__init__.py` sets Django up before a script imports backend code, which a plain
`python scripts/….py` skips.

A `dvc` command that is killed, for instance by recreating the container, leaves its locks in `ml/.dvc/tmp`, and the
next one refuses to start. With no DVC process running in the container, delete `rwlock`, `rwlock.lock` and `lock`
there.

