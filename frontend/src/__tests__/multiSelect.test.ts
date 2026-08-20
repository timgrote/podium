import { describe, expect, it } from 'vitest'
import { useMultiSelect } from '../composables/useMultiSelect'

const ORDER = ['a', 'b', 'c', 'd', 'e']

describe('useMultiSelect', () => {
  it('starts with no selection', () => {
    const { selected, multiSelecting } = useMultiSelect()
    expect(selected.value.size).toBe(0)
    expect(multiSelecting.value).toBe(false)
  })

  it('ctrl/cmd-click toggles a card in and out without clearing others', () => {
    const { selected, handleClick } = useMultiSelect()
    expect(handleClick('a', { ctrl: true }, ORDER)).toBe(true)
    expect(handleClick('b', { ctrl: true }, ORDER)).toBe(true)
    expect([...selected.value]).toEqual(expect.arrayContaining(['a', 'b']))
    expect(handleClick('a', { ctrl: true }, ORDER)).toBe(true)
    expect(selected.value.has('a')).toBe(false)
    expect(selected.value.has('b')).toBe(true)
  })

  it('plain click on an unselected card with no group returns false (navigate)', () => {
    const { handleClick, selected } = useMultiSelect()
    expect(handleClick('a', {}, ORDER)).toBe(false)
    expect(selected.value.size).toBe(0)
  })

  it('plain click while a group is active clears the group and returns false (navigate)', () => {
    const { selected, handleClick } = useMultiSelect()
    handleClick('a', { ctrl: true }, ORDER)
    handleClick('b', { ctrl: true }, ORDER)
    expect(selected.value.size).toBe(2)
    expect(handleClick('c', {}, ORDER)).toBe(false)
    expect(selected.value.size).toBe(0)
  })

  it('shift-click selects everything between the last click and the clicked card', () => {
    const { selected, handleClick } = useMultiSelect()
    handleClick('b', {}, ORDER) // anchor at b
    handleClick('d', { shift: true }, ORDER)
    expect([...selected.value]).toEqual(['b', 'c', 'd'])
  })

  it('shift-click works in reverse order too', () => {
    const { selected, handleClick } = useMultiSelect()
    handleClick('d', {}, ORDER) // anchor at d
    handleClick('b', { shift: true }, ORDER)
    expect([...selected.value]).toEqual(['b', 'c', 'd'])
  })

  it('shift-click extends an existing ctrl-selection rather than replacing it', () => {
    const { selected, handleClick } = useMultiSelect()
    handleClick('a', { ctrl: true }, ORDER)
    handleClick('b', { ctrl: true }, ORDER) // anchor at b
    handleClick('d', { shift: true }, ORDER)
    expect([...selected.value]).toEqual(['a', 'b', 'c', 'd'])
  })

  it('multiSelecting is true only when 2+ are selected', () => {
    const { selected, handleClick, multiSelecting } = useMultiSelect()
    handleClick('a', { ctrl: true }, ORDER)
    expect(multiSelecting.value).toBe(false)
    handleClick('b', { ctrl: true }, ORDER)
    expect(multiSelecting.value).toBe(true)
    selected.value = new Set()
    expect(multiSelecting.value).toBe(false)
  })

  it('isSelected reflects membership', () => {
    const { handleClick, isSelected } = useMultiSelect()
    handleClick('x', { ctrl: true }, ORDER)
    expect(isSelected('x')).toBe(true)
    expect(isSelected('y')).toBe(false)
  })

  it('clear empties the selection', () => {
    const { selected, handleClick, clear } = useMultiSelect()
    handleClick('a', { ctrl: true }, ORDER)
    handleClick('b', { ctrl: true }, ORDER)
    clear()
    expect(selected.value.size).toBe(0)
  })

  it('selectOnly replaces the selection with a single id', () => {
    const { selected, handleClick, selectOnly } = useMultiSelect()
    handleClick('a', { ctrl: true }, ORDER)
    handleClick('b', { ctrl: true }, ORDER)
    selectOnly('c')
    expect([...selected.value]).toEqual(['c'])
  })

  it('selection is not cleared by a plain click when nothing is selected', () => {
    const { selected, handleClick } = useMultiSelect()
    handleClick('a', {}, ORDER)
    expect(selected.value.size).toBe(0)
    expect(handleClick('b', {}, ORDER)).toBe(false)
  })
})
