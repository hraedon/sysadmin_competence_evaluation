import { beforeEach, describe, expect, it, vi } from 'vitest'
import { login, persistAuth } from './auth.js'

describe('auth persistence', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ access_token: 'token', user: { username: 'learner' } }),
    }))
  })

  it('does not persist a successful response until the UI accepts it', async () => {
    const response = await login('learner', 'password')

    expect(localStorage.getItem('sysadmin_assessment_auth')).toBeNull()
    persistAuth(response)
    expect(JSON.parse(localStorage.getItem('sysadmin_assessment_auth'))).toMatchObject({ access_token: 'token' })
  })
})
