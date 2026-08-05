"""In-memory stand-ins for the slice of the PyGithub API that GithubEmlImporter uses.

Hand-written rather than mocks so the contract with PyGithub is written down in one
place, and so the importer asking for something that does not exist fails loudly.
"""


class FakeFile:
    """Stands in for github.File.File."""

    def __init__(self, filename: str, status: str = "added") -> None:
        self.filename = filename
        self.status = status


class FakeCommit:
    """Stands in for github.Commit.Commit."""

    def __init__(self, sha: str, files: list[FakeFile] | None = None) -> None:
        self.sha = sha
        self.files = files or []


class FakeComparison:
    """Stands in for github.Comparison.Comparison."""

    def __init__(self, commits: list[FakeCommit], files: list[FakeFile]) -> None:
        self.commits = commits
        self.files = files


class FakeContentFile:
    """Stands in for github.ContentFile.ContentFile."""

    def __init__(self, decoded_content: bytes) -> None:
        self.decoded_content = decoded_content


class FakePaginatedList(list):
    """Stands in for github.PaginatedList.PaginatedList.

    PyGithub exposes ``reversed`` as a property, not a method.
    """

    @property
    def reversed(self) -> list:
        return list(reversed(self))


class FakeRepo:
    """Stands in for github.Repository.Repository.

    Holds the commits of every branch, since the importer walks more than one branch.
    Every call is appended to ``calls`` so tests can assert which requests were made,
    which is how the batching behaviour is pinned down.
    """

    def __init__(self, branches: dict[str, list[FakeCommit]], contents: dict[str, bytes] | None = None) -> None:
        self.branches = branches  # branch name -> commits, oldest first
        self.contents = contents or {}
        self.calls: list[tuple] = []

    def get_commits(self, sha: str) -> FakePaginatedList:
        self.calls.append(("get_commits", sha))
        # The real API returns the newest commit first; the importer flips it with .reversed
        return FakePaginatedList(reversed(self.branches[sha]))

    def get_commit(self, sha: str) -> FakeCommit:
        self.calls.append(("get_commit", sha))
        return next(commit for commit in self._branch_of(sha) if commit.sha == sha)

    def compare(self, base: str, head: str) -> FakeComparison:
        self.calls.append(("compare", base, head))
        commits = self._range(base, head)
        return FakeComparison(commits, [file for commit in commits for file in commit.files])

    def get_contents(self, path: str, ref: str) -> FakeContentFile:
        self.calls.append(("get_contents", path, ref))
        return FakeContentFile(self.contents[path])

    def calls_named(self, name: str) -> list[tuple]:
        return [call for call in self.calls if call[0] == name]

    def _branch_of(self, sha: str) -> list[FakeCommit]:
        """The commits of the branch containing the given sha."""
        return next(commits for commits in self.branches.values() if sha in [commit.sha for commit in commits])

    def _range(self, base: str, head: str) -> list[FakeCommit]:
        """The commits after base up to and including head.

        Mirrors the real API in two ways the importer depends on: the base commit itself
        is excluded, and head may be a branch name rather than a sha.
        """
        commits = self.branches[head] if head in self.branches else self._branch_of(head)
        shas = [commit.sha for commit in commits]
        end = shas.index(head) + 1 if head in shas else len(shas)
        return commits[shas.index(base) + 1 : end]


class FakeGithub:
    """Stands in for github.Github."""

    def __init__(self, repo: FakeRepo) -> None:
        self._repo = repo
        self.requested_repos: list[str] = []

    def get_repo(self, full_name: str) -> FakeRepo:
        self.requested_repos.append(full_name)
        return self._repo
