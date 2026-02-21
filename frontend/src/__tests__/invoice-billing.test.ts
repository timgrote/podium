import { describe, expect, it } from 'vitest'

/**
 * Invoice billing logic:
 * - quantity = delta percent for THIS invoice only (e.g., 25 means 25%)
 * - amount = unit_price * quantity / 100 (the dollar amount billed this invoice)
 * - previous_billing = cumulative dollars billed on prior invoices
 * - cumulative percent = (previous_billing + amount) / unit_price * 100
 */

function computeThisAmount(unitPrice: number, quantity: number): number {
  return (unitPrice * quantity) / 100
}

function computeCumulativePercent(
  unitPrice: number,
  previousBilling: number,
  thisAmount: number,
): number {
  if (unitPrice === 0) return 0
  return ((previousBilling + thisAmount) / unitPrice) * 100
}

function computeNextPreviousBilling(
  previousBilling: number,
  thisAmount: number,
): number {
  return previousBilling + thisAmount
}

describe('invoice billing calculations', () => {
  it('computes this amount from unit price and delta percent', () => {
    expect(computeThisAmount(10000, 25)).toBe(2500)
    expect(computeThisAmount(10000, 0)).toBe(0)
    expect(computeThisAmount(10000, 100)).toBe(10000)
    expect(computeThisAmount(5000, 50)).toBe(2500)
  })

  it('computes cumulative percent correctly', () => {
    // First invoice: 25% of $10,000
    const amount1 = computeThisAmount(10000, 25)
    expect(computeCumulativePercent(10000, 0, amount1)).toBe(25)

    // Second invoice: another 25% of $10,000, previous billing = $2,500
    const amount2 = computeThisAmount(10000, 25)
    expect(computeCumulativePercent(10000, 2500, amount2)).toBe(50)

    // Third invoice: 50% of $10,000, previous billing = $5,000
    const amount3 = computeThisAmount(10000, 50)
    expect(computeCumulativePercent(10000, 5000, amount3)).toBe(100)
  })

  it('handles zero unit price without division error', () => {
    expect(computeCumulativePercent(0, 0, 0)).toBe(0)
  })

  it('computes next previous billing for invoice chaining', () => {
    // First invoice billed $2,500 with no previous
    expect(computeNextPreviousBilling(0, 2500)).toBe(2500)

    // Second invoice billed $2,500 with $2,500 previous
    expect(computeNextPreviousBilling(2500, 2500)).toBe(5000)

    // Third invoice billed $5,000 with $5,000 previous
    expect(computeNextPreviousBilling(5000, 5000)).toBe(10000)
  })

  it('handles full invoice chain scenario', () => {
    const taskFee = 12000
    let prevBilling = 0

    // Invoice 1: 30%
    const amt1 = computeThisAmount(taskFee, 30)
    expect(amt1).toBe(3600)
    expect(computeCumulativePercent(taskFee, prevBilling, amt1)).toBe(30)
    prevBilling = computeNextPreviousBilling(prevBilling, amt1)
    expect(prevBilling).toBe(3600)

    // Invoice 2: 20%
    const amt2 = computeThisAmount(taskFee, 20)
    expect(amt2).toBe(2400)
    expect(computeCumulativePercent(taskFee, prevBilling, amt2)).toBe(50)
    prevBilling = computeNextPreviousBilling(prevBilling, amt2)
    expect(prevBilling).toBe(6000)

    // Invoice 3: 50%
    const amt3 = computeThisAmount(taskFee, 50)
    expect(amt3).toBe(6000)
    expect(computeCumulativePercent(taskFee, prevBilling, amt3)).toBe(100)
    prevBilling = computeNextPreviousBilling(prevBilling, amt3)
    expect(prevBilling).toBe(12000)
  })
})
