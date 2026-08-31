import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import LoginView from './LoginView.jsx'
import { login } from '../lib/auth.js'

vi.mock('../lib/auth.js', () => ({ login: vi.fn(), register: vi.fn() }))

describe('LoginView', () => {
  it('associates labels and uses login versus registration autocomplete semantics', () => {
    render(<LoginView onLogin={vi.fn()} onSkip={vi.fn()} />)

    expect(screen.getByLabelText('Username')).toHaveAttribute('id', 'login-username')
    expect(screen.getByLabelText('Username')).toHaveAttribute('autocomplete', 'username')
    expect(screen.getByLabelText('Password')).toHaveAttribute('id', 'login-password')
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'current-password')

    fireEvent.click(screen.getByRole('button', { name: 'Create one' }))

    expect(screen.getByRole('dialog', { name: 'Create Account' })).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toHaveAttribute('id', 'register-username')
    expect(screen.getByLabelText('Username')).toHaveAttribute('autocomplete', 'username')
    expect(screen.getByLabelText('Password')).toHaveAttribute('id', 'register-password')
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'new-password')
  })

  it('aborts and ignores a delayed login when the user skips', async () => {
    let resolveLogin
    login.mockImplementation((_username, _password, { signal }) => new Promise(resolve => {
      resolveLogin = () => resolve({ user: { username: 'late' }, signal })
    }))
    const onLogin = vi.fn()
    const onSkip = vi.fn()
    render(<LoginView onLogin={onLogin} onSkip={onSkip} />)

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'user' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }))
    fireEvent.click(screen.getByRole('button', { name: 'Continue without account' }))
    resolveLogin()
    await Promise.resolve()

    expect(login.mock.calls[0][2].signal.aborted).toBe(true)
    expect(onSkip).toHaveBeenCalledOnce()
    expect(onLogin).not.toHaveBeenCalled()
  })
})
