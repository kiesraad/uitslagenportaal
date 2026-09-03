**Let op: dit project bevindt zich momenteel in een opstartfase. Documentatie en code zullen onvolledig en soms incorrect zijn.**


# Uitslagenportaal


Het Uitslagenportaal is een webapplicatie die gebruikers in staat stelt meer inzicht in het
verkiezingsproces te krijgen. Allereerst ontsluit het portaal EMLs — digitale telbestanden —
tijdens en na een verkiezingsperiode op een overzichtelijke en leesbare manier. Daarnaast geeft
het portaal ook context over wat er in de verkiezingsperiode gebeurt en waar men in het verkiezingsproces
zit.

## Development setup (Docker)

Start the full stack (database, backend, frontend and reverse proxy) with Docker Compose:

```bash
docker compose up -d --build
```

The portal is then available at http://localhost:8080.

Install plugins for `ruff` and `biome` in your IDE to use the required formatting/linting.

De backend (`backend/`) is gemaakt met Django 6 + DRF in Python 3.13, managed met uv; the frontend
(`frontend/`) is React 19 + TypeScript + Vite + Tailwind 4. See [AGENTS.md](AGENTS.md) for the
repository layout and conventions, and [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute.

### Environment variables

No `.env` file is required for Docker development. Database and backend settings are configured in `docker-compose.yml` and passed to the containers automatically (`DB_HOST=db`, etc.).

### Election data (`.data`)

Put EML XML fixture files on your machine in:

```
backend/.data/
```

This can be recent data, or historical election EML XML data from [data.overheid.nl](https://data.overheid.nl).This folder is mounted into the backend container at `/app/.data`.

### Object storage

Uploaded and generated files are stored in an S3-compatible bucket. Locally that is
the `object-storage` service (RustFS); in production it is Scaleway Object Storage.

- API: http://localhost:9000
- Console: http://localhost:9001 (user `uitslagenportaal`, password `password`)
- Bucket: `uitslagenportaal`, created on `docker compose up` by a `pre_start` init
  container on the `backend` service, which also makes its objects publicly readable.
  To (re)create it by hand:
  `docker compose run --rm backend-scripts python manage.py ensure_bucket --public`

The backend reaches the bucket at `object-storage:9000` over the compose network,
but generates public URLs pointing at `localhost:9000`, since that is the host the
browser can reach. Both are configured through `S3_*` environment variables in
`docker-compose.yml`.

### First-time database setup

After the stack is running:

```bash
docker compose run --rm backend-scripts python manage.py migrate
docker compose run --rm backend-scripts python manage.py reset_and_import
```

`reset_and_import` wipes election data, seeds the election config, and imports all `*.xml` files from `backend/.data/`.

To import again without wiping (e.g. after adding files):

```bash
docker compose run --rm backend-scripts python manage.py import_election .data
```

### Importing from GitHub

On production, we import the XML files from a GitHub repo. We can test this import by generating our own
test-repo, based on the data in `.data`. Checkout the test-data repo next to this project and use 
the `build_ingress_repo` command to add branches with commits similar to the official repo (from backend folder): 
```bash
uv run manage.py build_ingress_repo --source .data/AB23 --dest ../../uitslagenportaal-test-emls/ --election-id AB2023
```
Then push the branches to the remote, and configure the repo in the `.env` file to start importing its data using
the Celery task `import_next_eml_commits`. 

### One-off commands

The `backend-scripts` service can run management commands while the stack keeps running:

```bash
docker compose run --rm backend-scripts python manage.py migrate
docker compose run --rm backend-scripts python manage.py seed
```

### Common commands

- Ruff format:
  ```bash
  docker compose run --rm backend-scripts ruff format
  ```

- Biome lint:
  ```bash
  docker compose run --rm frontend npm run lint
  ```
  
- Biome format:
  ```bash
  docker compose run --rm frontend npm run format
  ```

### Election visibility and deletion

Elections disappear from the portal automatically 3 months after their
`ElectionConfig.date`. This is derived from the date at request time, so nothing
has to be run to hide an election.

Deleting the data is a separate, manual step. An election becomes eligible one
week after it turned invisible, which leaves time to back up anything worth
keeping.

`delete_expired_elections` reports what it would remove and changes nothing:

```bash
docker compose run --rm backend-scripts python manage.py delete_expired_elections
```

Add `--confirm` to actually delete. This permanently removes the election
config, its elections, regions, parties, candidates, vote counts and documents,
including the stored files in object storage. There is no undo — re-importing
from the source EML files is the only way back.

```bash
docker compose run --rm backend-scripts python manage.py delete_expired_elections --confirm
```

## Running without Docker

_Section might be removed._

Running without Docker is not adviced, since this requires a lot more manual setup. In the case of setting up object-storage, we suggest setting it up yourself or using an existing object-storage provider.

### Backend

1. Install prerequisites:

- [Python](https://www.python.org/downloads/) 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [PostgreSQL](https://www.postgresql.org/download/)

2. Build and download development tools, from `backend/`:

```bash
uv sync
```

3. Make sure all the required files are there for debugging:

- Make a `backend/.env` file with `DB_NAME`, `DB_USER`, `DB_PASSWORD` and `DB_HOST`.
- Have a `backend/.data` folder for debug data and fill it with EML files from an election.
- For the GitHub EML ingress, optionally set `GITHUB_TOKEN` and `GITHUB_INGRESS_REPO`.
  Use a Personal Access Token (classic) with `repo` scope as `GITHUB_TOKEN`.
  If these are set, and branches are configured in the election config,
  then the Celery task will automatically start importing data from GitHub every 10 min.

4. Add new packages with `uv add <package>`.

Run the server:

```bash
uv run manage.py runserver
```

Migrate after a model change:

```bash
uv run manage.py makemigrations backend
uv run manage.py migrate backend
```

### Frontend

1. Install prerequisites:

- [Node & npm](https://nodejs.org/en/download)

2. Install dependencies and start the development server, from `frontend/`:

```bash
npm install
npm run dev
```

## Management commands

Run these from `backend/` with `uv run manage.py <command>`, or against the running stack with
`docker compose run --rm backend-scripts python manage.py <command>`.

| Command | Description |
| --- | --- |
| `wipe_db` | Wipes all election data, keeps the super user |
| `seed` | Seeds the `ElectionConfig` |
| `import_election` | Imports all EML files in the `.data` folder |
| `reset_and_import` | Wipe, seed & import in one |
| `import_next_github_commits [election identifier]` | Runs the GitHub importer for the next batch of commits |
| `ensure_bucket --public` | (Re)creates the object storage bucket |
| `delete_expired_elections [--confirm]` | Removes elections past their retention window |

## Object storage configuration

Files are stored in an S3-compatible bucket through Django's `default_storage`
(`django-storages`). All settings default to the local RustFS container from
`docker-compose.yml`, so no configuration is needed when you run the stack with
Docker. Outside Docker, set these in `backend/.env`:

| Variable | Default | Description |
| --- | --- | --- |
| `S3_BUCKET_NAME` | `uitslagenportaal` | Bucket name |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | Endpoint the backend uploads through |
| `S3_PUBLIC_DOMAIN` | `localhost:9000/uitslagenportaal` | Host used in the URLs handed to the browser |
| `S3_URL_PROTOCOL` | `http:` | Protocol for those URLs (note the trailing colon) |
| `S3_ACCESS_KEY` | `uitslagenportaal` | Access key |
| `S3_SECRET_KEY` | `password` | Secret key |
| `S3_REGION` | `nl-ams` | Region (Scaleway Amsterdam; ignored by RustFS) |
| `S3_ADDRESSING_STYLE` | `path` | `path` for RustFS, `auto` for real S3 providers |

Objects are public-read, so generated URLs are unsigned and do not expire. In
production the bucket must therefore be configured to allow anonymous
`s3:GetObject`. For Scaleway that means:

```
S3_ENDPOINT_URL=https://s3.nl-ams.scw.cloud
S3_PUBLIC_DOMAIN=<bucket>.s3.nl-ams.scw.cloud
S3_URL_PROTOCOL=https:
S3_ADDRESSING_STYLE=auto
```

## Internationalisation

The interface is available in Dutch and English, using [Lingui](https://lingui.dev). Dutch is
the **source locale**: messages are written in Dutch directly in the components, and the `nl`
catalogue is generated from that source rather than translated by hand.

```bash
npm run i18n:extract         # pull new/changed messages into the catalogues
npm run i18n:extract-clean   # pull new/changed messages into the catalogues and remove unused ones
npm run i18n:check           # fails when catalogues are out of step with the source (runs in CI)
```

Catalogues live in `frontend/src/locales/{locale}/messages.po` and are compiled on import by
`@lingui/vite-plugin`, so there is no separate compile step and nothing compiled to commit.
Each locale becomes its own lazily loaded chunk; a visitor downloads only their own language.

Marking text for translation:

| Case                                                         | Use                                                                             |
|--------------------------------------------------------------|---------------------------------------------------------------------------------|
| Text in JSX                                                  | `<Trans>` from `@lingui/react/macro`                                            |
| A count-dependent message                                    | `<Plural>` / `plural` — never a ternary between two strings                     |
| A string inside a component (`aria-label`, `title`, a prop)  | `` t`…` `` from `useLingui()`                                                   |
| A constant outside a component (lookup maps, config objects) | `msg` from `@lingui/core/macro`, resolved at the call site with `t(descriptor)` |

Translation rules:

- For common election-related English translations, see https://github.com/kiesraad/abacus-documentatie/blob/main/referentie/woordenlijst-NL-EN.md.
- Translate 'De Kiesraad' with 'De Kiesraad', as it's the organizational name, not a noun.
- Leave non-UI strings alone: `reason_code` values are keys matched against the API, and route
  paths, slugs, class names and `console.*` arguments are not user-facing copy.

Numbers and dates go through `useFormatters()` in `frontend/src/utils/format.ts`, which follows the
active locale. Dates keep the `Europe/Amsterdam` zone whatever the interface language, because
election times are always Dutch local time.

The language switcher lives in the footer; the choice is stored in `localStorage` and is
deliberately not part of the URL. Activating a catalogue is the root route's loader
(`localeLoader`), and the switcher only saves the choice and revalidates: that way a language
change is router work like any other, and the navigation progress bar covers the download.

> **When changing the build config:** the Lingui macros need a Babel pass, added in
> `vite.config.ts` via `@rolldown/plugin-babel`. `@vitejs/plugin-react` v6 removed the `babel`
> option that most Lingui guides use — wiring it that way fails silently: the build succeeds and
> the app ships untranslated. After touching the plugin setup, verify against a production build
> (`npm run build && npm run preview`), not the dev server.

## Playwright tests

Make sure to have the playwright Docker Compose running before running tests.
You can bring it down afterwards, and keep it running while working on tests:

```bash
docker compose -f docker-compose.yml -f docker-compose.playwright.yml up -d
docker compose -f docker-compose.yml -f docker-compose.playwright.yml down -v
```

Install Chromium once, then run the suite from `backend/`:

```bash
cd backend
uv run playwright install chromium
uv run pytest playwright_tests -m playwright
```

The `-m playwright` marker is required: a bare `uv run pytest` deliberately deselects
the browser tests, so `backend-ci` never tries to run them without a stack or a
browser.

Run a single module, or filter by test name:

```bash
uv run pytest playwright_tests/test_ws_election.py -m playwright
uv run pytest playwright_tests -m playwright -k "aa_en_hunze"
```

Watch the browser, or slow it down:

```bash
uv run pytest playwright_tests -m playwright --headed
uv run pytest playwright_tests -m playwright --headed --slowmo 500
```
