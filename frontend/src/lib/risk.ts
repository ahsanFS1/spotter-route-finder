import type { Level } from '../api/types'

export const LEVELS: { level: Level; key: string; label: string; color: string }[] = [
  { level: 0, key: 'low', label: 'Low', color: '#2e9e6b' },
  { level: 1, key: 'moderate', label: 'Moderate', color: '#d9b232' },
  { level: 2, key: 'high', label: 'High', color: '#e0782b' },
  { level: 3, key: 'severe', label: 'Severe', color: '#c92f3a' },
  { level: 4, key: 'no_travel', label: 'No travel', color: '#5b1230' },
]

export const levelLabel = (level: Level | null) => (level === null ? 'No forecast' : LEVELS[level].label)
export const levelColor = (level: Level | null) => (level === null ? '#9aa3ad' : LEVELS[level].color)

export const THRESHOLDS = [
  { condition: 'Wind (mph)', bands: ['<25', '25–34', '35–44', '45–54', '≥55'] },
  { condition: 'Rain (in/hr)', bands: ['<0.10', '0.10–0.25', '0.25–0.50', '0.50–1.00', '>1.00'] },
  { condition: 'Snow (in/hr)', bands: ['<0.5', '0.5–1.0', '1.0–2.0', '2.0–3.0', '>3.0'] },
]
