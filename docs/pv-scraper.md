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
It imports `pv_scraper/authorities.json` from default storage. Election pages in the file are merged with those
already known, so pages the scraper found since the file was exported are kept.

### Crawling

`dispatch_scrape_tasks` runs every 10 minutes and sends `run_scrape_for_source` to the `scraper` queue for each source
that is due. One scrape is split over three modules in `pv_scraper/utils/`:
- `SiteScraper` holds the state of the run. It keeps the queue of pages to visit, and pages about results go first.
  It decides which links to follow or download and stores PDFs in default storage under `pv_scraper/<code>/`. Every
  downloaded file becomes a `ScrapedFile`; files that are no PV are only recorded, with a `rejected_reason`, so that
  an unchanged one is not downloaded again. Every visited page becomes a `ScrapedPage`, with the page that led to it.
- `SiteCrawler` requests one link at a time with the browser's cookies. The response tells a page from a file: an HTML
  page is rendered in Playwright, where it accepts the cookie banner, expands collapsed content and collects the links;
  any other response is returned as a file.
- `link_rules` contains the patterns that pick out pages worth following and documents that may be PVs.

The scraper downloads every PDF that may be a PV of any election and year. It only skips documents that are clearly
something else, such as kandidatenlijsten, instructions and folders. The election and model of a file are decided
afterwards, by `PvClassifier`.

#### Election pages

A scrape starts from the source's `election_pages`, or from its `website` when there are none. The scraper keeps
that list up to date:
- **Added:** for each page with PV files, the highest page above it that is about elections in general, such as
  `/verkiezingen` rather than `/verkiezingen/gemeenteraad-2026`: a page about one election never links to the next.
  "Above" means the pages that linked to it, in this or an earlier run, or the folders in its URL that answered as a
  page. Without such a page, the page that led to the files is added, or the files page itself when that was the
  home page.
- **Removed:** a page that answered 404 or 410 for over a week, or that led to no PV files for over a month. The
  month only counts on runs that visited every link worth visiting. Errors, bot walls and 5xx answers don't count as
  missing.
- **Replaced:** a page that moved permanently within the site (301 or 308) is replaced by its new address.

Removals and replacements are noted in the source's `errors`. After a site redesign the old pages disappear from the
list, so the next scrape crawls the whole website again and finds the new ones.

The scraper from then on updates its state in the DB and keeps track of downloaded files, pages on which to find PVs and errors.
Based on the DB state, we can manually verify and update the list of authorities to increase coverage.
