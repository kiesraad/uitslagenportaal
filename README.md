# Uitslagenportaal

Webapplicatie voor weergeven van verkiezingsuitslagen.

## Development setup

Start the full stack (database, backend, frontend and reverse proxy) with Docker Compose:

```bash
docker compose up -d --build
```

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
- Bucket: `uitslagenportaal`, created on first `docker compose up` by the
  `object-storage-bootstrap` service, which also makes its objects publicly readable

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

- Eslint format:
  ```bash
  docker compose run --rm frontend npm run lint
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

## End-to-end tests (Playwright)

Browser tests live in `frontend/tests/e2e/`. They run on a separate  **throwaway stack** on http://localhost:8081. 

Playwright starts and stops this stack automatically via `frontend/playwright.config.ts` and `.docker/e2e/start.sh`. Each run migrates the database and imports EML fixtures from `backend/mainsite/tests/fixtures/eml/` (waterschap and provinciale staten).

`cd frontend && npm install` installs `@playwright/test` and downloads Chromium (cached in `~/.cache/ms-playwright`). The frontend Docker image skips that download. A CI job should install browsers separately with `npx playwright install --with-deps chromium` so Linux system libraries are present.

### Running tests

Always run Playwright from the `frontend/` directory:

```bash
cd frontend
npm run test:e2e
```

Run a single spec file:

```bash
npx playwright test ws-election
```

Filter by test title (substring match):

```bash
npx playwright test ps-election -g "Aa en Hunze"
```

Debug or watch the browser:

```bash
npx playwright test ws-election --debug
npx playwright test ws-election --headed
```
