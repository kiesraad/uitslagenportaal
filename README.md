# Uitslagenportaal

Webapplicatie voor weergeven van verkiezingsuitslagen.

## Development setup

Start the full stack (database, backend, frontend and reverse proxy) with Docker Compose:

```bash
docker compose up -d --build
```

Install plugins for `ruff` and `biome` in your IDE to use the required formatting/linting.

### Environment variables

No `.env` file is required for Docker development. Database and backend settings are configured in `docker-compose.yml` and passed to the containers automatically (`DB_HOST=db`, etc.).

### Election data (`.data`)

Put EML XML fixture files on your machine in:

```
backend/.data/
```

This folder is mounted into the backend container at `/app/.data`.

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
