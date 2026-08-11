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

const MS_PER_MINUTE = 60 * 1000
const MS_PER_HOUR = 60 * MS_PER_MINUTE
const MS_PER_DAY = 24 * MS_PER_HOUR

/**
 * Remaining time until an ISO deadline, using days (>= 24h), hours (>= 1h),
 * or minutes. Returns null when the deadline has passed or the date is invalid.
 */
export function getRemainingReportTime(isoDeadline: string, now = new Date()): {
  value: number
  unit: 'day' | 'hour' | 'minute'
} | null {
  const deadline = new Date(isoDeadline)
  if (Number.isNaN(deadline.getTime())) {
    return null
  }

  const remainingMs = deadline.getTime() - now.getTime()
  if (remainingMs <= 0) {
    return null
  }

  if (remainingMs >= MS_PER_DAY) {
    return { value: Math.floor(remainingMs / MS_PER_DAY), unit: 'day' }
  }
  if (remainingMs >= MS_PER_HOUR) {
    return { value: Math.floor(remainingMs / MS_PER_HOUR), unit: 'hour' }
  }
  return { value: Math.max(1, Math.ceil(remainingMs / MS_PER_MINUTE)), unit: 'minute' }
}

export function formatIssueReportDeadlineHeading(isoDeadline: string, now = new Date()): string {
  const remaining = getRemainingReportTime(isoDeadline, now)
  if (!remaining) {
    return 'U kunt geen fout meer melden'
  }

  const unitLabel =
    remaining.unit === 'day'
      ? remaining.value === 1
        ? 'dag'
        : 'dagen'
      : remaining.unit === 'hour'
        ? 'uur'
        : remaining.value === 1
          ? 'minuut'
          : 'minuten'

  return `U heeft nog ${remaining.value} ${unitLabel} om een melding te maken`
}
