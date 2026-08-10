**Let op: dit project bevindt zich momenteel in een opstartfase. Documentatie en code zullen onvolledig en soms incorrect zijn.**

# Uitslagenportaal - Backend

Het uitslagenplatform is een webapplicatie die gebruikers in staat stelt meer inzicht in het verkiezingsproces te krijgen. Allereerst ontsluit het uistlagenplatform EMLs - digitale telbestanden - tijdens en na een verkiezingsperiode op een overzichtelijke en leesbare manier. Daarnaast geeft het platform ook weer wat er in de verkiezingsperiode gebeurt en waar men in het verkiezingsproces zit.

## Requirements

Vul met verwijzingen naar stukken zoals Kieswet etc.

## Technische architectuur

Vul met presentatie van architectuur

Een diepere duik in de technische architectuur is te vinden in [deze documentatie](docs/code-architecture.md).

## Development setup

1. Install prerequisites:

- [Python](https://www.python.org/downloads/) or Command-Line
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [PostgreSQL](https://www.postgresql.org/download/)
- [Docker](https://docs.docker.com/get-docker/)

2. Build and download development tools:

```bash
cd /backend
uv venv
uv pip install -e .
```

3. Make sure all the required files are there for debugging

- Make an .env file with: DB_NAME, DB_USER, DB_PASSWORD and DB_HOST
- Have an .data folder for debug data and fill it with EML files from an election

4. Adding new packages

```bash
uv add [package]
```


## Run Server

```bash
python manage.py runserver
```

## Migrate after model change

```bash
python manage.py makemigrations backend
python manage.py migrate backend
```

## Management commands

### Wipes all election data, keeps super user
```bash
python manage.py wipe_db
```

### Seed the ElectionConfig
```bash
python manage.py seed
```

### Import all EML files in the .data folder
```bash
python manage.py import_election
```

### Wipe, seed & import in one
```bash
python manage.py reset_and_import
```

## Object storage

Files are stored in an S3-compatible bucket through Django's `default_storage`
(`django-storages`). All settings default to the local MinIO container from
`docker-compose.yml`, so no configuration is needed when you run the stack with
Docker. Outside Docker, set these in your `.env`:

| Variable | Default | Description |
| --- | --- | --- |
| `S3_BUCKET_NAME` | `uitslagenportaal` | Bucket name |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | Endpoint the backend uploads through |
| `S3_PUBLIC_DOMAIN` | `localhost:9000/uitslagenportaal` | Host used in the URLs handed to the browser |
| `S3_URL_PROTOCOL` | `http:` | Protocol for those URLs (note the trailing colon) |
| `S3_ACCESS_KEY` | `uitslagenportaal` | Access key |
| `S3_SECRET_KEY` | `password` | Secret key |
| `S3_REGION` | `nl-ams` | Region (Scaleway Amsterdam; ignored by MinIO) |
| `S3_ADDRESSING_STYLE` | `path` | `path` for MinIO, `auto` for real S3 providers |

Objects are public-read, so generated URLs are unsigned and do not expire. In
production the bucket must therefore be configured to allow anonymous
`s3:GetObject`. For Scaleway that means:

```
S3_ENDPOINT_URL=https://s3.nl-ams.scw.cloud
S3_PUBLIC_DOMAIN=<bucket>.s3.nl-ams.scw.cloud
S3_URL_PROTOCOL=https:
S3_ADDRESSING_STYLE=auto
```
