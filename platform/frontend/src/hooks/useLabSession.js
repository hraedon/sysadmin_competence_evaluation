import { useState, useEffect, useRef, useCallback } from 'react'
import { authFetch } from '../lib/auth.js'

const POLL_INTERVAL_MS = 3000

function getLocalUserId() {
  const key = 'sysadmin_lab_user_id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(key, id)
  }
  return id
}

export const PROVISION_STEPS = [
  { key: 'reverting', label: 'Restoring checkpoint', pct: 15 },
  { key: 'starting', label: 'Starting VM', pct: 30 },
  { key: 'waiting_ip', label: 'Waiting for guest OS', pct: 55 },
  { key: 'testing_connectivity', label: 'Testing guest OS response', pct: 65 },
  { key: 'creating_guac', label: 'Setting up console', pct: 75 },
  { key: 'running_scripts', label: 'Configuring environment', pct: 90 },
]

export function useLabSession(scenario, labControllerUrl, { enabled = true } = {}) {
  const [phase, setPhase] = useState('idle')
  const [session, setSession] = useState(null)
  const [verifyResults, setVerifyResults] = useState(null)
  const [error, setError] = useState(null)
  const [provisionStep, setProvisionStep] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const pollRef = useRef(null)
  const provisionStartRef = useRef(null)
  const elapsedRef = useRef(null)
  const generationRef = useRef(0)
  const verifyGenerationRef = useRef(0)
  const sessionRef = useRef(null)
  const mountedRef = useRef(true)

  function clearTimers() {
    if (pollRef.current) clearInterval(pollRef.current)
    if (elapsedRef.current) clearInterval(elapsedRef.current)
    pollRef.current = null
    elapsedRef.current = null
    provisionStartRef.current = null
  }

  function teardown(sessionRecord) {
    const sessionToken = sessionRecord?.session_token
    const controllerUrl = sessionRecord?.controllerUrl
    if (!sessionToken || !controllerUrl) return
    // The controller treats an absent or already-terminated session as success.
    // Do not await this: Cancel/End must remain bounded even if the controller is down.
    authFetch(`${controllerUrl}/lab/teardown/${sessionToken}`, { method: 'POST' })
      .catch(err => console.error('Teardown failed:', err))
  }

  function resetAll({ teardownSession = false } = {}) {
    generationRef.current += 1
    verifyGenerationRef.current += 1
    clearTimers()
    const activeSession = sessionRef.current
    sessionRef.current = null
    if (teardownSession) teardown(activeSession)
    if (!mountedRef.current) return
    setPhase('idle')
    setSession(null)
    setVerifyResults(null)
    setError(null)
    setProvisionStep(null)
    setElapsed(0)
  }

  // A session belongs to one enabled scenario only. This also clears a Mode E
  // session when the app switches back to a non-lab scenario.
  useEffect(() => {
    resetAll({ teardownSession: true })
  }, [scenario?.id, enabled, labControllerUrl])

  // React StrictMode replays effects in development. Restore this guard on
  // each setup so the replay cannot permanently mark a mounted hook stale.
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      resetAll({ teardownSession: true })
    }
  }, [])

  const handleStartLab = useCallback(async () => {
    if (!enabled) return
    if (!labControllerUrl) {
      setError('Lab controller URL is not configured. Set it in Settings.')
      setPhase('error')
      return
    }
    generationRef.current += 1
    verifyGenerationRef.current += 1
    const generation = generationRef.current
    const controllerUrl = labControllerUrl
    clearTimers()
    setPhase('provisioning')
    setError(null)
    setVerifyResults(null)
    setProvisionStep(null)
    setElapsed(0)
    provisionStartRef.current = Date.now()
    elapsedRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - provisionStartRef.current) / 1000))
    }, 1000)

    try {
      const res = await authFetch(`${controllerUrl}/lab/provision/${scenario.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: getLocalUserId(),
          capabilities: scenario.presentation?.modes?.E?.capabilities ?? [],
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
        throw new Error(detail ?? `HTTP ${res.status}`)
      }
      const data = await res.json()
      if (generation !== generationRef.current || !mountedRef.current) {
        teardown({ ...data, controllerUrl })
        return
      }
      sessionRef.current = { ...data, controllerUrl }
      setSession(data)
      setPhase('polling')

      pollRef.current = setInterval(async () => {
        try {
          const sr = await authFetch(`${controllerUrl}/lab/session/${data.session_token}`, {})
          if (!sr.ok) return
          const sd = await sr.json()
          if (generation !== generationRef.current || !mountedRef.current) return
          if (sd.provision_step) setProvisionStep(sd.provision_step)
          if (sd.environment_status === 'busy') {
            clearTimers()
            const readySession = { ...sd, session_token: data.session_token }
            sessionRef.current = { ...readySession, controllerUrl }
            setSession(readySession)
            setPhase('ready')
          } else if (sd.environment_status === 'faulted') {
            clearTimers()
            setError('Environment provisioning failed. Check the lab controller logs.')
            setPhase('error')
          }
        } catch { /* transient fetch error — keep polling */ }
      }, POLL_INTERVAL_MS)
    } catch (err) {
      if (generation !== generationRef.current) return
      clearTimers()
      setError(err.message)
      setPhase('error')
    }
  }, [enabled, labControllerUrl, scenario?.id])

  const handleVerify = useCallback(async () => {
    if (!enabled || !session?.session_token) return
    const generation = generationRef.current
    const activeSession = sessionRef.current
    if (!activeSession || activeSession.session_token !== session.session_token) return
    verifyGenerationRef.current += 1
    const verifyGeneration = verifyGenerationRef.current
    setPhase('verifying')
    setError(null)
    try {
      const res = await authFetch(`${activeSession.controllerUrl}/lab/verify/${session.session_token}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (generation !== generationRef.current || verifyGeneration !== verifyGenerationRef.current || !mountedRef.current) return
      setVerifyResults(data)
      setPhase('verified')
    } catch (err) {
      if (generation !== generationRef.current || verifyGeneration !== verifyGenerationRef.current || !mountedRef.current) return
      setError(err.message)
      setPhase('ready')
    }
  }, [enabled, session?.session_token])

  const handleEndLab = useCallback(async () => {
    resetAll({ teardownSession: true })
  }, [])

  return {
    phase,
    session,
    verifyResults,
    error,
    provisionStep,
    elapsed,
    handleStartLab,
    handleVerify,
    handleEndLab,
  }
}
