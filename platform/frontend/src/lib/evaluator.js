import OpenAI from 'openai'
import { buildSystemPrompt, performEvaluation } from '../../../core/evaluator.js'
import { isAuthenticated, getAuthHeaders } from './auth.js'

// ---------------------------------------------------------------------------
// Settings schema and persistence
// ---------------------------------------------------------------------------

export const SETTINGS_KEY = 'sysadmin_assessment_settings'
const LEGACY_KEY = 'sysadmin_assessment_api_key'

const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
const LOCAL_PROXY_ENDPOINT = '/llm-proxy/v1'
const INTERNAL_LOCAL_ENDPOINT = 'http://192.168.1.28:1234/v1'

export const DEFAULT_SETTINGS = {
  provider: 'local',
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
      const settings = { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }

      // If the user has the default "internal" IP but is in production,
      // upgrade them to the proxy endpoint automatically.
      if (IS_PRODUCTION && settings.endpoint === INTERNAL_LOCAL_ENDPOINT) {
        settings.endpoint = LOCAL_PROXY_ENDPOINT
      }

      return settings
    } catch {
      // fall through to defaults
    }
  }
  // Migrate legacy Anthropic-only key
  const legacyKey = localStorage.getItem(LEGACY_KEY)
  if (legacyKey) {
    const migrated = { ...DEFAULT_SETTINGS, provider: 'anthropic', apiKey: legacyKey }
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(migrated))
    localStorage.removeItem(LEGACY_KEY)
    return migrated
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
 * Only used when provider === 'local' — all other providers route
 * through the server-side /api/evaluate endpoint.
 */
export function buildClient({ provider = 'local', endpoint, apiKey }) {
  let baseURL = endpoint ?? (IS_PRODUCTION ? LOCAL_PROXY_ENDPOINT : INTERNAL_LOCAL_ENDPOINT)

  // Ensure the baseURL is absolute if it's a relative path
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
export async function evaluate({ scenario, artifactContent, responseText, settings, coachMode = false, coachRound = 0, coachHistory = [], isRetry = false }) {
  // Local provider: evaluate client-side for low latency / air-gapped use.
  if (settings.provider === 'local') {
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
    })
  }

  // Server-side evaluation via /api/evaluate.
  // Sends only scenarioId + responseText — rubric is loaded server-side.
  const labUrl = settings.labControllerUrl ?? (IS_PRODUCTION ? 'https://learning.hraedon.com' : 'http://localhost:8000')

  const headers = { 'Content-Type': 'application/json', ...getAuthHeaders() }

  const res = await fetch(`${labUrl}/api/evaluate`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      scenarioId: scenario.id,
      responseText,
      coachMode,
      coachRound,
      coachHistory
    })
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail ?? `Server evaluation failed: HTTP ${res.status}`)
  }

  return await res.json()
}
