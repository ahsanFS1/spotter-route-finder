export type Level = 0 | 1 | 2 | 3 | 4

export interface Place {
  label: string
  lat: number
  lng: number
}

export interface TripInput {
  origin: Place
  destination: Place
  departure: string // ISO 8601
  load_lb: number
  interval_mi: 10 | 25 | 50
}

export interface CheckpointWeather {
  wind_mph: number
  rain_in_hr: number
  snow_in_hr: number
}

export interface Checkpoint {
  lat: number
  lng: number
  mile: number
  eta: string
  level: Level | null
  weather: CheckpointWeather | null
  levels: { wind: Level; rain: Level; snow: Level } | null
}

export interface RouteSegment {
  level: Level | null
  coordinates: [number, number][]
}

export interface RouteMetrics {
  miles_by_level: Record<'low' | 'moderate' | 'high' | 'severe' | 'no_travel', number>
  scored_miles: number
  unscored_miles: number
  avg_risk: number
  max_level: Level | null
  has_no_travel: boolean
}

export interface Route {
  id: string
  label: string
  distance_mi: number
  duration_s: number
  arrival: string
  geometry: [number, number][]
  segments: RouteSegment[]
  metrics: RouteMetrics
  checkpoints: Checkpoint[]
  rank: number
  recommended: boolean
}

export interface Analysis {
  routes: Route[]
  recommended_route_id: string | null
  reason: string
  warnings: string[]
  departure: string
  load_lb: number
  interval_mi: number
}

export interface Heatmap {
  hours: string[]
  points: [number, number][] // [lat, lng]
  levels: number[][] // per point, per hour; -1 when there is no forecast
  max_level: number
}

export interface Suggestion extends Place {}

export interface ApiErrorBody {
  error: { code: string; message: string; fields: Record<string, string[]> }
}
