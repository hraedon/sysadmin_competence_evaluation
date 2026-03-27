# ARCH-10: No React Error Boundary — Component Exceptions White-Screen the App

## Severity
Low/Medium

## Location
`platform/frontend/src/` — no `ErrorBoundary` component exists anywhere in the component tree

## Description
React does not catch errors thrown during rendering by default — an uncaught exception in any component propagates up the tree and unmounts the entire app, replacing it with a blank white screen. There is no error boundary anywhere in this codebase.

Concrete failure scenarios:
- A malformed scenario YAML that passes manifest parsing but contains unexpected field types causes `ScenarioPanel` to throw while rendering, white-screening the app
- An evaluation result with unexpected JSON structure (EVAL-01) causes the results panel to throw rather than displaying the parse error
- A profile aggregation edge case (domain with no completed scenarios) causes `ProfileView` to throw during the median calculation
- A lab controller returning an unexpected response shape causes `LabPanel` to throw mid-session

The failure is silent from the user's perspective — they see a blank page with no actionable feedback, and may interpret it as a network or server error. Recovery requires a page reload (which may lose evaluation state).

## Remediation

Add a top-level `ErrorBoundary` class component wrapping the app, and sub-boundaries around high-risk component subtrees (`ScenarioPanel`, `LabPanel`, `ProfileView`). The top-level boundary should catch and display a recoverable error message rather than a blank screen.

React error boundaries are class components by convention (hooks can't catch render errors). This is ~30 lines of code:

```jsx
class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null } }
  static getDerivedStateFromError(error) { return { hasError: true, error } }
  componentDidCatch(error, info) { console.error('Boundary caught:', error, info) }
  render() {
    if (this.state.hasError) {
      return <div className="...">Something went wrong: {this.state.error?.message}. <button onClick={() => this.setState({ hasError: false })}>Retry</button></div>
    }
    return this.props.children
  }
}
```

Wrap `<App />` in `main.jsx` and the three high-risk panels in their parent components.

## Related
EVAL-01 (silent JSON parse failure — an error boundary prevents this from white-screening the app)

## Resolution — Session 25 (2026-03-27)

`ErrorBoundary.jsx` created at `platform/frontend/src/components/ErrorBoundary.jsx`. Added as:
- Top-level wrap in `main.jsx` around `<App />`
- Panel-level wraps in `App.jsx` around `<ScenarioPanel>` and `<EvalPanel>`

`ProfileView` and `LabPanel` are wrapped transitively via `ScenarioPanel`/`EvalPanel` or rendered as full-screen overlays (which fail visibly without a boundary, acceptable tradeoff).
