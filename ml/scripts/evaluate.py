import argparse
import csv
import json
import logging
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

import mlflow
import yaml
from dvc import api
from matplotlib.figure import Figure
from mlflow.exceptions import MlflowException
from PIL import Image

from pv_ocr.readers import get_reader

EXPERIMENT = "number-readers"
BATCH = 256  # crops opened and read at a time, between progress logs
BINS = 10  # confidence bins for the calibration error
EMPTY = "∅"  # the other side of a dropped or inserted digit in the confusion matrix
SYMBOLS = [*"0123456789", EMPTY]

logger = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("crops_csv", help="The test split, listing crops as crops.csv does")
    parser.add_argument("crops", help="The output of extract_crops")
    parser.add_argument("output")
    parser.add_argument("--reader", required=True, help="A key of `evaluate.readers` in params.yaml")
    return parser.parse_args()


def sample_pages(rows: list[dict], pages: int | None, rng: random.Random) -> list[dict]:
    """The crops of `pages` pages at random, spread evenly over the models; a model with fewer pages is taken whole."""
    if pages is None:
        return rows
    model_pages = defaultdict(set)
    for row in rows:
        model_pages[row["model"]].add((row["pdf"], row["page"]))
    chosen = set()
    # Smallest first, so what a small model cannot take goes to the bigger ones.
    models = sorted(model_pages, key=lambda m: (len(model_pages[m]), m))
    for i, name in enumerate(models):
        share = (pages - len(chosen)) // (len(models) - i)
        chosen.update(rng.sample(sorted(model_pages[name]), min(share, len(model_pages[name]))))
    return [row for row in rows if (row["pdf"], row["page"]) in chosen]


def align(label: str, prediction: str) -> list[tuple[str, str]]:
    """Label and predicted digits paired along a minimal edit (Levenshtein) alignment, EMPTY where one has none."""
    cost = [[i + j for j in range(len(prediction) + 1)] for i in range(len(label) + 1)]
    for i in range(1, len(label) + 1):
        for j in range(1, len(prediction) + 1):
            substitution = cost[i - 1][j - 1] + (label[i - 1] != prediction[j - 1])
            cost[i][j] = min(substitution, cost[i - 1][j] + 1, cost[i][j - 1] + 1)
    pairs = []
    i, j = len(label), len(prediction)
    while i or j:
        if i and j and cost[i][j] == cost[i - 1][j - 1] + (label[i - 1] != prediction[j - 1]):
            i, j = i - 1, j - 1
            pairs.append((label[i], prediction[j]))
        elif i and cost[i][j] == cost[i - 1][j] + 1:
            i -= 1
            pairs.append((label[i], EMPTY))
        else:
            j -= 1
            pairs.append((EMPTY, prediction[j]))
    return pairs


def confusion(results: list[dict]) -> list[list[int]]:
    """Digit counts of the written crops, label digits in the rows and predicted digits in the columns, both in SYMBOLS
    order. Blank crops are left out: their label 0 is not written, and `blank_exact_match` scores them."""
    counts = Counter(
        pair for result in results if not result["blank"] for pair in align(result["label"], result["prediction"])
    )
    return [[counts[label, predicted] for predicted in SYMBOLS] for label in SYMBOLS]


def calibration(results: list[dict]) -> list[dict]:
    """Per confidence bin, the count, mean confidence and accuracy of the crops in it."""
    bins = defaultdict(list)
    for result in results:
        bins[min(int(result["confidence"] * BINS), BINS - 1)].append(result)
    return [
        {
            "bin": f"{b / BINS:.1f}-{(b + 1) / BINS:.1f}",
            "count": len(bins[b]),
            "confidence": mean([result["confidence"] for result in bins[b]]),
            "accuracy": mean([result["correct"] for result in bins[b]]),
        }
        for b in range(BINS)
        if bins[b]
    ]


def mean(values: list) -> float | None:
    return sum(values) / len(values) if values else None


def share(matrix: list[list[int]], label: str, predicted: str) -> float | None:
    """The share of `label` digits read as `predicted`."""
    row = matrix[SYMBOLS.index(label)]
    return row[SYMBOLS.index(predicted)] / sum(row) if sum(row) else None


def metrics(results: list[dict]) -> dict:
    """The metrics of `results`, leaving out those with nothing to measure, such as blank crops of the corrigenda."""
    page_results = defaultdict(list)
    for result in results:
        page_results[result["pdf"], result["page"]].append(result["correct"])
    matrix = confusion(results)
    digits = sum(map(sum, matrix))
    values = {
        "crops": len(results),
        "pages": len(page_results),
        "exact_match": mean([result["correct"] for result in results]),
        "page_exact_match": mean([all(page) for page in page_results.values()]),
        "blank_exact_match": mean([result["correct"] for result in results if result["blank"]]),
        "written_exact_match": mean([result["correct"] for result in results if not result["blank"]]),
        "ece": sum(b["count"] * abs(b["accuracy"] - b["confidence"]) for b in calibration(results)) / len(results),
        "confusion_1_7": share(matrix, "1", "7"),
        "confusion_7_1": share(matrix, "7", "1"),
        "digit_error_rate": 1 - sum(matrix[i][i] for i in range(len(SYMBOLS))) / digits if digits else None,
    }
    return {name: value for name, value in values.items() if value is not None}


def heatmap(matrix: list[list[int]], title: str) -> Figure:
    """The confusion matrix with each row as shares, so rare digits show as clearly as common ones."""
    shares = [[count / (sum(row) or 1) for count in row] for row in matrix]
    figure = Figure(figsize=(6, 5.5))
    axes = figure.subplots()
    image = axes.imshow(shares, cmap="Blues", vmin=0, vmax=1)
    axes.set(xticks=range(len(SYMBOLS)), yticks=range(len(SYMBOLS)), xlabel="Predicted", ylabel="Label", title=title)
    axes.set_xticklabels(SYMBOLS)
    axes.set_yticklabels(SYMBOLS)
    for i, row in enumerate(matrix):
        for j, count in enumerate(row):
            if count:
                axes.text(
                    j, i, count, ha="center", va="center", fontsize=7, color="white" if shares[i][j] > 0.5 else "black"
                )
    figure.colorbar(image)
    return figure


def read(rows: list[dict], crops: Path, reader) -> list[dict]:
    """The rows with what the reader read, as a number: leading zeros are dropped, and nothing read counts as 0, as a
    blank field means 0."""
    results = []
    for start in range(0, len(rows), BATCH):
        batch = rows[start : start + BATCH]
        images = []
        for row in batch:
            with Image.open(crops / row["path"]) as image:
                images.append(image.copy())
        for row, reading in zip(batch, reader.read(images)):
            prediction = reading.digits.lstrip("0") or "0"
            results.append(
                {
                    **row,
                    "blank": row["blank"] == "True",
                    "prediction": prediction,
                    "confidence": reading.confidence,
                    "correct": prediction == row["label"],
                }
            )
        logger.info("%d/%d crops read", len(results), len(rows))
    return results


def write_csv(path: Path, fields: list[str], rows: list[dict]):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    """Read the crops of a sample of the test split with a reader, and write and log to MLflow how well it did."""
    params = api.params_show()["evaluate"]
    args = get_args()
    config = dict(params["readers"][args.reader])
    if "MLFLOW_TRACKING_URI" not in os.environ:
        raise SystemExit("Set MLFLOW_TRACKING_URI; without it MLflow would log to a local directory")
    # Before the reading, which takes long, so an unreachable server fails fast.
    try:
        mlflow.set_experiment(EXPERIMENT)
    except MlflowException as error:
        raise SystemExit(f"MLflow at {mlflow.get_tracking_uri()} cannot be reached: {error}")

    rows = list(csv.DictReader(Path(args.crops_csv).open()))
    rows = sample_pages(rows, params["pages"], random.Random(params["random-seed"]))
    logger.info("%s: reading %d crops", args.reader, len(rows))
    results = read(rows, Path(args.crops), get_reader(config.pop("reader"), **config))

    groups = defaultdict(list)
    for result in results:
        groups[result["model"]].append(result)
    groups = {"all": results} | dict(sorted(groups.items()))
    group_metrics = {name: metrics(group_results) for name, group_results in groups.items()}
    names = {name for values in group_metrics.values() for name in values} - {"crops", "pages"}
    # Unweighted over the models, so that Na31-2-B1, most of the crops, does not dominate; a model with too few crops
    # to score reliably is left out.
    in_macro = [v for g, v in group_metrics.items() if g != "all" and v["crops"] >= params["macro-min-crops"]]
    logger.info("macro over %d of %d models", len(in_macro), len(group_metrics) - 1)
    group_metrics["macro"] = {
        "models": len(in_macro),
        **{name: mean([values[name] for values in in_macro if name in values]) for name in sorted(names)},
    }

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "metrics.json").write_text(json.dumps(group_metrics, indent=2))
    fields = ["crops", "pages", "models", *sorted(names)]
    write_csv(output / "per_group.csv", ["group", *fields], [{"group": g, **v} for g, v in group_metrics.items()])
    misreads = sorted((r for r in results if not r["correct"]), key=lambda r: r["confidence"], reverse=True)
    write_csv(output / "misreads.csv", ["path", "model", "field", "label", "prediction", "confidence"], misreads)
    write_csv(
        output / "calibration.csv",
        ["group", "bin", "count", "confidence", "accuracy"],
        [{"group": name, **b} for name, group_results in groups.items() for b in calibration(group_results)],
    )
    matrices = {name: confusion(group_results) for name, group_results in groups.items()}
    write_csv(
        output / "confusion.csv",
        ["group", "label", *SYMBOLS],
        [
            {"group": name, "label": label, **dict(zip(SYMBOLS, row))}
            for name, matrix in matrices.items()
            for label, row in zip(SYMBOLS, matrix)
        ],
    )

    lock = yaml.safe_load(Path("dvc.lock").read_text())
    split_md5 = next(out["md5"] for out in lock["stages"]["split"]["outs"] if out["path"] == "data/split")
    with mlflow.start_run(run_name=args.reader):
        # MLflow tags the git commit itself, as `mlflow.source.git.commit`.
        mlflow.set_tag("split_md5", split_md5)
        reader_config = params["readers"][args.reader]
        mlflow.log_params(
            {
                **reader_config,
                "pages": params["pages"],
                "random_seed": params["random-seed"],
                "macro_min_crops": params["macro-min-crops"],
                "crops": len(results),
            }
        )
        mlflow.log_metrics(
            {f"{n}/{g}": v for g, values in group_metrics.items() for n, v in values.items() if v is not None}
        )
        for name in ("metrics.json", "per_group.csv", "misreads.csv", "calibration.csv", "confusion.csv"):
            mlflow.log_artifact(str(output / name))
        for name, matrix in matrices.items():
            mlflow.log_figure(heatmap(matrix, f"{args.reader}: {name}"), f"confusion/{name}.png")
    logger.info("%s: %s", args.reader, group_metrics["macro"])


if __name__ == "__main__":
    main()
