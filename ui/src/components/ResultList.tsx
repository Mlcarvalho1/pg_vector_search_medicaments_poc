import type { SearchResponse } from '../api/search'
import { ResultCard } from './ResultCard'
import styles from './ResultList.module.css'

interface Props {
  response: SearchResponse
}

export function ResultList({ response }: Props) {
  const { query, mode, exclusions, results } = response

  return (
    <div className={styles.wrapper}>
      <div className={styles.meta}>
        <span>
          <strong>{results.length}</strong> resultado{results.length !== 1 ? 's' : ''} para{' '}
          <em>"{query}"</em>
        </span>
        {exclusions.length > 0 && (
          <span className={styles.exclusions}>
            Excluindo: {exclusions.map((e) => <code key={e}>{e}</code>)}
          </span>
        )}
      </div>

      {results.length === 0 ? (
        <p className={styles.empty}>Nenhum resultado encontrado.</p>
      ) : (
        <ul className={styles.list}>
          {results.map((r) => (
            <li key={r.id}>
              <ResultCard result={r} mode={mode} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
