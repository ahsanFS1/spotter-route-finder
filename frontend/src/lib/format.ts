export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60)
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h ? `${h} h ${m.toString().padStart(2, '0')} min` : `${m} min`
}

const dateTime = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  timeZoneName: 'short',
})
const hourOnly = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric' })

export const formatDateTime = (iso: string) => dateTime.format(new Date(iso))
export const formatHour = (iso: string) => hourOnly.format(new Date(iso))

export const formatMiles = (mi: number) => `${Math.round(mi).toLocaleString()} mi`

/** Value for a datetime-local input: the next whole hour, in local time. */
export function defaultDeparture(now = new Date()): string {
  const d = new Date(now)
  d.setMinutes(0, 0, 0)
  d.setHours(d.getHours() + 1)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`
}
