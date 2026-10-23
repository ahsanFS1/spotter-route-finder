import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../api/client'
import { TripForm } from './TripForm'

const chicago = { label: 'Chicago, Illinois, US', lat: 41.88, lng: -87.63 }
const dallas = { label: 'Dallas, Texas, US', lat: 32.78, lng: -96.8 }

async function choose(label: string, typed: string, place: typeof chicago) {
  const user = userEvent.setup()
  vi.spyOn(client, 'searchPlaces').mockResolvedValueOnce([place])
  await user.type(screen.getByLabelText(label), typed)
  await user.click(await screen.findByRole('option', { name: place.label }, { timeout: 3000 }))
  return user
}

describe('TripForm', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('asks for both places before submitting', async () => {
    const onSubmit = vi.fn()
    render(<TripForm busy={false} fieldErrors={{}} onSubmit={onSubmit} />)
    await userEvent.click(screen.getByRole('button', { name: 'Find safest route' }))
    expect(screen.getByText('Choose a starting point from the suggestions.')).toBeInTheDocument()
    expect(screen.getByText('Choose a destination from the suggestions.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('rejects an out-of-range load', async () => {
    const onSubmit = vi.fn()
    render(<TripForm busy={false} fieldErrors={{}} onSubmit={onSubmit} />)
    const user = await choose('From', 'chi', chicago)
    await choose('To', 'dal', dallas)
    const load = screen.getByLabelText('Load (lb)')
    await user.clear(load)
    await user.type(load, '999999')
    await user.click(screen.getByRole('button', { name: 'Find safest route' }))
    expect(screen.getByText(/Enter a weight between 0 and 150,000 lb/)).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits the chosen places, load and interval', async () => {
    const onSubmit = vi.fn()
    render(<TripForm busy={false} fieldErrors={{}} onSubmit={onSubmit} />)
    const user = await choose('From', 'chi', chicago)
    await choose('To', 'dal', dallas)
    await user.click(screen.getByLabelText('50 mi'))
    await user.click(screen.getByRole('button', { name: 'Find safest route' }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    const trip = onSubmit.mock.calls[0][0]
    expect(trip).toMatchObject({ origin: chicago, destination: dallas, load_lb: 42000, interval_mi: 50 })
    expect(new Date(trip.departure).toString()).not.toBe('Invalid Date')
  })

  it('disables the button while a request is running', () => {
    render(<TripForm busy fieldErrors={{}} onSubmit={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Analyzing routes…' })).toBeDisabled()
  })

  it('shows server-side field errors', () => {
    render(<TripForm busy={false} fieldErrors={{ departure: ['Departure cannot be in the past.'] }} onSubmit={vi.fn()} />)
    expect(screen.getByText('Departure cannot be in the past.')).toBeInTheDocument()
  })
})
