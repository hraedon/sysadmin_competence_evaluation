import { useEffect, useRef, useState } from 'react'
import { login, register } from '../lib/auth.js'

/**
 * LoginView — modal-style login/register form.
 *
 * Props:
 *   onLogin(user)   — called after successful login/register with user object
 *   onSkip()        — called when user chooses "Continue without account"
 */
export default function LoginView({ onLogin, onSkip }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const requestRef = useRef(null)
  const generationRef = useRef(0)

  useEffect(() => {
    const onKeyDown = event => {
      if (event.key === 'Escape') handleSkip()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      requestRef.current?.abort()
    }
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    requestRef.current?.abort()
    const controller = new AbortController()
    requestRef.current = controller
    const generation = ++generationRef.current
    try {
      const fn = mode === 'login' ? login : register
      const data = await fn(username, password, { signal: controller.signal })
      if (generation !== generationRef.current || controller.signal.aborted) return
      onLogin(data.user, data)
    } catch (err) {
      if (generation !== generationRef.current || controller.signal.aborted) return
      setError(err.message)
    } finally {
      if (generation === generationRef.current) setLoading(false)
    }
  }

  function handleSkip() {
    generationRef.current += 1
    requestRef.current?.abort()
    onSkip()
  }

  return (
    <div role="dialog" aria-modal="true" aria-label={mode === 'login' ? 'Sign in' : 'Create Account'} className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 sm:p-8">
      <div className="w-full max-w-md overflow-y-auto rounded-lg bg-gray-800 p-6 shadow-xl sm:p-8">
        <h2 className="text-xl font-semibold text-white mb-6">
          {mode === 'login' ? 'Sign In' : 'Create Account'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor={`${mode}-username`} className="block text-sm text-gray-400 mb-1">Username</label>
            <input
              id={`${mode}-username`}
              type="text"
              autoFocus
              autoComplete="username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              required
              minLength={3}
            />
          </div>

          <div>
            <label htmlFor={`${mode}-password`} className="block text-sm text-gray-400 mb-1">Password</label>
            <input
              id={`${mode}-password`}
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              required
              minLength={mode === 'register' ? 8 : 1}
            />
            {mode === 'register' && (
              <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
            )}
          </div>

          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded font-medium transition-colors"
          >
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="mt-4 text-center text-sm text-gray-400">
          {mode === 'login' ? (
            <p>
              No account?{' '}
              <button onClick={() => { setMode('register'); setError(null) }} className="text-blue-400 hover:underline">
                Create one
              </button>
            </p>
          ) : (
            <p>
              Already have an account?{' '}
              <button onClick={() => { setMode('login'); setError(null) }} className="text-blue-400 hover:underline">
                Sign in
              </button>
            </p>
          )}
        </div>

        <div className="mt-6 pt-4 border-t border-gray-700 text-center">
          <button
            onClick={handleSkip}
            className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            Continue without account
          </button>
          <p className="text-xs text-gray-600 mt-1">
            Your profile will be stored locally in this browser only
          </p>
        </div>
      </div>
    </div>
  )
}
