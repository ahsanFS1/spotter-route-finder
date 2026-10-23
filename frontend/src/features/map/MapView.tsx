import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useEffect, useRef, useState } from 'react'
import type { Analysis, Heatmap } from '../../api/types'
import { formatDateTime } from '../../lib/format'
import { levelLabel } from '../../lib/risk'
import {
  checkpointsToGeoJSON, HEAT_COLOR_RAMP, routeLabelsToGeoJSON, HEAT_RADIUS, heatDotColor, heatDotOpacity, heatmapToGeoJSON,
  heatWeight, routesToGeoJSON,
} from './layers'

// Vite bundles the worker with its shared chunk; MapLibre cannot resolve it on its own.
maplibregl.setWorkerUrl(workerUrl)

const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron'
const US_CENTER: [number, number] = [-96, 38.5]

interface Props {
  analysis: Analysis | null
  selectedId: string | null
  onSelect: (routeId: string) => void
  heatmap: Heatmap | null
  hour: number
  showHeat: boolean
}

function popupContent(p: Record<string, unknown>): HTMLElement {
  const root = document.createElement('div')
  root.className = 'popup'
  const add = (tag: string, text: string, className?: string) => {
    const el = document.createElement(tag)
    el.textContent = text
    if (className) el.className = className
    root.appendChild(el)
  }
  const level = Number(p.level)
  add('strong', `${p.label} · mile ${p.mile}`)
  add('span', formatDateTime(String(p.eta)), 'muted')
  add('span', level >= 0 ? `Risk: ${levelLabel(level as 0 | 1 | 2 | 3 | 4)}` : 'No forecast for this time')
  if (p.wind !== null && p.wind !== undefined && p.wind !== 'null') {
    add('span', `Wind ${p.wind} mph · Rain ${p.rain} in/hr · Snow ${p.snow} in/hr`, 'muted')
  }
  return root
}

export function MapView({ analysis, selectedId, onSelect, heatmap, hour, showHeat }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markers = useRef<maplibregl.Marker[]>([])
  const onSelectRef = useRef(onSelect)
  useEffect(() => {
    onSelectRef.current = onSelect
  }, [onSelect])
  const [ready, setReady] = useState(false)
  const frame = useRef(0)

  // create the map and its empty sources and layers once
  useEffect(() => {
    if (!container.current) return
    const map = new maplibregl.Map({ container: container.current, style: STYLE_URL, center: US_CENTER, zoom: 3.4, attributionControl: { compact: true } })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    map.on('load', () => {
      const empty = { type: 'FeatureCollection', features: [] } as GeoJSON.FeatureCollection
      for (const id of ['heat', 'routes', 'checkpoints', 'route-labels']) map.addSource(id, { type: 'geojson', data: empty })
      const lineLayout = { 'line-cap': 'round', 'line-join': 'round' } as const

      map.addLayer({
        id: 'heat', type: 'heatmap', source: 'heat', maxzoom: 12,
        paint: { 'heatmap-weight': heatWeight(0) as never, 'heatmap-intensity': 1, 'heatmap-radius': HEAT_RADIUS as never, 'heatmap-color': HEAT_COLOR_RAMP as never, 'heatmap-opacity': 0.75 },
      })
      map.addLayer({
        id: 'heat-dots', type: 'circle', source: 'heat',
        paint: { 'circle-radius': 4, 'circle-color': heatDotColor(0) as never, 'circle-opacity': heatDotOpacity(0) as never, 'circle-stroke-width': 1, 'circle-stroke-color': '#ffffff' },
      })
      map.addLayer({ id: 'routes-other', type: 'line', source: 'routes', layout: lineLayout, filter: ['!=', ['get', 'routeId'], ''], paint: { 'line-color': ['get', 'color'], 'line-width': 4, 'line-opacity': 0.55 } })
      map.addLayer({ id: 'routes-casing', type: 'line', source: 'routes', layout: lineLayout, filter: ['==', ['get', 'routeId'], ''], paint: { 'line-color': '#ffffff', 'line-width': 10 } })
      map.addLayer({ id: 'routes-selected', type: 'line', source: 'routes', layout: lineLayout, filter: ['==', ['get', 'routeId'], ''], paint: { 'line-color': ['get', 'color'], 'line-width': 6 } })
      map.addLayer({
        id: 'route-labels', type: 'symbol', source: 'route-labels',
        layout: { 'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 12, 'text-offset': [0, -1.2], 'text-allow-overlap': true },
        paint: { 'text-color': '#1b2430', 'text-halo-color': '#ffffff', 'text-halo-width': 2 },
      })
      map.addLayer({
        id: 'checkpoints', type: 'circle', source: 'checkpoints', filter: ['==', ['get', 'routeId'], ''],
        paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 3, 8, 6, 12, 8], 'circle-color': ['get', 'color'], 'circle-stroke-width': 2, 'circle-stroke-color': '#ffffff' },
      })

      map.on('click', 'routes-other', (e) => {
        const id = e.features?.[0]?.properties?.routeId
        if (id) onSelectRef.current(String(id))
      })
      map.on('click', 'checkpoints', (e) => {
        const f = e.features?.[0]
        if (!f) return
        new maplibregl.Popup({ offset: 10, closeButton: false })
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setDOMContent(popupContent(f.properties))
          .addTo(map)
      })
      for (const layer of ['routes-other', 'checkpoints']) {
        map.on('mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'))
        map.on('mouseleave', layer, () => (map.getCanvas().style.cursor = ''))
      }
      setReady(true)
    })

    return () => {
      cancelAnimationFrame(frame.current)
      markers.current.forEach((m) => m.remove())
      markers.current = []
      map.remove()
      mapRef.current = null
      setReady(false)
    }
  }, [])

  // routes, checkpoints and endpoints
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    ;(map.getSource('routes') as maplibregl.GeoJSONSource).setData(routesToGeoJSON(analysis))
    ;(map.getSource('checkpoints') as maplibregl.GeoJSONSource).setData(checkpointsToGeoJSON(analysis))
    ;(map.getSource('route-labels') as maplibregl.GeoJSONSource).setData(routeLabelsToGeoJSON(analysis))

    markers.current.forEach((m) => m.remove())
    markers.current = []
    const first = analysis?.routes[0]
    if (!analysis || !first) return
    markers.current = [
      new maplibregl.Marker({ color: '#1f2933' }).setLngLat(first.start).addTo(map),
      new maplibregl.Marker({ color: '#0b5d8f' }).setLngLat(first.end).addTo(map),
    ]
    const bounds = new maplibregl.LngLatBounds()
    analysis.routes.forEach((r) => bounds.extend([[r.bounds[0], r.bounds[1]], [r.bounds[2], r.bounds[3]]]))
    map.fitBounds(bounds, { padding: 56, duration: 700 })
  }, [analysis, ready])

  // selection only changes filters
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const id = selectedId ?? ''
    map.setFilter('routes-other', ['!=', ['get', 'routeId'], id])
    map.setFilter('routes-casing', ['==', ['get', 'routeId'], id])
    map.setFilter('routes-selected', ['==', ['get', 'routeId'], id])
    map.setFilter('checkpoints', ['==', ['get', 'routeId'], id])
  }, [selectedId, ready, analysis])

  // heatmap data is set once; the slider only rewrites paint expressions
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    ;(map.getSource('heat') as maplibregl.GeoJSONSource).setData(heatmapToGeoJSON(heatmap))
  }, [heatmap, ready])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      map.setPaintProperty('heat', 'heatmap-weight', heatWeight(hour) as never)
      map.setPaintProperty('heat-dots', 'circle-color', heatDotColor(hour) as never)
      map.setPaintProperty('heat-dots', 'circle-opacity', heatDotOpacity(hour) as never)
    })
  }, [hour, ready, heatmap])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const visibility = showHeat ? 'visible' : 'none'
    map.setLayoutProperty('heat', 'visibility', visibility)
    map.setLayoutProperty('heat-dots', 'visibility', visibility)
  }, [showHeat, ready])

  return <div ref={container} className="map" role="region" aria-label="Route map" />
}
