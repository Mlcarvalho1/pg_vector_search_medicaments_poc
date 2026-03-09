import { useState } from 'react'
import { runSearch } from './api/search'
import type { SearchMode, SearchResponse } from './api/search'
import { SearchBar } from './components/SearchBar'
import { SearchModeToggle } from './components/SearchModeToggle'
import { ResultList } from './components/ResultList'
import styles from './App.module.css'

export default function App() {
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch(query: string) {
    setLoading(true)
    setError(null)
    try {
      const res = await runSearch(query, mode)
      setResponse(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro desconhecido')
      setResponse(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Busca de Medicamentos</h1>
        <p className={styles.subtitle}>Pesquisa semântica e híbrida sobre a base de medicamentos</p>
      </header>

      <main className={styles.main}>
        <div className={styles.controls}>
          <SearchModeToggle mode={mode} onChange={setMode} disabled={loading} />
        </div>

        <SearchBar onSearch={handleSearch} loading={loading} />

        {error && <div className={styles.error}>{error}</div>}

        {response && <ResultList response={response} />}
      </main>
    </div>
  )
}
