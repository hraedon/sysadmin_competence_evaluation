import { useState, useEffect, useRef } from 'react'
import { loadManifest, groupByDomain } from './lib/scenarios.js'
import { evaluate, loadSettings, saveSettings } from './lib/evaluator.js'
import { loadProfile, saveResult, migrateLocalProfile, isOnboardingDismissed, dismissOnboarding } from './lib/profile.js'
import { isAuthenticated, getUser, logout, persistAuth } from './lib/auth.js'
import { useLabSession } from './hooks/useLabSession.js'
import ScenarioSidebar from './components/ScenarioSidebar.jsx'
import ScenarioPanel from './components/ScenarioPanel.jsx'
import EvalPanel from './components/EvalPanel.jsx'
import LabInfoPanel from './components/LabInfoPanel.jsx'
import LabConsole from './components/LabConsole.jsx'
import SettingsPage from './components/SettingsPage.jsx'
import LoginView from './components/LoginView.jsx'
import OnboardingView from './components/OnboardingView.jsx'
import ProfileView from './components/ProfileView.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

export default function App() {
  const [scenarios, setScenarios] = useState([])       // flat manifest
  const [groups, setGroups] = useState([])             // grouped by domain for sidebar
  const [selected, setSelected] = useState(null)
  const [evalResult, setEvalResult] = useState(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [evalError, setEvalError] = useState(null)
  const [profile, setProfile] = useState(() => loadProfile())
  const [settings, setSettings] = useState(() => loadSettings())
  const [activeModal, setActiveModal] = useState(() => {
    const hasResults = Object.keys(loadProfile().domains).length > 0
    return !hasResults && !isOnboardingDismissed() ? 'onboarding' : null
  })
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isDesktop, setIsDesktop] = useState(() => window.matchMedia?.('(min-width: 768px)').matches ?? false)
  const [user, setUser] = useState(() => getUser())
  const [isFirstRun, setIsFirstRun] = useState(() => !isAuthenticated() && !getUser())
  const [loadError, setLoadError] = useState(null)

  const showSettings = activeModal === 'settings'
  const showProfile = activeModal === 'profile'
  const showLogin = activeModal === 'login'
  const showOnboarding = activeModal === 'onboarding'

  // Coach mode state
  const [coachPhase, setCoachPhase] = useState(null)  // null | 'active' | 'resolved' | 'exhausted'
  const [coachRound, setCoachRound] = useState(0)
  const [coachHistory, setCoachHistory] = useState([])
  const [storedArtifact, setStoredArtifact] = useState(null)
  const [storedResponse, setStoredResponse] = useState(null)
  const evaluationGenerationRef = useRef(0)
  const evaluationAbortRef = useRef(null)

  const isLabMode = selected?.delivery_mode === 'E'
  const labSession = useLabSession(selected, settings.labControllerUrl, { enabled: isLabMode })

  useEffect(() => {
    const media = window.matchMedia?.('(min-width: 768px)')
    if (!media) return undefined
    const update = () => setIsDesktop(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  function invalidateEvaluation() {
    evaluationGenerationRef.current += 1
    evaluationAbortRef.current?.abort()
    evaluationAbortRef.current = null
    setIsEvaluating(false)
  }

  useEffect(() => () => invalidateEvaluation(), [])

  useEffect(() => {
    loadManifest()
      .then(loaded => {
        setScenarios(loaded)
        setGroups(groupByDomain(loaded))
      })
      .catch(err => setLoadError(err.message))
  }, [])

  // First-run sequence: explain the assessment before offering sign-in.
  // This keeps the two full-screen overlays mutually exclusive.
  useEffect(() => {
    if (isFirstRun && !activeModal && !user) setActiveModal('login')
  }, [activeModal, isFirstRun, user])

  function openModal(modal) {
    setIsSidebarOpen(false)
    setActiveModal(modal)
  }

  async function handleLogin(loggedInUser, auth) {
    // LoginView only calls us after checking its request was not aborted.
    // Persist here so skipping a pending login can never leave credentials behind.
    if (auth) persistAuth(auth)
    setUser(loggedInUser)
    setIsFirstRun(false)
    setActiveModal(null)
    // Migrate localStorage profile to server on first login
    await migrateLocalProfile()
  }

  function handleLogout() {
    invalidateEvaluation()
    labSession.handleEndLab?.()
    logout()
    setUser(null)
  }

  function resetCoachState() {
    setCoachPhase(null)
    setCoachRound(0)
    setCoachHistory([])
    setStoredArtifact(null)
    setStoredResponse(null)
  }

  function handleSelectScenario(scenario) {
    invalidateEvaluation()
    setIsSidebarOpen(false)
    setSelected(scenario)
    setEvalResult(null)
    setEvalError(null)
    resetCoachState()
  }

  /** Select a scenario from onboarding or profile view — closes the overlay first. */
  function handleSelectFromView(scenario) {
    setActiveModal(null)
    handleSelectScenario(scenario)
  }

  function handleDismissOnboarding() {
    dismissOnboarding()
    setActiveModal(null)
  }

  function handleSkipLogin() {
    setIsFirstRun(false)
    setActiveModal(null)
  }

  async function handleSubmit(responseText, artifactContent) {
    invalidateEvaluation()
    const controller = new AbortController()
    const generation = ++evaluationGenerationRef.current
    evaluationAbortRef.current = controller
    const scenario = selected
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
      const result = await evaluate({ scenario, artifactContent, responseText, settings, coachMode, coachRound: 0, signal: controller.signal })
      if (generation !== evaluationGenerationRef.current || controller.signal.aborted) return
      setEvalResult(result)

      if (result.parsed === null) {
        setEvalError(result.error ?? 'Evaluation failed — the model returned an unreadable response. Try again.')
        return
      }

      if (result.parsed?.level) {
        const updated = saveResult({
          scenario,
          level: result.parsed.level,
          confidence: result.parsed.confidence,
          gap: result.parsed.gap ?? null,
          almost_caught: result.parsed.almost_caught ?? [],
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
      if (generation !== evaluationGenerationRef.current || controller.signal.aborted) return
      setEvalError(err.message ?? 'Unknown error')
    } finally {
      if (generation === evaluationGenerationRef.current) setIsEvaluating(false)
    }
  }

  async function handleFollowUp(followUpText) {
    invalidateEvaluation()
    const controller = new AbortController()
    const generation = ++evaluationGenerationRef.current
    evaluationAbortRef.current = controller
    const scenario = selected
    setIsEvaluating(true)
    setEvalError(null)

    const newHistory = [...coachHistory, { role: 'user', content: followUpText }]

    try {
      const result = await evaluate({
        scenario,
        artifactContent: storedArtifact,
        responseText: storedResponse,
        settings,
        coachMode: true,
        coachRound,
        coachHistory: newHistory,
        signal: controller.signal,
      })
      if (generation !== evaluationGenerationRef.current || controller.signal.aborted) return
      setEvalResult(result)

      if (result.parsed === null) {
        setEvalError(result.error ?? 'Evaluation failed — the model returned an unreadable response. Try again.')
        return
      }

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
      if (generation !== evaluationGenerationRef.current || controller.signal.aborted) return
      setEvalError(err.message ?? 'Unknown error')
    } finally {
      if (generation === evaluationGenerationRef.current) setIsEvaluating(false)
    }
  }

  function handleSaveSettings(newSettings) {
    setSettings(newSettings)
    saveSettings(newSettings)
    setActiveModal(null)
  }

  return (
    <div className="min-h-screen bg-gray-950">

      {/* Full-screen overlays — rendered above everything */}
      {showLogin && (
          <LoginView
            onLogin={handleLogin}
            onSkip={handleSkipLogin}
        />
      )}
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
          onClose={() => setActiveModal(null)}
          onSelect={handleSelectFromView}
        />
      )}
      {showSettings && (
          <SettingsPage
            settings={settings}
            onSave={handleSaveSettings}
            onProfileCleared={() => {
              invalidateEvaluation()
              labSession.handleEndLab?.()
              setEvalResult(null)
              setEvalError(null)
              setProfile(loadProfile())
              setUser(getUser())
              setIsFirstRun(!isAuthenticated() && !getUser())
            }}
            onClose={() => setActiveModal(null)}
          />
      )}

      <div className="min-h-screen md:flex md:h-screen md:overflow-hidden" aria-hidden={activeModal ? true : undefined} inert={activeModal ? '' : undefined}>
      {isSidebarOpen && (
        <button
          aria-label="Close scenario menu"
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
      <button
        aria-label="Open scenario menu"
        aria-expanded={isSidebarOpen}
        className="fixed left-3 top-3 z-20 rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 shadow-lg md:hidden"
        onClick={() => setIsSidebarOpen(true)}
      >
        Scenarios
      </button>
      <ScenarioSidebar
        groups={groups}
        selected={selected}
        profile={profile}
        onSelect={handleSelectScenario}
        onSettings={() => openModal('settings')}
        onProfile={() => openModal('profile')}
        onOnboarding={() => openModal('onboarding')}
        user={user}
        onLogin={() => openModal('login')}
        onLogout={handleLogout}
        isOpen={isSidebarOpen}
        isInert={!isSidebarOpen && !isDesktop}
        onClose={() => setIsSidebarOpen(false)}
      />

      {loadError ? (
        <div className="flex min-h-screen flex-1 items-center justify-center md:min-h-0">
          <div className="rounded-lg bg-red-900/30 px-6 py-4 text-red-300">
            <p className="font-semibold">Failed to load scenarios</p>
            <p className="text-sm">{loadError}</p>
          </div>
        </div>
      ) : (
        <main className={`flex min-w-0 flex-1 flex-col pt-14 md:pt-0 ${isLabMode ? 'md:overflow-y-auto lg:flex-row lg:overflow-hidden' : 'md:flex-row'}`}>
          {isLabMode ? (
            <ErrorBoundary label="The lab panel encountered an error.">
              <LabInfoPanel scenario={selected} {...labSession} />
              <LabConsole session={labSession.session} phase={labSession.phase} />
            </ErrorBoundary>
          ) : (
            <ErrorBoundary label="The scenario panel encountered an error.">
              <ScenarioPanel
                scenario={selected}
                onSubmit={handleSubmit}
                isEvaluating={isEvaluating}
                labControllerUrl={settings.labControllerUrl}
              />
            </ErrorBoundary>
          )}
          <ErrorBoundary label="The evaluation panel encountered an error.">
            <EvalPanel
              result={evalResult}
              isEvaluating={isEvaluating}
              error={evalError}
              coachPhase={coachPhase}
              coachRound={coachRound}
              scenario={selected}
              onFollowUp={handleFollowUp}
              isLabMode={isLabMode}
            />
          </ErrorBoundary>
        </main>
      )}
      </div>
    </div>
  )
}
