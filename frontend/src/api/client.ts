import type { Analysis, ApiErrorBody, Heatmap, Suggestion, TripInput } from './types'

const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  fields: Record<string, string[]>
  constructor(message: string, fields: Record<string, string[]> = {}) {
    super(message)
    this.fields = fields
  }
}

async function request<T>(path: string, init?: RequestInit, signal?: AbortSignal): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      signal,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError('Could not reach the server. Check your connection and try again.')
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiErrorBody | null
    throw new ApiError(body?.error.message ?? `Request failed (${res.status}).`, body?.error.fields)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) }, signal)

export const analyzeTrip = (trip: TripInput, signal?: AbortSignal) =>
  post<Analysis>('/api/routes/analyze/', trip, signal)

export const fetchHeatmap = (trip: TripInput, signal?: AbortSignal) =>
  post<Heatmap>('/api/heatmap/', trip, signal)

export const searchPlaces = async (query: string, signal?: AbortSignal) =>
  (await request<{ results: Suggestion[] }>(`/api/geocode/?q=${encodeURIComponent(query)}`, undefined, signal)).results

export const wakeServer = () => request<{ status: string }>('/api/health/').catch(() => null)
