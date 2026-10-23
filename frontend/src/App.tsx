import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { wakeServer } from './api/client'
import type { TripInput } from './api/types'
import { ForecastSlider } from './features/forecast-slider/ForecastSlider'
import { ResultsPanel } from './features/results/ResultsPanel'
import { TripForm } from './features/trip-form/TripForm'
import { useTripAnalysis } from './hooks/useTripAnalysis'
import { THRESHOLDS } from './lib/risk'

// MapLibre is the bulk of the bundle; load it after the form is interactive.
const MapView = lazy(() => import('./features/map/MapView').then((m) => ({ default: m.MapView })))

const STAGES = ['Finding routes…', 'Sampling weather along each route…', 'Scoring risk and ranking routes…']
const STAGE_MS = 4000

/** Mounted only while a request is running, so its stage always starts from the first. */
function Progress() {
  const [stage, setStage] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), STAGE_MS)
    return () => clearInterval(id)
  }, [])
  return <p className="progress" role="status">{STAGES[stage]}</p>
}

export default function App() {
  const { state, run } = useTripAnalysis()
  const { analysis, heatmap, heatmapStatus, busy, error, fieldErrors } = state
  const [picked, setPicked] = useState<string | null>(null)
  const [hour, setHour] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [showHeat, setShowHeat] = useState(true)

  useEffect(() => void wakeServer(), [])

  // the recommended route (or the first) unless the user picked another one for this analysis
  const selected = analysis
    ? (analysis.routes.some((r) => r.id === picked) ? picked : (analysis.recommended_route_id ?? analysis.routes[0]?.id ?? null))
    : null

  const submit = useCallback(
    (trip: TripInput) => {
      setPicked(null)
      setHour(0)
      setPlaying(false)
      run(trip)
    },
    [run],
  )

  return (
    <div className="app">
      <aside className="panel">
        <header className="brand">
          <span className="mark" aria-hidden />
          <h1>Spotter Route Finder</h1>
        </header>
        <p className="lede">Compare three routes by forecast weather at the time you will be there.</p>
        <TripForm busy={busy} fieldErrors={fieldErrors} onSubmit={submit} />
        {busy && <Progress />}
        {error && <p className="alert" role="alert">{error}</p>}
        {analysis && selected && <ResultsPanel analysis={analysis} selectedId={selected} onSelect={setPicked} />}
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
        <Suspense fallback={<div className="map" aria-busy="true" />}>
          <MapView analysis={analysis} selectedId={selected} onSelect={setPicked} heatmap={heatmap} hour={hour} showHeat={showHeat} />
        </Suspense>
        <div className="overlay">
          {heatmapStatus === 'loading' && <p className="muted">Loading forecast heatmap…</p>}
          {heatmapStatus === 'failed' && <p className="muted">The forecast heatmap is unavailable right now.</p>}
          {heatmap && (
            <>
              <label className="toggle">
                <input type="checkbox" checked={showHeat} onChange={(e) => setShowHeat(e.target.checked)} />
                Weather heatmap, next 48 h
              </label>
              {showHeat && <ForecastSlider hours={heatmap.hours} hour={hour} playing={playing} onHour={setHour} onPlaying={setPlaying} />}
            </>
          )}
          {!analysis && !busy && !heatmap && <p className="muted">Enter a trip to see routes and the weather along them.</p>}
        </div>
      </main>
    </div>
  )
}
