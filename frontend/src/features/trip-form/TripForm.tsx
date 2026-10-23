import { useState } from 'react'
import type { Place, TripInput } from '../../api/types'
import { defaultDeparture } from '../../lib/format'
import { PlaceInput } from './PlaceInput'

const INTERVALS = [10, 25, 50] as const
const MAX_LOAD_LB = 150_000

interface Props {
  busy: boolean
  fieldErrors: Record<string, string[]>
  onSubmit: (trip: TripInput) => void
}

export function TripForm({ busy, fieldErrors, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(defaultDeparture)
  const [load, setLoad] = useState('42000')
  const [interval, setInterval] = useState<10 | 25 | 50>(25)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const next: Record<string, string> = {}
    const loadLb = Number(load)
    if (!origin) next.origin = 'Choose a starting point from the suggestions.'
    if (!destination) next.destination = 'Choose a destination from the suggestions.'
    if (!departure || Number.isNaN(new Date(departure).getTime())) next.departure = 'Enter a departure date and time.'
    if (!load || !Number.isFinite(loadLb) || loadLb < 0 || loadLb > MAX_LOAD_LB)
      next.load = `Enter a weight between 0 and ${MAX_LOAD_LB.toLocaleString()} lb.`
    setErrors(next)
    if (Object.keys(next).length || !origin || !destination) return
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lb: loadLb,
      interval_mi: interval,
    })
  }

  const serverError = (name: string) => fieldErrors[name]?.[0]

  return (
    <form className="trip-form" onSubmit={submit} noValidate>
      <PlaceInput label="From" value={origin} onChange={setOrigin} error={errors.origin ?? serverError('origin')} />
      <PlaceInput
        label="To"
        value={destination}
        onChange={setDestination}
        error={errors.destination ?? serverError('destination')}
      />
      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            onChange={(e) => setDeparture(e.target.value)}
            aria-invalid={Boolean(errors.departure ?? serverError('departure'))}
          />
          {(errors.departure ?? serverError('departure')) && (
            <p className="error">{errors.departure ?? serverError('departure')}</p>
          )}
        </div>
        <div className="field">
          <label htmlFor="load">Load (lb)</label>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={0}
            max={MAX_LOAD_LB}
            step={500}
            value={load}
            onChange={(e) => setLoad(e.target.value)}
            aria-invalid={Boolean(errors.load ?? serverError('load_lb'))}
          />
          {(errors.load ?? serverError('load_lb')) && <p className="error">{errors.load ?? serverError('load_lb')}</p>}
        </div>
      </div>
      <fieldset className="field">
        <legend>Weather check every</legend>
        <div className="segmented" role="radiogroup">
          {INTERVALS.map((mi) => (
            <label key={mi} className={interval === mi ? 'selected' : undefined}>
              <input type="radio" name="interval" value={mi} checked={interval === mi} onChange={() => setInterval(mi)} />
              {mi} mi
            </label>
          ))}
        </div>
      </fieldset>
      <button type="submit" className="primary" disabled={busy}>
        {busy ? 'Analyzing routes…' : 'Find safest route'}
      </button>
    </form>
  )
}
