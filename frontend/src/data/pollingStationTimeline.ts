import type { Step } from '../components/Timeline'

export const POLLING_STATION_TIMELINE_STEPS: Step[] = [
  {
    state: 'pending',
    title: 'Centraal Stembureau controleert',
    date: 'Tot 14 december 10:00',
    body: 'De Kiesraad controleert de telresultaten van alle gemeenten en stembureaus. Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er meldingen van kiezers die onderzocht moeten worden? Als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld, en wordt de uitslag vastgesteld.',
  },
  {
    state: 'in-progress',
    title: 'Centraal Stembureau controleert',
    date: 'Tot 14 december 10:00',
    body: 'De Kiesraad controleert de telresultaten van alle gemeenten en stembureaus. Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er meldingen van kiezers die onderzocht moeten worden? Als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld, en wordt de uitslag vastgesteld.',
  },
  {
    state: 'done',
    title: 'Nieuwe gemeentelijke optelling ',
    date: '13 december op centrale tellocatie in gemeente Lissendam',
    body: `De resultaten van hertelde stembureaus zijn van papier overgetypt in de uitslagensoftware in de uitslagensoftwareen verwerkt in de optelling van de gemeente.

Bekijk de [resultaten van de hele gemeente](#) → `,
  },
  {
    state: 'done',
    title: 'Onderzoek, hertelling en gecorrigeerde resultaten',
    date: '13 december op centrale tellocatie in gemeente Lissendam',
    body: 'Het gemeentelijk stembureau heeft in opdracht van het Centraal Stembureau de resultaten van dit stembureau onderzocht, en een hertelling gedaan.',
    files: [
      {
        name: 'Resultaten hertelling stembureau',
        url: '#',
        type: 'PDF',
        size: '5.4 MB',
        description: 'Scan van het papieren proces-verbaal (Bijlage 2 bij Na 14-2)',
      },
    ],
  },
  {
    state: 'done',
    title: 'Gemeentelijke optelling',
    date: '9 december op centrale tellocatie in gemeente Lisserdam',
    body: 'De resultaten van alle stembureaus worden op papier gecontroleerd en in de uitslagensoftware overgetypt. Daarna telt het gemeentelijk stembureau de resultaten bij elkaar op.',
  },
  {
    state: 'done',
    title: 'Telling per lijst en kandidaat',
    date: '9 december op centrale tellocatie in gemeente Lisserdam',
    body: 'Het gemeentelijk stembureau telt per stembureau alle stembiljetten op kandidaatsniveau: voor welke kandidaten per partij de stemmen precies zijn uitgebracht. **Deze telling is de basis van de officiele uitslag.**',
    files: [
      {
        name: 'Telling van het stembureau op kandidaatniveau',
        url: '#',
        type: 'PDF',
        size: '6 MB',
        description: 'Scan van het papieren proces-verbaal (Bijlage 1 bij Na 31-2)',
      },
    ],
  },
  {
    state: 'done',
    title: 'Sneltelling per lijst',
    date: '8 december na 21:00 in het stembureau',
    body: 'Na het sluiten van de stembussen tellen de leden van het stembureau hoeveel mensen hebben gestemd en hoeveel stemmen elke partij heeft gekregen. De voorlopige uitslag die je in het nieuws ziet is gebaseerd op de eerste tellingen van het stembureau. **Dit is niet de officiele uitslag.**',
    files: [
      {
        name: 'Sneltelling van het stembureau op lijstniveau',
        url: '#',
        type: 'PDF',
        size: '3 MB',
        description: 'Scan van het papieren proces-verbaal (N 10-2)',
      },
    ],
  },
]
