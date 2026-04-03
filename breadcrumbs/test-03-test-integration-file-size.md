# ~~TEST-03~~: test_integration.py Exceeds 500-Line Guideline — **Won't Do**

## Status
Closed 2026-04-03. Refactor evaluated and rejected — see Verdict below.

## Severity
Low — the file is functional and well-organized; this is a maintainability concern, not a correctness one.

## Location
`platform/lab-controller/tests/test_integration.py` — currently ~1468 lines across 9 test classes.

## Description
`test_integration.py` is nearly 3× the project's 500-line refactor trigger. The file grew organically as new test classes were added for each architectural fix (T-1 through T-9). The classes are already logically distinct and have no real coupling beyond two shared fixtures (`db_factory`, `seeded_db`).

### Section sizes (approximate, as of 2026-04-03)
| Class | Lines |
|---|---|
| Fixtures block | ~40 |
| T-1 `TestDatabase` | ~60 |
| T-2 `TestHelpers` + T-3 `TestProvisioningFlow` | ~83 |
| T-4 `TestTeardownAndReaper` | ~182 |
| T-5 `TestEvaluatorPromptBuilder` | ~48 |
| T-6 `TestFaultedEnvironmentRecovery` | ~218 |
| T-7 `TestReconciler` | ~340 |
| T-8 `TestSharedVMValidation` | ~63 |
| T-9 `TestProvisioningFlowExecution` | ~355 |

T-7 and T-9 are the primary drivers. If either continues growing (more reconciler scenarios, more provisioning edge cases), the file becomes unwieldy.

## Proposed Split (5 files + conftest)

Move `db_factory` and `seeded_db` fixtures to `tests/conftest.py` (standard pytest pattern — they're automatically available to all test files in the directory). Then split by class grouping:

| File | Classes | Est. lines |
|---|---|---|
| `conftest.py` | fixtures + shared imports | ~70 |
| `test_database_helpers.py` | T-1, T-2, T-3 | ~200 |
| `test_teardown_evaluator.py` | T-4, T-5 | ~240 |
| `test_faulted_recovery.py` | T-6 | ~225 |
| `test_reconciler.py` | T-7, T-8 | ~415 |
| `test_provisioning_flow.py` | T-9 | ~365 |

All resulting files are under 500 lines. `pytest tests/` continues to discover and run everything unchanged.

## Caveats
The 500-line guideline in CLAUDE.md was written for production modules, not test files. Test files are conventionally more permissive about size because:
- There is no runtime coupling concern.
- Pytest doesn't care about file boundaries.
- A single large file with section comments is still navigable.

This refactor is worth doing if the file continues to grow (e.g., when D06 lab scenarios and their verification tests are added) or if T-7/T-9 need significant expansion. It is not urgent while the file is stable.

## Verdict
The 500-line guideline targets production modules where coupling, side effects, and import graphs create real risk. Test files are structurally flat — independent classes, no shared mutable state, no inter-class coupling. The section comments already serve as a table of contents. A split would add a `conftest.py` to maintain and one more place to look when a fixture breaks, with no improvement to how quickly a test can be found, read, or added.

**Exception trigger:** if a single class (T-7 or T-9) grows to the point where it alone is unwieldy, extract just that class into its own file at that time. Don't do the wholesale reorganization preemptively.

## Related
TEST-01 (general testing gaps — closed), TEST-02 (missing high-value tests — closed 2026-04-03)
