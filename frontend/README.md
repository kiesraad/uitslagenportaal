**Let op: dit project bevindt zich momenteel in een opstartfase. Documentatie en code zullen onvolledig en soms incorrect zijn.**

# Uitslagenportaal - Frontend

Het uitslagenplatform is een webapplicatie die gebruikers in staat stelt meer inzicht in het verkiezingsproces te krijgen. Allereerst ontsluit het uistlagenplatform EMLs - digitale telbestanden - tijdens en na een verkiezingsperiode op een overzichtelijke en leesbare manier. Daarnaast geeft het platform ook weer wat er in de verkiezingsperiode gebeurt en waar men in het verkiezingsproces zit.

## Requirements

Vul met verwijzingen naar stukken zoals Kieswet etc.

## Technische architectuur

Vul met presentatie van architectuur

Een diepere duik in de technische architectuur is te vinden in [deze documentatie](docs/code-architecture.md).

## Development setup

1. Install prerequisites:

- [Node & npm](https://nodejs.org/en/download)
- [Vite](https://vite.dev/)
- [Docker](https://docs.docker.com/get-docker/)

2. Build and download development tools:

```bash
cd /frontend
npm install
```

3. Start the development environment

```bash
npm run dev
```

## Internationalisation

The interface is available in Dutch and English, using [Lingui](https://lingui.dev). Dutch is
the **source locale**: messages are written in Dutch directly in the components, and the `nl`
catalogue is generated from that source rather than translated by hand.

```bash
npm run i18n:extract         # pull new/changed messages into the catalogues
npm run i18n:extract-clean   # pull new/changed messages into the catalogues and remove unused ones
npm run i18n:check           # fails when catalogues are out of step with the source (runs in CI)
```

Catalogues live in `src/locales/{locale}/messages.po` and are compiled on import by
`@lingui/vite-plugin`, so there is no separate compile step and nothing compiled to commit.
Each locale becomes its own lazily loaded chunk; a visitor downloads only their own language.

Marking text for translation:

| Case                                                         | Use                                                                             |
|--------------------------------------------------------------|---------------------------------------------------------------------------------|
| Text in JSX                                                  | `<Trans>` from `@lingui/react/macro`                                            |
| A count-dependent message                                    | `<Plural>` / `plural` — never a ternary between two strings                     |
| A string inside a component (`aria-label`, `title`, a prop)  | `` t`…` `` from `useLingui()`                                                   |
| A constant outside a component (lookup maps, config objects) | `msg` from `@lingui/core/macro`, resolved at the call site with `t(descriptor)` |

Translation rules:

- For common election-related English translations, see https://github.com/kiesraad/abacus-documentatie/blob/main/referentie/woordenlijst-NL-EN.md.
- Translate 'De Kiesraad' with 'De Kiesraad', as it's the organizational name, not a noun.
- Leave non-UI strings alone: `reason_code` values are keys matched against the API, and route
  paths, slugs, class names and `console.*` arguments are not user-facing copy.

Numbers and dates go through `useFormatters()` in `src/utils/format.ts`, which follows the
active locale. Dates keep the `Europe/Amsterdam` zone whatever the interface language, because
election times are always Dutch local time.

The language switcher lives in the footer; the choice is stored in `localStorage` and is
deliberately not part of the URL. Activating a catalogue is the root route's loader
(`localeLoader`), and the switcher only saves the choice and revalidates: that way a language
change is router work like any other, and the navigation progress bar covers the download.

> **When changing the build config:** the Lingui macros need a Babel pass, added in
> `vite.config.ts` via `@rolldown/plugin-babel`. `@vitejs/plugin-react` v6 removed the `babel`
> option that most Lingui guides use — wiring it that way fails silently: the build succeeds and
> the app ships untranslated. After touching the plugin setup, verify against a production build
> (`npm run build && npm run preview`), not the dev server.
