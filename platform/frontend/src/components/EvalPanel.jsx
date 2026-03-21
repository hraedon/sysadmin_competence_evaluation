const LEVEL_COLORS = ['', 'bg-yellow-900 text-yellow-300', 'bg-blue-900 text-blue-300', 'bg-purple-900 text-purple-300', 'bg-green-900 text-green-300']
const LEVEL_LABELS = ['', 'Awareness', 'Application', 'Analysis', 'Adaptation']

export default function EvalPanel({ result, isEvaluating, error }) {
  if (isEvaluating) {
    return (
      <div className="flex w-80 shrink-0 items-center justify-center border-l border-gray-800 bg-gray-900/50">
        <div className="text-center">
          <div className="mb-2 h-6 w-6 animate-spin rounded-full border-2 border-gray-600 border-t-indigo-500 mx-auto" />
          <p className="text-sm text-gray-500">Evaluating…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex w-80 shrink-0 flex-col border-l border-gray-800 bg-gray-900/50 p-4">
        <p className="mb-2 text-sm font-semibold text-red-400">Evaluation error</p>
        <p className="text-xs text-gray-400">{error}</p>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="flex w-80 shrink-0 items-center justify-center border-l border-gray-800 bg-gray-900/50">
        <p className="text-sm text-gray-600">Evaluation will appear here.</p>
      </div>
    )
  }

  const { parsed, raw } = result

  if (!parsed) {
    return (
      <div className="w-80 shrink-0 overflow-y-auto border-l border-gray-800 bg-gray-900/50 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Raw Evaluation</p>
        <pre className="whitespace-pre-wrap font-mono text-xs text-gray-300">{raw}</pre>
      </div>
    )
  }

  const { level, confidence, caught = [], missed = [], unlisted = [], severity_calibration, gap, narrative } = parsed
  const levelColor = LEVEL_COLORS[level] ?? 'bg-gray-700 text-gray-300'
  const levelLabel = LEVEL_LABELS[level] ?? ''

  return (
    <div className="flex w-80 shrink-0 flex-col overflow-y-auto border-l border-gray-800 bg-gray-900/50">
      <div className="border-b border-gray-800 px-4 py-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Evaluation</p>
        <div className="flex items-center gap-2">
          <span className={`rounded-lg px-3 py-1.5 text-sm font-bold ${levelColor}`}>
            Level {level} — {levelLabel}
          </span>
          <span className="text-xs text-gray-500">{confidence} confidence</span>
        </div>
      </div>

      <div className="flex-1 px-4 py-4 space-y-5 text-sm">

        {/* Narrative */}
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">Assessment</p>
          <p className="leading-relaxed text-gray-300">{narrative}</p>
        </div>

        {/* Gap */}
        {gap && (
          <div className="rounded-lg bg-indigo-950/50 px-3 py-2.5 ring-1 ring-indigo-900">
            <p className="mb-1 text-xs font-semibold text-indigo-400">Next level gap</p>
            <p className="text-xs leading-relaxed text-indigo-200">{gap}</p>
          </div>
        )}

        {/* Findings */}
        {(caught.length > 0 || missed.length > 0) && (
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">Findings</p>
            <div className="space-y-1">
              {caught.map(id => (
                <div key={id} className="flex items-center gap-2 text-xs">
                  <span className="text-green-500">✓</span>
                  <span className="font-mono text-gray-400">{id}</span>
                </div>
              ))}
              {missed.map(id => (
                <div key={id} className="flex items-center gap-2 text-xs">
                  <span className="text-gray-600">○</span>
                  <span className="font-mono text-gray-600">{id}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Severity calibration */}
        {severity_calibration && severity_calibration !== 'accurate' && (
          <div className="rounded-lg bg-amber-950/40 px-3 py-2 ring-1 ring-amber-900/50">
            <p className="text-xs text-amber-400">Severity calibration: {severity_calibration}</p>
          </div>
        )}

        {/* Unlisted findings */}
        {unlisted.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Additional findings credited</p>
            {unlisted.map((desc, i) => (
              <p key={i} className="text-xs text-gray-400">+ {desc}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
