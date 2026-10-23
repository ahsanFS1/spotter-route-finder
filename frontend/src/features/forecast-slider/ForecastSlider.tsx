import { useEffect, useRef } from 'react'
import { formatHour } from '../../lib/format'
import { LEVELS } from '../../lib/risk'

interface Props {
  hours: string[]
  hour: number
  playing: boolean
  onHour: (h: number) => void
  onPlaying: (p: boolean) => void
}

const STEP_MS = 450

export function ForecastSlider({ hours, hour, playing, onHour, onPlaying }: Props) {
  const current = useRef(hour)
  useEffect(() => {
    current.current = hour
  }, [hour])

  useEffect(() => {
    if (!playing) return
    const id = setInterval(() => onHour((current.current + 1) % hours.length), STEP_MS)
    return () => clearInterval(id)
  }, [playing, hours.length, onHour])

  return (
    <div className="forecast">
      <div className="forecast-top">
        <button type="button" className="icon-btn" onClick={() => onPlaying(!playing)} aria-label={playing ? 'Pause forecast' : 'Play forecast'}>
          {playing ? '❚❚' : '▶'}
        </button>
        <div>
          <strong>{formatHour(hours[hour])}</strong>
          <span className="muted"> · {hour === 0 ? 'at departure' : `+${hour} h after departure`}</span>
        </div>
      </div>
      <input
        type="range"
        min={0}
        max={hours.length - 1}
        step={1}
        value={hour}
        onChange={(e) => onHour(Number(e.target.value))}
        aria-label="Forecast hour after departure"
        aria-valuetext={`${formatHour(hours[hour])}, ${hour} hours after departure`}
      />
      <div className="legend" aria-label="Risk legend">
        {LEVELS.map((l) => (
          <span key={l.key}><i style={{ background: l.color }} />{l.label}</span>
        ))}
      </div>
    </div>
  )
}
