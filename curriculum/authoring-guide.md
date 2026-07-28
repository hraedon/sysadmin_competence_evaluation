---
reviewed: 2026-07-10
---

# Authoring Guide: Writing a New Curriculum Chapter

This guide is for agents drafting new domain chapters for the Modern Systems Administration Competency Map. It is concise — read it before you write.

The map has standing rules (R1–R4) established in `plans/001-curriculum-expansion.md`. This guide restates them in the order you will encounter them while authoring. When this guide and the plan disagree, the plan is authoritative.

## 1. Domain Numbers Are Stable IDs (R1)

Never renumber a domain. New domains take the next free number. The number is an identity, not a position. Reading order is a property of the build manifest (`scripts/build_map.sh` ORDER), not of the file or the domain. A domain numbered 17 may read after domain 12 — that is the manifest's job, not yours. Do not renumber to "fix" reading order. The v0.19 renumbering left stale cross-references for four versions. It will not happen again.

## 2. Chapter Shape (R4)

Every domain chapter follows the same structure. This is not a suggestion — it is what makes the map a map rather than a pile of essays. The shape:

1. **Front matter** (YAML block): `domain` (number), `id` (kebab-case slug), `title` (quoted string), `subtitle` (quoted string, the one-line thesis), `reviewed` (ISO date). The `reviewed` date makes staleness mechanically visible — a map claiming "modern" should be able to show which parts recently were.

2. **Domain heading and subtitle** — `# Domain N: Title` followed by the subtitle in italics.

3. **Scope and Boundary** — what the domain covers, what it does not cover, and which existing domains own adjacent content. Name the neighbors explicitly: "Domain 11 (Log Reading and Diagnosis) owns the mechanics of finding it in real log data." This is where you prevent content duplication before it starts. If two domains could plausibly own a topic, the boundary statement resolves it.

4. **Reasoning Framework** — the taught / actually-for / misuse cadence (see section 3 below).

5. **Core concepts** — the domain's technical substance, organized under subheadings. This is where the domain earns its existence. If the core concepts section is thin, the domain should be a section in another chapter, not its own domain.

6. **Level Definitions** — a four-row table (see section 4 below).

7. **Assessment Exercises** — 3–6 exercises, each with a scenario block (italicized) and a **Watch For** note (see section 5 below).

## 3. The Reasoning Framework: Taught / Actually-For / Misuse

Every domain's Reasoning Framework section follows the same three-part cadence. This is the map's signature structure. It appears in every chapter from Domain 1 through Domain 14, and Domain 13 (Frameworks as Tools — Synthesis) names the pattern explicitly. By the time a reader reaches Domain 13, the synthesis should be recognition, not introduction.

- **How it is normally taught**: the conventional presentation — the way textbooks, certifications, and training materials frame the domain. Name the implicit model. This is usually a simplification that is not wrong but is incomplete in a way that matters.

- **What it is actually for**: the real purpose. The mental model a practitioner actually uses, the one that survives contact with production. This is where the domain's thesis lives. It should be a transferable model the candidate can apply to novel situations, not a fact to recall.

- **What misuse looks like**: the failure mode. What happens when someone applies the taught model without understanding the actual purpose. This is the most important paragraph in the section — it is what the assessment exercises test for. If you cannot articulate the misuse pattern, the reasoning framework is not sharp enough yet.

The three parts are not optional. If you find yourself wanting to skip one, the reasoning framework needs more work, not less structure.

## 4. Level Definitions and the L4 Taxonomy

All domains use the same four-level taxonomy. Levels are cumulative — Level 3 implies Levels 1 and 2. Levels are described as **work products**: the artifact a practitioner at that level produces that a third party could review. Describing levels as work products keeps cross-domain comparability honest.

| Level | Label | Work product |
|-------|-------|-------------|
| 1 | Literacy | A description |
| 2 | Audit | A risk assessment |
| 3 | Commission | A specification |
| 4 | Domain-appropriate expert level | A defensible judgment under constraints |

**L4 is the domain-appropriate expert level.** It is not a fixed label. Each domain names its own L4 variant:

- In most domains, L4 is **adaptation** — making targeted, understood modifications to existing work. Taking a correct implementation and safely adapting it to a different context. Example: Domain 12's "Linux Maintenance" — maintaining a system in a known state over time and recognizing when accumulated undocumented state is a liability.

- In judgment-heavy domains, L4 is **arbitration or design** — making defensible tradeoff decisions under organizational pressure and competing constraints. Example: Domain 8's "Security Arbitration" — holding a coherent risk management position when the business wants to skip a control.

The common thread: L4 work is **defensible, not just correct**. A third party reviewing it can follow the reasoning that produced it. Name your domain's L4 variant in the level table. If you cannot distinguish your L4 from your L3, the domain may not have enough judgment depth to warrant a separate L4 — and that is fine, but say so.

## 5. Assessment Exercises and R3 Rubric Style

Each domain carries 3–6 assessment exercises. Each exercise has two parts:

- **The scenario** (italicized block): a specific situation, transcript, or artifact the candidate must work with. Novel scenarios are required — a candidate who has seen the scenario before is being assessed on memory, not reasoning. Information reveals should be staged where the domain supports it.

- **Watch For note** (bolded): what distinguishes candidates at different reasoning levels. The Watch For note is the rubric. It describes the reasoning that demonstrates competence, not the answer that earns points.

**Rubrics reward tradeoff articulation, never conclusion-matching.** This is R3, and it is the most violated rule in assessment design. When a domain's reasoning framework argues a position (e.g. the portability argument in Domain 7, the Kubernetes organizational-fit question), the rubric must reward the candidate's ability to articulate the tradeoff — what is gained, what is given up, and under what conditions the position holds or breaks. A candidate who reaches the author's conclusion without articulating the tradeoff has not demonstrated the skill. A candidate who reaches a different conclusion but articulates the tradeoff defensibly has.

**Reasoning frameworks vs. house opinions are labeled.** Sections that argue a position are legitimate and stay, but are marked as positions. The distinction: a reasoning framework (e.g. "security is risk management") is a transferable mental model. A house opinion (e.g. "Kubernetes is overkill for a shop this size") is a judgment call that depends on context the candidate may not share. Assessment exercises built on house opinions must frame them as tradeoff questions, not as facts to be recalled.

## 6. The D7 Lesson: Concepts Endure, Vendor Specifics Rot

*Concepts stable across the transition; vendor specifics only where load-bearing.*

This is the standing rule that is easiest to violate and hardest to detect after the fact. Vendor specifics rot — instance families change, console layouts shift, pricing tiers move, product names get rebranded. Concepts endure — the reconciliation loop, the risk management tradeoff, the commission-audit discipline.

Include vendor specifics only where they are **load-bearing for the reasoning**, not for recall. "kubectl get pods" is load-bearing if the exercise is about triaging a CrashLoopBackOff — the command is the vehicle for the reasoning. A table of AWS instance families is not load-bearing — it is recall-shaped and will be wrong within eighteen months.

The Kubernetes and Okta content is where authors will be most tempted to violate this rule. The temptation is understandable: vendor specifics feel concrete and useful. They are also the first thing that makes a chapter look dated. When in doubt, ask: *would this content still be correct if the vendor renamed the product tomorrow?* If yes, it is conceptual. If no, it is vendor-specific — include it only if the reasoning cannot be expressed without it, and frame it as an example, not a specification.

## 7. Cross-References (R2)

Cross-references are gated. `scripts/check_map_refs.py` runs in CI (`.github/workflows/map-gate.yml`). The gate validates that named references match the target domain's canonical title.

- **Use the named form for all cross-domain references:** "Domain 11 (Log Reading and Diagnosis)" — not "Domain 11" alone. The named form is validatable; the bare form is not.

- **The title in the reference must match the `title` field in the target domain's YAML front matter exactly.** If you rename a domain's title in its front matter, every cross-reference to it across the map must be updated. The gate will catch mismatches in CI, but fixing them is your job, not the gate's.

- **Bare "Domain N" references are unvalidatable.** Audit them with `check_map_refs.py --list-bare` after any structural change. Prefer the named form in all new writing.

## 8. Every Chapter Gets an Adversarial Review Pass Before Merge

No chapter merges on first draft. Every new domain gets an adversarial review pass before it lands. The review checks:

- Does the reasoning framework's misuse section actually describe a failure mode the exercises can test? Or is it hand-waving?
- Do the Watch For notes reward tradeoff articulation, or do they secretly reward conclusion-matching? (R3)
- Are vendor specifics load-bearing, or are they recall-shaped? (D7 lesson)
- Do cross-references use the named form and match canonical titles? (R2)
- Does the L4 variant make sense for this domain, or is it a copy-paste from another domain's level table?
- Is the scope and boundary statement specific enough that a reader knows which adjacent domain owns the content this one does not?

If the review surfaces issues, fix them before merge. The map's quality is a function of what survives review, not what survives the first draft.

## Quick Reference: Front Matter Template

```yaml
---
domain: 15
id: directing-ai-agents
title: "Directing AI Agents"
subtitle: "Commissioning is a contract, not a wish"
reviewed: 2026-07-10
---
```

The `domain` number is the next free integer (R1). The `id` is the kebab-case slug used in filenames and cross-references. The `title` is the canonical name used in named cross-references (R2) — get it right, because every reference across the map must match it exactly. The `subtitle` is the one-line thesis. The `reviewed` date is the ISO date of the most recent content review.

## Quick Reference: File Naming

Domain chapters live in `curriculum/` as `NN-slug.md`, where `NN` is the zero-padded domain number and `slug` matches the `id` field in the front matter. Example: `curriculum/08-security-reasoning.md`.

## What Not to Do

- Do not renumber domains to improve reading order. (R1)
- Do not use bare "Domain N" references. (R2)
- Do not write rubrics that reward agreement with your conclusion. (R3)
- Do not skip the taught / actually-for / misuse cadence. (R4)
- Do not include vendor specifics that are not load-bearing for the reasoning. (D7 lesson)
- Do not merge without an adversarial review pass.
- Do not add comments to chapter files. The curriculum speaks in prose.
