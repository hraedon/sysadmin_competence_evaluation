import { afterEach, describe, expect, it, vi } from 'vitest'

describe('evaluation mode runtime contract', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
    localStorage.clear()
  })

  it('selects the server proxy by default in a server build', async () => {
    vi.stubEnv('VITE_EVALUATION_MODE', 'server')
    const { DEFAULT_SETTINGS, EVALUATION_MODE, loadSettings } = await import('./evaluator.js')

    expect(EVALUATION_MODE).toBe('server')
    expect(DEFAULT_SETTINGS.provider).toBe('anthropic')
    expect(loadSettings().provider).toBe('anthropic')
  })

  it('keeps a local build on the local evaluator and migrates unsupported custom settings', async () => {
    vi.stubEnv('VITE_EVALUATION_MODE', 'local')
    localStorage.setItem('sysadmin_assessment_settings', JSON.stringify({ provider: 'custom', endpoint: 'http://local.test/v1' }))
    const { DEFAULT_SETTINGS, EVALUATION_MODE, loadSettings } = await import('./evaluator.js')

    expect(EVALUATION_MODE).toBe('local')
    expect(DEFAULT_SETTINGS.provider).toBe('local')
    expect(loadSettings()).toMatchObject({ provider: 'local', endpoint: 'http://local.test/v1' })
  })
})
