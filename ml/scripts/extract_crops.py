import argparse
import json
import logging
from pathlib import Path

from dvc import api
from mainsite.utils.utils import parallel_map

logger = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    parser.add_argument("tocs", help="The JSON-files the toc stage wrote")
    return parser.parse_args()


def main():
    """Run the written numbers crop extraction"""
    params = api.params_show()
    args = get_args()
    tocs = json.loads(Path(args.tocs).read_text())

    with parallel_map(params["jobs"]) as run:
        pass


if __name__ == "__main__":
    main()
