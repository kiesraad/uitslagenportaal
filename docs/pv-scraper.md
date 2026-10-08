## PV scraper

We want to be able to automatically download PVs from municipality websites until an official process of gathering PVs is in place.
This will help us to verify the PV processing and viewing functionality.

The scraper has as goal to:
- Automatically download as many relevant PVs as possible
- Classify which model they are
- Determine to which authority they belong
- Store them using a naming convention to a specific bucket, which the import PV task uses as a source.

The scraper has a best-effort policy and does not intend to cover all authorities fully.
PV models are subject to change, but we're targeting the models as listed on
https://www.rijksoverheid.nl/themas/overheid-en-democratie/verkiezingen/verkiezingentoolkit/modellen.

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
  It decides which links to follow or download, and yields each new PDF that may be a PV for classification. Every
  downloaded file becomes a `ScrapedFile`; files that are no PV are only recorded, with a `rejected_reason`, so that
  an unchanged one is not downloaded again. Every visited page becomes a `ScrapedPage`, with the page that led to it.
- `SiteCrawler` requests one link at a time with the browser's cookies. The response tells a page from a file: an HTML
  page is rendered in Playwright, where it accepts the cookie banner, expands collapsed content and collects the links;
  any other response is returned as a file.
- `link_rules` contains the patterns that pick out pages worth following and documents that may be PVs.

The scraper downloads every PDF that may be a PV of any election and year. It only skips documents that are clearly
something else, such as kandidatenlijsten, instructions and folders. The election and model of a file are decided
afterwards, by `PvClassifier`.

### Classification

`run_scrape_for_source` hands each downloaded file to `PvClassifier` (`pv_scraper/utils/pv_classifier.py`), which runs
Tesseract on the first page or two. To try it on a folder of PDFs, use
`docker compose run --rm backend-scripts python manage.py classify_pvs <folder>`
or `docker compose run --rm backend-scripts python manage.py classify_pv <path>`.

- **Model:** a model counts as identified when its title is on the page, with or without its code. Only the models
  in `MODELS` are recognized; other files are discarded.
- **Election:** the OSV forms name the election and its date in the header, just above the model code, worded in many
  ways ("Verkiezing Gemeenteraad 2026", "De verkiezing van de leden van het algemeen bestuur van het hoogheemraadschap
  van Delfland", "Gemeenteraad Purmerend 2026"). The Kiesraad's own models, such as O 7 and P 22-1, name it just below
  the model code and title instead, always as "De verkiezing van de leden van …". The classifier reads the id and date
  from there first, falling back
  to the rest of the text and then the file name. Of the wording it keeps only the authority: the gemeente,
  province or waterschap the header names ("Purmerend", "Delfland"), or nothing when it names none, as TK, EP and most
  GR headers. A province or waterschap is corrected to its name in `AUTHORITIES`, or dropped when it is none of them;
  that list needs updating after a merger. The id follows the EML election identifiers, so a waterschap election is
  `AB2027`, also when a file says `WS`.
- **Region:** gemeente code and name, stembureau and kieskring are read from the text. A Na 31-2 bijlage 1 takes its
  stembureau from the heading that starts the stembureau's section, on page 1 or behind a cover page on page 2, as
  the running header of some gemeenten repeats one stembureau on every page. When OCR misses the stembureau of a
  model that belongs to one stembureau, the number is taken from the file name (`Brunssum_10_…_GR26`,
  `stembureau_7`).

#### Naming convention

An identified PV is stored in default storage under `pvs/` as `<election>_<model>[_<csb>]_<region>[_SB<n>].pdf`. The
name is built from what the PV and its source say, and the application's database only corrects the gemeente's name,
so another platform delivering PVs can follow it too.

| Part     | Contents                                                                                                                                                                        | Example                          |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| election | election id, as in the EML                                                                                                                                                      | `GR2026`, `AB2027`               |
| model    | model code without spaces; a bijlage as `-B<n>`                                                                                                                                 | `N10-2`, `Na31-2-B1`             |
| csb      | slug of the province or waterschap, for PS and AB elections only; left out when not known or when it is the region                                                              | `vallei-en-veluwe`               |
| region   | the gemeente as `<code>-<slug of its name>`, or either one when only that is known; for a CSB model the CSB; for a hoofdstembureau model `kieskring[-<n>][-<slug of its name>]` | `0228-ede`, `kieskring-1-arnhem` |
| SB\<n\>  | the stembureau, for the models of one stembureau only                                                                                                                           | `SB12`                           |

The gemeente's name is taken from the gemeenten of the most recent election that has it: by its code when known, or else
by the name read, which may have one misread letter or a mangled accent (an exact match wins); the code is then taken
from there too. A gemeente not found keeps what the PV and its source say.

The CSB of TK and EP is `Nederland`. It is in the metadata of every PV of those elections, but not in the file name,
where it would be the same for all of them.

The models of a centraal stembureau (P 22-1, P 22-2) name no gemeente. Of a PS, AB, TK or EP election, their region is
the CSB, named once and without a code, and a PS or AB PV without a known CSB is not stored. Of a GR election, the CSB
is the gemeente itself.

The models of a hoofdstembureau (O 7, P 1f-1), of TK, EP and PS with more than one kieskring, are about a kieskring.
Their region is the kieskring, by the number and name the PV gives it: "Kieskring 1 Arnhem", "Kieskring 12 (
's-Gravenhage)", or with an arrow after it as OSV writes it ("Kieskring 2 Nijmegen → Gemeente …"). A PV that names
only one of them is named by that one ("Kieskring 's-Gravenhage"); one without either is not stored. `/PvRegionCode`
holds the kieskring's number (`1`) and `/PvRegionName` its name (`Arnhem`).

For example `GR2026_N10-2_0228-ede_SB12.pdf`, `AB2027_Na31-1_vallei-en-veluwe_0228-ede.pdf`,
`AB2027_P22-2_vallei-en-veluwe.pdf`, `TK2025_P22-2_nederland.pdf`, `PS2023_O7_gelderland_kieskring-1-arnhem.pdf`. Slugs
consist of
`[a-z0-9-]`, so `_` only separates parts. To read a name back: the first two parts are election and model, a last part
`SB<n>` is the stembureau, then the last remaining part is the region and one before it the CSB.

The stored PDF also carries what it is in its document information, added with pypdf as an incremental update: the
original bytes stay in front unchanged, so a digital signature stays valid. `/Title` (`Na31-2-B1 Ede stembureau 12`)
and `/Subject` (`AB2027 Vallei en Veluwe`) show in any PDF viewer; software reads `/PvElection`, `/PvElectionDate`,
`/PvModel`, `/PvCsb`, `/PvRegionCode`, `/PvRegionName`, `/PvStembureau` and `/PvMatchedOn`. A key whose value is
unknown is left out. The metadata, not the file name, is what software should rely on; the name only has to be
readable and unique.

A file of the same name is replaced, since it holds the same PV. So that a misread stembureau doesn't replace another
stembureau's PV, a PV whose stembureau differs from the one in its file name is not stored. A PV found on a gemeente's
website must be about that
gemeente by code or name, unless its region is a CSB or a kieskring, and a GR header naming another gemeente is
refused;
the source then gives the gemeente's code
and name. A waterschap's or province's website gives the CSB when the header doesn't name it.

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
