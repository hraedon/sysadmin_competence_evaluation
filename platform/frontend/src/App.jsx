import { useState, useEffect } from 'react'
import { loadManifest, groupByDomain } from './lib/scenarios.js'
import { evaluate, loadSettings, saveSettings } from './lib/evaluator.js'
import { loadProfile, saveResult, isOnboardingDismissed, dismissOnboarding } from './lib/profile.js'
import ScenarioSidebar from './components/ScenarioSidebar.jsx'
import ScenarioPanel from './components/ScenarioPanel.jsx'
import EvalPanel from './components/EvalPanel.jsx'
import SettingsPage from './components/SettingsPage.jsx'
import OnboardingView from './components/OnboardingView.jsx'
import ProfileView from './components/ProfileView.jsx'

export default function App() {
  const [scenarios, setScenarios] = useState([])       // flat manifest
  const [groups, setGroups] = useState([])             // grouped by domain for sidebar
  const [selected, setSelected] = useState(null)
  const [evalResult, setEvalResult] = useState(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [evalError, setEvalError] = useState(null)
  const [profile, setProfile] = useState(() => loadProfile())
  const [settings, setSettings] = useState(() => loadSettings())
  const [showSettings, setShowSettings] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [loadError, setLoadError] = useState(null)

  // Onboarding: show on first visit (no profile results and not previously dismissed)
  const [showOnboarding, setShowOnboarding] = useState(() => {
    const hasResults = Object.keys(loadProfile().domains).length > 0
    return !hasResults && !isOnboardingDismissed()
  })

  // Coach mode state
  const [coachPhase, setCoachPhase] = useState(null)  // null | 'active' | 'resolved' | 'exhausted'
  const [coachRound, setCoachRound] = useState(0)
  const [coachHistory, setCoachHistory] = useState([])
  const [storedArtifact, setStoredArtifact] = useState(null)
  const [storedResponse, setStoredResponse] = useState(null)

  useEffect(() => {
    loadManifest()
      .then(loaded => {
        setScenarios(loaded)
        setGroups(groupByDomain(loaded))
      })
      .catch(err => setLoadError(err.message))
  }, [])

  // Auto-open settings only when a key-requiring provider is configured without a key
  useEffect(() => {
    const needsKey = (settings.provider === 'anthropic' || settings.provider === 'openai') && !settings.apiKey
    if (needsKey) setShowSettings(true)
  }, [])

  function resetCoachState() {
    setCoachPhase(null)
    setCoachRound(0)
    setCoachHistory([])
    setStoredArtifact(null)
    setStoredResponse(null)
  }

  function handleSelectScenario(scenario) {
    setSelected(scenario)
    setEvalResult(null)
    setEvalError(null)
    resetCoachState()
  }

  /** Select a scenario from onboarding or profile view — closes the overlay first. */
  function handleSelectFromView(scenario) {
    setShowOnboarding(false)
    setShowProfile(false)
    handleSelectScenario(scenario)
  }

  function handleDismissOnboarding() {
    dismissOnboarding()
    setShowOnboarding(false)
  }

  async function handleSubmit(responseText, artifactContent) {
    const coachMode = settings.evaluatorMode === 'coach'
    setIsEvaluating(true)
    setEvalResult(null)
    setEvalError(null)
    resetCoachState()

    if (coachMode) {
      setStoredArtifact(artifactContent)
      setStoredResponse(responseText)
    }

    try {
      const result = await evaluate({ scenario: selected, artifactContent, responseText, settings, coachMode, coachRound: 0 })
      setEvalResult(result)

      if (result.parsed?.level) {
        const updated = saveResult({
          scenario: selected,
          level: result.parsed.level,
          confidence: result.parsed.confidence,
          gap: result.parsed.gap ?? null,
        })
        setProfile(updated)
      }

      if (coachMode && result.parsed) {
        if (result.parsed.coach_question) {
          setCoachPhase('active')
          setCoachRound(1)
          setCoachHistory([{ role: 'assistant', content: result.parsed.coach_question }])
        } else {
          // No findings missed — coaching auto-resolves
          setCoachPhase('resolved')
        }
      }
    } catch (err) {
      setEvalError(err.message ?? 'Unknown error')
    } finally {
      setIsEvaluating(false)
    }
  }

  async function handleFollowUp(followUpText) {
    setIsEvaluating(true)
    setEvalError(null)

    const newHistory = [...coachHistory, { role: 'user', content: followUpText }]

    try {
      const result = await evaluate({
        scenario: selected,
        artifactContent: storedArtifact,
        responseText: storedResponse,
        settings,
        coachMode: true,
        coachRound,
        coachHistory: newHistory,
      })
      setEvalResult(result)

      if (result.parsed?.resolved === true) {
        setCoachPhase('resolved')
        setCoachHistory([])
        setCoachRound(0)
      } else if (coachRound >= 3 || !result.parsed?.coach_question) {
        setCoachPhase('exhausted')
        setCoachHistory([])
        setCoachRound(0)
      } else {
        const updatedHistory = [...newHistory, { role: 'assistant', content: result.parsed.coach_question }]
        setCoachHistory(updatedHistory)
        setCoachRound(r => r + 1)
      }
    } catch (err) {
      setEvalError(err.message ?? 'Unknown error')
    } finally {
      setIsEvaluating(false)
    }
  }

  function handleSaveSettings(newSettings) {
    setSettings(newSettings)
    saveSettings(newSettings)
    setShowSettings(false)
  }

  return (
    <div className="flex h-screen overflow-hidden">

      {/* Full-screen overlays — rendered above everything */}
      {showOnboarding && (
        <OnboardingView
          allScenarios={scenarios}
          onDismiss={handleDismissOnboarding}
          onSelect={handleSelectFromView}
        />
      )}
      {showProfile && (
        <ProfileView
          profile={profile}
          allScenarios={scenarios}
          onClose={() => setShowProfile(false)}
          onSelect={handleSelectFromView}
        />
      )}
      {showSettings && (
        <SettingsPage
          settings={settings}
          onSave={handleSaveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}

      <ScenarioSidebar
        groups={groups}
        selected={selected}
        profile={profile}
        onSelect={handleSelectScenario}
        onSettings={() => setShowSettings(true)}
        onProfile={() => setShowProfile(true)}
        onOnboarding={() => setShowOnboarding(true)}
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
            coachPhase={coachPhase}
            coachRound={coachRound}
            scenario={selected}
            onFollowUp={handleFollowUp}
          />
        </>
      )}
    </div>
  )
}
