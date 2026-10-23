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

/** Runs the route analysis and the forecast heatmap in parallel; the heatmap never blocks the results. */
export function useTripAnalysis() {
  const [state, setState] = useState<TripState>(INITIAL)
  const controller = useRef<AbortController | null>(null)

  const run = useCallback((trip: TripInput) => {
    controller.current?.abort()
    const ctl = new AbortController()
    controller.current = ctl
    setState({ ...INITIAL, trip, busy: true, heatmapStatus: 'loading' })

    analyzeTrip(trip, ctl.signal)
      .then((analysis) => setState((s) => ({ ...s, analysis, busy: false })))
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

    fetchHeatmap(trip, ctl.signal)
      .then((heatmap) => setState((s) => ({ ...s, heatmap, heatmapStatus: 'ready' })))
      .catch(() => !ctl.signal.aborted && setState((s) => ({ ...s, heatmapStatus: 'failed' })))
  }, [])

  return { state, run }
}
