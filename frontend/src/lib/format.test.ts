import { describe, expect, it } from 'vitest'
import { defaultDeparture, formatDuration, formatMiles } from './format'

describe('formatDuration', () => {
  it('formats minutes only', () => expect(formatDuration(45 * 60)).toBe('45 min'))
  it('formats hours with padded minutes', () => expect(formatDuration(3 * 3600 + 5 * 60)).toBe('3 h 05 min'))
})

describe('formatMiles', () => {
  it('rounds and groups digits', () => expect(formatMiles(1085.6)).toBe('1,086 mi'))
})

describe('defaultDeparture', () => {
  it('is the next whole hour in datetime-local form', () => {
    expect(defaultDeparture(new Date(2026, 9, 23, 14, 20))).toBe('2026-10-23T15:00')
  })
  it('rolls over midnight', () => {
    expect(defaultDeparture(new Date(2026, 9, 23, 23, 40))).toBe('2026-10-24T00:00')
  })
})
