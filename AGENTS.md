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

## Layout

```
backend/    Django 6 + DRF, Python 3.13+, managed with uv
frontend/   React 19 + TypeScript + Vite + Tailwind 4
.docker/    nginx reverse proxy config, postgres init
docker-compose.yml  full stack: db, backend, frontend, proxy, object storage
```

### Backend apps (`backend/`)

| App          | Contents                                                                                                       |
|--------------|----------------------------------------------------------------------------------------------------------------|
| `mainsite`   | Django project: settings, root urls, `BaseModel`, `EmlType` enum, management commands                          |
| `election`   | `ElectionConfig`, `Election`, `Contest`, `VoteCount`, `VoterTurnoutCount`, `TimelineEntry`, `ElectionDocument` |
| `region`     | `Region` — self-referencing tree (CSB → HSB/kieskring → gemeente → stembureau)                                 |
| `party`      | `Party`, `Candidate`                                                                                           |
| `eml_import` | EML parsing/import and the GitHub ingress importer                                                             |

Each app follows Django convention: `models.py`, `serializers.py`, `views.py`, `urls.py`,
`tests/`. API routes are mounted under `/api/` in `mainsite/urls.py`.

EML import lives in `eml_import/utils/`: `election_importer.py` orchestrates (parallel,
via `ProcessPoolExecutor`), and per-type importers subclass `EMLBaseImporter`
(110a definition, 230b candidate lists, 510b/510d counts). Uploaded and generated files
go to S3-compatible storage through Django's `default_storage`.

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
backend and **eslint** for the frontend. Run them before finishing a change.

See [README.md](README.md) and [backend/README.md](backend/README.md) for management
commands, object-storage variables, and the election visibility/deletion rules.

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
  real bucket.

Frontend: **vitest + Testing Library** (jsdom), tests in `frontend/tests/`, mirroring the
`src/` structure.

```bash
docker compose run --rm frontend npm run test    # or: npm run test
```

Stub `fetch` with `vi.stubGlobal`; wrap components in `QueryClientProvider` and
`MemoryRouter` as the existing tests do.

## CI

`.github/workflows/backend-ci.yml`: ruff check + format check, `pytest` against Postgres 16,
`makemigrations --check --dry-run`, and a Docker build.
`.github/workflows/frontend-ci.yml`: eslint, vitest, `npm run build` (`tsc -b` + vite), Docker build.

Both run on PRs. So: after a model change, commit the generated migration — a missing one
fails CI. PRs target `dev`.
