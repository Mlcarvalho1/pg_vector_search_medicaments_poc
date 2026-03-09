import { type FormEvent, useRef } from 'react'
import styles from './SearchBar.module.css'

interface Props {
  onSearch: (query: string) => void
  loading?: boolean
}

export function SearchBar({ onSearch, loading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const q = inputRef.current?.value.trim()
    if (q) onSearch(q)
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <input
        ref={inputRef}
        className={styles.input}
        type="text"
        placeholder="ex: antibiótico para crianças, alérgico a penicilina…"
        disabled={loading}
        autoFocus
      />
      <button className={styles.button} type="submit" disabled={loading}>
        {loading ? <span className={styles.spinner} /> : 'Buscar'}
      </button>
    </form>
  )
}
