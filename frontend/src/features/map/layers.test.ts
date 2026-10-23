import { describe, expect, it } from 'vitest'
import type { Analysis, Heatmap } from '../../api/types'
import { checkpointsToGeoJSON, heatmapToGeoJSON, hourKey, routesToGeoJSON } from './layers'

const analysis = {
  routes: [
    {
      id: 'route-1',
      label: 'Fastest',
      segments: [
        { level: 3, coordinates: [[-90, 40], [-89, 40]] },
        { level: null, coordinates: [[-89, 40], [-88, 40]] },
      ],
      checkpoints: [
        { lat: 40, lng: -90, mile: 0, eta: '2026-10-24T12:00:00Z', level: 3, weather: { wind_mph: 50, rain_in_hr: 0, snow_in_hr: 0 }, levels: null },
        { lat: 40, lng: -88, mile: 25, eta: '2026-10-24T13:00:00Z', level: null, weather: null, levels: null },
      ],
    },
  ],
} as unknown as Analysis

describe('map layer data', () => {
  it('colours route segments by level and greys unscored ones', () => {
    const [a, b] = routesToGeoJSON(analysis).features
    expect(a.properties?.color).toBe('#c92f3a')
    expect(b.properties?.color).toBe('#9aa3ad')
  })

  it('keeps checkpoints without a forecast, marked -1', () => {
    const [, missing] = checkpointsToGeoJSON(analysis).features
    expect(missing.properties?.level).toBe(-1)
    expect(missing.properties?.wind).toBeNull()
  })

  it('packs every forecast hour into one static collection', () => {
    const heat: Heatmap = { hours: ['a', 'b'], points: [[40, -90]], levels: [[0, 4]], max_level: 4 }
    const [f] = heatmapToGeoJSON(heat).features
    expect(f.properties?.[hourKey(0)]).toBe(0)
    expect(f.properties?.[hourKey(1)]).toBe(4)
    expect(f.geometry).toEqual({ type: 'Point', coordinates: [-90, 40] })
  })

  it('handles no data', () => expect(heatmapToGeoJSON(null).features).toEqual([]))
})
