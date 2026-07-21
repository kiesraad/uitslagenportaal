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

/**
 * Formats an ISO date string as "10 december 2025 - 12:17".
 * Returns the input unchanged if it cannot be parsed.
 */
export function formatDate(isoDate: string): string {
  const date = new Date(isoDate)
  if (Number.isNaN(date.getTime())) {
    return isoDate
  }
  const datePart = date.toLocaleDateString('nl-NL', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'Europe/Amsterdam',
  })
  const timePart = date.toLocaleTimeString('nl-NL', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Amsterdam',
  })
  return `${datePart} - ${timePart}`
}
