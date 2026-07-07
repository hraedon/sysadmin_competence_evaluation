# INFRA-01: environments.yaml Committed to Public Repository

## Severity
Medium

## Location
`platform/lab-controller/environments.yaml`

## Description
`environments.yaml` is committed to the public GitHub repo and contains internal VM hostnames (e.g., `LabDC01`, `LabServer01`). Combined with the predictable token construction in SEC-02, any person who reads the repo can construct a valid Guacamole client URL for any lab environment without authenticating to the lab controller.

The file also documents the internal lab subnet topology, VM naming conventions, and scenario-to-environment mappings — useful reconnaissance for anyone targeting the infrastructure.

Note: `guac_connection_id` was removed from `environments.yaml` under ARCH-15; the remaining concern is VM hostnames.

## Remediation

Move environment-specific values (connection IDs, VM names, hostnames) out of the committed file and into a secret or ConfigMap:

- Keep the schema and non-sensitive structure in the committed `environments.yaml` (capability declarations, scenario assignments, timeout values)
- Inject VM hostnames from a k8s Secret or a gitignored local override file at deploy time
- Add `environments.yaml` (or a `environments.local.yaml`) to `.gitignore` for any file that contains real infrastructure identifiers

Fixing SEC-02 (ephemeral per-session Guacamole tokens) reduces the blast radius of this exposure significantly, but doesn't eliminate the reconnaissance value of the hostname data.

## Related
SEC-02, SEC-04
