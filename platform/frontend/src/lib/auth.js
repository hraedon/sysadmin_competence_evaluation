/**
 * Authentication client library.
 *
 * Handles JWT-based auth with the backend API. Tokens are stored in
 * localStorage (access_token is short-lived, refresh_token handles renewal).
 */

const AUTH_KEY = 'sysadmin_assessment_auth'

function getBaseUrl() {
  const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
  return IS_PRODUCTION ? '' : 'http://localhost:8000'
}

function loadAuth() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY)) || null
  } catch {
    return null
  }
}

function saveAuth(data) {
  localStorage.setItem(AUTH_KEY, JSON.stringify(data))
}

function clearAuth() {
  localStorage.removeItem(AUTH_KEY)
}

export function isAuthenticated() {
  const auth = loadAuth()
  return !!(auth && auth.access_token)
}

export function getUser() {
  const auth = loadAuth()
  return auth?.user || null
}

export function getAuthHeaders() {
  const auth = loadAuth()
  if (!auth?.access_token) return {}
  return { Authorization: `Bearer ${auth.access_token}` }
}

export async function register(username, password) {
  const res = await fetch(`${getBaseUrl()}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Registration failed: HTTP ${res.status}`)
  }
  const data = await res.json()
  saveAuth(data)
  return data
}

export async function login(username, password) {
  const res = await fetch(`${getBaseUrl()}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Login failed: HTTP ${res.status}`)
  }
  const data = await res.json()
  saveAuth(data)
  return data
}

export async function refreshToken() {
  const auth = loadAuth()
  if (!auth?.refresh_token) throw new Error('No refresh token')

  const res = await fetch(`${getBaseUrl()}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: auth.refresh_token }),
  })
  if (!res.ok) {
    clearAuth()
    throw new Error('Token refresh failed')
  }
  const data = await res.json()
  saveAuth({ ...auth, access_token: data.access_token })
  return data
}

export function logout() {
  clearAuth()
}
