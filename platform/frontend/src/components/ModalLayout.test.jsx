import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import LoginView from './LoginView.jsx'
import OnboardingView from './OnboardingView.jsx'
import SettingsPage from './SettingsPage.jsx'

const settings = {
  provider: 'local', endpoint: 'http://localhost:1234', apiKey: '', model: 'model', evaluatorMode: 'auditor', labControllerUrl: '',
}

describe('modal layout', () => {
  it('keeps onboarding, settings, and login top-accessible and scrollable', () => {
    const { rerender } = render(<OnboardingView allScenarios={[]} onDismiss={vi.fn()} onSelect={vi.fn()} />)
    let dialog = screen.getByRole('dialog', { name: 'Assessment introduction' })
    expect(dialog).toHaveClass('items-start', 'overflow-y-auto', 'p-4', 'sm:p-8')
    expect(dialog.firstElementChild).toHaveClass('overflow-y-auto')

    rerender(<SettingsPage settings={settings} onSave={vi.fn()} onClose={vi.fn()} />)
    dialog = screen.getByRole('dialog', { name: 'Settings' })
    expect(dialog).toHaveClass('items-start', 'overflow-y-auto', 'p-4', 'sm:p-8')
    expect(dialog.firstElementChild).toHaveClass('overflow-y-auto')

    rerender(<LoginView onLogin={vi.fn()} onSkip={vi.fn()} />)
    dialog = screen.getByRole('dialog', { name: 'Sign in' })
    expect(dialog).toHaveClass('items-start', 'overflow-y-auto', 'p-4', 'sm:p-8')
  })
})
