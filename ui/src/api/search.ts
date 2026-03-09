export type SearchMode = 'semantic' | 'hybrid'

export interface SearchResult {
  rank: number
  id: number
  name: string
  description: string | null
  score: number
}

export interface SearchResponse {
  query: string
  mode: SearchMode
  exclusions: string[]
  results: SearchResult[]
}

export async function runSearch(
  query: string,
  mode: SearchMode,
  limit = 10,
): Promise<SearchResponse> {
  const endpoint = mode === 'hybrid' ? '/search/hybrid' : '/search'
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API error ${res.status}: ${detail}`)
  }
  return res.json()
}
