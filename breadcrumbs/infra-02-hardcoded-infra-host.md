# INFRA-02: Hardcoded Infrastructure Host in Lab Controller

## Severity
Low

## Location
`platform/lab-controller/app/main.py` — `Settings.hyperv_host` (line ~35)

## Description
The `hyperv_host` setting is hardcoded to `mvmhyperv02.ad.hraedon.com` in the `Settings` class. While it can be overridden by an environment variable, having a specific internal FQDN as the default is a minor security risk (leaking internal infrastructure names) and a portability issue.

## Remediation
Change the default value to an empty string or a placeholder (e.g., `hyperv-host.local`) and require it to be set via `.env` or k8s secrets.

## Related
INFRA-01 (Environments YAML in public repo).
