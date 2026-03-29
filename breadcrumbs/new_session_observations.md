# ~~ARCH-12~~: Guacamole Token Refresh — **Closed**
# ~~ARCH-13~~: Baseline Checkpoint Name Inconsistency — **Closed**
# ~~ARCH-14~~: Reconciler Silent Failure / Health Tracking — **Closed**

# ARCH-19: SQLite UTC "Naivety" and SQLAlchemy Transitions
- **Priority**: Low (Internal Consistency)
- **Context**: During the Reviewer session (2026-03-28), we discovered that SQLite + SQLAlchemy defaults return naive datetimes, causing `TypeError` when comparing against `datetime.now(datetime.UTC)`.
- **Current Fix**: A `UTCDateTime(TypeDecorator)` was implemented in `app/database.py`.
- **Long-term**: When migrating to PostgreSQL (ARCH-09), this decorator can be simplified. Ensure that the Postgres migration uses `TIMESTAMPTZ` to avoid regressing on this issue.

# EVAL-08: L3/L4 Differentiator Variance in Domain 14
- **Priority**: Medium (Evaluation Quality)
- **Context**: Calibration on 2026-03-28 showed that L3 responses are often graded as L4 in `d14-audit-the-messenger`.
- **Finding**: The model sees "good leadership advice" and checks the L4 box even if the specific "floor/ceiling" stable-constraint structure isn't perfectly formed.
- **Action**: Refine the `miss_signal` for L4 findings in D14 to explicitly look for the *absence* of the floor/ceiling split, rather than just the *presence* of general clarity.

# INFRA-03: Container Start Latency and Probe Readiness
- **Priority**: Low (UX)
- **Context**: The `lab-controller` image is large. K8s probes might fail if the container takes too long to initialize the Python environment + PSWSMan modules.
- **Action**: Keep the `initialDelaySeconds` for liveness/readiness probes at 30s+ to account for image pull and initialization.
