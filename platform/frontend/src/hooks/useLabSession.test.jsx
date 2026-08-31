import { act, renderHook } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useLabSession } from './useLabSession.js'
import { authFetch } from '../lib/auth.js'

vi.mock('../lib/auth.js', () => ({ authFetch: vi.fn() }))

const scenario = id => ({ id, presentation: { modes: { E: { capabilities: [] } } } })
const provisionedSession = { session_token: 'session-token' }

describe('useLabSession', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.useFakeTimers()
    vi.clearAllMocks()
    authFetch.mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue(provisionedSession) })
  })

  afterEach(() => vi.useRealTimers())

  async function start(result) {
    await act(async () => {
      await result.current.handleStartLab()
    })
  }

  it('stops timers and resets when the scenario changes', async () => {
    const { result, rerender } = renderHook(
      ({ activeScenario, enabled }) => useLabSession(activeScenario, 'http://controller', { enabled }),
      { initialProps: { activeScenario: scenario('one'), enabled: true } },
    )

    await start(result)
    await act(async () => { vi.advanceTimersByTime(1000) })
    expect(result.current.elapsed).toBe(1)

    rerender({ activeScenario: scenario('two'), enabled: true })
    expect(result.current).toMatchObject({ phase: 'idle', session: null, elapsed: 0 })

    await act(async () => { vi.advanceTimersByTime(9000) })
    expect(authFetch).toHaveBeenCalledWith('http://controller/lab/teardown/session-token', { method: 'POST' })
  })

  it('resets and prevents polling when Mode E is disabled', async () => {
    const { result, rerender } = renderHook(
      ({ activeScenario, enabled }) => useLabSession(activeScenario, 'http://controller', { enabled }),
      { initialProps: { activeScenario: scenario('one'), enabled: true } },
    )

    await start(result)
    rerender({ activeScenario: scenario('one'), enabled: false })
    expect(result.current).toMatchObject({ phase: 'idle', session: null, elapsed: 0 })

    await act(async () => { vi.advanceTimersByTime(9000) })
    expect(authFetch).toHaveBeenCalledWith('http://controller/lab/teardown/session-token', { method: 'POST' })
  })

  it('ignores a provisioning response after the lab is disabled', async () => {
    let resolveProvision
    authFetch.mockImplementation(() => new Promise(resolve => { resolveProvision = resolve }))
    const { result, rerender } = renderHook(
      ({ activeScenario, enabled }) => useLabSession(activeScenario, 'http://controller', { enabled }),
      { initialProps: { activeScenario: scenario('one'), enabled: true } },
    )

    const startPromise = result.current.handleStartLab()
    rerender({ activeScenario: scenario('one'), enabled: false })
    await act(async () => {
      resolveProvision({ ok: true, json: vi.fn().mockResolvedValue(provisionedSession) })
      await startPromise
    })

    expect(result.current).toMatchObject({ phase: 'idle', session: null, elapsed: 0 })
    await act(async () => { vi.advanceTimersByTime(9000) })
    expect(authFetch).toHaveBeenCalledWith('http://controller/lab/teardown/session-token', { method: 'POST' })
  })

  it('ignores a delayed verification result after ending the lab', async () => {
    let resolveVerify
    authFetch
      .mockResolvedValueOnce({ ok: true, json: vi.fn().mockResolvedValue(provisionedSession) })
      .mockImplementationOnce(() => new Promise(resolve => { resolveVerify = resolve }))
      .mockResolvedValueOnce({ ok: true, json: vi.fn().mockResolvedValue({ status: 'success' }) })
    const { result } = renderHook(() => useLabSession(scenario('one'), 'http://controller'))

    await start(result)
    const verification = result.current.handleVerify()
    await act(async () => { await result.current.handleEndLab() })
    await act(async () => {
      resolveVerify({ ok: true, json: vi.fn().mockResolvedValue([{ finding_id: 'f-1' }]) })
      await verification
    })

    expect(result.current).toMatchObject({ phase: 'idle', verifyResults: null })
    expect(authFetch).toHaveBeenLastCalledWith('http://controller/lab/teardown/session-token', { method: 'POST' })
  })

  it('tears down a session created after cancellation while provision was pending', async () => {
    let resolveProvision
    authFetch.mockImplementationOnce(() => new Promise(resolve => { resolveProvision = resolve }))
    const { result } = renderHook(() => useLabSession(scenario('one'), 'http://controller'))

    const provisioning = result.current.handleStartLab()
    await act(async () => { await result.current.handleEndLab() })
    await act(async () => {
      resolveProvision({ ok: true, json: vi.fn().mockResolvedValue(provisionedSession) })
      await provisioning
    })

    expect(result.current).toMatchObject({ phase: 'idle', session: null })
    expect(authFetch).toHaveBeenLastCalledWith('http://controller/lab/teardown/session-token', { method: 'POST' })
  })

  it('tears down a late provision response after unmount without starting polling', async () => {
    let resolveProvision
    authFetch.mockImplementationOnce(() => new Promise(resolve => { resolveProvision = resolve }))
    const { result, unmount } = renderHook(() => useLabSession(scenario('one'), 'http://controller'))

    const provisioning = result.current.handleStartLab()
    unmount()
    await act(async () => {
      resolveProvision({ ok: true, json: vi.fn().mockResolvedValue(provisionedSession) })
      await provisioning
      vi.advanceTimersByTime(9000)
    })

    expect(authFetch).toHaveBeenCalledTimes(2)
    expect(authFetch).toHaveBeenLastCalledWith('http://controller/lab/teardown/session-token', { method: 'POST' })
  })

  it('provisions once when mounted in StrictMode', async () => {
    const { result } = renderHook(
      () => useLabSession(scenario('one'), 'http://controller'),
      { wrapper: StrictMode },
    )

    await start(result)

    expect(authFetch).toHaveBeenCalledTimes(1)
    expect(authFetch).toHaveBeenCalledWith(expect.stringContaining('/lab/provision/one'), expect.any(Object))
  })

  it('tears down through the controller that created the session after its URL changes', async () => {
    const { result, rerender } = renderHook(
      ({ controllerUrl }) => useLabSession(scenario('one'), controllerUrl),
      { initialProps: { controllerUrl: 'http://first-controller' } },
    )
    await start(result)

    rerender({ controllerUrl: 'http://second-controller' })

    expect(authFetch).toHaveBeenLastCalledWith(
      'http://first-controller/lab/teardown/session-token',
      { method: 'POST' },
    )
  })

  it('clears the elapsed timer when provisioning fails', async () => {
    let rejectProvision
    authFetch.mockImplementationOnce(() => new Promise((resolve, reject) => { rejectProvision = reject }))
    const { result } = renderHook(() => useLabSession(scenario('one'), 'http://controller'))

    const provisioning = result.current.handleStartLab()
    await act(async () => { vi.advanceTimersByTime(2000) })
    expect(result.current.elapsed).toBe(2)
    await act(async () => {
      rejectProvision(new Error('controller unavailable'))
      await provisioning
    })
    expect(result.current).toMatchObject({ phase: 'error', elapsed: 2 })
    await act(async () => { vi.advanceTimersByTime(3000) })
    expect(result.current.elapsed).toBe(2)
  })
})
