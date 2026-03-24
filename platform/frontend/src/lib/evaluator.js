import OpenAI from 'openai'
import { buildSystemPrompt, performEvaluation } from '../../../core/evaluator.js'

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
// Provider abstraction
// ---------------------------------------------------------------------------

const PROVIDER_BASE_URLS = {
  local:     null,                             // uses settings.endpoint
  anthropic: 'https://api.anthropic.com/v1',
  openai:    'https://api.openai.com/v1',
  custom:    null,                             // uses settings.endpoint
}

/**
 * Build an OpenAI-compatible client for the given provider settings.
 * All providers (including Anthropic) are accessed via the openai package
 * using their OpenAI-compatible endpoints.
 */
export function buildClient({ provider = 'local', endpoint, apiKey }) {
  let baseURL = PROVIDER_BASE_URLS[provider] ?? endpoint ?? (IS_PRODUCTION ? LOCAL_PROXY_ENDPOINT : INTERNAL_LOCAL_ENDPOINT)
  
  // Ensure the baseURL is absolute if it's a relative path (OpenAI client prefers this)
  if (baseURL.startsWith('/')) {
    baseURL = window.location.origin + baseURL
  }

  // Local providers don't require a real key; use a placeholder so the header is valid
  const key = apiKey || (provider === 'local' ? 'lm-studio' : 'no-key')
  return new OpenAI({ baseURL, apiKey: key, dangerouslyAllowBrowser: true })
}

/**
 * Call the configured provider and return a parsed evaluation result.
 *
 * In coach mode, coachRound and coachHistory extend the conversation:
 *   coachRound 0 = initial evaluation (coach_question added to JSON if findings missed)
 *   coachRound 1+ = follow-up (coachHistory contains prior exchanges, resolved field added)
 *
 * coachHistory is an array of { role: 'assistant'|'user', content } messages
 * representing exchanges after the initial response.
 *
 * Throws on API/network error. Returns { raw, parsed } where parsed may be
 * null if JSON extraction fails.
 */
export async function evaluate({ scenario, artifactContent, responseText, settings, coachMode = false, coachRound = 0, coachHistory = [], isRetry = false }) {
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
