# Breadcrumbs

Tracked gaps and remediation tasks identified through architectural review.

## Index

| ID | File | Severity | Summary |
|----|------|----------|---------|
| ~~SEC-01~~ | [sec-01-credentials-in-process-args.md](sec-01-credentials-in-process-args.md) | ~~High~~ **Closed** | Credentials now passed via env vars, not process args. Resolved Session 25. |
| ~~SEC-02~~ | [sec-02-guacamole-predictable-token.md](sec-02-guacamole-predictable-token.md) | ~~High~~ **Closed** | Static guac_client_token() removed; provision response no longer returns Guacamole URL; session endpoint uses only ephemeral per-session connection IDs. Resolved Session 28. |
| SEC-03 | [sec-03-api-key-in-browser.md](sec-03-api-key-in-browser.md) | Medium | Anthropic/OpenAI key in localStorage + dangerouslyAllowBrowser; proxy path exists |
| ~~SEC-04~~ | [sec-04-no-api-authentication.md](sec-04-no-api-authentication.md) | ~~High~~ **Closed** | All endpoints now gated by verify_api_key dependency. Resolved Session 25. |
| SEC-05 | [sec-05-rubric-fields-in-public-manifest.md](sec-05-rubric-fields-in-public-manifest.md) | Medium — **partially resolved** | miss_signal and level_indicators stripped from manifest; finding descriptions remain until ARCH-09 |
| SEC-06 | [sec-06-labpanel-hardcoded-api-key.md](sec-06-labpanel-hardcoded-api-key.md) | Medium — **partially resolved** | Key moved to VITE_CONTROLLER_KEY env var (S25); still in bundle until ARCH-09 |
| ARCH-01 | [arch-01-provisioning-race-condition.md](arch-01-provisioning-race-condition.md) | Low/Medium | Read-then-update without SELECT FOR UPDATE; safe at replicas=1, breaks if scaled |
| ~~ARCH-02~~ | [arch-02-session-flush-on-restart.md](arch-02-session-flush-on-restart.md) | ~~Medium~~ **Closed** | Sessions marked suspect on restart; stuck-provisioning envs faulted. Forced-expiry approach (S28) was itself a bug — corrected S29 (c0ae237). |
| ~~ARCH-03~~ | [arch-03-provisioning-no-watchdog.md](arch-03-provisioning-no-watchdog.md) | ~~Medium~~ **Closed** | run_provisioning_with_watchdog wraps flow in asyncio.wait_for(). Resolved Session 27. |
| ARCH-04 | [arch-04-sqlite-in-container.md](arch-04-sqlite-in-container.md) | Medium | SQLite hardcoded in lab controller; state lost on restart, scaling impossible |
| ARCH-05 | [arch-05-no-test-suite.md](arch-05-no-test-suite.md) | Low — **mostly resolved** | 94 tests total: Python (61), JS (33). T-6 covers faulted env recovery; T-7 covers reconciler. Frontend component tests (Vitest) and HTTP-layer endpoint tests still missing. |
| ~~ARCH-06~~ | [arch-06-no-rate-limiting.md](arch-06-no-rate-limiting.md) | ~~Low/Medium~~ **Closed** | slowapi rate limiting on provision (5/min), evaluate (20/min), auth (3/hr register, 10/min login). Per-user or per-IP keying. |
| ~~ARCH-07~~ | [arch-07-verification-script-injection.md](arch-07-verification-script-injection.md) | ~~Medium~~ **Closed** | run_script_in_guest already uses file-copy approach, not string interpolation. Resolved Session 25. |
| ~~ARCH-08~~ | [arch-08-no-explicit-teardown.md](arch-08-no-explicit-teardown.md) | ~~Low/Medium~~ **Closed** | POST /lab/teardown/{session_token} exists and is called by both useLabSession.js and LabPanel.jsx. Resolved Sessions 21/26. |
| ~~ARCH-09~~ | [arch-09-no-backend-convergence.md](arch-09-no-backend-convergence.md) | ~~High~~ **Closed** | /api/evaluate, JWT auth, profile API, rate limiting all implemented 2026-03-28. See ARCH-19, ARCH-20 for remaining items. |
| ~~ARCH-10~~ | [arch-10-no-react-error-boundary.md](arch-10-no-react-error-boundary.md) | ~~Low/Medium~~ **Closed** | ErrorBoundary added in main.jsx + App.jsx wrapping ScenarioPanel/EvalPanel. Resolved Session 25. |
| ARCH-11 | [arch-11-cicd-commits-to-main.md](arch-11-cicd-commits-to-main.md) | Low — **partially resolved** | GHA workflow commits image tag to main; `[skip ci]` prevents CI loops. Deploy-branch or kubectl-set-image approach deferred. |
| ~~EVAL-01~~ | [eval-01-silent-json-parse-failure.md](eval-01-silent-json-parse-failure.md) | ~~Medium~~ **Closed** | Null parse result now surfaces error message in App.jsx handleSubmit + handleFollowUp. Resolved Session 25. |
| ~~EVAL-02~~ | [eval-02-almost-caught-unused.md](eval-02-almost-caught-unused.md) | ~~Low~~ **Closed** | almost_caught now displayed in EvalPanel (amber ◐) and stored in profile. Resolved Session 27. |
| EVAL-03 | [eval-03-profile-localStorage-only.md](eval-03-profile-localStorage-only.md) | Low/Medium | Profile in localStorage only; no portability, export, or verifiability |
| EVAL-04 | [eval-04-coach-history-token-growth.md](eval-04-coach-history-token-growth.md) | Low | Coach context heavy for long artifacts; failure mode is silent quality degradation, not error |
| EVAL-05 | [eval-05-calibration-synthetic-only.md](eval-05-calibration-synthetic-only.md) | Medium | Calibration tests clean synthetic responses only; robustness against real messy responses unvalidated |
| EVAL-06 | [eval-06-d14-evaluator-variance.md](eval-06-d14-evaluator-variance.md) | Medium | D14 subtle level distinctions have high expected LLM evaluator variance; no human baseline |
| ~~ARCH-12~~ | [arch-12-guacamole-stale-token.md](arch-12-guacamole-stale-token.md) | ~~Medium~~ **Closed** | _request() helper auto-authenticates and retries on 401. Resolved 2026-03-28. |
| ~~ARCH-13~~ | [arch-13-checkpoint-name-mismatch.md](arch-13-checkpoint-name-mismatch.md) | ~~High~~ **Closed** | Verified on Hyper-V: all VMs use `"Baseline Checkpoint"`. Default corrected. |
| ~~ARCH-14~~ | [arch-14-reconciler-no-alerting.md](arch-14-reconciler-no-alerting.md) | ~~Medium~~ **Closed** | Heartbeat table + /health endpoint track background job status. Resolved 2026-03-28. |
| ~~ARCH-15~~ | [arch-15-vestigial-guac-connection-id.md](arch-15-vestigial-guac-connection-id.md) | ~~Low~~ **Closed** | `guac_connection_id` removed from `LabEnvironment` model, `environments.yaml`, `load_environments()`, migration, and test fixtures. `LabSession.guac_connection_id` retained (active). |
| INFRA-01 | [infra-01-environments-yaml-in-public-repo.md](infra-01-environments-yaml-in-public-repo.md) | Medium | VM hostnames and Guacamole connection IDs in public repo |
| CONTENT-01 | [content-01-domain-coverage-gaps.md](content-01-domain-coverage-gaps.md) | Medium — **improving** | D06 still 1 scenario; D08→2, D10→2, D12→3 (56 total). D06 remains the most undercovered domain. |
| ~~CONTENT-02~~ | [content-02-recall-disguised-as-reasoning.md](content-02-recall-disguised-as-reasoning.md) | ~~Low/Medium~~ **Closed** | 4 L4 indicators reworded to test reasoning over terminology (d02-ticket-flags, d04-revocation, d02-upn-routing, d02-sql-spn). Resolved Session 27. |
| SEC-07 | [sec-07-guacamole-admin-token-leak.md](sec-07-guacamole-admin-token-leak.md) | Low — **partially resolved** | Per-session restricted Guac users implemented; admin token still used as fallback on failure |
| ~~ARCH-16~~ | [arch-16-brittle-verification-parsing.md](arch-16-brittle-verification-parsing.md) | ~~Medium~~ **Closed** | Regex JSON extraction already implemented in admin.py; raw output snippet included in error detail. |
| ~~ARCH-17~~ | [arch-17-disconnected-lab-ai-evaluation.md](arch-17-disconnected-lab-ai-evaluation.md) | ~~Medium~~ **Closed** | verify_lab now persists results to LabSession.verification_results; evaluate_v2 includes them as LAB STATE context. Resolved Session 29. |
| ~~ARCH-18~~ | [arch-18-sequential-calibration.md](arch-18-sequential-calibration.md) | ~~Low/Medium~~ **Closed** | Calibration harness now supports `--concurrency <n>` (default 5) via worker-pool pattern. ~56 min → ~12 min. |
| ~~EVAL-07~~ | [eval-07-missing-hit-signal.md](eval-07-missing-hit-signal.md) | ~~Low/Medium~~ **Closed** | Optional `hit_signal` field added to both evaluators (JS + Python) under `LOOK FOR (HIT SIGNAL):` label, suppressed in compact mode. Resolved Session 32. |
| INFRA-02 | [infra-02-hardcoded-infra-host.md](infra-02-hardcoded-infra-host.md) | Low | Hardcoded Hyper-V host FQDN in lab controller settings |
| ~~ARCH-19~~ | [arch-19-legacy-evaluate-endpoint.md](arch-19-legacy-evaluate-endpoint.md) | ~~Low~~ **Closed** | Legacy v1 `/evaluate` and `/lab/evaluate` routes deleted; `evaluate.py` removed from `main.py` and `routers/__init__.py`. Resolved Session 32. |
| ~~ARCH-20~~ | [arch-20-frontend-jwt-refresh.md](arch-20-frontend-jwt-refresh.md) | ~~Low/Medium~~ **Closed** | `authFetch` 401-retry wrapper wired into `evaluator.js` and `profile.js`; silent 401s now trigger refresh-and-retry. Resolved Session 32. |
| ~~ARCH-22~~ | [arch-22-pssession-for-powershell-direct.md](arch-22-pssession-for-powershell-direct.md) | ~~High~~ **Closed** | PSSession for PowerShell Direct; hardened provisioning flow with teardown on failure. Resolved 2026-03-28. |
| ~~ARCH-23~~ | [arch-23-reconciler-shared-vm-orphan-false-positive.md](arch-23-reconciler-shared-vm-orphan-false-positive.md) | ~~High~~ **Closed** | Reconciler falsely reverted VMs shared between env entries; active sessions killed within 5 min. Fixed S29 (c015102). |
| ARCH-24 | [arch-24-proxmox-orchestrator.md](arch-24-proxmox-orchestrator.md) | Medium | Proxmox VE orchestrator stub exists; needs implementation (REST API, QEMU Guest Agent, aiohttp) |
| ~~ARCH-25~~ | [arch-25-dead-labpanel-component.md](arch-25-dead-labpanel-component.md) | ~~Low~~ **Closed** | Dead `LabPanel.jsx` removed; replaced by LabInfoPanel + LabConsole architecture. Resolved 2026-04-02. |
| ~~ARCH-26~~ | [arch-26-shared-vm-topology-validation.md](arch-26-shared-vm-topology-validation.md) | ~~Medium~~ **Closed** | Startup validation warns on shared-VM topology in environments.yaml. Resolved 2026-04-02. |
