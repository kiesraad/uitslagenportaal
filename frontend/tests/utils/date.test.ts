import { describe, expect, it } from 'vitest'

import {
  formatIssueReportDeadlineHeading,
  getRemainingReportTime,
} from '@/utils/date'

const NOW = new Date('2026-12-10T12:00:00+01:00')

describe('getRemainingReportTime', () => {
  it('returns days when at least 24 hours remain', () => {
    expect(getRemainingReportTime('2026-12-13T12:00:00+01:00', NOW)).toEqual({
      value: 3,
      unit: 'day',
    })
  })

  it('returns hours when less than 24 hours remain', () => {
    expect(getRemainingReportTime('2026-12-10T17:00:00+01:00', NOW)).toEqual({
      value: 5,
      unit: 'hour',
    })
  })

  it('returns minutes when less than 1 hour remains', () => {
    expect(getRemainingReportTime('2026-12-10T12:45:00+01:00', NOW)).toEqual({
      value: 45,
      unit: 'minute',
    })
  })

  it('rounds up partial minutes to at least 1', () => {
    expect(getRemainingReportTime('2026-12-10T12:00:30+01:00', NOW)).toEqual({
      value: 1,
      unit: 'minute',
    })
  })

  it('returns null when the deadline has passed', () => {
    expect(getRemainingReportTime('2026-12-09T12:00:00+01:00', NOW)).toBeNull()
  })

  it('returns null for an invalid date', () => {
    expect(getRemainingReportTime('not-a-date', NOW)).toBeNull()
  })
})

describe('formatIssueReportDeadlineHeading', () => {
  it('formats remaining days', () => {
    expect(formatIssueReportDeadlineHeading('2026-12-13T12:00:00+01:00', NOW)).toBe(
      'U heeft nog 3 dagen om een melding te maken',
    )
  })

  it('formats a single remaining day', () => {
    expect(formatIssueReportDeadlineHeading('2026-12-11T12:00:00+01:00', NOW)).toBe(
      'U heeft nog 1 dag om een melding te maken',
    )
  })

  it('formats remaining hours', () => {
    expect(formatIssueReportDeadlineHeading('2026-12-10T17:00:00+01:00', NOW)).toBe(
      'U heeft nog 5 uur om een melding te maken',
    )
  })

  it('formats remaining minutes', () => {
    expect(formatIssueReportDeadlineHeading('2026-12-10T12:45:00+01:00', NOW)).toBe(
      'U heeft nog 45 minuten om een melding te maken',
    )
  })

  it('formats a single remaining minute', () => {
    expect(formatIssueReportDeadlineHeading('2026-12-10T12:00:30+01:00', NOW)).toBe(
      'U heeft nog 1 minuut om een melding te maken',
    )
  })

  it('says reporting is closed when the deadline has passed', () => {
    expect(formatIssueReportDeadlineHeading('2026-12-09T12:00:00+01:00', NOW)).toBe(
      'U kunt geen fout meer melden',
    )
  })
})
