import { describe, expect, it } from 'vitest'
import { buildZip, crc32 } from './zip'

const FIXED = new Date(2026, 8, 14, 10, 30, 0)

function u32(bytes: Uint8Array, at: number): number {
  return new DataView(bytes.buffer, bytes.byteOffset).getUint32(at, true)
}

function u16(bytes: Uint8Array, at: number): number {
  return new DataView(bytes.buffer, bytes.byteOffset).getUint16(at, true)
}

describe('crc32', () => {
  it('matches the known checksum of a standard string', () => {
    // The canonical test vector: CRC-32 of "123456789" is 0xCBF43926.
    expect(crc32(new TextEncoder().encode('123456789'))).toBe(0xcbf43926)
  })

  it('is zero for empty input', () => {
    expect(crc32(new Uint8Array())).toBe(0)
  })
})

describe('buildZip', () => {
  it('starts with the local file header signature', () => {
    const zip = buildZip([{ name: 'a.md', text: 'hello' }], FIXED)
    expect(u32(zip, 0)).toBe(0x04034b50)
  })

  it('ends with the end-of-central-directory record naming every entry', () => {
    const zip = buildZip(
      [
        { name: 'compliance-act.md', text: 'one' },
        { name: 'compliance-know.md', text: 'two' },
        { name: 'regulation-act.md', text: 'three' },
      ],
      FIXED
    )
    const end = zip.length - 22
    expect(u32(zip, end)).toBe(0x06054b50)
    expect(u16(zip, end + 8)).toBe(3)
    expect(u16(zip, end + 10)).toBe(3)
  })

  it('stores rather than compresses, so sizes match the text', () => {
    const text = 'a week of briefing text'
    const zip = buildZip([{ name: 'a.md', text }], FIXED)
    expect(u16(zip, 8)).toBe(0) // method 0 = stored
    expect(u32(zip, 18)).toBe(text.length) // compressed size
    expect(u32(zip, 22)).toBe(text.length) // uncompressed size
  })

  it('records the checksum of each entry', () => {
    const text = '123456789'
    const zip = buildZip([{ name: 'a.md', text }], FIXED)
    expect(u32(zip, 14)).toBe(0xcbf43926)
  })

  it('marks names as UTF-8 so a non-ascii filename survives', () => {
    const zip = buildZip([{ name: 'super-tax.md', text: 'x' }], FIXED)
    expect(u16(zip, 6) & 0x0800).toBe(0x0800)
  })

  it('produces a valid empty archive when there is nothing to write', () => {
    const zip = buildZip([], FIXED)
    expect(zip.length).toBe(22)
    expect(u32(zip, 0)).toBe(0x06054b50)
    expect(u16(zip, 8)).toBe(0)
  })
})
