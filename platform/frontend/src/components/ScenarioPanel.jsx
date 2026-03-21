import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { loadArtifact } from '../lib/scenarios.js'

const MODE_LABELS = { A: 'Artifact Analysis', B: 'Commission', C: 'Socratic Dialogue', D: 'Transcript Analysis', E: 'Lab Exercise' }

export default function ScenarioPanel({ scenario, onSubmit, isEvaluating }) {
  const [artifactContent, setArtifactContent] = useState(null)
  const [artifactLoading, setArtifactLoading] = useState(false)
  const [response, setResponse] = useState('')
  const [artifactCollapsed, setArtifactCollapsed] = useState(false)
  const textareaRef = useRef(null)

  useEffect(() => {
    setResponse('')
    setArtifactContent(null)
    setArtifactCollapsed(false)
    if (scenario?.presentation?.artifact_file) {
      setArtifactLoading(true)
      loadArtifact(scenario.presentation.artifact_file)
        .then(text => { setArtifactContent(text); setArtifactLoading(false) })
        .catch(() => setArtifactLoading(false))
    }
  }, [scenario?.id])

  if (!scenario) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-600">
        <p className="text-center">Select a scenario from the sidebar to begin.</p>
      </div>
    )
  }

  const { title, domain_name, level, delivery_mode, presentation } = scenario
  const canSubmit = response.trim().length > 20 && !isEvaluating

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit(response.trim(), artifactContent)
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Scenario header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="mb-1 flex items-center gap-2 text-xs text-gray-500">
          <span>{domain_name}</span>
          <span>·</span>
          <span>Level {level}</span>
          <span>·</span>
          <span>{MODE_LABELS[delivery_mode] ?? `Mode ${delivery_mode}`}</span>
        </div>
        <h1 className="text-xl font-semibold text-gray-100">{title}</h1>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-6 py-5">

        {/* Context */}
        <div className="mb-5 rounded-lg bg-gray-800/60 px-4 py-3 text-sm leading-relaxed text-gray-300">
          <ReactMarkdown>{presentation.context ?? ''}</ReactMarkdown>
        </div>

        {/* Artifact */}
        {presentation.artifact_file && (
          <div className="mb-5 rounded-lg border border-gray-700 bg-gray-900">
            <button
              onClick={() => setArtifactCollapsed(c => !c)}
              className="flex w-full items-center justify-between px-4 py-2.5 text-left"
            >
              <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                {presentation.type?.replace(/_/g, ' ') ?? 'Artifact'}
              </span>
              <span className="text-gray-600">{artifactCollapsed ? '▼' : '▲'}</span>
            </button>
            {!artifactCollapsed && (
              artifactLoading
                ? <p className="px-4 pb-4 text-sm text-gray-500">Loading…</p>
                : artifactContent
                  ? <pre className="overflow-x-auto px-4 pb-4 font-mono text-xs leading-relaxed text-gray-300 whitespace-pre-wrap">{artifactContent}</pre>
                  : <p className="px-4 pb-4 text-sm text-gray-500">Artifact file not found.</p>
            )}
          </div>
        )}

        {/* Response */}
        <form onSubmit={handleSubmit}>
          <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-500">
            Your Response
          </label>
          <textarea
            ref={textareaRef}
            value={response}
            onChange={e => setResponse(e.target.value)}
            placeholder={
              delivery_mode === 'B'
                ? 'Write your specification, plan, or document here…'
                : 'Write your analysis here. Identify findings, assess severity, explain your reasoning…'
            }
            rows={10}
            className="mb-3 w-full resize-y rounded-lg bg-gray-800 px-4 py-3 text-sm text-gray-200 placeholder-gray-600 outline-none ring-1 ring-gray-700 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isEvaluating ? 'Evaluating…' : 'Submit for Evaluation'}
          </button>
        </form>
      </div>
    </div>
  )
}
