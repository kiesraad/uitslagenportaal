"""
Build a local replica of the EML ingress repository from a `.data` fixture folder.

The ingress repository that `GithubEmlImporter` reads is written by an external party, so it
cannot be replayed or pointed at test data. This command rebuilds it offline: one repository
holding every election, each on a pair of branches off `main` named `auto-<election id>-uit` and
`auto-<election id>-tel` -- the exchange documents (`dob2pk/`) on the first and the counting
results (`dob1/`) on the second, each organization's upload its own small commit, and the EML
documents wrapped in the same nested zips.

Run it once per election against the same `--dest`. It refuses to touch an election whose
branches are already there, so rebuilding one means deleting its two branches first.

The folder layout is a simplified `<root>/<level>/<organisation>/` and does not copy the real
repository folder for folder. `GithubEmlImporter` ignores paths entirely -- it classifies on the
root element `Id` of every XML it finds -- so what has to be right is the branch a document lands
on, the order of the commits, and the zip nesting. Keeping the layout uniform is what lets this
handle TK/EK/EP, whose real repository spreads kieskringen over `hoofdstembureau`, `nbsb` and
`openbaar_lichaam` folders.
"""

import io
import os
import re
import subprocess
import unicodedata
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path
from xml.etree import ElementTree as ET

from django.core.management.base import BaseCommand, CommandError

from mainsite.utils.eml_type import EmlType

EML_NS = "urn:oasis:names:tc:evs:schema:eml"
KR_NS = "http://www.kiesraad.nl/extensions"

_AUTHORITY_TAG = f"{{{EML_NS}}}AuthorityIdentifier"
_ELECTION_IDENTIFIER_TAG = f"{{{EML_NS}}}ElectionIdentifier"
_ELECTION_DOMAIN_TAG = f"{{{KR_NS}}}ElectionDomain"

EXCHANGE_ROOT = "dob2pk"
COUNTING_ROOT = "dob1"

# One repository holds every election, each on its own pair of branches off `main`.
MAIN_BRANCH = "main"
BRANCH_PREFIX = "auto-"

# The counting levels, in the order they report: a gemeente counts, its hoofdstembureau totals the
# kieskring, and the central stembureau publishes last. Commits are replayed in this order.
GSB, HSB, CSB = "gemeente", "hoofdstembureau", "centraalstembureau"
LEVEL_ORDER = (GSB, HSB, CSB)

# The central stembureau of a national election (TK, EP). Its documents name no election domain,
# and its Verkiezingsdefinitie names no managing authority either, so it has to be named here.
NATIONAL_CSB = "De Kiesraad"

# Which branch each EML document belongs on, and which level uploaded it.
EXCHANGE_LEVELS: dict[str, str] = {
    EmlType.EML_110a: CSB,  # Verkiezingsdefinitie
    EmlType.EML_110b: GSB,  # Stembureaus
    EmlType.EML_230b: CSB,  # Kandidatenlijsten
}
COUNTING_LEVELS: dict[str, str] = {
    EmlType.EML_510b: GSB,  # Telling
    EmlType.EML_510c: HSB,  # Totaaltelling kieskring
    EmlType.EML_510d: CSB,  # Totaaltelling
    EmlType.EML_520: CSB,  # Resultaat
}

COMMIT_MODES = ("per-org", "per-file", "single")

# Copied verbatim from the ingress repository: the uploads carry scans and printed models
# next to the EML files, and those are kept out of git.
GITIGNORE = """\
# Additional rules from environment variable
*.docx
*.doc
*.jpg
*.jpeg
*.pdf
*.png
*.[dD][oO][cC][xX]
*.[dD][oO][cC]
*.[jJ][pP][gG]
*.[jJ][pP][eE][gG]
*.[pP][dD][fF]
*.[pP][nN][gG]
"""

README = """\
# verkiezingen-emls

Replica of the `.eml` ingress repository, generated offline from `.data` fixture folders by
`manage.py build_ingress_repo`.

Every election gets its own pair of branches off this one, named after its identifier:

- `{prefix}<election id>-uit` holds the exchange documents under
  `{exchange_root}/<level>/<organisation>/`, each zipped under its own name.
- `{prefix}<election id>-tel` holds the counting results under
  `{counting_root}/<level>/<organisation>/`, each in an upload archive holding the zipped
  EML document.
"""


def slugify(name: str, separator: str) -> str:
    """
    Fold `name` to ASCII and join its alphanumeric runs with `separator`.

    `mainsite.utils.name_to_slug` deletes punctuation instead of replacing it, which would turn
    `Alphen-Chaam` into `alphenchaam`; the repository writes `alphen_chaam` / `alphen-chaam`.
    """
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", separator, ascii_name.lower()).strip(separator)


def folder_slug(name: str) -> str:
    """Slug as used in folder names: `Alphen-Chaam` -> `alphen_chaam`."""
    return slugify(name, "_")


def file_slug(name: str) -> str:
    """Slug as used inside upload filenames: `Alphen-Chaam` -> `alphen-chaam`."""
    return slugify(name, "-")


def eml_stem(path: Path) -> str:
    """`Telling_GR2026_Vlieland.eml.xml` -> `Telling_GR2026_Vlieland`."""
    return path.name.removesuffix(".xml").removesuffix(".eml")


def make_zip(entries: list[tuple[str, bytes]], timestamp: datetime) -> bytes:
    """Zip `entries` in memory, stamping every member so repeated runs produce identical bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=timestamp.timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return buffer.getvalue()


@dataclass(frozen=True)
class EmlMeta:
    """The handful of fields needed to place an EML file in the repository tree."""

    path: Path
    doc_type: str  # root element Id, e.g. "510b"
    election_id: str  # ElectionIdentifier/@Id, e.g. "GR2026_Eemsdelta"
    domain: str | None  # kr:ElectionDomain, the name of the body holding the election
    authority: str | None  # ManagingAuthority, the gemeente for a Telling


def read_eml_meta(path: Path) -> EmlMeta | None:
    """
    Read the document type and placement fields from an EML file in a single streaming pass.

    The document type is the root element's `Id`, the same attribute
    `ElectionImporter._document_id` classifies on, so this command groups files exactly the way
    the importer will later interpret them.
    """
    doc_type: str | None = None
    election_id: str | None = None
    domain: str | None = None
    authority: str | None = None
    root_seen = False

    with path.open("rb") as handle:
        for event, element in ET.iterparse(handle, events=("start", "end")):
            if not root_seen:
                root_seen = True
                doc_type = element.get("Id")
                continue

            if event != "end":
                continue

            if element.tag == _AUTHORITY_TAG:
                # The first one is the ManagingAuthority; later ones belong to nested bodies.
                authority = authority or (element.text or "").strip() or None
            elif element.tag == _ELECTION_DOMAIN_TAG:
                domain = (element.text or "").strip() or None
            elif element.tag == _ELECTION_IDENTIFIER_TAG:
                election_id = element.get("Id")
                # Every field above lives at or before the election identifier.
                break

    if not doc_type or not election_id:
        return None

    return EmlMeta(path, doc_type, election_id, domain, authority)


@dataclass(frozen=True)
class Upload:
    """One EML document, as the organization that produced it would have uploaded it."""

    level: str
    organisation: str
    election_id: str
    path: Path

    @property
    def subject(self) -> str:
        """
        The election and body the document is about: everything after the document type in its
        filename, so `Kandidatenlijsten_GR2026_Bunnik` and `Verkiezingsdefinitie_GR2026_Bunnik`
        share `GR2026_Bunnik`, while the Tweede Kamer's per-kieskring candidate lists do not.
        """
        stem = eml_stem(self.path)
        _, _, subject = stem.partition("_")
        return subject or stem

    @property
    def group(self) -> tuple[int, str, str]:
        """Uploads sharing a group were pushed together and become one commit."""
        return LEVEL_ORDER.index(self.level), self.organisation, self.subject


@dataclass
class CommitUnit:
    """A single commit: the files it introduces and the time it claims to have been pushed."""

    timestamp: datetime
    files: list[tuple[str, bytes]] = field(default_factory=list)


class Command(BaseCommand):
    help = "Build a local git replica of the EML ingress repository from a .data fixture folder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            required=True,
            help="Path to a .data election folder containing EML XML files, e.g. .data/GR26.",
        )
        parser.add_argument(
            "--dest",
            required=True,
            help="The replica repository; created when missing, added to when it already exists.",
        )
        parser.add_argument(
            "--election-id",
            required=True,
            help=f"Election identifier, e.g. GR2026; names the {BRANCH_PREFIX}<id>-uit and -tel branches.",
        )
        parser.add_argument(
            "--commit-mode",
            choices=COMMIT_MODES,
            default="per-org",
            help="How to spread files over commits (default: per-org).",
        )
        parser.add_argument(
            "--author",
            default="Auto Import <auto-import@localhost>",
            help='Commit author, as "Name <email>" (default: Auto Import <auto-import@localhost>).',
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).resolve()
        if not source.is_dir():
            raise CommandError(f"Source folder does not exist: {source}")

        election_id = options["election_id"]
        exchange_branch, counting_branch = self._branch_names(election_id)
        self._author = self._split_author(options["author"])

        # Create branches
        dest = Path(options["dest"]).resolve()
        self._open_repo(dest)
        for branch in (exchange_branch, counting_branch):
            if self._branch_exists(dest, branch):
                raise CommandError(f"Branch {branch} already exists in {dest}; delete it to rebuild {election_id}")

        # Get the files to upload in commits
        exchange_uploads, counting_uploads = self._collect_uploads(source)
        if not exchange_uploads and not counting_uploads:
            raise CommandError(f"No usable EML documents found in {source}")

        # Get the commits
        year = self._election_year(election_id)
        mode = options["commit_mode"]
        exchange_commits = self._build_commits(
            exchange_uploads, self._exchange_file, base=datetime(year, 2, 1, 9, 0), mode=mode
        )
        counting_commits = self._build_commits(
            counting_uploads, self._counting_file, base=datetime(year, 3, 19, 9, 0), mode=mode
        )

        self._write_repo(
            dest=dest,
            election_id=election_id,
            exchange_branch=exchange_branch,
            counting_branch=counting_branch,
            exchange_commits=exchange_commits,
            counting_commits=counting_commits,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Built {dest} - {exchange_branch}: {len(exchange_commits)} commits, "
                f"{counting_branch}: {len(counting_commits)} commits."
            )
        )

    # Argument handling ------------------------------------------------------------------

    @staticmethod
    def _branch_names(election_id: str) -> tuple[str, str]:
        prefix = f"{BRANCH_PREFIX}{election_id.lower()}"
        return f"{prefix}-uit", f"{prefix}-tel"

    def _open_repo(self, dest: Path) -> None:
        """Create the repository, or take the one that is already there."""
        if (dest / ".git").is_dir():
            self._adopt_repo(dest)
            return

        if dest.exists() and any(dest.iterdir()):
            raise CommandError(f"Destination is not empty and not a git repository: {dest}")

        dest.mkdir(parents=True, exist_ok=True)
        self._git(dest, "init", "--quiet")
        self._point_head_at_main(dest)

    def _adopt_repo(self, dest: Path) -> None:
        """
        Put an existing repository on `main` before anything is written to it.

        A repository created under another `init.defaultBranch` has its unborn HEAD on `master`,
        and `_ensure_main` would commit the README there: `_write_repo` would then fail on a
        `main` that was never created, leaving that commit behind.
        """
        if self._branch_exists(dest, MAIN_BRANCH):
            return

        if self._git(dest, "rev-parse", "--verify", "--quiet", "HEAD", check=False) is not None:
            raise CommandError(
                f"Repository {dest} has commits but no {MAIN_BRANCH} branch; "
                f"the election branches are built off {MAIN_BRANCH}."
            )

        # Nothing has been committed yet, so HEAD is free to move.
        self._point_head_at_main(dest)

    def _point_head_at_main(self, dest: Path) -> None:
        self._git(dest, "symbolic-ref", "HEAD", f"refs/heads/{MAIN_BRANCH}")

    def _branch_exists(self, dest: Path, branch: str) -> bool:
        return self._git(dest, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False) is not None

    @staticmethod
    def _split_author(author: str) -> tuple[str, str]:
        name, separator, email = author.partition("<")
        if not separator or not email.endswith(">"):
            raise CommandError(f'Could not parse --author {author!r}; expected "Name <email>"')
        return name.strip(), email[:-1].strip()

    @staticmethod
    def _election_year(election_id: str) -> int:
        for start in range(len(election_id) - 3):
            chunk = election_id[start : start + 4]
            if chunk.isdigit():
                return int(chunk)
        raise CommandError(f"Could not read a year from election id {election_id!r}")

    # Collecting -------------------------------------------------------------------------

    def _collect_uploads(self, source: Path) -> tuple[list[Upload], list[Upload]]:
        exchange: list[Upload] = []
        counting: list[Upload] = []
        skipped: list[Path] = []

        for path in sorted(source.rglob("*.xml")):
            meta = read_eml_meta(path)
            if meta is None:
                skipped.append(path)
            elif level := EXCHANGE_LEVELS.get(meta.doc_type):
                exchange.append(self._upload(meta, level))
            elif level := COUNTING_LEVELS.get(meta.doc_type):
                counting.append(self._upload(meta, level))
            else:
                skipped.append(path)

        exchange.sort(key=lambda upload: (upload.group, upload.path.name))
        counting.sort(key=lambda upload: (upload.group, upload.path.name))
        self.stdout.write(
            f"Collected {len(exchange)} exchange and {len(counting)} counting documents ({len(skipped)} files skipped)."
        )
        for path in skipped:
            self.stdout.write(f"  skipped {path}")
        return exchange, counting

    def _upload(self, meta: EmlMeta, level: str) -> Upload:
        return Upload(level, self._organisation(meta, level), meta.election_id, meta.path)

    @staticmethod
    def _organisation(meta: EmlMeta, level: str) -> str:
        """
        Name the organization that uploaded the document.

        A central stembureau names itself inconsistently across document types ("Gelderland" in
        one, "Centraal stembureau Gelderland" in the next), so use the election domain there and
        keep every document of one central stembureau in a single folder. Gemeenten and
        hoofdstembureaus identify themselves in the managing authority. Use NATIONAL_CSB if not set.
        """
        if level == CSB:
            return meta.domain or meta.authority or NATIONAL_CSB
        return meta.authority or meta.domain or meta.election_id

    # Building the trees -----------------------------------------------------------------

    def _wrap(self, path: Path, timestamp: datetime) -> bytes:
        """Zip a single EML document under its own name, as the uploads do."""
        return make_zip([(path.name, path.read_bytes())], timestamp)

    def _exchange_file(self, upload: Upload, timestamp: datetime) -> tuple[str, bytes]:
        """Exchange documents are published as one zip named after the document itself."""
        directory = f"{EXCHANGE_ROOT}/{upload.level}/{folder_slug(upload.organisation)}"
        return f"{directory}/{eml_stem(upload.path)}.zip", self._wrap(upload.path, timestamp)

    def _counting_file(self, upload: Upload, timestamp: datetime) -> tuple[str, bytes]:
        """Counting documents arrive as an upload archive holding the zipped EML document."""
        directory = f"{COUNTING_ROOT}/{upload.level}/{folder_slug(upload.organisation)}"
        name = (
            f"definitieve-documenten_{upload.election_id.lower()}"
            f"_{file_slug(upload.organisation)}-{timestamp:%Y%m%d-%H%M%S}.zip"
        )
        entries = [(f"{eml_stem(upload.path)}.zip", self._wrap(upload.path, timestamp))]
        return f"{directory}/{name}", make_zip(entries, timestamp)

    def _build_commits(
        self,
        uploads: list[Upload],
        file_for: Callable[[Upload, datetime], tuple[str, bytes]],
        *,
        base: datetime,
        mode: str,
    ) -> list[CommitUnit]:
        commits: list[CommitUnit] = []
        for offset, (_, group) in enumerate(groupby(uploads, key=lambda upload: upload.group)):
            timestamp = base + timedelta(minutes=offset)
            # Stagger by a second so an organisation uploading several documents at once cannot
            # produce the same archive name twice.
            files = [file_for(upload, timestamp + timedelta(seconds=index)) for index, upload in enumerate(group)]
            commits.append(CommitUnit(timestamp, files))

        return self._apply_commit_mode(commits, mode)

    @staticmethod
    def _apply_commit_mode(commits: list[CommitUnit], mode: str) -> list[CommitUnit]:
        if mode == "per-org":
            return commits
        if mode == "per-file":
            return [CommitUnit(commit.timestamp, [file]) for commit in commits for file in commit.files]
        # single
        files = [file for commit in commits for file in commit.files]
        return [CommitUnit(commits[-1].timestamp, files)] if files else []

    # Writing the repository -------------------------------------------------------------

    def _write_repo(
        self,
        *,
        dest: Path,
        election_id: str,
        exchange_branch: str,
        counting_branch: str,
        exchange_commits: list[CommitUnit],
        counting_commits: list[CommitUnit],
    ) -> None:
        root_timestamp = min(
            (commit.timestamp for commit in exchange_commits + counting_commits),
            default=datetime(self._election_year(election_id), 1, 1, 9, 0),
        ) - timedelta(days=1)
        self._ensure_main(dest, root_timestamp)

        branches = ((exchange_branch, exchange_commits), (counting_branch, counting_commits))
        for index, (branch, commits) in enumerate(branches):
            self._git(dest, "checkout", "--quiet", MAIN_BRANCH)
            self._git(dest, "checkout", "--quiet", "-b", branch)
            # Stagger the scaffolding commits: identical content, message and date would otherwise
            # hash to one commit shared by both branches, moving their merge base off `main`.
            scaffolding_timestamp = root_timestamp + timedelta(minutes=index)
            scaffolding = CommitUnit(scaffolding_timestamp, [(".gitignore", GITIGNORE.encode()), (".keep", b"")])
            self._commit(dest, scaffolding, message=f"Auto commit @ {scaffolding_timestamp:%H:%M}")
            for commit in commits:
                self._commit(dest, commit, message=f"Auto commit @ {commit.timestamp:%H:%M}")
            self.stdout.write(f"  {branch}: {len(commits) + 1} commits")

        # Leave the replica on the counting branch, matching the ingress repository's default.
        self._git(dest, "checkout", "--quiet", counting_branch)

    def _ensure_main(self, dest: Path, timestamp: datetime) -> None:
        """
        Give the repository its `main` branch and shared README, once.

        The README describes the branch layout rather than any one election, so a repository that
        already holds other elections keeps the `main` it has.
        """
        if self._branch_exists(dest, MAIN_BRANCH):
            self.stdout.write(f"Adding to the existing repository at {dest}")
            return

        readme = README.format(
            prefix=BRANCH_PREFIX,
            exchange_root=EXCHANGE_ROOT,
            counting_root=COUNTING_ROOT,
            levels=", ".join(LEVEL_ORDER),
        )
        self._commit(dest, CommitUnit(timestamp, [("README.md", readme.encode())]), message="Initial commit")

    def _commit(self, dest: Path, unit: CommitUnit, *, message: str) -> None:
        for relative_path, content in unit.files:
            target = dest / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_bytes(content)
            except OSError as error:
                # The generated paths are long by nature; on Windows they run into MAX_PATH
                # unless long paths are enabled or --dest sits near the drive root.
                raise CommandError(f"Could not write {target} ({error}). Try a shorter --dest.") from error

        self._git(dest, "add", "--all")
        name, email = self._author
        stamp = unit.timestamp.isoformat()
        # Identify the author through the environment rather than `git config`, so building into
        # an existing repository leaves its configuration untouched.
        self._git(
            dest,
            "commit",
            "--quiet",
            "--message",
            message,
            env={
                "GIT_AUTHOR_NAME": name,
                "GIT_AUTHOR_EMAIL": email,
                "GIT_AUTHOR_DATE": stamp,
                "GIT_COMMITTER_NAME": name,
                "GIT_COMMITTER_EMAIL": email,
                "GIT_COMMITTER_DATE": stamp,
            },
        )

    @staticmethod
    def _git(cwd: Path, *args: str, env: dict[str, str] | None = None, check: bool = True) -> str | None:
        """Run git in `cwd`, returning its output, or None when `check` is off and it failed."""
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env={**os.environ, **env} if env else None,
        )
        if result.returncode != 0:
            if not check:
                return None
            raise CommandError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
        return result.stdout.strip()
