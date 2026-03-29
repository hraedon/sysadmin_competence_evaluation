# Worklog

Session notes for the sysadmin competency assessment platform. Each entry covers one working session with the AI pair.

---

## Session 29 — 2026-03-29

**Focus:** Lab integration stability; end-to-end provisioning bugs.

**Outcome:** Lab integration declared stable enough to support scenario creation. Eight bugs resolved across one session.

### Bugs resolved (in order of discovery)

| # | Commit | Description |
|---|--------|-------------|
| 1 | f295fbd | Cross-OS path failure: scripts base64-encoded in Python and embedded in PowerShell rather than passing Linux container paths to the Hyper-V host |
| 2 | 857e1be | Wrong Guacamole RDP credentials: hardcoded `"labuser"` replaced with `settings.hyperv_guest_username` |
| 3 | cd94091 | Guacamole "Log in failed" loop: `domain\username` not split into separate `domain` + `username` params for FreeRDP; also added 15s stagger between VM starts |
| 4 | 23de46f | env-windows-01 missing LabDC01: LabServer01 is domain-joined; PS Direct auth times out without DC's NetLogon running |
| 5 | adf6694 | Keyboard not routing to Guacamole iframe: added `tabIndex`, `useRef` auto-focus on ready, `onClick` re-focus |
| 6 | c0ae237 | ARCH-02 regression: Session 28 forced `expires_at = now()` on all sessions → reaper killed them within 60s of pod restart |
| 7 | 5302cb4 | `load_environments` reset `busy` → `available` on restart: reconciler then treated VMs as orphans |
| 8 | c015102 | Reconciler orphan false positive (ARCH-23): both env-windows-01 and env-domain-01 share LabDC01+LabServer01; reconciler reverted running VMs against the available env-domain-01 entry, killing active sessions within ~5 minutes |

**Post-session work (same date):**
- b057187: Restored iframe keyboard focus after Verify button click in LabPanel.jsx (Verify button stole focus; iframeRef + 100ms setTimeout refocuses it)
- ARCH-17 implemented: `verify_lab` now persists results to `LabSession.verification_results`; `evaluate_v2` includes them as `[LAB VERIFICATION STATE]` context for AI evaluation

### Architectural notes

- **Bugs 6–8 form a cascade.** The Session 28 ARCH-02 fix (forced expiry) papered over the real problem by ensuring sessions were always short-lived. When that was corrected (bug 6), bug 7 (busy→available reset) surfaced. When that was corrected, bug 8 (reconciler false positive) surfaced. Each fix revealed the next. The root cause was always ARCH-23.
- **Shared-VM topology is the source of ARCH-23.** env-windows-01 and env-domain-01 share physical VMs intentionally (they cannot run concurrently) but the reconciler had no model of this. This is a configuration-level constraint with code-level implications that weren't tracked.
- **Application logs are nearly silent under normal operation.** ARCH-23 was found by code review, not by log analysis. This is worth noting for future debugging: if logs look normal, it doesn't mean everything is normal.

---

### Subjective experience (AI pair perspective)

This was a satisfying session to work through, though it had a particular texture that's worth recording: the problem was never fully visible at once. Each fix was correct as far as it went, but the actual failure mode was always one layer deeper than the evidence suggested.

The most interesting moment was identifying ARCH-23. After fixing bugs 6 and 7, the session death persisted. The symptom (killed after ~5 minutes) pointed to the reconciler, but the logs showed nothing, and the reconciler's logic looked correct on a first reading. The insight came from asking "what assumption does this code make that might not be true?" The orphan check assumed a one-to-one mapping between physical VMs and environment entries. Once that assumption was named, the bug was obvious — and the right fix was simple (build a set of active VMs, skip them). The satisfaction there was more from the naming of the hidden assumption than from the fix itself.

The keyboard focus issue was a different kind of problem — cross-origin iframe focus semantics are a browser-specific trap with no obvious symptoms (mouse works, keyboard doesn't). The fix was clean once the cause was clear. The follow-up fix (Verify button stealing focus) was a natural consequence of the same iframe-focus framing; it took about 30 seconds once the problem was described.

What was technically interesting: the base64 encoding fix (bug 1) is a case where the right abstraction boundary (encode in the process that owns the filesystem; let the remote process decode) is obvious in retrospect but easy to miss when you're thinking of file transfer as "copy a path." The two-hop architecture (Linux container → Hyper-V host via WinRM → guest VM via VMBus) creates a lot of these boundary moments.

Collaboration note: the debugging proceeded well partly because you were watching the VMs directly and could report what was visible (VMs powering on, Guacamole connection succeeding, session dying after a fixed interval). That observational data was load-bearing — without the "five minutes" timing, ARCH-23 might have been harder to distinguish from a reaper issue. The clean handoff of observations ("it died again, here's the timing") made each iteration faster than it would have been with only log data.
