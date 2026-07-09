# Plan 001 — Curriculum expansion: living up to the name

**Status:** in progress (Phase 0 complete)
**Triggered by:** 2026-07-09 owner review discussion. A full content review
of the map (v0.23) identified mechanical defects, map/platform drift, and
coverage gaps. The owner made the scope decisions recorded below; this
plan formalizes them and assigns the work.

## Owner decisions (2026-07-09)

1. **The canonical source is no longer the .docx.** The map moves to
   markdown; the .docx becomes a rendered artifact.
2. **Add an Observability & Alert Design domain.** The map's own recurring
   thread ("detection is the consistently underthin layer") gets a home.
3. **Add minimum viable database coverage.**
4. **Bite the bullet on DevOps:** minimum viable Kubernetes,
   containerization, and git at least. Editorial skepticism about k8s
   organizational fit stands, but k8s is not going away, and agentic
   assistance makes it far more tractable for a small shop — the
   curriculum must cover operating it, not only deciding whether to
   adopt it.
5. **The skill-development problem gets addressed head-on** — both the
   audit-without-authorship acquisition question and the junior-incubation
   economics (training cost vs. agentic substitution; the poaching
   asymmetry; the case for a guild-like neutral body).

## Standing rules established by this plan

**R1 — Domain numbers are stable IDs. Never renumber again.** The v0.19
renumbering left stale cross-references in the document for four
versions (repaired in v0.24). Reading order is a property of the build
manifest (`scripts/build_map.sh` ORDER), not of domain identity. New
domains take the next free number regardless of where they sit in
reading order.

**R2 — Cross-references are gated.** `scripts/check_map_refs.py` runs in
CI (`.github/workflows/map-gate.yml`). Named references
("Domain N (Title)") must match the canonical title in the target
domain's front matter. Prefer the named form for all cross-domain
references; bare "Domain N" references are unvalidatable (audit them
with `--list-bare` after any structural change).

**R3 — Reasoning frameworks vs. house opinions are labeled.** Sections
that argue a position (e.g. the portability argument) are legitimate and
stay — marked as positions. Assessment rubrics built on them must reward
tradeoff articulation, not agreement with the author's conclusion.
(The Domain 6 Kubernetes organizational-fit editorial was demoted to a
neutral fit-question framing in v0.25 per owner decision 2026-07-09:
agentic support lowers the operational-overhead ledger, and basic
orchestration fluency is now assumed of any modern sysadmin.)

**R4 — New domains follow the established chapter shape:** why-this-domain,
scope/boundary statement (naming which existing domains own adjacent
content), Reasoning Framework (taught/actually-for/misuse), core
concepts, level definitions (1 Literacy / 2 Audit / 3 Commission /
4 domain-appropriate expert level), 3–6 exercises with Watch For notes.

## Phase 0 — Canonical source migration (DONE, this session)

- [x] Convert v0.23 .docx → markdown, one file per domain plus
  front matter, assessment design principles, version history
  (`curriculum/`, 17 files). Custom converter preserved headings,
  tables, exercise blocks, and inline formatting.
- [x] Repair all 24 confirmed stale cross-references and counts from the
  v0.19 renumbering (see v0.24 version-history entry for the list).
- [x] Cross-reference gate: `scripts/check_map_refs.py` + CI workflow.
  Regression-verified: reintroducing a stale reference fails the gate.
- [x] Render pipeline: `scripts/build_map.sh` → `dist/*.docx`, `dist/*.html`.
- [x] README: taxonomy table synced to the map's canonical labels
  (was Awareness/Application/Analysis; now Literacy/Audit/Commission/
  Adaptation), canonical-source note added.
- [x] Version bumped to 0.24 with a full changelog entry.

The original `sysadmin_competency_map_v23.docx` stays in the repo root as
the last hand-edited artifact; it should be moved to an `archive/` folder
once the team confirms the rendered .docx is an acceptable replacement.

## Phase 1 — New domains (team, with owner review)

Numbering per R1: next free numbers, appended. Suggested reading order
in parentheses; the manifest decides, not the number.

### Domain 15 — Directing AI Agents (reads after 1)

**Absorb the existing d15.** The platform already assesses 20 scenarios
synced from agentic-onboarding; the map has no chapter for them. This is
authoring-by-reverse-engineering: derive the level ladder and reasoning
framework from the scenarios that exist, then reconcile.

- Candidate reasoning framework: *commissioning is a contract, not a
  wish* — scope, constraints, verification, and abort criteria for
  delegated work, whether the delegate is a junior or an agent. Domain 1
  is its scripting instance; Domain 14's verification strategy section
  is its epistemics. Cross-reference both; move content only if d15's
  scenarios demand it.
- The AI thread becomes structural: preface gains a paragraph naming
  Domains 1 → 14 → 15 as the framework's through-line on
  machine-generated work. This is the framework's clearest
  differentiation from legacy certs; make it legible.

### Domain 16 — Observability & Alert Design (reads after 11)

Pull the threads the map already has: detection as underthin layer (D8),
alert fatigue / success-noise / absence-as-signal (D10), backup
monitoring, "what monitoring would have caught this" (D4, D8, D10, D11).

- Candidate reasoning framework: *an alert is a contract with a
  responder* — every alert asserts "this signal is worth a human's
  attention and has an owner who will act." Alert volume that breaks the
  contract produces the same outcome as no alerting (D10's lesson,
  generalized).
- Core concepts: monitoring the absence of expected events; routing and
  acknowledgment; signal-to-noise engineering; coverage mapping against
  attack/failure paths rather than compliance lists; the
  tool-gap pattern (a SIEM detects nothing on its own — D8).
- Boundary: D11 keeps log-reading mechanics and keeps its Level 4
  (Detection Design) with a cross-reference; this domain owns the
  design/operate layer. Reconcile the two L4s during authoring — the
  cleanest split is D11-L4 = "design detection for an investigation
  posture," D16 = the full alerting lifecycle.

### Domain 17 — Minimum Viable DevOps: Git, Containers, Orchestration (reads after 12)

The "Minimum Viable Linux" framing is proven; reuse it. Not a platform
engineering curriculum — the functional floor for operating in
environments where these are load-bearing, plus knowing when you're out
of your depth. Three sections under one domain (they share the reasoning
framework and the assessment posture):

- **Git**: version control as the change ledger — D9's pre-commitment
  discipline made mechanical. Clone/branch/commit/diff/log/blame;
  reading a diff before applying it (D1's audit discipline transposed);
  what merge conflicts mean; why force-push is a destructive operation.
  Config-as-code repos, GitOps at literacy level.
- **Containers (operational)**: D6 owns the conceptual layer (isolation
  tradeoffs, supply chain) — keep it there, cross-reference. This
  section owns operations: build/run/inspect/logs/exec, image vs.
  container vs. registry, reading a Dockerfile (audit level: what does
  this image contain and run as?), volumes and the ephemeral-filesystem
  reflex (already taught in D6's "wrong model" exercise — deepen to
  intervention level).
- **Kubernetes (operational)**: operating an existing cluster, not
  building one. Candidate reasoning framework: *the reconciliation loop
  as the operational contract* — you do not fix pods; you fix desired
  state, and the controller converges. Extends D6's pod-as-cattle
  mindset shift into practice. kubectl get/describe/logs/events; what
  a Deployment/Service/Ingress/PVC is at literacy level; triage of
  CrashLoopBackOff / ImagePullBackOff / pending-unschedulable;
  when the answer is "this needs a platform engineer."
- The D6 organizational-fit section was demoted to a neutral fit
  question in v0.25; this domain is likewise neutral — the cluster
  exists, operate it competently.

### Domain 18 — Minimum Viable Database Administration (reads after 17; owner said "section" — see note)

Compact domain rather than a section: the level/exercise machinery is
what the platform assesses, and a section can't carry exercises. Keep it
to the MV Linux scale (3–4 exercises).

- Candidate reasoning framework: *the database is state, everything else
  is replaceable* — the asymmetry that explains why DB backup/restore
  semantics differ from VM semantics, why transaction logs exist, and
  why "restore the VM" is not "restore the database."
- Core concepts: transaction log growth as the classic disk-filler
  (ties to D12's disk exercise); backup semantics (full/differential/log;
  point-in-time restore; why a VM snapshot of a busy DB may not be
  consistent); connection strings and auth failure modes; the
  read-replica-is-not-a-backup instance of D10's replica rule; when to
  call a DBA.
- Boundary: D5 keeps storage performance (IOPS/latency for DB
  workloads); D10 keeps restore-test discipline; this domain owns the
  database-specific semantics both of them currently gesture at.

## Phase 1.5 — Platform parity (CONFIRMED by owner 2026-07-09)

The map extends to genuinely fit the "Modern Systems Administration"
title rather than declaring a Windows-centric persona. The organizing move: **the persona is not
"Windows sysadmin" — it is "sysadmin with a declared native platform
plus a functional floor on the other."** The reasoning layer (~80% of
the map's content) is already platform-neutral; the platform-specific
content becomes explicit tracks. The "minimum viable X" pattern —
already proven for Linux, extended by Domains 17–18 — becomes the map's
signature structure: platform-neutral judgment + declared native depth
+ calibrated floors everywhere else.

Work items, sized:

- **Front matter: native-track mechanism** (small). Candidate declares a
  native platform; a full assessment = native-track depth + the MV floor
  on the other platform. Preface persona paragraph written around this.
- **Domain 1 dual-language parity** (moderate). Scope keeps
  PowerShell + Bash as the two languages; author Bash-flavored parallels
  for the five exercises. The audit/commission reasoning is identical —
  that's the point, and the exercises should demonstrate it.
- **Domain 2 → "Identity & Access" extension** (the big lift, part 1).
  Keep the AD/Entra hybrid depth — it is the map's crown jewel and
  reflects market reality (most enterprise Linux identity is still
  AD-joined). Add: Linux-in-AD (SSSD/realmd, Kerberos on Linux), cloud
  IdP / OIDC / SAML as the identity plane for SaaS-first shops, sudo/PAM
  as the tiering instrument on Linux hosts, workload/machine identity.
  The tiering-as-blast-radius framework already covers all of it.

  **Non-Microsoft IdP requirement (owner, 2026-07-09):** include at
  least one Entra/AD-alternative IdP chosen by actual usage, not vibes.
  Research finding (July 2026): among *dedicated* workforce IdPs, Okta
  leads by a wide margin — ~41% of the tracked IdP/SSO category and the
  most-used vendor in spend-based trackers — and every vendor-neutral
  roundup places it as the default non-Microsoft choice in the mid-size
  segment this map targets. Google (Workspace/Cloud Identity) is the
  clear second *pattern*: dominant as the incumbent IdP in
  Google-estate shops (startup/SMB/education) rather than as a chosen
  standalone IdP. The owner's "Google distant second" instinct is right
  weighted by org count, but in the map's mid-size persona segment the
  alternative IdP actually encountered is Okta. Decision: **Okta is the
  primary alternative worked example** (audit-level exercise — e.g.
  reading an Okta org's policy/assignment model against a stated
  intent); **Google Workspace gets a literacy-level treatment** as the
  incumbent-IdP pattern (what it provides, what it lacks vs. Entra
  conditional access, when it is the pragmatic answer). Concepts stay
  protocol-first (SAML/OIDC/SCIM) so Ping/OneLogin/JumpCloud estates
  still map onto the chapter. Sources: ramp.com vendor category data
  (Okta most-used IdP, June 2026); bluefletch.com market-share analysis
  (~41% of IdP category); securityboulevard.com Fortune-2000 IdP
  coverage list; askmeidentity.com / startwithidentity.com 2026
  roundups. Re-verify share at authoring time; the segment nuance
  matters more than the precise number.
- **Domain 3 / Domain 11 example sweeps** (small). Dual-tool examples
  (dig/nslookup, traceroute/tracert, nftables/Windows Firewall); a
  syslog/journald credential-stuffing mirror of the Event 4625 exercise.
- **New domain: Minimum Viable Windows Administration** (the big lift,
  part 2; next free number). The symmetric mirror of Domain 12, for
  Linux-native candidates: AD member-server basics and what GPO does to
  a box, Event Viewer navigation, services/sc, PowerShell survival
  vocabulary, WinRM/RDP, licensing/activation gotchas, the
  Windows-reflex-on-Linux failure mode inverted. Domain 12's chapter
  shape makes this near-mechanical to author.
- **Coverage matrix** (small): add RHCSA / Linux+ columns so the gap
  analysis isn't benchmarked only against Windows-adjacent certs.
- **Platform implication**: exercises exist in platform flavors where
  content is platform-specific; capability profiles annotate native
  track vs. floor. Calibration per flavor.

Total honest sizing: roughly two Phase-1 domains' worth of authoring
(the Domain 2 extension and MV Windows), plus sweeps. Deliberately still
out of scope: macOS/endpoint management, network engineering depth,
full DBA — the floors stop where the specialist roles begin.

## Phase 2 — Revisions to existing content (team)

- **Persona/preface rewrite**: superseded by Phase 1.5 if approved —
  the preface then declares the native-track model instead of a
  Windows-centric persona. If Phase 1.5 is declined, fall back to the
  original item: declare the hybrid Windows-infrastructure persona on
  page one.
- **Coverage matrix honesty**: the Importance column is author judgment —
  label it as such or cite incident-cause data. Add a row note for the
  new domains once authored.
- **Domain 7 trim**: keep the approximation-map framework and divergence
  patterns; cut or drastically compress the provider comparison tables
  (instance families, Spot interruption rates, governance hierarchies) —
  recall-shaped and fast-rotting, contra the preface's own standard.
- **Rubric neutrality pass (R3)**: Portability Decision and
  Kubernetes-adjacent exercises re-rubriced to reward tradeoff
  articulation over conclusion-matching.
- **L4 taxonomy reconciliation**: global taxonomy text updated to say L4
  is the domain-appropriate expert level (adaptation OR
  arbitration/design), naming the variants. Levels described as
  work products ("L3 output = a commission artifact a third party could
  review") to keep cross-domain comparability honest.
- **Patch & vulnerability management**: add as a section in Domain 9
  (change discipline owns the cadence/test-ring/emergency-change
  machinery; D8 cross-references for the risk framing). Prioritization
  (exploitability × exposure vs. raw CVSS), ring design, out-of-band
  decisions.
- **Domain 10 title**: either add the resilience-architecture content
  (HA vs DR, failover testing, dependency-ordered recovery) or retitle
  to "Backup & Recovery." Small; decide during the pass.
- **Platform README / map drift**: fixed for the taxonomy (Phase 0);
  keep in sync when Domains 15–18 land (README's "14-domain" language,
  scenario counts).

## Phase 3 — The development-path essay (owner + agent, drafted for owner's voice)

A new front-matter section (or companion essay): **"How Competence Forms
Now."** The map asserts the audit/commission inversion; this section
defends its development path. Outline:

1. **The old paths are closing.** You either got in early and learned at
   work, or you burned free time on home labs — usually both. Much of
   the surface is now gated behind cost or enterprise tiers; the
   self-taught path no longer replicates.
2. **The acquisition problem.** If Levels 1–3 are where AI-assisted work
   lives, where do audit skills come from without authorship reps?
   Position to defend: deliberate practice on *reading and predicting* —
   simulate-then-verify against real artifacts — can substitute for
   authorship reps if it is structured (which is precisely what the
   assessment platform's staged-reveal scenarios are). Authorship
   doesn't vanish; it becomes a training exercise rather than the job.
3. **The incubation economics.** Training a junior now carries a
   visible, priceable cost against agentic substitution — and the
   poaching asymmetry (train for a year, lose to the competitor who
   didn't pay for training) is sharper than it was. Individually
   rational, collectively ruinous: the industry consumes seniors it no
   longer produces.
4. **The guild argument.** Historically, portable credentials and
   apprenticeship norms were exactly what guilds provided: a neutral
   body that made training investment legible and transferable instead
   of a pure loss to the trainer. A calibrated, vendor-neutral
   capability profile — which is what this map plus the assessment
   platform produce — is proto-guild infrastructure. State the ambition
   honestly and modestly: this project cannot fix the economics, but it
   can supply the measurement layer a guild-like arrangement would need.
5. Connect to the spiral-learning model and D13's scaffolding argument.

The argument is the owner's (2026-07-09 discussion); the draft should be
reviewed for voice before merge. This section also answers the strongest
standing objection to the framework's thesis, so it earns front-matter
placement rather than an appendix.

## Phase 4 — Structural split (deferred, revisit after Phase 1)

Map / field guide / item bank. The published Watch For notes are burned
as assessment items (fine — they become worked examples); the platform's
calibrated item bank stays private and is generated fresh to the map's
specs. The curriculum/ layout was chosen so this split is a file move,
not a rewrite. Do not start until Domains 15–18 have stabilized the
map's shape.

## Sequencing and ownership

| Work | Owner | Depends on |
|------|-------|-----------|
| Phase 0 (migration, gate, repairs) | done — agent, 2026-07-09 | — |
| D6 editorial demotion (v0.25) | done — agent, 2026-07-09 | — |
| Phase 1.5 (platform parity) | team — confirmed 2026-07-09 | Phase 0 |
| Domain 15 (Directing AI Agents) | team | Phase 0 |
| Domain 16 (Observability) | team | Phase 0 |
| Domain 17 (MV DevOps) | team | Phase 0 |
| Domain 18 (MV Database) | team | Phase 0 |
| Phase 2 revisions | team (rubric pass needs owner sign-off per R3) | can run parallel to Phase 1 |
| Phase 3 essay | draft: agent; voice/merge: owner | none — high value, start early |
| Phase 4 split | team | Phases 1–2 |
| Calibration of new-domain scenarios | team | each domain as it lands |

Each new domain lands as: map chapter (curriculum/NN-\*.md, front matter
per R2) → gate green → scenarios authored to Schema V2.0 → calibration
harness pass → README counts updated.

## Out of scope

- Renumbering anything (R1).
- Changing the four-level taxonomy itself (reconciling its description
  is Phase 2; replacing it is not on the table).
- The assessment platform's evaluator/calibration mechanics (tracked in
  breadcrumbs, not this plan).
- Public credentialing/guild operations — Phase 3 states the argument;
  building an institution is not a work item.
