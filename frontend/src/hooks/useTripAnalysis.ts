import { useCallback, useRef, useState } from 'react'
import { analyzeTrip, ApiError, fetchHeatmap } from '../api/client'
import type { Analysis, Heatmap, TripInput } from '../api/types'

export interface TripState {
  trip: TripInput | null
  analysis: Analysis | null
  heatmap: Heatmap | null
  heatmapStatus: 'idle' | 'loading' | 'ready' | 'failed'
  busy: boolean
  error: string | null
  fieldErrors: Record<string, string[]>
}

const INITIAL: TripState = {
  trip: null,
  analysis: null,
  heatmap: null,
  heatmapStatus: 'idle',
  busy: false,
  error: null,
  fieldErrors: {},
}

/**
 * Runs the route analysis, then the forecast heatmap. They share one weather API with a per-minute
 * allowance, so they are sequential; the results show as soon as the analysis finishes.
 */
export function useTripAnalysis() {
  const [state, setState] = useState<TripState>(INITIAL)
  const controller = useRef<AbortController | null>(null)

  const run = useCallback((trip: TripInput) => {
    controller.current?.abort()
    const ctl = new AbortController()
    controller.current = ctl
    setState({ ...INITIAL, trip, busy: true, heatmapStatus: 'loading' })

    analyzeTrip(trip, ctl.signal)
      .then((analysis) => {
        setState((s) => ({ ...s, analysis, busy: false }))
        return fetchHeatmap(trip, ctl.signal)
          .then((heatmap) => setState((s) => ({ ...s, heatmap, heatmapStatus: 'ready' })))
          .catch(() => !ctl.signal.aborted && setState((s) => ({ ...s, heatmapStatus: 'failed' })))
      })
      .catch((err) => {
        if (ctl.signal.aborted) return
        setState((s) => ({
          ...s,
          busy: false,
          heatmapStatus: 'idle',
          error: err instanceof ApiError ? err.message : 'Something went wrong. Please try again.',
          fieldErrors: err instanceof ApiError ? err.fields : {},
        }))
      })
  }, [])

  return { state, run }
}
