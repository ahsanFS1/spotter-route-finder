import { useState } from 'react'
import type { Analysis, Route } from '../../api/types'
import { formatDateTime, formatDuration, formatMiles } from '../../lib/format'
import { levelColor, levelLabel } from '../../lib/risk'
import { CheckpointTable } from './CheckpointTable'
import { RiskBar } from './RiskBar'

interface Props {
  analysis: Analysis
  selectedId: string
  onSelect: (id: string) => void
}

function RouteCard({ route, selected, onSelect }: { route: Route; selected: boolean; onSelect: () => void }) {
  const [showTable, setShowTable] = useState(false)
  const m = route.metrics
  return (
    <article className={`route-card${selected ? ' selected' : ''}`} aria-current={selected}>
      <button type="button" className="route-head" onClick={onSelect} aria-pressed={selected}>
        <span className="route-name">
          {route.label}
          {route.recommended && <span className="badge">Recommended</span>}
          {m.has_no_travel && <span className="badge danger">No travel</span>}
        </span>
        <span className="route-time">{formatDuration(route.duration_s)}</span>
      </button>
      <p className="route-sub">
        {formatMiles(route.distance_mi)} · arrive {formatDateTime(route.arrival)}
      </p>
      <RiskBar metrics={m} />
      <dl className="stats">
        <div><dt>Severe</dt><dd>{m.miles_by_level.severe + m.miles_by_level.no_travel} mi</dd></div>
        <div><dt>High</dt><dd>{m.miles_by_level.high} mi</dd></div>
        <div><dt>Avg risk</dt><dd>{m.scored_miles ? m.avg_risk.toFixed(2) : '–'}</dd></div>
        <div>
          <dt>Worst</dt>
          <dd>
            <span className="dot" style={{ background: levelColor(m.max_level) }} aria-hidden />
            {levelLabel(m.max_level)}
          </dd>
        </div>
      </dl>
      {m.unscored_miles > 0 && <p className="note">{formatMiles(m.unscored_miles)} have no forecast and are not scored.</p>}
      {selected && (
        <>
          <button type="button" className="link" aria-expanded={showTable} onClick={() => setShowTable((v) => !v)}>
            {showTable ? 'Hide' : 'Show'} {route.checkpoints.length} checkpoints
          </button>
          {showTable && <CheckpointTable route={route} />}
        </>
      )}
    </article>
  )
}

export function ResultsPanel({ analysis, selectedId, onSelect }: Props) {
  const ordered = [...analysis.routes].sort((a, b) => a.rank - b.rank)
  return (
    <section className="results" aria-label="Route results">
      <div className={`verdict${analysis.recommended_route_id ? '' : ' danger'}`}>
        <h2>
          {analysis.recommended_route_id
            ? `Take ${analysis.routes.find((r) => r.id === analysis.recommended_route_id)?.label}`
            : 'Do not depart on any route'}
        </h2>
        <p>{analysis.reason}</p>
      </div>
      {analysis.warnings.map((w) => (
        <p className="warning" key={w}>{w}</p>
      ))}
      {ordered.map((r) => (
        <RouteCard key={r.id} route={r} selected={r.id === selectedId} onSelect={() => onSelect(r.id)} />
      ))}
    </section>
  )
}
