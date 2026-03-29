# TEST-01: Integrated Testing Gaps

## Status
- **Priority**: Medium
- **Context**: Reviewed testing infrastructure on 2026-03-28. Lab Controller (Python) has excellent unit/integration coverage. Core logic (JS) has good unit coverage. Frontend was missing all testing infrastructure.

## Improvements Made
1. **Frontend Testing Foundation**: Installed Vitest and React Testing Library in `platform/frontend`. Configured `vite.config.js` and `setup.js`.
2. **Component Testing**: Added `ScenarioPanel.test.jsx` as a pattern for testing React components.
3. **Cross-Language Consistency**: Added `test_evaluator_consistency.py` in the Lab Controller to ensure `evaluator.py` and `evaluator.js` always produce identical system prompts.
4. **Encoding Standardization**: Replaced em-dashes (`—`) with standard hyphens (`-`) in evaluator logic to prevent Python/Node encoding mismatches.

## Remaining Gaps
1. **End-to-End (E2E) Testing**: No automated suite exists to test the full "Frontend -> Lab Controller -> Evaluator" loop. 
   - **Recommendation**: Implement a Playwright or Cypress suite in a new `tests/e2e` directory.
2. **API Contract Testing**: Frontend and Backend talk via JSON but have no shared schema enforcement (e.g., OpenAPI/Pydantic-to-TypeScript).
   - **Recommendation**: Use a tool like `openapi-typescript` to generate types from the FastAPI backend and ensure the frontend stays in sync.
3. **Lab Verification Smoke Tests**: Current tests mock the Hyper-V orchestrator. 
   - **Recommendation**: Create a "Stage 0" CI job that runs a minimal verification script against a real target to catch WinRM/PSWSMan compatibility regressions.
