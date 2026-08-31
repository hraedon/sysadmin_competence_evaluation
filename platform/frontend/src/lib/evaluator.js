import OpenAI from 'openai'
import { buildSystemPrompt, performEvaluation } from '../../../../core/evaluator.js'
import { isAuthenticated, authFetch } from './auth.js'

// ---------------------------------------------------------------------------
// Settings schema and persistence
// ---------------------------------------------------------------------------

export const SETTINGS_KEY = 'sysadmin_assessment_settings'
const LEGACY_KEY = 'sysadmin_assessment_api_key'
export const EVALUATION_MODE = import.meta.env.VITE_EVALUATION_MODE === 'server' ? 'server' : 'local'

const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
const LOCAL_PROXY_ENDPOINT = '/llm-proxy/v1'
// Dev default for the local LLM endpoint. Override per-machine via
// VITE_LOCAL_LLM_ENDPOINT in platform/frontend/.env.local (gitignored);
// the hardcoded fallback is the author's LM Studio host.
const INTERNAL_LOCAL_ENDPOINT = import.meta.env.VITE_LOCAL_LLM_ENDPOINT ?? 'http://192.168.1.28:1234/v1'

export const DEFAULT_SETTINGS = {
  provider: EVALUATION_MODE === 'server' ? 'anthropic' : 'local',
  endpoint: IS_PRODUCTION ? LOCAL_PROXY_ENDPOINT : INTERNAL_LOCAL_ENDPOINT,
  apiKey: '',
  model: 'qwen3-next-80b-a3b-instruct-mlx',
  evaluatorMode: 'auditor',
  labControllerUrl: IS_PRODUCTION ? 'https://learning.hraedon.com' : 'http://localhost:8000',
}

/** Load settings from localStorage, migrating legacy keys and ensuring modern defaults. */
export function loadSettings() {
  const stored = localStorage.getItem(SETTINGS_KEY)
  if (stored) {
    try {
      const storedSettings = JSON.parse(stored)
      const settings = { ...DEFAULT_SETTINGS, ...storedSettings }
      if (settings.provider === 'custom') settings.provider = 'local'
      if (EVALUATION_MODE === 'server' && settings.provider === 'local') settings.provider = DEFAULT_SETTINGS.provider
      if (settings.provider === 'anthropic' || settings.provider === 'openai') settings.apiKey = ''

      // If the user has the default "internal" IP but is in production,
      // upgrade them to the proxy endpoint automatically.
      if (IS_PRODUCTION && settings.endpoint === INTERNAL_LOCAL_ENDPOINT) {
        settings.endpoint = LOCAL_PROXY_ENDPOINT
      }

      if (JSON.stringify(settings) !== JSON.stringify(storedSettings)) saveSettings(settings)
      return settings
    } catch {
      // fall through to defaults
    }
  }
  // The legacy value is a commercial browser credential. Do not migrate it.
  if (localStorage.getItem(LEGACY_KEY)) {
    localStorage.removeItem(LEGACY_KEY)
  }
  return { ...DEFAULT_SETTINGS }
}

/** Persist settings to localStorage. */
export function saveSettings(settings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
}

// ---------------------------------------------------------------------------
// Provider abstraction (used only for local/air-gapped mode)
// ---------------------------------------------------------------------------

/**
 * Build an OpenAI-compatible client for local evaluation.
 *
 * SECURITY: This function is restricted to the 'local' provider only.
 * Commercial providers (anthropic, openai) must route through the
 * server-side /api/evaluate endpoint — never instantiate an API client
 * in the browser with a real API key.  dangerouslyAllowBrowser is
 * acceptable here because local providers (LM Studio, Ollama) use no
 * secret — the API key is a dummy placeholder.
 *
 * @throws {Error} if called with a non-local provider.
 */
export function buildClient({ provider = 'local', endpoint, apiKey }) {
  if (provider !== 'local') {
    throw new Error(
      `buildClient() refuses to create a browser-side client for provider '${provider}'. ` +
      'Commercial providers must route through /api/evaluate (server-side). ' +
      'This guard prevents API key exposure via browser-side client creation.'
    )
  }

  let baseURL = endpoint ?? (IS_PRODUCTION ? LOCAL_PROXY_ENDPOINT : INTERNAL_LOCAL_ENDPOINT)

  if (baseURL.startsWith('/')) {
    baseURL = window.location.origin + baseURL
  }

  const key = apiKey || 'lm-studio'
  return new OpenAI({ baseURL, apiKey: key, dangerouslyAllowBrowser: true })
}

// ---------------------------------------------------------------------------
// Evaluation
// ---------------------------------------------------------------------------

/**
 * Call the configured provider and return a parsed evaluation result.
 *
 * - Local mode: evaluates client-side via core/evaluator.js (for air-gapped use).
 * - All other providers: calls POST /api/evaluate on the backend, which loads
 *   the rubric server-side and calls the AI model. The browser never sees the
 *   rubric (SEC-03/SEC-05 closed).
 */
export async function evaluate({ scenario, artifactContent, responseText, settings, coachMode = false, coachRound = 0, coachHistory = [], isRetry = false, signal }) {
  // A server build deliberately has no rubric, irrespective of stale settings.
  // A local build can still deliberately use the server proxy.
  if (EVALUATION_MODE === 'local' && settings.provider === 'local') {
    const client = buildClient(settings)
    return performEvaluation({
      client,
      model: settings.model,
      scenario,
      artifactContent,
      responseText,
      coachMode,
      coachRound,
      coachHistory,
      isRetry
    }, signal ? { signal } : undefined)
  }

  // Server-side evaluation via /api/evaluate.
  // Sends only scenarioId + responseText — rubric is loaded server-side.
  const labUrl = settings.labControllerUrl ?? (IS_PRODUCTION ? 'https://learning.hraedon.com' : 'http://localhost:8000')

  const res = await authFetch(`${labUrl}/api/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenarioId: scenario.id,
      responseText,
      coachMode,
      coachRound,
      coachHistory
    }),
    signal,
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail ?? `Server evaluation failed: HTTP ${res.status}`)
  }

  return await res.json()
}
