# ~~ARCH-25~~: Dead LabPanel.jsx Component — **Closed**

## Status
- **Priority**: Low
- **Resolved**: 2026-04-02

## Context
`LabPanel.jsx` was the original standalone lab UI component from Session 21. It was replaced by a three-part architecture in Session 26:
- `useLabSession.js` hook (state management)
- `LabInfoPanel.jsx` (scenario info + controls)
- `LabConsole.jsx` (maximized Guacamole iframe)

`LabPanel.jsx` remained in the codebase. `build_notes.md` described it as "still works independently" but nothing in `App.jsx` routed to it — all lab scenarios go through the `LabInfoPanel` + `LabConsole` layout.

## Resolution
Removed `LabPanel.jsx` and all references to it. The newer architecture is the sole lab UI path.

## Related
ARCH-08 (explicit teardown — originally wired through LabPanel, now through useLabSession hook)
