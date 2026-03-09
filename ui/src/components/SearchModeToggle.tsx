import type { SearchMode } from '../api/search'
import styles from './SearchModeToggle.module.css'

interface Props {
  mode: SearchMode
  onChange: (mode: SearchMode) => void
  disabled?: boolean
}

const MODES: { value: SearchMode; label: string; title: string }[] = [
  {
    value: 'semantic',
    label: 'Semântica',
    title: 'Busca por similaridade vetorial — entende o significado da consulta',
  },
  {
    value: 'hybrid',
    label: 'Híbrida',
    title: 'Combina busca vetorial + texto completo (RRF) e detecta exclusões por alergia',
  },
]

export function SearchModeToggle({ mode, onChange, disabled }: Props) {
  return (
    <div className={styles.toggle}>
      {MODES.map((m) => (
        <button
          key={m.value}
          className={`${styles.btn} ${mode === m.value ? styles.active : ''}`}
          onClick={() => onChange(m.value)}
          disabled={disabled}
          title={m.title}
          type="button"
        >
          {m.label}
        </button>
      ))}
    </div>
  )
}
