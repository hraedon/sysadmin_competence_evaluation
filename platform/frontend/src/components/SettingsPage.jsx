import { useState } from 'react'
import { buildClient } from '../lib/evaluator.js'

const PROVIDERS = [
  { id: 'local',     label: 'Local (LM Studio / Ollama)', hasEndpoint: true,  hasKey: true  },
  { id: 'anthropic', label: 'Anthropic',                  hasEndpoint: false, hasKey: true  },
  { id: 'openai',    label: 'OpenAI',                     hasEndpoint: false, hasKey: true  },
  { id: 'custom',    label: 'Custom',                     hasEndpoint: true,  hasKey: true  },
]

const MODEL_DEFAULTS = {
  local:     'qwen3-next-80b-a3b-instruct-mlx',
  anthropic: 'claude-sonnet-4-6',
  openai:    'gpt-4o',
  custom:    '',
}

export default function SettingsPage({ settings, onSave, onClose }) {
  const [draft, setDraft] = useState({ ...settings })
  const [testStatus, setTestStatus] = useState(null)   // null | 'testing' | 'ok' | { error: string }
  const [clearConfirm, setClearConfirm] = useState(false)

  const provider = PROVIDERS.find(p => p.id === draft.provider) ?? PROVIDERS[0]

  function setField(key, value) {
    setDraft(d => ({ ...d, [key]: value }))
    setTestStatus(null)
  }

  function handleProviderChange(id) {
    setDraft(d => ({
      ...d,
      provider: id,
      // Reset model to provider default when switching providers
      model: MODEL_DEFAULTS[id] ?? '',
    }))
    setTestStatus(null)
  }

  async function handleTest() {
    setTestStatus('testing')
    try {
      const client = buildClient(draft)
      await client.chat.completions.create({
        model: draft.model,
        max_tokens: 1,
        messages: [{ role: 'user', content: 'ping' }],
      })
      setTestStatus('ok')
    } catch (err) {
      setTestStatus({ error: err.message ?? String(err) })
    }
  }

  function handleSave(e) {
    e.preventDefault()
    onSave(draft)
  }

  function handleExportProfile() {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sysadmin_'))
    const exported = {}
    for (const k of keys) {
      try { exported[k] = JSON.parse(localStorage.getItem(k)) }
      catch { exported[k] = localStorage.getItem(k) }
    }
    const blob = new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `sysadmin-profile-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleClearProfile() {
    if (!clearConfirm) { setClearConfirm(true); return }
    Object.keys(localStorage)
      .filter(k => k.startsWith('sysadmin_') && k !== 'sysadmin_assessment_settings')
      .forEach(k => localStorage.removeItem(k))
    setClearConfirm(false)
  }

  const canSave = draft.model.trim() &&
    (draft.provider === 'local' || draft.apiKey.trim() ||
     (draft.provider === 'custom' && !draft.apiKey.trim()))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 overflow-y-auto py-8">
      <div className="w-full max-w-lg rounded-xl bg-gray-800 shadow-2xl">
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-gray-100">Settings</h2>
          {onClose && (
            <button onClick={onClose} className="text-gray-400 hover:text-gray-200 text-xl leading-none">&times;</button>
          )}
        </div>

        <form onSubmit={handleSave} className="p-6 space-y-6">

          {/* Provider */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">Provider</h3>
            <div className="grid grid-cols-2 gap-2 mb-4">
              {PROVIDERS.map(p => (
                <label key={p.id}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 cursor-pointer text-sm transition-colors
                    ${draft.provider === p.id
                      ? 'border-indigo-500 bg-indigo-950/60 text-gray-100'
                      : 'border-gray-600 text-gray-400 hover:border-gray-500'}`}>
                  <input type="radio" name="provider" value={p.id} checked={draft.provider === p.id}
                    onChange={() => handleProviderChange(p.id)} className="accent-indigo-500" />
                  {p.label}
                </label>
              ))}
            </div>

            {provider.hasEndpoint && (
              <div className="mb-3">
                <label className="block text-xs text-gray-400 mb-1">Endpoint URL</label>
                <input type="text" value={draft.endpoint} onChange={e => setField('endpoint', e.target.value)}
                  placeholder="http://192.168.1.28:1234/v1"
                  className="w-full rounded-lg bg-gray-700 px-3 py-2 font-mono text-sm text-gray-100 placeholder-gray-500 outline-none ring-1 ring-gray-600 focus:ring-indigo-500" />
                {draft.provider === 'local' && draft.endpoint.startsWith('/') && (
                  <p className="mt-1 text-[10px] text-indigo-400/80 leading-tight">Using pod-based reverse proxy to mask internal IP.</p>
                )}
              </div>
            )}

            {provider.hasKey && (
              <div className="mb-3">
                <label className="block text-xs text-gray-400 mb-1">
                  {draft.provider === 'local' ? 'Proxy Secret (Optional)' : 'API Key'}
                </label>
                <input type="password" autoComplete="off" value={draft.apiKey}
                  onChange={e => setField('apiKey', e.target.value)}
                  placeholder={draft.provider === 'local' ? 'your-secret-key' : (draft.provider === 'anthropic' ? 'sk-ant-...' : 'sk-...')}
                  className="w-full rounded-lg bg-gray-700 px-3 py-2 font-mono text-sm text-gray-100 placeholder-gray-500 outline-none ring-1 ring-gray-600 focus:ring-indigo-500" />
                <p className="mt-1 text-xs text-gray-500">
                  {draft.provider === 'local' ? 'Sent as Bearer token if using the Nginx proxy PSK.' : 'Stored in browser localStorage only. Never sent to this platform\'s servers.'}
                </p>
              </div>
            )}

            <div className="mb-3">
              <label className="block text-xs text-gray-400 mb-1">Model</label>
              <input type="text" value={draft.model} onChange={e => setField('model', e.target.value)}
                placeholder="model name"
                className="w-full rounded-lg bg-gray-700 px-3 py-2 font-mono text-sm text-gray-100 placeholder-gray-500 outline-none ring-1 ring-gray-600 focus:ring-indigo-500" />
            </div>

            <div className="flex items-center gap-3">
              <button type="button" onClick={handleTest}
                disabled={testStatus === 'testing' || !draft.model.trim()}
                className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-300 hover:border-gray-400 hover:text-gray-100 disabled:opacity-40 transition-colors">
                {testStatus === 'testing' ? 'Testing…' : 'Test connection'}
              </button>
              {testStatus === 'ok' && (
                <span className="text-sm text-green-400">Connected</span>
              )}
              {testStatus?.error && (
                <span className="text-sm text-red-400 truncate max-w-xs" title={testStatus.error}>
                  {testStatus.error.length > 60 ? testStatus.error.slice(0, 60) + '…' : testStatus.error}
                </span>
              )}
            </div>

            {draft.provider === 'local' && (
              <p className="mt-3 text-xs text-amber-400/80">
                Evaluation quality depends on the model. Run the calibration harness to verify before using with learners.
              </p>
            )}
          </section>

          {/* Evaluator Mode */}
          <section className="border-t border-gray-700 pt-5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">Evaluator Mode</h3>
            <div className="flex gap-2">
              {[
                { id: 'auditor', label: 'Strict Auditor', desc: 'Full evaluation immediately after submission' },
                { id: 'coach',   label: 'Socratic Coach', desc: 'Guided questions before revealing results' },
              ].map(m => (
                <label key={m.id}
                  className={`flex-1 cursor-pointer rounded-lg border p-3 text-sm transition-colors
                    ${draft.evaluatorMode === m.id
                      ? 'border-indigo-500 bg-indigo-950/60'
                      : 'border-gray-600 text-gray-400 hover:border-gray-500'}`}>
                  <input type="radio" name="evaluatorMode" value={m.id}
                    checked={draft.evaluatorMode === m.id}
                    onChange={() => setField('evaluatorMode', m.id)}
                    className="sr-only" />
                  <div className="font-medium text-gray-100">{m.label}</div>
                  <div className="mt-0.5 text-xs text-gray-400">{m.desc}</div>
                </label>
              ))}
            </div>
          </section>

          {/* Data */}
          <section className="border-t border-gray-700 pt-5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">Profile Data</h3>
            <div className="flex gap-2">
              <button type="button" onClick={handleExportProfile}
                className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-300 hover:border-gray-400 hover:text-gray-100 transition-colors">
                Export profile
              </button>
              <button type="button" onClick={handleClearProfile}
                className={`rounded-lg border px-3 py-1.5 text-sm transition-colors
                  ${clearConfirm
                    ? 'border-red-500 bg-red-950/40 text-red-300 hover:bg-red-900/40'
                    : 'border-gray-600 text-gray-300 hover:border-gray-400 hover:text-gray-100'}`}>
                {clearConfirm ? 'Confirm clear' : 'Clear profile'}
              </button>
              {clearConfirm && (
                <button type="button" onClick={() => setClearConfirm(false)}
                  className="text-sm text-gray-400 hover:text-gray-200">
                  Cancel
                </button>
              )}
            </div>
          </section>

          {/* Actions */}
          <div className="flex justify-end gap-2 border-t border-gray-700 pt-4">
            {onClose && (
              <button type="button" onClick={onClose}
                className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:text-gray-200">
                Cancel
              </button>
            )}
            <button type="submit" disabled={!canSave}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40">
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
