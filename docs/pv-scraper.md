## PV scraper

We want to be able to automatically download PVs from municipality websites until an official process of gathering PVs is in place.
This will help us to verify the PV processing and viewing functionality.

The scraper has as goal to:
- Automatically download as many relevant PVs as possible
- Classify which model they are
- Determine to which authority they belong
- Store them using a naming convention to a specific bucket, which the import PV task uses as a source.

The scraper has a best-effort policy and does not intend to cover all authorities fully.

### Architecture

A separate Django app is added for the code to download the PVs from municipality websites, named `pv_scraper`. 
It runs a Celery task which uses its own queue, and the task is handled by a specific worker, with access to Playwright.
This allows us to separate the scraping process from the other tasks while still using Celery's task handling logic.

### List of authorities

The scraper is based on a list of authorities, which lists municipalities, water authorities, provinces and the state with their main website.
The list is created by hand (or a manually run script) and will need updating if websites of municipalities change or when there are mergers.
The list is imported using the `import_scrape_sources` command to seed the `ScrapeSource` model: 
`docker compose run --rm backend-scripts python manage.py import_scrape_sources`.
It imports `pv_scraper/authorities.json` from default storage.

The scraper from then on updates its state in the DB and keeps track of downloaded files, pages on which to find PVs and errors.
Based on the DB state, we can manually verify and update the list of authorities to increase coverage.
