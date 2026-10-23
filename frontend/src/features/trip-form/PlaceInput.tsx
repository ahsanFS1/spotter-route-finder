import { useEffect, useId, useRef, useState } from 'react'
import { searchPlaces } from '../../api/client'
import type { Place, Suggestion } from '../../api/types'

const MIN_CHARS = 3
const DEBOUNCE_MS = 300

interface Props {
  label: string
  value: Place | null
  onChange: (place: Place | null) => void
  error?: string
}

export function PlaceInput({ label, value, onChange, error }: Props) {
  const id = useId()
  const [text, setText] = useState(value?.label ?? '')
  const [options, setOptions] = useState<Suggestion[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [status, setStatus] = useState<'idle' | 'loading' | 'empty' | 'failed'>('idle')
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const query = text.trim()
    if (value || query.length < MIN_CHARS) {
      setOptions([])
      setStatus('idle')
      return
    }
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setStatus('loading')
      try {
        const found = await searchPlaces(query, controller.signal)
        setOptions(found)
        setStatus(found.length ? 'idle' : 'empty')
        setActive(-1)
      } catch (err) {
        if (!(err instanceof DOMException && err.name === 'AbortError')) setStatus('failed')
      }
    }, DEBOUNCE_MS)
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [text, value])

  useEffect(() => {
    const close = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const choose = (place: Suggestion) => {
    setText(place.label)
    onChange(place)
    setOpen(false)
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || !options.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => (i + 1) % options.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => (i <= 0 ? options.length - 1 : i - 1))
    } else if (e.key === 'Enter' && active >= 0) {
      e.preventDefault()
      choose(options[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const showList = open && !value && (options.length > 0 || status !== 'idle')

  return (
    <div className="field" ref={box}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        autoComplete="off"
        role="combobox"
        aria-expanded={showList}
        aria-controls={`${id}-list`}
        aria-activedescendant={active >= 0 ? `${id}-opt-${active}` : undefined}
        aria-invalid={Boolean(error)}
        placeholder="City, address or place"
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          setOpen(true)
          if (value) onChange(null) // editing invalidates the chosen place
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul className="suggestions" id={`${id}-list`} role="listbox">
          {options.map((o, i) => (
            <li
              key={`${o.lat},${o.lng}`}
              id={`${id}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'active' : undefined}
              onMouseDown={(e) => {
                e.preventDefault()
                choose(o)
              }}
            >
              {o.label}
            </li>
          ))}
          {status === 'loading' && <li className="note">Searching…</li>}
          {status === 'empty' && <li className="note">No matches in the US, Canada or Mexico.</li>}
          {status === 'failed' && <li className="note">Search is unavailable. Try again in a moment.</li>}
        </ul>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
