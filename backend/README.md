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

# Wipes all election data, keeps super user
```bash
python manage.py wipe_db
```

# Seed the ElectionConfig
```bash
python manage.py seed
```

# Import all EML files in the .data folder
```bash
python manage.py import_election
```

# Wipe, seed & import in one
```bash
python manage.py reset_and_import
```
