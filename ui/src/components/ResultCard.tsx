import type { SearchResult, SearchMode } from '../api/search'
import styles from './ResultCard.module.css'

interface Props {
  result: SearchResult
  mode: SearchMode
}

export function ResultCard({ result, mode }: Props) {
  const scoreLabel = mode === 'hybrid' ? 'RRF' : 'sim'
  const desc = result.description?.replace(/\n/g, ' ') ?? ''
  const preview = desc.length > 160 ? desc.slice(0, 160) + '…' : desc

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.rank}>#{result.rank}</span>
        <span className={styles.name}>{result.name}</span>
        <span className={styles.score} title={`${scoreLabel}: ${result.score}`}>
          {scoreLabel} {result.score.toFixed(4)}
        </span>
      </div>
      {preview && <p className={styles.description}>{preview}</p>}
    </div>
  )
}
