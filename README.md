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
