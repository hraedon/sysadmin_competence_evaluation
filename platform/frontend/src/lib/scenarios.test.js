import { beforeEach, describe, expect, it, vi } from 'vitest'
import { loadArtifact } from './scenarios.js'

describe('loadArtifact', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it.each([
    ['an HTML content type', 'text/html; charset=utf-8', '<!doctype html><html><body>app</body></html>'],
    ['an HTML document with an incorrect content type', 'text/plain', '<html><body>app</body></html>'],
  ])('rejects %s instead of caching an SPA fallback', async (_label, contentType, body) => {
    const text = vi.fn().mockResolvedValue(body)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': contentType }),
      text,
    }))

    await expect(loadArtifact(`scenarios/test-${contentType}.txt`)).resolves.toBeNull()
    expect(text).toHaveBeenCalledTimes(contentType === 'text/plain' ? 1 : 0)
  })
})
