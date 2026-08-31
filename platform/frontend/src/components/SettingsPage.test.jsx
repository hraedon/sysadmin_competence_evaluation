import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import SettingsPage from './SettingsPage.jsx'

const settings = {
  provider: 'local', endpoint: 'http://localhost:1234', apiKey: '', model: 'local-model', evaluatorMode: 'auditor', labControllerUrl: '',
}

describe('SettingsPage provider contract', () => {
  it.each(['Anthropic (Server Proxy)', 'OpenAI (Server Proxy)'])('saves %s without a browser API key', label => {
    const onSave = vi.fn()
    render(<SettingsPage settings={settings} onSave={onSave} />)

    fireEvent.click(screen.getByLabelText(label))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
      provider: label.startsWith('Anthropic') ? 'anthropic' : 'openai',
      apiKey: '',
    }))
  })
})
