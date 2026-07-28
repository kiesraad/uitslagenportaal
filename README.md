# uitslagenportaal
Webapplicatie voor verkiezingsuitslagen.

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
