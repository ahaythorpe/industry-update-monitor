/**
 * A minimal ZIP writer, so a grouped briefing downloads as a folder.
 *
 * One Markdown file per group is the useful shape — compliance-act.md opens
 * in its own tab and pastes as one chat message — but a browser can only hand
 * over one file at a time. A zip is that folder.
 *
 * Written here rather than pulled in: the whole job is to concatenate a few
 * small text files with headers around them, and the project has kept its
 * dependency list to Next, React and Supabase. Entries are STORED, not
 * deflated — Markdown compresses well, but adding a compressor would mean
 * shipping one, and a week's briefing is tens of kilobytes either way.
 */

const CRC_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let n = 0; n < 256; n += 1) {
    let c = n
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    table[n] = c >>> 0
  }
  return table
})()

export function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff
  for (let i = 0; i < bytes.length; i += 1) crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

/** MS-DOS date and time, the only clock the ZIP format understands. */
function dosStamp(date: Date): { time: number; date: number } {
  return {
    time: (date.getHours() << 11) | (date.getMinutes() << 5) | (Math.floor(date.getSeconds() / 2)),
    // DOS counts years from 1980 and months from 1.
    date: ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate(),
  }
}

export type ZipEntry = { name: string; text: string }

/**
 * Build a ZIP archive of UTF-8 text files.
 *
 * Names are taken as given — the caller already slugs them — and the UTF-8
 * name flag is set so a non-ASCII one still unpacks correctly.
 */
export function buildZip(entries: ZipEntry[], modified = new Date()): Uint8Array<ArrayBuffer> {
  const encoder = new TextEncoder()
  const stamp = dosStamp(modified)

  const local: Uint8Array[] = []
  const central: Uint8Array[] = []
  let offset = 0

  entries.forEach((entry) => {
    const name = encoder.encode(entry.name)
    const body = encoder.encode(entry.text)
    const crc = crc32(body)

    const header = new DataView(new ArrayBuffer(30))
    header.setUint32(0, 0x04034b50, true) // local file header
    header.setUint16(4, 20, true) // version needed
    header.setUint16(6, 0x0800, true) // names are UTF-8
    header.setUint16(8, 0, true) // stored, not deflated
    header.setUint16(10, stamp.time, true)
    header.setUint16(12, stamp.date, true)
    header.setUint32(14, crc, true)
    header.setUint32(18, body.length, true)
    header.setUint32(22, body.length, true)
    header.setUint16(26, name.length, true)
    header.setUint16(28, 0, true) // no extra field

    local.push(new Uint8Array(header.buffer), name, body)

    const entryRecord = new DataView(new ArrayBuffer(46))
    entryRecord.setUint32(0, 0x02014b50, true) // central directory header
    entryRecord.setUint16(4, 20, true) // version made by
    entryRecord.setUint16(6, 20, true) // version needed
    entryRecord.setUint16(8, 0x0800, true)
    entryRecord.setUint16(10, 0, true)
    entryRecord.setUint16(12, stamp.time, true)
    entryRecord.setUint16(14, stamp.date, true)
    entryRecord.setUint32(16, crc, true)
    entryRecord.setUint32(20, body.length, true)
    entryRecord.setUint32(24, body.length, true)
    entryRecord.setUint16(28, name.length, true)
    entryRecord.setUint16(30, 0, true) // extra
    entryRecord.setUint16(32, 0, true) // comment
    entryRecord.setUint16(34, 0, true) // disk number
    entryRecord.setUint16(36, 0, true) // internal attributes
    entryRecord.setUint32(38, 0, true) // external attributes
    entryRecord.setUint32(42, offset, true)

    central.push(new Uint8Array(entryRecord.buffer), name)
    offset += 30 + name.length + body.length
  })

  const centralSize = central.reduce((total, part) => total + part.length, 0)

  const end = new DataView(new ArrayBuffer(22))
  end.setUint32(0, 0x06054b50, true) // end of central directory
  end.setUint16(4, 0, true) // this disk
  end.setUint16(6, 0, true) // disk with the central directory
  end.setUint16(8, entries.length, true)
  end.setUint16(10, entries.length, true)
  end.setUint32(12, centralSize, true)
  end.setUint32(16, offset, true)
  end.setUint16(20, 0, true) // no archive comment

  const parts = [...local, ...central, new Uint8Array(end.buffer)]
  const archive = new Uint8Array(
    new ArrayBuffer(parts.reduce((total, part) => total + part.length, 0))
  )
  let at = 0
  parts.forEach((part) => {
    archive.set(part, at)
    at += part.length
  })
  return archive
}
