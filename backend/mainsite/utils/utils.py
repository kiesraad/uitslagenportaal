import multiprocessing
import os
import re
import unicodedata
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager

import django


def name_to_slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", "", ascii_name.lower()).strip().replace(" ", "-")


@contextmanager
def parallel_map(jobs: int) -> Iterator[Callable]:
    """A map that runs in `jobs` worker processes, or the built-in map for one job. Results come back in input order,
    so a slow item holds back the ones after it."""
    if jobs <= 1:
        yield map
        return
    # OpenMP threads, such as Tesseract's, compete with the other workers; one each is about 1.6x faster with 4 jobs.
    os.environ["OMP_THREAD_LIMIT"] = "1"
    # Spawned workers don't inherit Django's setup, which unpickling a task needs when it imports models.
    with ProcessPoolExecutor(jobs, mp_context=multiprocessing.get_context("spawn"), initializer=django.setup) as pool:
        yield pool.map
