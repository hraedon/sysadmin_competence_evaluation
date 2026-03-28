import { PROVISION_STEPS } from '../hooks/useLabSession.js'

const STATUS_BADGE = {
  correct:    { label: 'Correct',    cls: 'bg-green-900/50 text-green-300 ring-green-700' },
  workaround: { label: 'Partial',    cls: 'bg-yellow-900/50 text-yellow-300 ring-yellow-700' },
  incomplete: { label: 'Incomplete', cls: 'bg-red-900/50 text-red-300 ring-red-700' },
}

export default function LabInfoPanel({
  scenario,
  phase,
  session,
  verifyResults,
  error,
  provisionStep,
  elapsed,
  handleStartLab,
  handleVerify,
  handleEndLab,
}) {
  const modeE = scenario?.presentation?.modes?.E
  const instructions = modeE?.instructions ?? ''

  return (
    <div className="w-80 shrink-0 flex flex-col overflow-y-auto border-r border-gray-800 bg-gray-900/50">

      {/* Scenario header */}
      <div className="border-b border-gray-800 px-4 py-4">
        <div className="mb-1 flex items-center gap-2 text-xs text-gray-500">
          <span>{scenario.domain_name}</span>
          <span>·</span>
          <span>Level {scenario.level}</span>
        </div>
        <h1 className="text-base font-semibold text-gray-100">{scenario.title}</h1>
        <span className="mt-1 inline-block rounded bg-indigo-900/40 px-1.5 py-0.5 text-xs text-indigo-300">Lab Exercise</span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

        {/* Instructions */}
        <div className="rounded-lg bg-gray-800/60 px-3 py-2.5 text-xs leading-relaxed text-gray-300 whitespace-pre-wrap">
          {instructions}
        </div>

        {/* Error banner */}
        {error && (
          <div className="rounded-lg bg-red-900/30 px-3 py-2.5 text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Idle — start button */}
        {phase === 'idle' && (
          <button
            onClick={handleStartLab}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
          >
            Start Lab
          </button>
        )}

        {/* Error — restart option */}
        {phase === 'error' && (
          <button
            onClick={handleEndLab}
            className="w-full rounded-lg border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:border-gray-400 hover:text-gray-100 transition-colors"
          >
            Try again
          </button>
        )}

        {/* Provisioning / polling — progress bar + elapsed timer */}
        {(phase === 'provisioning' || phase === 'polling') && (
          <div className="space-y-2.5">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
                {provisionStep
                  ? (PROVISION_STEPS.find(s => s.key === provisionStep)?.label ?? provisionStep)
                  : 'Requesting environment…'}
              </div>
              <div className="h-1.5 rounded-full bg-gray-700 overflow-hidden">
                <div
                  className="h-full rounded-full bg-indigo-500 transition-all duration-500 ease-out"
                  style={{ width: `${PROVISION_STEPS.find(s => s.key === provisionStep)?.pct ?? 5}%` }}
                />
              </div>
            </div>
            <p className="text-xs text-gray-500">
              Elapsed: {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, '0')} · Typically 1–2 min
            </p>
          </div>
        )}

        {/* Ready/verified — action buttons */}
        {(phase === 'ready' || phase === 'verifying' || phase === 'verified') && (
          <div className="space-y-2">
            <button
              onClick={handleVerify}
              disabled={phase === 'verifying'}
              className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
            >
              {phase === 'verifying' ? 'Verifying…' : 'Verify'}
            </button>
            <button
              onClick={handleEndLab}
              className="w-full rounded-lg border border-gray-600 px-4 py-2 text-sm text-gray-400 hover:border-gray-400 hover:text-gray-200 transition-colors"
            >
              End lab
            </button>
            {session?.expires_at && (
              <p className="text-xs text-gray-500 text-center">
                Expires {new Date(session.expires_at).toLocaleTimeString()}
              </p>
            )}
          </div>
        )}

        {/* Verification results */}
        {phase === 'verified' && verifyResults && (
          <div className="rounded-lg border border-gray-700 bg-gray-800/40 px-3 py-3 space-y-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Results</h3>
            {verifyResults.map(r => {
              const badge = STATUS_BADGE[r.status] ?? STATUS_BADGE.incomplete
              return (
                <div key={r.finding_id} className="flex items-start gap-2">
                  <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ring-1 ${badge.cls}`}>
                    {badge.label}
                  </span>
                  <div>
                    <p className="text-xs font-mono text-gray-400">{r.finding_id}</p>
                    <p className="text-xs text-gray-300">{r.detail}</p>
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
