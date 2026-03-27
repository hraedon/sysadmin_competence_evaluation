import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
          <p className="text-sm text-red-400">
            {this.props.label ?? 'Something went wrong.'}{' '}
            {this.state.error?.message && (
              <span className="font-mono text-xs text-gray-500">{this.state.error.message}</span>
            )}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="rounded border border-gray-600 px-3 py-1.5 text-xs text-gray-300 hover:border-gray-400 hover:text-gray-100"
          >
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
