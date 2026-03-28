import { useState } from 'react'

const MODE_COLORS = {
  A: 'bg-blue-900 text-blue-300',
  B: 'bg-green-900 text-green-300',
  C: 'bg-purple-900 text-purple-300',
  D: 'bg-orange-900 text-orange-300',
  E: 'bg-red-900 text-red-300',
}

const LEVEL_COLORS = ['', 'text-yellow-400', 'text-blue-400', 'text-purple-400', 'text-green-400']

function Badge({ children, className }) {
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${className}`}>
      {children}
    </span>
  )
}

export default function ScenarioSidebar({ groups, selected, profile, onSelect, onSettings, onProfile, onOnboarding, user, onLogin, onLogout }) {
  const [filter, setFilter] = useState('')
  const query = filter.toLowerCase()

  const domainCount = Object.keys(profile?.domains ?? {}).length

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-gray-800 bg-gray-900">

      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
        <span className="text-sm font-semibold text-gray-200">Scenarios</span>
        <div className="flex items-center gap-1">
          <button
            onClick={onOnboarding}
            title="How this works"
            className="rounded p-1 text-gray-500 hover:text-gray-300 text-base font-bold leading-none"
          >
            ?
          </button>
          <button
            onClick={onSettings}
            title="Settings"
            className="rounded p-1 text-gray-500 hover:text-gray-300"
          >
            ⚙
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="px-3 pt-3">
        <input
          type="search"
          placeholder="Filter…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="w-full rounded-md bg-gray-800 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-600 outline-none ring-1 ring-gray-700 focus:ring-indigo-500"
        />
      </div>

      {/* Scenario list */}
      <nav className="mt-2 flex-1 overflow-y-auto px-2 pb-4">
        {groups.map(group => {
          const visible = group.scenarios.filter(s =>
            !query || s.title.toLowerCase().includes(query) || s.domain_name.toLowerCase().includes(query)
          )
          if (!visible.length) return null

          return (
            <div key={group.domain} className="mb-4">
              <div className="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                D{group.domain} — {group.domain_name}
              </div>
              {visible.map(s => {
                const isActive = selected?.id === s.id
                const domainResult = profile?.domains?.[s.domain]?.results?.find(r => r.scenario_id === s.id)
                return (
                  <button
                    key={s.id}
                    onClick={() => onSelect(s)}
                    className={`mb-0.5 w-full rounded-lg px-3 py-2 text-left transition-colors ${
                      isActive ? 'bg-indigo-900/60 ring-1 ring-indigo-700' : 'hover:bg-gray-800'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span className={`mt-0.5 shrink-0 text-xs font-bold ${LEVEL_COLORS[s.level] ?? 'text-gray-400'}`}>
                        L{s.level}
                      </span>
                      <span className="flex-1 text-sm leading-snug text-gray-200">{s.title}</span>
                      <div className="flex shrink-0 flex-col items-end gap-1">
                        <Badge className={MODE_COLORS[s.delivery_mode] ?? 'bg-gray-700 text-gray-300'}>
                          {s.delivery_mode}
                        </Badge>
                        {domainResult && (
                          <span className={`text-xs font-bold ${LEVEL_COLORS[domainResult.level] ?? ''}`}>
                            ✓{domainResult.level}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          )
        })}
      </nav>

      {/* Profile button */}
      <div className="border-t border-gray-800 px-3 py-3">
        <button
          onClick={onProfile}
          className="w-full rounded-lg border border-gray-700 py-2 text-sm text-gray-400 hover:border-gray-500 hover:text-gray-200 transition-colors"
        >
          View Profile
          {domainCount > 0 && (
            <span className="ml-2 text-xs text-gray-600">
              {domainCount} domain{domainCount !== 1 ? 's' : ''}
            </span>
          )}
        </button>
      </div>

      {/* Auth indicator */}
      <div className="border-t border-gray-800 px-3 py-2">
        {user ? (
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 truncate" title={user.username}>{user.username}</span>
            <button onClick={onLogout} className="text-xs text-gray-500 hover:text-gray-300">
              Sign out
            </button>
          </div>
        ) : (
          <button
            onClick={onLogin}
            className="w-full text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Sign in to sync profile across devices
          </button>
        )}
      </div>

    </aside>
  )
}
