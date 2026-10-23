import { useCallback, useEffect, useState } from 'react'
import { wakeServer } from './api/client'
import { ForecastSlider } from './features/forecast-slider/ForecastSlider'
import { MapView } from './features/map/MapView'
import { ResultsPanel } from './features/results/ResultsPanel'
import { TripForm } from './features/trip-form/TripForm'
import { useTripAnalysis } from './hooks/useTripAnalysis'
import { THRESHOLDS } from './lib/risk'

const STAGES = ['Finding routes…', 'Sampling weather along each route…', 'Scoring risk and ranking routes…']

function useStage(active: boolean) {
  const [stage, setStage] = useState(0)
  useEffect(() => {
    if (!active) return setStage(0)
    const id = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 4000)
    return () => clearInterval(id)
  }, [active])
  return STAGES[stage]
}

export default function App() {
  const { state, run } = useTripAnalysis()
  const { analysis, heatmap, heatmapStatus, busy, error, fieldErrors } = state
  const [selected, setSelected] = useState<string | null>(null)
  const [hour, setHour] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [showHeat, setShowHeat] = useState(true)
  const stage = useStage(busy)

  useEffect(() => void wakeServer(), [])

  // pick the recommended route (or the fastest if none) whenever a new analysis arrives
  useEffect(() => {
    if (!analysis) return setSelected(null)
    setSelected(analysis.recommended_route_id ?? analysis.routes[0]?.id ?? null)
    setHour(0)
    setPlaying(false)
  }, [analysis])

  const changeHour = useCallback((h: number) => setHour(h), [])

  return (
    <div className="app">
      <aside className="panel">
        <header className="brand">
          <span className="mark" aria-hidden />
          <h1>Spotter Route Finder</h1>
        </header>
        <p className="lede">Compare three routes by forecast weather at the time you will be there.</p>
        <TripForm busy={busy} fieldErrors={fieldErrors} onSubmit={run} />
        {busy && <p className="progress" role="status">{stage}</p>}
        {error && <p className="alert" role="alert">{error}</p>}
        {analysis && selected && <ResultsPanel analysis={analysis} selectedId={selected} onSelect={setSelected} />}
        <details className="rules">
          <summary>How risk is scored</summary>
          <table>
            <thead>
              <tr><th scope="col" />{['Low', 'Moderate', 'High', 'Severe', 'No travel'].map((l) => <th scope="col" key={l}>{l}</th>)}</tr>
            </thead>
            <tbody>
              {THRESHOLDS.map((t) => (
                <tr key={t.condition}><th scope="row">{t.condition}</th>{t.bands.map((b) => <td key={b}>{b}</td>)}</tr>
              ))}
            </tbody>
          </table>
          <p>
            Each checkpoint takes its worst condition. Wind of 55 mph or more is No Travel for any load. Wind of 45–54 mph is
            No Travel above 30,000 lb. Wind of 35–44 mph is Severe above 40,000 lb. Routes are ranked by fewest Severe
            miles, then High miles, then average risk, then travel time.
          </p>
        </details>
      </aside>
      <main className="stage">
        <MapView analysis={analysis} selectedId={selected} onSelect={setSelected} heatmap={heatmap} hour={hour} showHeat={showHeat} />
        <div className="overlay">
          {heatmapStatus === 'loading' && <p className="muted">Loading forecast heatmap…</p>}
          {heatmapStatus === 'failed' && <p className="muted">The forecast heatmap is unavailable right now.</p>}
          {heatmap && (
            <>
              <label className="toggle">
                <input type="checkbox" checked={showHeat} onChange={(e) => setShowHeat(e.target.checked)} />
                Weather heatmap, next 48 h
              </label>
              {showHeat && <ForecastSlider hours={heatmap.hours} hour={hour} playing={playing} onHour={changeHour} onPlaying={setPlaying} />}
            </>
          )}
          {!analysis && !busy && !heatmap && <p className="muted">Enter a trip to see routes and the weather along them.</p>}
        </div>
      </main>
    </div>
  )
}
