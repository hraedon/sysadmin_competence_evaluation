import { useState, useEffect, useRef } from 'react'

const POLL_INTERVAL_MS = 3000

// Returns a stable per-browser user ID stored in localStorage.
function getLocalUserId() {
  const key = 'sysadmin_lab_user_id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(key, id)
  }
  return id
}

const STATUS_BADGE = {
  correct:    { label: 'Correct',    cls: 'bg-green-900/50 text-green-300 ring-green-700' },
  workaround: { label: 'Partial',    cls: 'bg-yellow-900/50 text-yellow-300 ring-yellow-700' },
  incomplete: { label: 'Incomplete', cls: 'bg-red-900/50 text-red-300 ring-red-700' },
}

export default function LabPanel({ scenario, labControllerUrl }) {
  // phase: idle | provisioning | polling | ready | verifying | verified | error
  const [phase, setPhase]             = useState('idle')
  const [session, setSession]         = useState(null)
  const [verifyResults, setVerifyResults] = useState(null)
  const [error, setError]             = useState(null)
  const pollRef = useRef(null)

  // Reset on scenario change
  useEffect(() => {
    setPhase('idle')
    setSession(null)
    setVerifyResults(null)
    setError(null)
    if (pollRef.current) clearInterval(pollRef.current)
  }, [scenario?.id])

  // Clean up poll on unmount
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  async function handleStartLab() {
    if (!labControllerUrl) {
      setError('Lab controller URL is not configured. Set it in Settings.')
      setPhase('error')
      return
    }
    setPhase('provisioning')
    setError(null)
    setVerifyResults(null)

    try {
      const res = await fetch(`${labControllerUrl}/lab/provision/${scenario.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
          const sr = await fetch(`${labControllerUrl}/lab/session/${data.session_token}`)
          if (!sr.ok) return
          const sd = await sr.json()
          if (sd.environment_status === 'busy') {
            clearInterval(pollRef.current)
            setPhase('ready')
          } else if (sd.environment_status === 'faulted') {
            clearInterval(pollRef.current)
            setError('Environment provisioning failed. Check the lab controller logs.')
            setPhase('error')
          }
        } catch { /* transient fetch error — keep polling */ }
      }, POLL_INTERVAL_MS)
    } catch (err) {
      setError(err.message)
      setPhase('error')
    }
  }

  async function handleVerify() {
    setPhase('verifying')
    setError(null)
    try {
      const res = await fetch(`${labControllerUrl}/lab/verify/${session.session_token}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setVerifyResults(data)
      setPhase('verified')
    } catch (err) {
      setError(err.message)
      setPhase('ready')  // allow retry
    }
  }

  async function handleEndLab() {
    // Best-effort teardown request (renew endpoint not available, controller reaps on timeout)
    setPhase('idle')
    setSession(null)
    setVerifyResults(null)
    setError(null)
    if (pollRef.current) clearInterval(pollRef.current)
  }

  const modeE = scenario?.presentation?.modes?.E
  const instructions = modeE?.instructions ?? ''

  return (
    <div className="flex flex-1 flex-col overflow-hidden">

      {/* Scenario header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="mb-1 flex items-center gap-2 text-xs text-gray-500">
          <span>{scenario.domain_name}</span>
          <span>·</span>
          <span>Level {scenario.level}</span>
          <span>·</span>
          <span>Lab Exercise</span>
        </div>
        <h1 className="text-xl font-semibold text-gray-100">{scenario.title}</h1>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

        {/* Instructions */}
        <div className="rounded-lg bg-gray-800/60 px-4 py-3 text-sm leading-relaxed text-gray-300 whitespace-pre-wrap">
          {instructions}
        </div>

        {/* Error banner */}
        {error && (
          <div className="rounded-lg bg-red-900/30 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Idle — start button */}
        {phase === 'idle' && (
          <button
            onClick={handleStartLab}
            className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
          >
            Start Lab
          </button>
        )}

        {/* Error — restart option */}
        {phase === 'error' && (
          <button
            onClick={() => setPhase('idle')}
            className="rounded-lg border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:border-gray-400 hover:text-gray-100 transition-colors"
          >
            Try again
          </button>
        )}

        {/* Provisioning / polling */}
        {(phase === 'provisioning' || phase === 'polling') && (
          <div className="flex items-center gap-3 text-sm text-gray-400">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
            {phase === 'provisioning' ? 'Requesting environment…' : 'Waiting for environment to become ready…'}
          </div>
        )}

        {/* Ready + verified — Guacamole console */}
        {(phase === 'ready' || phase === 'verifying' || phase === 'verified') && session && (
          <>
            <div className="rounded-lg overflow-hidden border border-gray-700" style={{ height: '480px' }}>
              <iframe
                src={session.guacamole_url}
                title="Lab console"
                className="w-full h-full bg-black"
                allow="fullscreen"
              />
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleVerify}
                disabled={phase === 'verifying'}
                className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
              >
                {phase === 'verifying' ? 'Verifying…' : 'Verify'}
              </button>
              <button
                onClick={handleEndLab}
                className="rounded-lg border border-gray-600 px-4 py-2 text-sm text-gray-400 hover:border-gray-400 hover:text-gray-200 transition-colors"
              >
                End lab
              </button>
              {session.expires_at && (
                <span className="text-xs text-gray-500">
                  Expires {new Date(session.expires_at).toLocaleTimeString()}
                </span>
              )}
            </div>
          </>
        )}

        {/* Verification results */}
        {phase === 'verified' && verifyResults && (
          <div className="rounded-lg border border-gray-700 bg-gray-800/40 px-4 py-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Verification Results</h3>
            {verifyResults.map(r => {
              const badge = STATUS_BADGE[r.status] ?? STATUS_BADGE.incomplete
              return (
                <div key={r.finding_id} className="flex items-start gap-3">
                  <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ring-1 ${badge.cls}`}>
                    {badge.label}
                  </span>
                  <div>
                    <p className="text-xs font-mono text-gray-400">{r.finding_id}</p>
                    <p className="text-sm text-gray-300">{r.detail}</p>
                  </div>
                </div>
              )
            })}
          </div>
        )}

      </div>
    </div>
  )
}
