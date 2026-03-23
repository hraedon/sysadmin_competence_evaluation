const LEVEL_COLORS = ['', 'bg-yellow-900 text-yellow-300', 'bg-blue-900 text-blue-300', 'bg-purple-900 text-purple-300', 'bg-green-900 text-green-300']
const LEVEL_LABELS = ['', 'Awareness', 'Application', 'Analysis', 'Adaptation']
const LEVEL_DESCRIPTIONS = [
  '',
  'You can read a system and describe what it is doing. Observation with minimal interpretation.',
  'You can identify risks, gaps, and violations in a system you are auditing. You know what to look for.',
  'You can specify what should be done — write the change plan, escalation, or specification. You can explain your reasoning.',
  'You can reason under uncertainty, calibrate severity accurately, and handle edge cases the scenario did not prepare you for.',
]

const HOW_IT_WORKS = [
  ['Select a scenario', 'Read the context and the artifact — a script, a log, a change plan, a certificate chain.'],
  ['Write your analysis', 'Describe what you see, what concerns you, what you would do. There is no time limit.'],
  ['Receive evaluation', 'The AI assesses your response against a calibrated rubric and identifies what you caught, what you missed, and what separates your current level from the next.'],
]

/**
 * First-run overlay explaining the framework and suggesting a starting scenario.
 *
 * Props:
 *   allScenarios  — flat manifest array (used to pick a starting suggestion)
 *   onDismiss     — close without selecting a scenario
 *   onSelect      — (scenario) => void: close and select a scenario
 */
export default function OnboardingView({ allScenarios, onDismiss, onSelect }) {
  // Lowest-difficulty uncompleted scenario in D01 — sensible cold-start
  const suggested = allScenarios
    .filter(s => s.domain === 1)
    .sort((a, b) => (a.level - b.level) || ((a.difficulty ?? 3) - (b.difficulty ?? 3)))[0] ?? null

  function handleBegin() {
    if (suggested) onSelect(suggested)
    onDismiss()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 overflow-y-auto py-8 px-4">
      <div className="w-full max-w-2xl rounded-xl bg-gray-800 shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-700">
          <h2 className="text-base font-semibold text-gray-100">Modern Systems Administration Assessment</h2>
          <button onClick={onDismiss} className="text-gray-400 hover:text-gray-200 text-xl leading-none">&times;</button>
        </div>

        <div className="p-6 space-y-6">

          {/* What this is */}
          <p className="text-sm leading-relaxed text-gray-300">
            This platform assesses applied reasoning — what you actually do when faced with an
            unfamiliar system, an ambiguous log, or a change plan that doesn't add up.
            It doesn't test whether you've memorized the right answers. It tests whether you
            can think through the right questions.
          </p>

          {/* The four levels */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">The Four Levels</h3>
            <div className="grid grid-cols-2 gap-2">
              {[1, 2, 3, 4].map(l => (
                <div key={l} className="rounded-lg bg-gray-900/60 px-3 py-2.5 ring-1 ring-gray-700">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${LEVEL_COLORS[l]}`}>
                      L{l}
                    </span>
                    <span className="text-sm font-medium text-gray-200">{LEVEL_LABELS[l]}</span>
                  </div>
                  <p className="text-xs leading-relaxed text-gray-400">{LEVEL_DESCRIPTIONS[l]}</p>
                </div>
              ))}
            </div>
          </section>

          {/* How it works */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">How a Session Works</h3>
            <ol className="space-y-2">
              {HOW_IT_WORKS.map(([title, desc], i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="mt-0.5 shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-900 text-xs font-bold text-indigo-300">
                    {i + 1}
                  </span>
                  <span>
                    <span className="font-medium text-gray-200">{title} — </span>
                    <span className="text-gray-400">{desc}</span>
                  </span>
                </li>
              ))}
            </ol>
          </section>

          {/* Profile callout */}
          <div className="rounded-lg bg-indigo-950/30 px-4 py-3 ring-1 ring-indigo-900/50">
            <p className="text-sm text-indigo-200">
              After each scenario, your result is stored locally and builds a capability profile —
              a map of where you stand across the 14 domains of the framework. Nothing leaves your
              browser except the evaluation API call.
            </p>
          </div>

          {/* Start here */}
          <div className="flex items-center justify-between gap-4 border-t border-gray-700 pt-4">
            {suggested ? (
              <>
                <div>
                  <p className="text-xs text-gray-500 mb-0.5">Suggested first scenario</p>
                  <p className="text-sm font-medium text-gray-200">{suggested.title}</p>
                  <p className="text-xs text-gray-500">D{suggested.domain} — {suggested.domain_name}</p>
                </div>
                <button
                  onClick={handleBegin}
                  className="shrink-0 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
                >
                  Begin
                </button>
              </>
            ) : (
              <button
                onClick={onDismiss}
                className="w-full rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
              >
                Begin
              </button>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
