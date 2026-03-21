import { useState } from 'react'

export default function SettingsModal({ apiKey, onSave, onClose }) {
  const [value, setValue] = useState(apiKey ?? '')

  function submit(e) {
    e.preventDefault()
    const trimmed = value.trim()
    if (trimmed) onSave(trimmed)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="w-full max-w-md rounded-xl bg-gray-800 p-6 shadow-2xl">
        <h2 className="mb-1 text-lg font-semibold text-gray-100">Anthropic API Key</h2>
        <p className="mb-4 text-sm text-gray-400">
          Your key is stored only in your browser's localStorage and sent directly to the Anthropic API.
          It never touches a server operated by this platform.
        </p>
        <form onSubmit={submit}>
          <input
            type="password"
            autoComplete="off"
            placeholder="sk-ant-..."
            value={value}
            onChange={e => setValue(e.target.value)}
            className="mb-4 w-full rounded-lg bg-gray-700 px-3 py-2 font-mono text-sm text-gray-100 placeholder-gray-500 outline-none ring-1 ring-gray-600 focus:ring-indigo-500"
          />
          <div className="flex justify-end gap-2">
            {onClose && (
              <button type="button" onClick={onClose}
                className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:text-gray-200">
                Cancel
              </button>
            )}
            <button type="submit"
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
              disabled={!value.trim()}>
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
