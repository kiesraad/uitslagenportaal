import argparse
import csv
import logging
import random
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from dvc import api

from scripts.extract_crops import CORRIGENDUM_MODELS, CSV_FIELDS

SPLITS = ("train", "validate", "test")
# Train only: the 510b holds the recount of the gemeentelijk stembureau, which differs from what is written in about 5%.
RECOUNTED = {("N10-2", "votes-cast"), ("N10-2", "differences")}

logger = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("crops", help="The output of extract_crops")
    parser.add_argument("output")
    return parser.parse_args()


def stembureau(row: dict) -> tuple[PurePosixPath, str]:
    path = PurePosixPath(row["pdf"])
    return path.parent, re.search(r"_SB(\d+)\.pdf$", path.name).group(1)


def select(rows: list[dict], blank_share: float, rng: random.Random) -> list[dict]:
    """The saved crops whose label is what is written, and as many saved blank ones at random as `blank_share` of those.

    A corrigendum is filled in only where a count changed, so only its changed crops are kept. Where its count did not
    change, or it has a single 510b, the first 510b may hold the correction already, so the original PV of that
    stembureau leaves out the field. Where it changed, the `_origineel` holds the count from before, which that PV
    says."""
    corrigenda = [row for row in rows if row["model"] in CORRIGENDUM_MODELS]
    corrected = {
        (stembureau(row), row["field"]) for row in corrigenda if row["blank"] != "True" and row["changed"] != "True"
    }
    kept = [row for row in corrigenda if row["changed"] == "True"]
    kept += [
        row
        for row in rows
        if row["model"] not in CORRIGENDUM_MODELS and (stembureau(row), row["field"]) not in corrected
    ]
    kept = [row for row in kept if row["saved"] == "True"]
    written = [row for row in kept if row["blank"] != "True"]
    blank = [row for row in kept if row["blank"] == "True" and row["model"] not in CORRIGENDUM_MODELS]
    wanted = round(blank_share * len(written))
    if len(blank) < wanted:
        logger.warning(
            "%d saved blank crops, fewer than the %d `split.blank` asks for; raise `extract_crops.blank`",
            len(blank),
            wanted,
        )
    return written + rng.sample(blank, min(len(blank), wanted))


def assign(rows: list[dict], shares: dict[str, float], rng: random.Random) -> dict[str, list[dict]]:
    """Split by gemeente, so that no handwriting is in two splits, with each model in every split. Model by model, the
    one in fewest gemeenten first, each of its gemeenten not split yet goes, at random, to a split without the model,
    else to the split furthest below its share of the model's crops."""
    crops = defaultdict(Counter)  # per gemeente, the crops of each model
    for row in rows:
        crops[PurePosixPath(row["pdf"]).parent][row["model"]] += 1
    totals = Counter(row["model"] for row in rows)
    split_of = {}
    for model in sorted(totals, key=lambda m: sum(m in models for models in crops.values())):
        gemeenten = sorted(gemeente for gemeente, models in crops.items() if model in models)
        count = Counter({split: 0 for split in SPLITS})
        for gemeente in gemeenten:
            if gemeente in split_of:
                count[split_of[gemeente]] += crops[gemeente][model]
        rest = [gemeente for gemeente in gemeenten if gemeente not in split_of]
        rng.shuffle(rest)
        for gemeente in rest:
            split = min(SPLITS, key=lambda s: (count[s] > 0, count[s] - shares[s] * totals[model]))
            split_of[gemeente] = split
            count[split] += crops[gemeente][model]
        if missing := [split for split in SPLITS if not count[split]]:
            logger.warning("%s: too few gemeenten for %s", model, ", ".join(missing))
    splits = {split: [] for split in SPLITS}
    for row in rows:
        splits[split_of[PurePosixPath(row["pdf"]).parent]].append(row)
    return splits


def main():
    """Split the crops in `crops` into a CSV per split in `output`, listing the crops as `crops.csv` does."""
    params = api.params_show()["split"]
    args = get_args()
    rows = list(csv.DictReader((Path(args.crops) / "crops.csv").open()))
    rng = random.Random(params["seed"])
    total = sum(params[split] for split in SPLITS)
    splits = assign(select(rows, params["blank"], rng), {split: params[split] / total for split in SPLITS}, rng)
    for split in ("validate", "test"):
        splits[split] = [row for row in splits[split] if (row["model"], row["content"]) not in RECOUNTED]

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for split, selected in splits.items():
        with (output / f"{split}.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, CSV_FIELDS)
            writer.writeheader()
            writer.writerows(selected)
        blank = sum(row["blank"] == "True" for row in selected)
        models = dict(Counter(row["model"] for row in selected))
        logger.info("%s: %d crops, %d blank, per model %s", split, len(selected), blank, models)


if __name__ == "__main__":
    main()
