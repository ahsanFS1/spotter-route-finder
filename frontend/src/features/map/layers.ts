import type { Analysis, Heatmap } from '../../api/types'
import { LEVELS, levelColor } from '../../lib/risk'

type Feature = GeoJSON.Feature
type Collection = GeoJSON.FeatureCollection

export const hourKey = (hour: number) => `l${hour}`

export function routesToGeoJSON(analysis: Analysis | null): Collection {
  const features: Feature[] = []
  for (const route of analysis?.routes ?? []) {
    for (const seg of route.segments) {
      features.push({
        type: 'Feature',
        properties: { routeId: route.id, color: levelColor(seg.level) },
        geometry: { type: 'LineString', coordinates: seg.coordinates },
      })
    }
  }
  return { type: 'FeatureCollection', features }
}

export function routeLabelsToGeoJSON(analysis: Analysis | null): Collection {
  return {
    type: 'FeatureCollection',
    features: (analysis?.routes ?? []).map((r) => ({
      type: 'Feature',
      properties: { routeId: r.id, label: r.label },
      geometry: { type: 'Point', coordinates: r.label_at },
    })),
  }
}

export function checkpointsToGeoJSON(analysis: Analysis | null): Collection {
  const features: Feature[] = []
  for (const route of analysis?.routes ?? []) {
    for (const cp of route.checkpoints) {
      features.push({
        type: 'Feature',
        properties: {
          routeId: route.id,
          label: route.label,
          mile: cp.mile,
          eta: cp.eta,
          level: cp.level ?? -1,
          color: levelColor(cp.level),
          wind: cp.weather?.wind_mph ?? null,
          rain: cp.weather?.rain_in_hr ?? null,
          snow: cp.weather?.snow_in_hr ?? null,
        },
        geometry: { type: 'Point', coordinates: [cp.lng, cp.lat] },
      })
    }
  }
  return { type: 'FeatureCollection', features }
}

/** One static collection holding every forecast hour as a property, so the slider never reloads data. */
export function heatmapToGeoJSON(heatmap: Heatmap | null): Collection {
  const features: Feature[] = (heatmap?.points ?? []).map(([lat, lng], i) => {
    const properties: Record<string, number> = {}
    heatmap!.levels[i].forEach((level, hour) => (properties[hourKey(hour)] = level))
    return { type: 'Feature', properties, geometry: { type: 'Point', coordinates: [lng, lat] } }
  })
  return { type: 'FeatureCollection', features }
}

const value = (hour: number) => ['coalesce', ['get', hourKey(hour)], -1] as const

export const heatWeight = (hour: number) => [
  'interpolate', ['linear'], value(hour),
  -1, 0, 0, 0.15, 1, 0.35, 2, 0.6, 3, 0.85, 4, 1,
]

export const heatDotColor = (hour: number) => [
  'match', value(hour),
  ...LEVELS.flatMap((l) => [l.level, l.color]),
  '#9aa3ad',
]

export const heatDotOpacity = (hour: number) => ['case', ['<', value(hour), 0], 0, 0.95]

export const HEAT_COLOR_RAMP = [
  'interpolate', ['linear'], ['heatmap-density'],
  0, 'rgba(46,158,107,0)',
  0.1, 'rgba(46,158,107,0.35)',
  0.3, 'rgba(217,178,50,0.55)',
  0.55, 'rgba(224,120,43,0.65)',
  0.8, 'rgba(201,47,58,0.75)',
  1, 'rgba(91,18,48,0.85)',
]

export const HEAT_RADIUS = ['interpolate', ['exponential', 2], ['zoom'], 3, 22, 5, 40, 6, 58, 8, 130, 10, 280]
