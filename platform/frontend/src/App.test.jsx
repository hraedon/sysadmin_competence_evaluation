import { act, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.jsx'
import { groupByDomain, loadManifest } from './lib/scenarios.js'
import { logout } from './lib/auth.js'
import { useLabSession } from './hooks/useLabSession.js'
import { evaluate } from './lib/evaluator.js'

vi.mock('./lib/scenarios.js', () => ({
  loadManifest: vi.fn(() => Promise.resolve([])),
  groupByDomain: vi.fn(() => []),
}))

vi.mock('./lib/auth.js', () => ({
  isAuthenticated: vi.fn(() => Boolean(JSON.parse(localStorage.getItem('sysadmin_assessment_auth') || 'null')?.access_token)),
  getUser: vi.fn(() => JSON.parse(localStorage.getItem('sysadmin_assessment_auth') || 'null')?.user ?? null),
  logout: vi.fn(),
  persistAuth: vi.fn(),
  authFetch: vi.fn(),
}))

vi.mock('./hooks/useLabSession.js', () => ({
  useLabSession: vi.fn(() => ({})),
}))

vi.mock('./lib/evaluator.js', async importOriginal => ({
  ...await importOriginal(),
  evaluate: vi.fn(),
}))

describe('App first-run and mobile layout', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    loadManifest.mockResolvedValue([])
    groupByDomain.mockReturnValue([])
  })

  it('shows onboarding before login and never renders both dialogs', async () => {
    render(<App />)

    expect(screen.getByRole('dialog', { name: 'Assessment introduction' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Sign in' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Begin' }))

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'Sign in' })).toBeInTheDocument()
    })
    expect(screen.queryByRole('dialog', { name: 'Assessment introduction' })).not.toBeInTheDocument()
  })

  it('replaces onboarding with settings rather than stacking full-screen modals', () => {
    render(<App />)

    fireEvent.click(screen.getByTitle('Settings'))

    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Assessment introduction' })).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Sign in' })).not.toBeInTheDocument()
  })

  it('keeps desktop flex layout on the inert application wrapper', async () => {
    localStorage.setItem('sysadmin_onboarding_dismissed', '1')
    render(<App />)
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Sign in' })).toBeInTheDocument())

    const appShell = document.querySelector('[inert]')
    expect(appShell).toHaveClass('md:flex', 'md:h-screen', 'md:overflow-hidden')
  })

  it('does not reopen settings after saving a keyless proxy provider', async () => {
    localStorage.setItem('sysadmin_onboarding_dismissed', '1')
    render(<App />)
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Sign in' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Continue without account' }))
    fireEvent.click(screen.getByTitle('Settings'))
    fireEvent.click(screen.getByLabelText('Anthropic (Server Proxy)'))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.queryByRole('dialog', { name: 'Settings' })).not.toBeInTheDocument()
  })

  it('opens and closes the mobile drawer and stacks the evaluation panel below md', async () => {
    localStorage.setItem('sysadmin_onboarding_dismissed', '1')
    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'Sign in' })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Continue without account' }))

    const toggle = screen.getByRole('button', { name: 'Open scenario menu' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')

    const sidebar = screen.getByRole('complementary', { name: 'Scenario navigation' })
    expect(sidebar).toHaveClass('translate-x-0')
    fireEvent.click(screen.getAllByRole('button', { name: 'Close scenario menu' })[0])
    expect(sidebar).toHaveClass('-translate-x-full')
    expect(sidebar).toHaveAttribute('aria-hidden', 'true')
    expect(sidebar).toHaveAttribute('inert')

    const evaluation = screen.getByText('Evaluation will appear here.').parentElement.parentElement
    expect(evaluation).toHaveClass('w-full', 'border-t', 'md:w-80', 'md:border-l')
  })

  it('clears the in-memory profile and completion indicators immediately', async () => {
    localStorage.setItem('sysadmin_assessment_profile', JSON.stringify({
      updated: '2026-01-01T00:00:00.000Z',
      domains: {
        1: {
          domain_name: 'Test Domain',
          results: [{ scenario_id: 'scenario-1', title: 'Completed scenario', level: 2, timestamp: '2026-01-01T00:00:00.000Z' }],
        },
      },
    }))
    const scenario = { id: 'scenario-1', title: 'Completed scenario', domain: 1, domain_name: 'Test Domain', level: 2, delivery_mode: 'A' }
    loadManifest.mockResolvedValue([scenario])
    groupByDomain.mockReturnValue([{ domain: 1, domain_name: 'Test Domain', scenarios: [scenario] }])

    render(<App />)
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Sign in' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Continue without account' }))

    await waitFor(() => expect(screen.getByText('✓2')).toBeInTheDocument())
    fireEvent.click(screen.getByTitle('Settings'))
    fireEvent.click(screen.getByRole('button', { name: 'Clear profile' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm clear' }))

    expect(screen.queryByText('✓2')).not.toBeInTheDocument()
    expect(document.querySelector('aside')).not.toHaveTextContent('1 domain')
  })

  it('clearing profile data clears the signed-in user state', async () => {
    localStorage.setItem('sysadmin_onboarding_dismissed', '1')
    localStorage.setItem('sysadmin_assessment_auth', JSON.stringify({
      access_token: 'token', user: { username: 'alice' },
    }))
    render(<App />)

    expect(screen.getByText('alice')).toBeInTheDocument()
    fireEvent.click(screen.getByTitle('Settings'))
    fireEvent.click(screen.getByRole('button', { name: 'Clear profile' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm clear' }))

    expect(localStorage.getItem('sysadmin_assessment_auth')).toBeNull()
    expect(screen.getByText('Sign in to sync profile across devices')).toBeInTheDocument()
  })

  it('ends the active lab before logging out', () => {
    const handleEndLab = vi.fn()
    useLabSession.mockReturnValue({ handleEndLab })
    localStorage.setItem('sysadmin_onboarding_dismissed', '1')
    localStorage.setItem('sysadmin_assessment_auth', JSON.stringify({
      access_token: 'token', user: { username: 'alice' },
    }))
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Open scenario menu' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(handleEndLab).toHaveBeenCalledOnce()
    expect(logout).toHaveBeenCalledOnce()
  })

  it('ends the active lab when profile data is cleared', () => {
    const handleEndLab = vi.fn()
    useLabSession.mockReturnValue({ handleEndLab })
    localStorage.setItem('sysadmin_onboarding_dismissed', '1')
    render(<App />)

    fireEvent.click(screen.getByTitle('Settings'))
    fireEvent.click(screen.getByRole('button', { name: 'Clear profile' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm clear' }))

    expect(handleEndLab).toHaveBeenCalledOnce()
  })

  it('ignores a delayed evaluation after changing scenarios', async () => {
    let resolveEvaluation
    evaluate.mockImplementation(() => new Promise(resolve => { resolveEvaluation = resolve }))
    localStorage.setItem('sysadmin_onboarding_dismissed', '1')
    const first = { id: 'first', title: 'First scenario', domain: 1, domain_name: 'Test Domain', level: 1, delivery_mode: 'A', presentation: { context: 'First context' } }
    const second = { ...first, id: 'second', title: 'Second scenario', presentation: { context: 'Second context' } }
    loadManifest.mockResolvedValue([first, second])
    groupByDomain.mockReturnValue([{ domain: 1, domain_name: 'Test Domain', scenarios: [first, second] }])
    render(<App />)
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Sign in' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Continue without account' }))
    fireEvent.click(screen.getByRole('button', { name: 'Open scenario menu' }))
    await waitFor(() => expect(screen.getByText('First scenario')).toBeInTheDocument())
    fireEvent.click(screen.getByText('First scenario'))
    fireEvent.change(screen.getByPlaceholderText(/Write your analysis here/i), { target: { value: 'This response is deliberately long enough to submit for evaluation.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Submit for Evaluation' }))
    await waitFor(() => expect(evaluate).toHaveBeenCalledOnce())

    fireEvent.click(screen.getByRole('button', { name: 'Open scenario menu' }))
    fireEvent.click(screen.getByText('Second scenario'))
    expect(evaluate.mock.calls[0][0].signal.aborted).toBe(true)
    await act(async () => resolveEvaluation({ raw: '{}', parsed: { level: 4, confidence: 'high' } }))

    expect(screen.getByRole('heading', { name: 'Second scenario' })).toBeInTheDocument()
    expect(screen.queryByText('L4 Adaptation')).not.toBeInTheDocument()
  })
})
