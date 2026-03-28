# ARCH-08: No Explicit Teardown Endpoint

## Severity
Low/Medium (Usability & Resource Efficiency)

## Location
`platform/lab-controller/app/main.py`

## Description
The Lab Controller currently relies exclusively on a background "reaper" process (running every 60 seconds) or session timeouts to reclaim lab environments. There is no `POST /lab/teardown/{session_token}` endpoint that allows the frontend (or a user) to explicitly signal that they are finished with a lab.

In `LabPanel.jsx`, the `handleEndLab` function merely resets the frontend state:
```javascript
async function handleEndLab() {
  setPhase('idle')
  setSession(null)
  // ...
}
```
The environment remains in a `busy` state until the reaper identifies it as expired. This leads to unnecessary "lock-in" of limited lab resources (VMs/snapshots) even after a learner has completed their work.

## Remediation
1. Add a `POST /lab/teardown/{session_token}` endpoint to the Lab Controller.
2. This endpoint should trigger the `teardown_environment_logic` immediately for the associated environment.
3. Update `LabPanel.jsx` to call this endpoint when the "End lab" button is clicked.

## Related
ARCH-02 (session flush), ARCH-03 (provisioning timeout)

## Resolution — Sessions 21/26

`POST /lab/teardown/{session_token}` endpoint exists in `main.py`. It triggers `teardown_environment_logic` as a background task (VM revert, Guacamole connection cleanup, session deletion). `useLabSession.js` calls this endpoint from `handleEndLab`. The standalone `LabPanel.jsx` also calls it. Both paths release the environment immediately rather than waiting for reaper timeout.
