# ARCH-14: Reconciler Silent Failure After Max Retries

## Severity
Low/Medium

## Location
`platform/lab-controller/app/main.py` — `reconcile_environments()`, `_attempt_auto_recovery()`

## Description
When an environment fails auto-recovery `fault_max_auto_retries` times, the reconciler stops
retrying and leaves the environment faulted. This is the correct behaviour — the reconciler
should not spin indefinitely — but there is no proactive signal to an operator that this
threshold has been crossed.

The only way to discover this state is:
- Poll `GET /health` or `GET /lab/status` and notice `fault_retry_count >= fault_max_auto_retries`
- Read the logs

If the environment is the only one capable of serving a required capability, the platform will
silently serve 503s to learners until an operator notices and issues a manual reset.

## Remediation

When `fault_retry_count` reaches `fault_max_auto_retries`, emit a structured warning log at
ERROR level with a clear message (this is already logged, just not specially flagged). Additional
options in priority order:

1. **Webhook notification** — add an optional `alert_webhook_url` setting; POST a JSON payload
   to it when max retries is crossed. Compatible with Slack incoming webhooks, Teams, ntfy.sh,
   Alertmanager, etc.

2. **Health check status escalation** — return `"critical"` instead of `"degraded"` when any
   environment has `fault_retry_count >= fault_max_auto_retries`. A k8s readinessProbe checking
   for non-`"healthy"` status would then pull the pod from the load balancer, which surfaces the
   problem at the infrastructure level.

3. **Email/SMS** — viable if an SMTP relay is already available on the network (which it is:
   see infra inventory).

## Related
`_reset_environment()` (manual recovery path), `GET /health` (polling surface),
ARCH-05 (observability gap in test suite)
