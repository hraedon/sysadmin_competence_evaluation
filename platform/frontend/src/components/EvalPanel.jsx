import { useState, useEffect } from 'react'

const LEVEL_COLORS = ['', 'bg-yellow-900 text-yellow-300', 'bg-blue-900 text-blue-300', 'bg-purple-900 text-purple-300', 'bg-green-900 text-green-300']
const LEVEL_LABELS = ['', 'Awareness', 'Application', 'Analysis', 'Adaptation']
const PANEL_CLASS = 'w-full shrink-0 border-t border-gray-800 bg-gray-900/50 md:w-80 md:border-l md:border-t-0'

/** Look up a learning_note from the scenario rubric by finding ID. */
function getLearningNote(scenario, findingId, learningNotes) {
  if (learningNotes?.[findingId]) return learningNotes[findingId]
  if (!scenario?.rubric) return null
  const all = [
    ...(scenario.rubric.critical_findings ?? []),
    ...(scenario.rubric.secondary_findings ?? []),
  ]
  return all.find(f => f.id === findingId)?.learning_note ?? null
}

/** Full evaluation view — used in auditor mode and after coach session ends. */
function FullEval({ parsed, scenario, learningNotes, showLearningNotes = false }) {
  const [expandedNotes, setExpandedNotes] = useState({})
  const { level, confidence, caught = [], missed = [], almost_caught = [], unlisted = [], severity_calibration, gap, narrative } = parsed
  const levelColor = LEVEL_COLORS[level] ?? 'bg-gray-700 text-gray-300'
  const levelLabel = LEVEL_LABELS[level] ?? ''

  function toggleNote(id) {
    setExpandedNotes(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <>
      {/* Level badge */}
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
        {(caught.length > 0 || almost_caught.length > 0 || missed.length > 0) && (
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">Findings</p>
            <div className="space-y-1.5">
              {caught.map(id => (
                <div key={id} className="flex items-center gap-2 text-xs">
                  <span className="text-green-500">✓</span>
                  <span className="font-mono text-gray-400">{id}</span>
                </div>
              ))}
              {almost_caught.map(id => (
                <div key={id} className="flex items-center gap-2 text-xs">
                  <span className="text-amber-500">◐</span>
                  <span className="font-mono text-amber-400/70">{id}</span>
                  <span className="text-amber-600 text-[10px]">near miss</span>
                </div>
              ))}
              {missed.map(id => {
                const note = getLearningNote(scenario, id, learningNotes)
                return (
                  <div key={id}>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-600">○</span>
                      <span className="font-mono text-gray-600">{id}</span>
                      {note && (
                        <button
                          onClick={() => toggleNote(id)}
                          className="ml-auto text-indigo-500 hover:text-indigo-400 transition-colors"
                        >
                          {expandedNotes[id] ? 'hide' : 'explain'}
                        </button>
                      )}
                    </div>
                    {/* Learning note — shown on demand (auditor) or always (exhausted coach) */}
                    {note && (showLearningNotes || expandedNotes[id]) && (
                      <div className="mt-1.5 ml-4 rounded-lg bg-gray-800/80 px-3 py-2.5 ring-1 ring-gray-700">
                        <p className="mb-1 text-xs font-semibold text-indigo-400">Concept note</p>
                        <p className="text-xs leading-relaxed text-gray-300 whitespace-pre-wrap">{note}</p>
                      </div>
                    )}
                  </div>
                )
              })}
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
    </>
  )
}

export default function EvalPanel({ result, isEvaluating, error, coachPhase, coachRound, scenario, onFollowUp, isLabMode = false }) {
  const [followUpText, setFollowUpText] = useState('')
  const [collapsed, setCollapsed] = useState(true)
  const panelClass = isLabMode
    ? 'w-full shrink-0 border-t border-gray-800 bg-gray-900/50 lg:w-80 lg:border-l lg:border-t-0'
    : PANEL_CLASS

  useEffect(() => {
    setCollapsed(isLabMode)
  }, [isLabMode, scenario?.id])

  // Clear follow-up input when coaching phase changes
  useEffect(() => {
    setFollowUpText('')
  }, [coachPhase])

  // Auto-expand when results arrive in lab mode
  useEffect(() => {
    if (isLabMode && result) setCollapsed(false)
  }, [isLabMode, result])

  // Reset collapsed state when switching away from lab mode
  useEffect(() => {
    if (!isLabMode) setCollapsed(false)
  }, [isLabMode])

  // Collapsed strip for lab mode
  if (isLabMode && collapsed && !isEvaluating && !error) {
    return (
      <div className="flex h-10 w-full shrink-0 items-center border-t border-gray-800 bg-gray-900/50 lg:h-auto lg:w-10 lg:flex-col lg:border-l lg:border-t-0">
        <button
          onClick={() => setCollapsed(false)}
          className="mt-3 p-1.5 rounded hover:bg-gray-800 text-gray-500 hover:text-gray-300 transition-colors"
          title="Expand evaluation panel"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>
    )
  }

  // ── Loading ──────────────────────────────────────────────────────────────
  if (isEvaluating) {
    return (
        <div className={`flex min-h-32 items-center justify-center ${panelClass}`}>
        <div className="text-center">
          <div className="mb-2 h-6 w-6 animate-spin rounded-full border-2 border-gray-600 border-t-indigo-500 mx-auto" />
          <p className="text-sm text-gray-500">
            {coachPhase === 'active' ? 'Thinking…' : 'Evaluating…'}
          </p>
        </div>
      </div>
    )
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (error) {
    return (
        <div className={`flex min-h-32 flex-col p-4 ${panelClass}`}>
        <p className="mb-2 text-sm font-semibold text-red-400">Evaluation error</p>
        <p className="text-xs text-gray-400">{error}</p>
      </div>
    )
  }

  // ── Empty state ──────────────────────────────────────────────────────────
  if (!result) {
    return (
        <div className={`flex min-h-32 flex-col ${panelClass}`}>
        {isLabMode && (
          <button
            onClick={() => setCollapsed(true)}
            className="self-start m-2 p-1.5 rounded hover:bg-gray-800 text-gray-500 hover:text-gray-300 transition-colors"
            title="Collapse panel"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-gray-600">Evaluation will appear here.</p>
        </div>
      </div>
    )
  }

  const { parsed, raw } = result

  // ── Raw fallback (JSON parse failed) ─────────────────────────────────────
  if (!parsed) {
    return (
      <div className={`overflow-visible p-4 md:overflow-y-auto ${panelClass}`}>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Raw Evaluation</p>
        <pre className="whitespace-pre-wrap font-mono text-xs text-gray-300">{raw}</pre>
      </div>
    )
  }

  // ── Coach mode: active (coaching in progress) ─────────────────────────────
  if (coachPhase === 'active') {
    const { level, confidence, narrative, coach_question } = parsed
    const levelColor = LEVEL_COLORS[level] ?? 'bg-gray-700 text-gray-300'
    const levelLabel = LEVEL_LABELS[level] ?? ''
    const canRespond = followUpText.trim().length > 5

    return (
      <div className={`flex flex-col overflow-visible md:overflow-y-auto ${panelClass}`}>
        {/* Level badge */}
        <div className="border-b border-gray-800 px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Coach Mode</p>
            <span className="text-xs text-gray-600">round {coachRound} of 3</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`rounded-lg px-3 py-1.5 text-sm font-bold ${levelColor}`}>
              Level {level} — {levelLabel}
            </span>
            <span className="text-xs text-gray-500">{confidence} confidence</span>
          </div>
        </div>

        <div className="flex-1 px-4 py-4 space-y-4 text-sm">
          {/* Narrative */}
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">Assessment</p>
            <p className="leading-relaxed text-gray-300">{narrative}</p>
          </div>

          {/* Coaching question */}
          {coach_question && (
            <div className="rounded-lg bg-indigo-950/60 px-3 py-3 ring-1 ring-indigo-800">
              <p className="mb-1.5 text-xs font-semibold text-indigo-400">Consider this</p>
              <p className="text-sm leading-relaxed text-indigo-100">{coach_question}</p>
            </div>
          )}

          {/* Follow-up input */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Your response
            </label>
            <textarea
              value={followUpText}
              onChange={e => setFollowUpText(e.target.value)}
              placeholder="Respond to the question above…"
              rows={5}
              className="mb-2 w-full resize-y rounded-lg bg-gray-800 px-3 py-2.5 text-sm text-gray-200 placeholder-gray-600 outline-none ring-1 ring-gray-700 focus:ring-indigo-500"
            />
            <button
              disabled={!canRespond}
              onClick={() => { onFollowUp(followUpText); setFollowUpText('') }}
              className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Respond
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Coach mode: resolved (learner found it) ───────────────────────────────
  if (coachPhase === 'resolved') {
    return (
      <div className={`flex flex-col overflow-visible md:overflow-y-auto ${panelClass}`}>
        <div className="border-b border-gray-800 px-4 py-3">
          <p className="text-sm font-semibold text-green-400">You got there.</p>
          <p className="mt-0.5 text-xs text-gray-500">Here's the full picture.</p>
        </div>
        <FullEval parsed={parsed} scenario={scenario} learningNotes={result.learning_notes} />
      </div>
    )
  }

  // ── Coach mode: exhausted (3 rounds without resolution) ───────────────────
  if (coachPhase === 'exhausted') {
    return (
      <div className={`flex flex-col overflow-visible md:overflow-y-auto ${panelClass}`}>
        <div className="border-b border-gray-800 px-4 py-3">
          <p className="text-sm font-semibold text-amber-400">Let's look at this together.</p>
          <p className="mt-0.5 text-xs text-gray-500">Here's the full evaluation after your coaching rounds.</p>
        </div>
        <FullEval parsed={parsed} scenario={scenario} learningNotes={result.learning_notes} showLearningNotes={true} />
      </div>
    )
  }

  // ── Auditor mode (default) ────────────────────────────────────────────────
  return (
    <div className={`flex flex-col overflow-visible md:overflow-y-auto ${panelClass}`}>
      <FullEval parsed={parsed} scenario={scenario} learningNotes={result.learning_notes} />
    </div>
  )
}
