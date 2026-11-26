# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["fiftyone>=1.22"]
# ///
"""Browse the crops with their labels in FiftyOne, to check them by hand and tag the wrong ones.

FiftyOne needs OpenCV 4, the project OpenCV 5, so this runs on the host in its own environment rather than in the ml
service: `uv run ml/scripts/browse_crops.py`."""

import argparse
import csv
import random
import sys
from pathlib import Path

import fiftyone as fo
from fiftyone import ViewField as F

NAME = "crops"
SPLITS = ("train", "validate", "test")


def flag(value: str) -> bool | None:
    return {"True": True, "False": False}.get(value)


def load(crops: Path, sample: int | None) -> fo.Dataset:
    rows = [row for row in csv.DictReader((crops / "crops.csv").open()) if row["saved"] == "True"]
    if sample and sample < len(rows):
        rows = random.Random(0).sample(rows, sample)
    dataset = fo.Dataset(NAME, overwrite=True, persistent=True)
    dataset.add_samples(
        fo.Sample(
            filepath=str((crops / row["path"]).resolve()),
            label=fo.Classification(label=row["label"]),
            model=row["model"],
            pdf=row["pdf"],
            page=int(row["page"]),
            content=row["content"],
            field=row["field"],
            blank=flag(row["blank"]),
            changed=flag(row["changed"]),
        )
        for row in rows
    )
    return dataset


def mark_splits(dataset: fo.Dataset, crops: Path, splits: Path):
    """Give each crop the split it is in, empty for the crops `split` left out, and save a view of each split."""
    found = {}
    for name in SPLITS:
        if (path := splits / f"{name}.csv").exists():
            found |= {str((crops / row["path"]).resolve()): name for row in csv.DictReader(path.open())}
    if not found:
        print(f"No splits in {splits}; the split field and views stay as they were")
        return
    if not dataset.has_sample_field("split"):
        dataset.add_sample_field("split", fo.StringField)
    values = [found.get(path) for path in dataset.values("filepath")]
    if dataset.values("split") != values:
        dataset.set_values("split", values)
    for name in SPLITS:
        dataset.save_view(name, dataset.match(F("split") == name), overwrite=True)


def selects(args) -> bool:
    return bool(args.split or args.model or args.content or args.written or args.take is not None)


def saved_view(dataset: fo.Dataset, args) -> fo.DatasetView:
    """The view saved as `args.view`, saved anew when crops are selected for it: a fixed random set to check by hand."""
    if not selects(args):
        if args.view not in dataset.list_saved_views():
            saved = ", ".join(dataset.list_saved_views()) or "none"
            sys.exit(f"No view {args.view!r}, as --reload and --sample drop the views you saved; saved: {saved}")
        return dataset.load_saved_view(args.view)
    view = dataset.view()
    if args.split:
        view = view.match(F("split") == args.split)
    if args.model:
        view = view.match(F("model") == args.model)
    if args.content:
        view = view.match(F("content") == args.content)
    if args.written:
        view = view.match(F("blank") == False)  # noqa: E712
    if args.take is not None:
        # Picked by path rather than with `take`, whose order changes when the dataset is loaded again.
        paths = sorted(view.values("filepath"))
        view = view.select_by("filepath", random.Random(0).sample(paths, min(args.take, len(paths))))
    dataset.save_view(args.view, view, overwrite=True)
    return view


def export_tags(crops: fo.Dataset | fo.DatasetView, output: Path):
    """Write the crops given a tag in the app, with their tags."""
    tagged = crops.match_tags(crops.distinct("tags"))
    with output.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["path", "label", "tags"])
        for sample in tagged:
            writer.writerow([sample.filepath, sample.label.label, " ".join(sample.tags)])
    print(f"{len(tagged)} tagged crops written to {output}")


def get_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("crops", type=Path, nargs="?", default=Path("ml/data/crops"), help="extract_crops output")
    parser.add_argument("--splits", type=Path, default=Path("ml/data/split"), help="split output")
    parser.add_argument("--sample", type=int, help="Load this many crops at random rather than all of them")
    parser.add_argument("--reload", action="store_true", help="Load crops.csv again, which drops the tags given")
    parser.add_argument("--export-tags", type=Path, help="Write the tagged crops to this CSV instead of browsing")
    parser.add_argument("--all", action="store_true", help="Open all crops rather than the train split")
    parser.add_argument("--view", help="Open this saved view, saved anew with the crops the options below select")
    parser.add_argument("--split", choices=SPLITS, help="Only the crops of this split")
    parser.add_argument("--model", help="Only the crops of this model, e.g. N10-2")
    parser.add_argument("--content", help="Only the crops of this page content, e.g. votes-cast")
    parser.add_argument("--written", action="store_true", help="Only the crops with writing")
    parser.add_argument("--take", type=int, help="This many of the crops at random, the same ones each time")
    parser.add_argument("--port", type=int, default=5151)
    parser.add_argument("--browser", action="store_true", help="Also open the app in a browser")
    args = parser.parse_args()
    if selects(args) and not args.view:
        parser.error("--split, --model, --content, --written and --take select the crops of a --view")
    if selects(args) and args.view in SPLITS:
        parser.error(f"--view {args.view} is the view of that split; save a selection under another name")
    return args


def main():
    args = get_args()
    # The dataset is kept between runs, with the tags given in the app.
    if args.reload or args.sample or not fo.dataset_exists(NAME):
        dataset = load(args.crops, args.sample)
    else:
        dataset = fo.load_dataset(NAME)
    # Every run, so the splits stay in step with a new split run without dropping the tags.
    mark_splits(dataset, args.crops, args.splits)
    if args.view:
        crops = saved_view(dataset, args)
    elif "train" in dataset.list_saved_views() and not (args.all or args.export_tags):
        # The crops left out of every split are no use for training, such as the blank crops past `split.blank`.
        crops = dataset.load_saved_view("train")
    else:
        crops = dataset
    if args.view:
        # The share of crops tagged wrong is the error rate of the view.
        tags = ", ".join(f"{tag} {count}" for tag, count in sorted(crops.count_sample_tags().items()))
        print(f"{args.view}: {len(crops)} crops; tagged: {tags or 'none'}")
    if args.export_tags:
        export_tags(crops, args.export_tags)
        return
    session = fo.launch_app(crops, port=args.port, remote=not args.browser)
    session.wait()


if __name__ == "__main__":
    main()
