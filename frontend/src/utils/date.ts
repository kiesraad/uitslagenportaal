const TIMELINE_DATE_FORMAT: Intl.DateTimeFormatOptions = {
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'Europe/Amsterdam',
}

/**
 * Formats an ISO date string as a readable Dutch date with time,
 * e.g. "8 december om 21:00". Returns the input unchanged if it
 * cannot be parsed.
 */
export function formatTimelineDate(isoDate: string): string {
  const date = new Date(isoDate)
  if (Number.isNaN(date.getTime())) {
    return isoDate
  }
  return new Intl.DateTimeFormat('nl-NL', TIMELINE_DATE_FORMAT).format(date)
}
