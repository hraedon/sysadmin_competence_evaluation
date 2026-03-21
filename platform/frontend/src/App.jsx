import { useState, useEffect } from 'react'
import { loadManifest, groupByDomain } from './lib/scenarios.js'
import { evaluate } from './lib/evaluator.js'
import { loadProfile, saveResult } from './lib/profile.js'
import ScenarioSidebar from './components/ScenarioSidebar.jsx'
import ScenarioPanel from './components/ScenarioPanel.jsx'
import EvalPanel from './components/EvalPanel.jsx'
import SettingsModal from './components/SettingsModal.jsx'

const API_KEY_STORAGE = 'sysadmin_assessment_api_key'

export default function App() {
  const [groups, setGroups] = useState([])
  const [selected, setSelected] = useState(null)
  const [evalResult, setEvalResult] = useState(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [evalError, setEvalError] = useState(null)
  const [profile, setProfile] = useState(() => loadProfile())
  const [apiKey, setApiKey] = useState(() => localStorage.getItem(API_KEY_STORAGE) ?? '')
  const [showSettings, setShowSettings] = useState(false)
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    loadManifest()
      .then(scenarios => setGroups(groupByDomain(scenarios)))
      .catch(err => setLoadError(err.message))
  }, [])

  // Show settings automatically if no API key
  useEffect(() => {
    if (!apiKey) setShowSettings(true)
  }, [])

  function handleSelectScenario(scenario) {
    setSelected(scenario)
    setEvalResult(null)
    setEvalError(null)
  }

  async function handleSubmit(responseText, artifactContent) {
    if (!apiKey) { setShowSettings(true); return }
    setIsEvaluating(true)
    setEvalResult(null)
    setEvalError(null)
    try {
      const result = await evaluate({ scenario: selected, artifactContent, responseText, apiKey })
      setEvalResult(result)
      if (result.parsed?.level) {
        const updated = saveResult({ scenario: selected, level: result.parsed.level, confidence: result.parsed.confidence })
        setProfile(updated)
      }
    } catch (err) {
      setEvalError(err.message ?? 'Unknown error')
    } finally {
      setIsEvaluating(false)
    }
  }

  function handleSaveKey(key) {
    setApiKey(key)
    localStorage.setItem(API_KEY_STORAGE, key)
    setShowSettings(false)
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {showSettings && (
        <SettingsModal
          apiKey={apiKey}
          onSave={handleSaveKey}
          onClose={apiKey ? () => setShowSettings(false) : undefined}
        />
      )}

      <ScenarioSidebar
        groups={groups}
        selected={selected}
        profile={profile}
        onSelect={handleSelectScenario}
        onSettings={() => setShowSettings(true)}
      />

      {loadError ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="rounded-lg bg-red-900/30 px-6 py-4 text-red-300">
            <p className="font-semibold">Failed to load scenarios</p>
            <p className="text-sm">{loadError}</p>
          </div>
        </div>
      ) : (
        <>
          <ScenarioPanel
            scenario={selected}
            onSubmit={handleSubmit}
            isEvaluating={isEvaluating}
          />
          <EvalPanel
            result={evalResult}
            isEvaluating={isEvaluating}
            error={evalError}
          />
        </>
      )}
    </div>
  )
}
