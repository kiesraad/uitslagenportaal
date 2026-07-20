# uitslagenportaal
Webapplicatie voor verkiezingsuitslagen.

## Development setup

Start the full stack (database, backend, frontend and reverse proxy) with Docker Compose:

```bash
docker compose up -d --build
```

The app is then available at http://localhost:8080.
The `backend-scripts` service can be used for one-off commands, like migrating the DB, while the backend keeps running:
```bash
docker compose run --rm backend-scripts python manage.py migrate
```
