import { useState } from 'react'
import { domainLevel, recommendNext, staleScenariosForReview } from '../lib/profile.js'

const LEVEL_COLORS = ['', 'bg-yellow-900 text-yellow-300', 'bg-blue-900 text-blue-300', 'bg-purple-900 text-purple-300', 'bg-green-900 text-green-300']
const LEVEL_TEXT_COLORS = ['', 'text-yellow-400', 'text-blue-400', 'text-purple-400', 'text-green-400']
const LEVEL_LABELS = ['', 'Awareness', 'Application', 'Analysis', 'Adaptation']

function daysAgo(timestamp) {
  const days = Math.floor((Date.now() - new Date(timestamp).getTime()) / (1000 * 60 * 60 * 24))
  if (days === 0) return 'today'
  if (days === 1) return '1 day ago'
  return `${days} days ago`
}

/** Most recent gap text stored for a domain, or null. */
function mostRecentGap(domainData) {
  return [...domainData.results]
    .filter(r => r.gap)
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))[0]?.gap ?? null
}

/**
 * Full-screen capability profile view.
 *
 * Props:
 *   profile       — loaded profile object from localStorage
 *   allScenarios  — flat manifest array
 *   onClose       — () => void
 *   onSelect      — (scenario) => void: close profile and select scenario
 */
export default function ProfileView({ profile, allScenarios, onClose, onSelect }) {
  const [expanded, setExpanded] = useState(new Set())

  const domains = Object.entries(profile.domains ?? {})
    .map(([d, data]) => ({ domain: Number(d), data }))
    .sort((a, b) => a.domain - b.domain)

  const stale = staleScenariosForReview(profile)
  const totalCompleted = domains.reduce((n, { data }) => n + data.results.length, 0)

  function toggleExpand(domain) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(domain) ? next.delete(domain) : next.add(domain)
      return next
    })
  }

  return (
    <div className="fixed inset-0 z-50 bg-gray-900 overflow-y-auto">

      {/* Sticky header */}
      <div className="sticky top-0 z-10 border-b border-gray-800 bg-gray-900 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-gray-100">Capability Profile</h1>
          <p className="mt-0.5 text-xs text-gray-500">
            {totalCompleted} scenario{totalCompleted !== 1 ? 's' : ''} completed
            {profile.updated ? ` · last updated ${daysAgo(profile.updated)}` : ''}
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg border border-gray-700 px-3 py-1.5 text-sm text-gray-400 hover:border-gray-500 hover:text-gray-200 transition-colors"
        >
          Close
        </button>
      </div>

      <div className="mx-auto max-w-4xl px-6 py-6 space-y-8">

        {/* Empty state */}
        {domains.length === 0 && (
          <div className="rounded-xl border border-gray-800 bg-gray-800/40 px-6 py-12 text-center">
            <p className="text-sm text-gray-400">Complete a scenario to see your profile.</p>
            <button
              onClick={onClose}
              className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
            >
              Go to scenarios
            </button>
          </div>
        )}

        {/* Domain cards */}
        {domains.length > 0 && (
          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Domains</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {domains.map(({ domain, data }) => {
                const level = domainLevel(profile, domain)
                const next = recommendNext(allScenarios, profile, domain)
                const gap = mostRecentGap(data)
                const domainTotal = allScenarios.filter(s => s.domain === domain).length
                const isExpanded = expanded.has(domain)

                return (
                  <div key={domain} className="rounded-xl border border-gray-800 bg-gray-800/40">

                    {/* Clickable header — toggles history */}
                    <button
                      onClick={() => toggleExpand(domain)}
                      className="w-full px-4 pt-4 pb-3 text-left"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-xs text-gray-500">D{domain}</p>
                          <p className="text-sm font-medium leading-snug text-gray-200">{data.domain_name}</p>
                          <p className="mt-0.5 text-xs text-gray-600">
                            {data.results.length} of {domainTotal > 0 ? domainTotal : '?'} completed
                          </p>
                        </div>
                        <div className="ml-3 flex shrink-0 flex-col items-end gap-1.5">
                          {level && (
                            <span className={`rounded px-2 py-0.5 text-xs font-bold ${LEVEL_COLORS[level]}`}>
                              L{level} {LEVEL_LABELS[level]}
                            </span>
                          )}
                          <span className="text-xs text-gray-600">{isExpanded ? '▲' : '▼'}</span>
                        </div>
                      </div>
                    </button>

                    {/* Gap text + next scenario (always visible) */}
                    <div className="px-4 pb-3 space-y-2">
                      {gap && (
                        <p className="text-xs leading-relaxed text-gray-400">{gap}</p>
                      )}
                      {next && (
                        <button
                          onClick={() => onSelect(next)}
                          className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                        >
                          <span>Next: {next.title}</span>
                          <span>→</span>
                        </button>
                      )}
                    </div>

                    {/* Expanded: attempt history */}
                    {isExpanded && (
                      <div className="border-t border-gray-700/60 px-4 py-3 space-y-1.5">
                        {[...data.results]
                          .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                          .map(r => (
                            <div key={r.scenario_id} className="flex items-center justify-between text-xs">
                              <span className="max-w-[200px] truncate text-gray-400">{r.title}</span>
                              <div className="ml-2 flex shrink-0 items-center gap-2">
                                <span className={`font-bold ${LEVEL_TEXT_COLORS[r.level] ?? 'text-gray-400'}`}>
                                  L{r.level}
                                </span>
                                {r.almost_caught?.length > 0 && (
                                  <span className="text-amber-500" title={`${r.almost_caught.length} near miss${r.almost_caught.length > 1 ? 'es' : ''}`}>
                                    ◐{r.almost_caught.length}
                                  </span>
                                )}
                                <span className="text-gray-600">{daysAgo(r.timestamp)}</span>
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {/* Suggested review */}
        {stale.length > 0 && (
          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Suggested Review</h2>
            <div className="space-y-1.5">
              {stale.map(r => {
                const scenario = allScenarios.find(s => s.id === r.scenario_id)
                return (
                  <div
                    key={r.scenario_id}
                    className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-800/30 px-4 py-2.5"
                  >
                    <div className="min-w-0">
                      <span className="text-sm text-gray-300">{r.title}</span>
                      <span className="ml-2 text-xs text-gray-600">
                        D{r.domain} · {LEVEL_LABELS[r.level] ?? `L${r.level}`}
                      </span>
                    </div>
                    <div className="ml-3 flex shrink-0 items-center gap-3">
                      <span className="text-xs text-gray-600">{daysAgo(r.timestamp)}</span>
                      {scenario && (
                        <button
                          onClick={() => onSelect(scenario)}
                          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                        >
                          Revisit →
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )}

      </div>
    </div>
  )
}
