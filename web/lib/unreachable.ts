/**
 * Sources worth reading that the monitor cannot fetch: paywalled, blocking
 * automated readers, or with no feed. Listed so they are read by hand, not
 * forgotten. The tool only links to them; opening one is always you.
 *
 * `checked` is the date the reason was confirmed by a probe. Without it the
 * reason is expected, not tested.
 */

export type UnreachableReason = 'paywall' | 'blocks-bots' | 'no-feed'

export interface UnreachableSource {
  name: string
  url: string
  reason: UnreachableReason
  why: string
  checked?: string
}

export const REASON_LABEL: Record<UnreachableReason, string> = {
  paywall: 'Paywall',
  'blocks-bots': 'Blocks automated readers',
  'no-feed': 'No feed',
}

export const UNREACHABLE_SOURCES: UnreachableSource[] = [
  // Paywalled
  { name: 'Australian Financial Review', url: 'https://www.afr.com/wealth', reason: 'paywall', why: 'Breaks advice, super and ASIC stories first. The biggest gap.' },
  { name: 'The Australian, Business', url: 'https://www.theaustralian.com.au/business', reason: 'paywall', why: 'Super funds, banks and the politics behind reform.' },
  { name: 'Financial Times', url: 'https://www.ft.com', reason: 'paywall', why: 'Global markets and banks.', checked: '25 Sep 2026' },
  { name: 'Bloomberg', url: 'https://www.bloomberg.com/australia', reason: 'paywall', why: 'Global markets and fund flows.' },
  { name: 'Wall Street Journal', url: 'https://www.wsj.com', reason: 'paywall', why: 'US markets and regulation that flows through to Australia.' },
  { name: 'Sydney Morning Herald, Money', url: 'https://www.smh.com.au/money', reason: 'paywall', why: 'Consumer finance: what clients are reading. A few free articles, then paid.' },
  { name: 'Reuters', url: 'https://www.reuters.com/world/asia-pacific/', reason: 'paywall', why: 'Wire news. Partly paywalled and no public feeds.' },
  { name: 'Morningstar', url: 'https://www.morningstar.com.au', reason: 'paywall', why: 'Fund research and ratings. Media releases are free.' },
  { name: 'Lonsec', url: 'https://www.lonsec.com.au', reason: 'paywall', why: 'Product ratings used on approved product lists.' },
  { name: 'Zenith', url: 'https://www.zenithpartners.com.au', reason: 'paywall', why: 'Product ratings used on approved product lists.' },
  { name: 'Chant West', url: 'https://www.chantwest.com.au', reason: 'paywall', why: 'Super fund performance and ratings.' },
  { name: 'SuperRatings', url: 'https://www.superratings.com.au', reason: 'paywall', why: 'Super fund performance and ratings.' },
  { name: 'Rainmaker', url: 'https://www.rainmaker.com.au', reason: 'paywall', why: 'Super and funds market data.' },
  { name: 'Adviser Ratings', url: 'https://www.adviserratings.com.au', reason: 'paywall', why: 'Adviser numbers, fees and the industry landscape report.' },
  { name: 'Intelligent Investor', url: 'https://www.intelligentinvestor.com.au', reason: 'paywall', why: 'Investor newsletter: what self-directed clients act on.' },
  { name: 'Eureka Report', url: 'https://www.eurekareport.com.au', reason: 'paywall', why: 'Investor newsletter: what self-directed clients act on.' },

  // Free, but blocking automated readers
  { name: 'AFCA determinations', url: 'https://www.afca.org.au/what-to-expect/search-published-decisions', reason: 'blocks-bots', why: 'How complaints against advisers are decided.', checked: '25 Sep 2026' },
  { name: 'ACCC media releases', url: 'https://www.accc.gov.au/news-centre', reason: 'blocks-bots', why: 'Consumer law, scams and unfair contract terms.', checked: '25 Sep 2026' },
  { name: 'Scamwatch', url: 'https://www.scamwatch.gov.au', reason: 'blocks-bots', why: 'Scams hitting clients, including investment scams.', checked: '25 Sep 2026' },
  { name: 'AustLII', url: 'https://www.austlii.edu.au', reason: 'blocks-bots', why: 'Free case law, including advice and ASIC cases.' },

  // Free, no feed
  { name: 'ASIC media releases', url: 'https://www.asic.gov.au/about-asic/news-centre/find-a-media-release/', reason: 'no-feed', why: 'Enforcement, bans and new rules. Check weekly.', checked: '25 Sep 2026' },
  { name: 'Financial Advisers Register', url: 'https://moneysmart.gov.au/financial-advice/financial-advisers-register', reason: 'no-feed', why: 'Adviser bans and new entrants.' },
  { name: 'Moneysmart', url: 'https://moneysmart.gov.au', reason: 'no-feed', why: 'ASIC consumer guidance clients will quote back.', checked: '25 Sep 2026' },
  { name: 'ATO media centre', url: 'https://www.ato.gov.au/about-ato/media-centre', reason: 'no-feed', why: 'Tax and SMSF rulings.', checked: '25 Sep 2026' },
  { name: 'Treasury consultations', url: 'https://treasury.gov.au/consultation', reason: 'no-feed', why: 'Advice reform drafts before they become law. Feed exists but is empty.', checked: '25 Sep 2026' },
  { name: 'APRA media releases', url: 'https://www.apra.gov.au/news-and-publications', reason: 'no-feed', why: 'Super fund enforcement. The APRA feed only carries statistics.', checked: '25 Sep 2026' },
  { name: 'AUSTRAC', url: 'https://www.austrac.gov.au/news-and-media', reason: 'no-feed', why: 'AML/CTF obligations reaching advice practices.', checked: '25 Sep 2026' },
  { name: 'ABS releases', url: 'https://www.abs.gov.au', reason: 'no-feed', why: 'CPI, wages and household data.', checked: '25 Sep 2026' },
  { name: 'Consumer Data Right', url: 'https://www.cdr.gov.au/news', reason: 'no-feed', why: 'Open banking rules and advice data sharing.', checked: '25 Sep 2026' },
  { name: 'Federal Court judgments', url: 'https://www.judgments.fedcourt.gov.au', reason: 'no-feed', why: 'ASIC cases won and lost.' },
  { name: 'Administrative Review Tribunal', url: 'https://www.art.gov.au', reason: 'no-feed', why: 'Appeals against ASIC adviser bans.' },
  { name: 'Senate Economics Committee', url: 'https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Economics', reason: 'no-feed', why: 'Inquiries into advice, super and scams.' },
  { name: 'Federal Register of Legislation', url: 'https://www.legislation.gov.au', reason: 'no-feed', why: 'Where new regulations and ASIC instruments are published.' },
  { name: 'Productivity Commission', url: 'https://www.pc.gov.au', reason: 'no-feed', why: 'Super and retirement reviews.' },
  { name: 'SMSF Association', url: 'https://www.smsfassociation.com', reason: 'no-feed', why: 'SMSF policy and technical updates. Much is members only.' },
  { name: 'Actuaries Institute', url: 'https://www.actuaries.asn.au', reason: 'no-feed', why: 'Retirement income and insurance research.' },
  { name: 'Holley Nethercote', url: 'https://hnlaw.com.au', reason: 'no-feed', why: 'Plain-English legal updates for licensees. Email signup.' },
  { name: 'Allens insights', url: 'https://www.allens.com.au/insights-news/', reason: 'no-feed', why: 'Financial services law updates. Email signup.' },
]

/** The prompt to paste above an article you copied in yourself. */
export const PASTE_PROMPT = `Summarise the article below for an Australian financial adviser.
Use ONLY the text I have pasted. Do not fetch or look up anything else.
Give: 1) what changed, 2) who it affects, 3) whether an adviser must act, and by when.
If the text is too thin to answer, say so.

[paste the article text here]`
