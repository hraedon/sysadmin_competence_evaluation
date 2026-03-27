# Breadcrumbs

Tracked gaps and remediation tasks identified through architectural review.

## Index

| ID | File | Severity | Summary |
|----|------|----------|---------|
| SEC-01 | [sec-01-credentials-in-process-args.md](sec-01-credentials-in-process-args.md) | High | WinRM/guest credentials visible in process args; internal-only caveat is stale |
| SEC-02 | [sec-02-guacamole-predictable-token.md](sec-02-guacamole-predictable-token.md) | High | Guacamole URL reconstructable from static connection_id; no per-session token |
| SEC-03 | [sec-03-api-key-in-browser.md](sec-03-api-key-in-browser.md) | Medium | Anthropic/OpenAI key in localStorage + dangerouslyAllowBrowser; proxy path exists |
| SEC-04 | [sec-04-no-api-authentication.md](sec-04-no-api-authentication.md) | High | Lab controller has no authentication on any endpoint; public ingress |
| ARCH-01 | [arch-01-provisioning-race-condition.md](arch-01-provisioning-race-condition.md) | Low/Medium | Read-then-update without SELECT FOR UPDATE; safe at replicas=1, breaks if scaled |
| ARCH-02 | [arch-02-session-flush-on-restart.md](arch-02-session-flush-on-restart.md) | Medium | Hard delete of all sessions on startup orphans partially-provisioned VMs |
| ARCH-03 | [arch-03-provisioning-no-watchdog.md](arch-03-provisioning-no-watchdog.md) | Medium | run_provisioning_flow has no outer timeout; hung scripts lock environments forever |
| EVAL-01 | [eval-01-silent-json-parse-failure.md](eval-01-silent-json-parse-failure.md) | Medium | Null parsed result from evaluator produces no error message to user |
| EVAL-02 | [eval-02-almost-caught-unused.md](eval-02-almost-caught-unused.md) | Low | almost_caught captured but not used in scoring, coaching, or profile display |
| INFRA-01 | [infra-01-environments-yaml-in-public-repo.md](infra-01-environments-yaml-in-public-repo.md) | Medium | VM hostnames and Guacamole connection IDs in public repo |
| SEC-05 | [sec-05-rubric-fields-in-public-manifest.md](sec-05-rubric-fields-in-public-manifest.md) | High | Full rubric/miss_signal/level_indicators served to every browser in manifest |
| ARCH-04 | [arch-04-sqlite-in-container.md](arch-04-sqlite-in-container.md) | Medium | SQLite hardcoded in lab controller; state lost on restart, scaling impossible |
| ARCH-05 | [arch-05-no-test-suite.md](arch-05-no-test-suite.md) | Low/Medium | No automated tests; path traversal guard and prompt field exclusion uncovered |
| ARCH-06 | [arch-06-no-rate-limiting.md](arch-06-no-rate-limiting.md) | Low/Medium | No rate limiting on lab provision endpoint; pool exhaustion via unauthenticated flood |
| EVAL-03 | [eval-03-profile-localStorage-only.md](eval-03-profile-localStorage-only.md) | Low/Medium | Profile in localStorage only; no portability, export, or verifiability |
| EVAL-04 | [eval-04-coach-history-token-growth.md](eval-04-coach-history-token-growth.md) | Low | Coach history accumulates full context per round; bounded at 3 but heavy for long artifacts |
| ARCH-07 | [arch-07-verification-script-injection.md](arch-07-verification-script-injection.md) | Medium | Verification script injection via string interpolation in orchestrator |
| ARCH-08 | [arch-08-no-explicit-teardown.md](arch-08-no-explicit-teardown.md) | Low/Medium | No explicit teardown endpoint leads to unnecessary environment lock-in |
