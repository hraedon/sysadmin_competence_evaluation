import { useState, useEffect, useRef, useCallback } from 'react'

const POLL_INTERVAL_MS = 3000
const CONTROLLER_API_KEY = import.meta.env.VITE_CONTROLLER_KEY ?? ''

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

  function clearTimers() {
    if (pollRef.current) clearInterval(pollRef.current)
    if (elapsedRef.current) clearInterval(elapsedRef.current)
    provisionStartRef.current = null
  }

  function resetAll() {
    setPhase('idle')
    setSession(null)
    setVerifyResults(null)
    setError(null)
    setProvisionStep(null)
    setElapsed(0)
    clearTimers()
  }

  // Reset on scenario change
  useEffect(() => {
    if (enabled) resetAll()
  }, [scenario?.id])

  // Clean up timers on unmount
  useEffect(() => () => clearTimers(), [])

  const handleStartLab = useCallback(async () => {
    if (!enabled) return
    if (!labControllerUrl) {
      setError('Lab controller URL is not configured. Set it in Settings.')
      setPhase('error')
      return
    }
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
      const res = await fetch(`${labControllerUrl}/lab/provision/${scenario.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': CONTROLLER_API_KEY
        },
        body: JSON.stringify({
          user_id: getLocalUserId(),
          capabilities: scenario.presentation?.modes?.E?.capabilities ?? [],
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail ?? `HTTP ${res.status}`)
      }
      const data = await res.json()
      setSession(data)
      setPhase('polling')

      pollRef.current = setInterval(async () => {
        try {
          const sr = await fetch(`${labControllerUrl}/lab/session/${data.session_token}`, {
            headers: { 'X-API-Key': CONTROLLER_API_KEY }
          })
          if (!sr.ok) return
          const sd = await sr.json()
          if (sd.provision_step) setProvisionStep(sd.provision_step)
          if (sd.environment_status === 'busy') {
            clearInterval(pollRef.current)
            if (elapsedRef.current) clearInterval(elapsedRef.current)
            setSession(sd)
            setPhase('ready')
          } else if (sd.environment_status === 'faulted') {
            clearInterval(pollRef.current)
            if (elapsedRef.current) clearInterval(elapsedRef.current)
            setError('Environment provisioning failed. Check the lab controller logs.')
            setPhase('error')
          }
        } catch { /* transient fetch error — keep polling */ }
      }, POLL_INTERVAL_MS)
    } catch (err) {
      setError(err.message)
      setPhase('error')
    }
  }, [enabled, labControllerUrl, scenario?.id])

  const handleVerify = useCallback(async () => {
    if (!enabled || !session?.session_token) return
    setPhase('verifying')
    setError(null)
    try {
      const res = await fetch(`${labControllerUrl}/lab/verify/${session.session_token}`, {
        method: 'POST',
        headers: { 'X-API-Key': CONTROLLER_API_KEY }
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setVerifyResults(data)
      setPhase('verified')
    } catch (err) {
      setError(err.message)
      setPhase('ready')
    }
  }, [enabled, labControllerUrl, session?.session_token])

  const handleEndLab = useCallback(async () => {
    if (!enabled) return
    if (session?.session_token) {
      fetch(`${labControllerUrl}/lab/teardown/${session.session_token}`, {
        method: 'POST',
        headers: { 'X-API-Key': CONTROLLER_API_KEY }
      }).catch(err => console.error('Teardown failed:', err))
    }
    resetAll()
  }, [enabled, labControllerUrl, session?.session_token])

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
