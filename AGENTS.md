# AGENTS.md

Instructions for AI agents working in this repository.

## What this is

Uitslagenportaal: a portal that publishes Dutch election results. The backend imports
EML files (the official XML count files) into Postgres and exposes them through a REST
API; the React frontend renders them.

Docs and comments are a mix of Dutch and English. Domain terms stay Dutch
(`kieskring`, `stembureau`, `gemeente`, CSB/HSB/GSB); code identifiers are English.

Write English in British English with Oxford spelling, in prose, comments, docstrings
and identifiers alike.

**Read [docs/ai-policy.md](docs/ai-policy.md) before generating code.** The project bans
"vibe-coding": a developer must fully understand every committed line. Prefer small,
reviewable, explainable changes over large generated blocks, and stay inside existing
patterns.

## Version control

Never run `git commit`, `git push`, or anything else that rewrites history or publishes
work — not even when a change looks finished. Leave everything in the working tree and say
what changed; the developer reviews it and commits it themselves, because they carry
responsibility for every line that lands. Ask first if you think a commit is needed.

## Comments

Keep comments short and to the point, and write them from the perspective of the
application as a whole rather than the change that introduced them. Never restate what the
code obviously does; a comment earns its place only by adding what cannot be derived from
the code itself — an EML quirk, a domain rule, a non-obvious trade-off, a reason for doing
it the awkward way. Do not narrate the session that produced it: no "changed to…", "used
to be…", "as requested", or references to a review remark or an earlier implementation. If
a comment would read as stale a month from now, leave it out.

## Layout

```
backend/    Django 6 + DRF, Python 3.13+, managed with uv
frontend/   React 19 + TypeScript + Vite + Tailwind 4
.docker/    nginx reverse proxy config, postgres init
docker-compose.yml  full stack: db, redis, backend, celery, frontend, proxy, object storage
```

### Backend apps (`backend/`)

| App          | Contents                                                                                                       |
|--------------|----------------------------------------------------------------------------------------------------------------|
| `mainsite`   | Django project: settings, root urls, `BaseModel`, `EmlType` enum, management commands                          |
| `election`   | `ElectionConfig`, `Election`, `Contest`, `VoteCount`, `VoterTurnoutCount`, `TimelineEntry`, `ElectionDocument` |
| `region`     | `Region` — self-referencing tree (CSB → HSB/kieskring → gemeente → stembureau)                                 |
| `party`      | `Party`, `Candidate`                                                                                           |
| `eml_import` | EML parsing/import, the GitHub ingress importer, `ImportedCommit`, and the Celery tasks         |

Each app follows Django convention: `models.py`, `serializers.py`, `views.py`, `urls.py`,
`tests/`. API routes are mounted under `/api/` in `mainsite/urls.py`.

EML import lives in `eml_import/utils/`: `election_importer.py` orchestrates (parallel,
via `ProcessPoolExecutor`), and per-type importers subclass `EMLBaseImporter`
(110a definition, 230b candidate lists, 510b/510d counts). Uploaded and generated files
go to S3-compatible storage through Django's `default_storage`.

### Background jobs

Celery (app in `mainsite/celery.py`, tasks in `<app>/tasks.py`) runs with Redis backend.
Celery Beat is used for periodic tasks, and tasks are scheduled in `tasks.py`. The `celery` compose service
runs worker and beat together (`celery -A mainsite worker --beat`) under `watchmedo`
for autoreload. Put new tasks in `<app>/tasks.py` — the app autodiscovers them.

### Frontend (`frontend/src`)

`api/` (fetch client, endpoints, generated-by-hand types) · `hooks/queries.ts`
(TanStack Query) · `pages/` (routed screens) · `components/` (shared + per-page folders) ·
`utils/`. Import with the `@/` alias for `src/`. Styling is Tailwind utility classes.

## Tooling

Everything runs in Docker Compose; `backend-scripts` is the one-off command service.

```bash
docker compose up -d --build                                   # full stack, http://localhost:8080
docker compose run --rm backend-scripts python manage.py migrate
docker compose run --rm backend-scripts python manage.py reset_and_import   # wipe + seed + import backend/.data/*.xml
docker compose run --rm backend-scripts ruff format
docker compose run --rm frontend npm run lint
```

Outside Docker: backend uses **uv** (`uv sync`, `uv add <pkg>`, `uv run <cmd>`) and needs a
`backend/.env` with `DB_*`; frontend uses **npm** (`npm install`, `npm run dev`).

Lint/format is **ruff** (line length 120, rules `E,F,I`, migrations excluded) for the
backend and **biome** (`npm run lint`, `npm run format`) for the frontend. Run them before
finishing a change.

See [README.md](README.md) and [backend/README.md](backend/README.md) for management
commands, object-storage variables, and the election visibility/deletion rules.

## Translations

See the Internationalisation section in [frontend/README.md](frontend/README.md) for the setup,
marking text for translations and translation rules.

Lingui publishes agent skills, context files and an MCP server for working with its API:
<https://lingui.dev/ai-tools>.

Process in short:

```bash
cd frontend
npm run i18n:extract-clean    # or: docker compose run --rm frontend npm run i18n:extract-clean
```

Extraction adds new entries to both catalogues, drops ones no longer used, and reports how
many English messages are still missing. Fill each empty `msgstr` in the `en` catalogue and
re-run extraction until it reports `Missing 0`.

## Testing

Backend: **pytest + pytest-django**, tests in `<app>/tests/test_*.py`.

```bash
docker compose run --rm backend-scripts pytest            # or: uv run pytest
docker compose run --rm backend-scripts pytest election/tests/test_views.py::test_name
```

- Mark anything touching the database with `@pytest.mark.django_db`.
- Build data with the `factory-boy` factories in `<app>/tests/factories.py` — extend those
  rather than hand-building model instances.
- The root `conftest.py` swaps in `InMemoryStorage` for every test, so tests never hit the
  real storage backend.
- Test Celery tasks by calling the task function directly and patching `.delay` on the
  ones it fans out to (see `eml_import/tests/test_tasks.py`); no worker or broker runs.
- Unit tests do not read the XML fixture files in `mainsite/tests/fixtures/eml/`. Build
  the EML input in code with the real `pyeml_bindings` dataclasses, as the importer tests
  do — they are about what the importer writes, not about parsing XML. The fixtures are
  for integration tests that run a whole import (`mainsite/tests/test_election_importer.py`,
  `test_eml_type_api.py`); use them there, or when explicitly asked to.

Frontend: **vitest + Testing Library** (jsdom), tests in `frontend/tests/`, mirroring the
`src/` structure.

```bash
docker compose run --rm frontend npm run test    # or: npm run test
```

Stub `fetch` with `vi.stubGlobal`; wrap components in `QueryClientProvider` and
`MemoryRouter` as the existing tests do.

## CI

`.github/workflows/backend-ci.yml`: ruff check + format check, `pytest` against Postgres 16,
and `makemigrations --check --dry-run`.
`.github/workflows/frontend-ci.yml`: `biome ci`, vitest, `npm run i18n:check` and
`npm run build` (`tsc -b` + vite).
`.github/workflows/playwright.yml`: the browser tests, against a throwaway stack.

All three run on PRs — the backend and frontend suites filtered by path, Playwright on every
PR — and the first two check that generated files are in step with the source, so regenerate
them as part of the change: `makemigrations` after a model change,
`npm run i18n:extract-clean` after a message change. A missing migration or a stale
catalogue fails CI. PRs target `dev`.

`.github/workflows/branch-ci-cd.yml` runs on pushes to `dev` and `main`. It calls all three
workflows above in full — path filters apply to a workflow's own triggers, not to a call —
and publishes the frontend and backend images to ghcr.io only once every one of them passes.
`publish-docker-image.yml` is the reusable workflow that builds and pushes one image.
