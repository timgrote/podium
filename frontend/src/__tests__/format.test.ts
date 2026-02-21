import { describe, expect, it } from 'vitest'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

function formatCurrencyShort(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-US')
}

describe('currency formatting', () => {
  it('formats with two decimal places', () => {
    expect(formatCurrency(12345.67)).toBe('$12,345.67')
    expect(formatCurrency(0)).toBe('$0.00')
    expect(formatCurrency(1000000)).toBe('$1,000,000.00')
  })

  it('formats short (no decimals)', () => {
    expect(formatCurrencyShort(12345)).toBe('$12,345')
    expect(formatCurrencyShort(0)).toBe('$0')
    expect(formatCurrencyShort(999999)).toBe('$999,999')
  })
})

describe('date formatting', () => {
  it('formats ISO date strings', () => {
    const result = formatDate('2026-02-20T12:00:00')
    expect(result).toContain('2026')
    expect(result).toContain('20')
  })

  it('returns dash for null', () => {
    expect(formatDate(null)).toBe('-')
  })
})
