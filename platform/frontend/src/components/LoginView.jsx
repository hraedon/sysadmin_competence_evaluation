import { useState } from 'react'
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

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const fn = mode === 'login' ? login : register
      const data = await fn(username, password)
      onLogin(data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-8 w-full max-w-md shadow-xl">
        <h2 className="text-xl font-semibold text-white mb-6">
          {mode === 'login' ? 'Sign In' : 'Create Account'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              required
              minLength={3}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Password</label>
            <input
              type="password"
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
            onClick={onSkip}
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
