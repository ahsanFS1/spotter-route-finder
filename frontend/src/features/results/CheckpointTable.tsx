import type { Route } from '../../api/types'
import { formatDateTime } from '../../lib/format'
import { levelColor, levelLabel } from '../../lib/risk'

export function CheckpointTable({ route }: { route: Route }) {
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">Checkpoints for {route.label}</caption>
        <thead>
          <tr>
            <th scope="col">Mile</th>
            <th scope="col">ETA</th>
            <th scope="col" className="num">Wind</th>
            <th scope="col" className="num">Rain</th>
            <th scope="col" className="num">Snow</th>
            <th scope="col">Risk</th>
          </tr>
        </thead>
        <tbody>
          {route.checkpoints.map((cp) => (
            <tr key={cp.mile}>
              <td className="num">{cp.mile}</td>
              <td>{formatDateTime(cp.eta)}</td>
              <td className="num">{cp.weather ? `${cp.weather.wind_mph} mph` : '–'}</td>
              <td className="num">{cp.weather ? `${cp.weather.rain_in_hr} in/hr` : '–'}</td>
              <td className="num">{cp.weather ? `${cp.weather.snow_in_hr} in/hr` : '–'}</td>
              <td>
                <span className="dot" style={{ background: levelColor(cp.level) }} aria-hidden />
                {levelLabel(cp.level)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
