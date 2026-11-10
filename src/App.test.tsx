import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

describe('Fluxora workspace', () => {
  it('renders the converter and tool navigation', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /universal converter/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pdf studio/i })).toBeInTheDocument()
    expect(screen.getByText(/api not connected/i)).toBeInTheDocument()
  })

  it('accepts local files and does not claim a conversion without the backend contract', async () => {
    const user = userEvent.setup()
    render(<App />)
    expect(screen.getByRole('button', { name: /convert files/i })).toBeDisabled()
    const file = new File(['hello'], 'notes.txt', { type: 'text/plain', lastModified: 1 })
    await user.upload(screen.getByLabelText('Choose files to convert'), file)
    expect(screen.getByText('notes.txt')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /convert files/i }))
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/api integration is not configured/i))
    expect(screen.queryByText(/conversion complete/i)).not.toBeInTheDocument()
  })

  it('navigates to job history and shows a truthful empty state', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /job history/i }))
    expect(screen.getByRole('heading', { name: /processing jobs/i })).toBeInTheDocument()
    expect(screen.getByText(/no jobs to show yet/i)).toBeInTheDocument()
  })

  it('toggles the color theme accessibly', async () => {
    const user = userEvent.setup()
    const { container } = render(<App />)
    await user.click(screen.getByRole('button', { name: /switch to dark theme/i }))
    expect(container.querySelector('.app-shell')).toHaveClass('theme-dark')
    expect(screen.getByRole('button', { name: /switch to light theme/i })).toBeInTheDocument()
  })

  it('opens the mobile navigation from its labelled control', async () => {
    const user = userEvent.setup()
    const { container } = render(<App />)
    await user.click(screen.getByRole('button', { name: /open navigation/i }))
    expect(container.querySelector('.sidebar')).toHaveClass('sidebar-open')
    expect(screen.getByRole('button', { name: /close navigation/i })).toBeInTheDocument()
  })
})
