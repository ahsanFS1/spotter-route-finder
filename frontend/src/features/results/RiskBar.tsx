import type { RouteMetrics } from '../../api/types'
import { LEVELS } from '../../lib/risk'

/** Miles at each risk level as one flat bar. */
export function RiskBar({ metrics }: { metrics: RouteMetrics }) {
  const total = metrics.scored_miles + metrics.unscored_miles || 1
  return (
    <div className="riskbar" role="img" aria-label={LEVELS.map((l) => `${l.label} ${metrics.miles_by_level[l.key as keyof RouteMetrics['miles_by_level']]} miles`).join(', ')}>
      {LEVELS.map((l) => {
        const mi = metrics.miles_by_level[l.key as keyof RouteMetrics['miles_by_level']]
        return mi > 0 ? <span key={l.key} style={{ width: `${(mi / total) * 100}%`, background: l.color }} /> : null
      })}
      {metrics.unscored_miles > 0 && <span className="unscored" style={{ width: `${(metrics.unscored_miles / total) * 100}%` }} />}
    </div>
  )
}
