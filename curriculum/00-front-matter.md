---
reviewed: 2026-07-10
---

# Modern Systems Administration

Competency Map & Assessment Framework

*Version 0.26 — Working Draft*

# Preface: Why This Exists

The systems administrator role has changed faster than the credentialing ecosystem has been able to follow. CompTIA Server+ was last substantially revised in 2019. The exam tests whether a candidate can recall the maximum cable length for Cat6, the default port for LDAP, and the difference between RAID 5 and RAID 6. These are not unimportant facts. They are also not what separates a capable junior administrator from an ineffective one.

The gap is not about knowledge breadth. Candidates who pass Server+ often have reasonable breadth. The gap is about reasoning under uncertainty — the ability to take a symptom, form a hypothesis, gather targeted evidence, and revise. It is about knowing which things to touch during a change window and which things not to touch. It is about being able to read a script that an AI system generated and recognize that it will do something destructive on line 47.

*This document is not a competing credential. It is an opinionated map of what modern sysadmin competency actually looks like, and a framework for assessing it honestly. The intended audience is candidates who want a more accurate picture of their own capabilities, and organizations that want a better signal than a multiple-choice score.*

A note on AI tooling: the continued improvement of AI coding assistants like Claude Code and GitHub Copilot has already begun to erode the value of scripting authorship as a differentiating skill. A junior administrator who can describe a task clearly and evaluate whether the resulting script is safe, correct, and minimal is more valuable than one who can write PowerShell from memory but can't audit someone else's work. This framework reflects that shift explicitly.

A note on the AI through-line: three domains form the framework's spine on machine-generated work. Domain 1 (Scripting & Automation) teaches the commission-audit discipline — specifying what an agent should do and verifying what comes back. Domain 14 (Theory of Mind) teaches the cognitive operation — modeling what another agent knows, defaults to, and will do next. Domain 15 (Directing AI Agents) applies both to the specific case of AI coding agents — the contract is the same, the delegate is different. This is the framework's clearest differentiation from legacy certifications, none of which address the judgment of directing AI-produced work. The thread is structural, not a sidebar: by the time a reader reaches Domain 15, they have practiced the underlying skills in every preceding domain.

A note on how this document is structured: each domain contains a section called 'Reasoning Framework' that introduces a foundational model — sometimes a named industry framework, sometimes an implicit mental model that practitioners use without having a name for it. These sections share a common structure: here is how the framework is normally taught, here is what it is actually for, here is what misuse looks like. A late domain, Domain 13 (Frameworks as Tools — Synthesis), synthesizes the pattern explicitly. The goal is that by the time a reader reaches Domain 13, they have practiced the underlying skill enough that the synthesis is recognition rather than introduction.

A note on progression: this framework does not assume linear completion. The intended learning model is spiral rather than sequential — a learner moves through all domains, identifies weaknesses, and returns to those areas at increasing depth across multiple passes. Competence develops through repeated exposure and iteration, not through clearing domains in order. There is no ceremony marking the transition from one level to the next. The levels exist to describe where reasoning currently sits, not to gate further exploration.

A note on Domain 14: Theory of Mind is the name given to the cognitive skill of accurately modeling another agent's knowledge state, intentions, and likely behavior. It appears last because it draws on specific situations from all preceding domains and requires the full technical context to be non-trivial. It applies equally to human agents — users, colleagues, managers, vendors — and to AI systems. Domain 14 is not a soft skills module. It is a reasoning domain with the same structure as the others, and its assessment exercises use transcript analysis rather than scenario response, because the skill is reading a communication situation accurately rather than producing a technical artifact.

# The Coverage Gap

The matrix below maps all eighteen competency domains in this framework against two widely-used certifications: CompTIA Server+ and Microsoft AZ-104. The 'Importance' column reflects real-world weighting based on what actually causes outages, security incidents, and failed change windows — not exam frequency. Theory of Mind and Reasoning Frameworks have no cert coverage by definition; they are included because the gap is the point.

| Domain | Importance | Server+ | AZ-104 | Gap Note |
| --- | --- | --- | --- | --- |
| Scripting/Automation | High | Low | Medium | *Tests syntax, not audit or commissioning* |
| Identity & Hybrid IAM | Critical | Low | Medium | *On-prem AD depth missing from cloud certs* |
| Networking Fundamentals | High | Medium | Low | *Cloud certs skip practical routing/VLAN work* |
| Certificate & PKI | High | Low | Low | *Nearly absent from all mainstream certs* |
| Storage Architecture | Medium | Medium | Low | *Reasonable Server+ coverage; burst/sustained and SDS gaps* |
| Compute Architecture | High | Low | Low | *VM basics covered; containers, orchestration, blast radius absent* |
| Cloud Primitives & Abstraction | High | None | Medium | *AZ-104 covers cloud vocabulary; physical substrate translation absent* |
| Security Reasoning | Critical | Low | Low | *Covered by Sec+/CISSP, not sysadmin certs* |
| Change Management | High | None | None | *Absent across all technical certifications* |
| Backup & Recovery | High | Medium | Low | *RPO/RTO concepts rarely tested with scenarios* |
| Log Reading & Diagnosis | High | Low | Low | *Tested conceptually, not with real log data* |
| Linux Administration | Medium | Low | None | *Windows-centric certs ignore Linux entirely* |
| Reasoning Frameworks | High | None | None | *Meta-skill not addressed in any certification* |
| Theory of Mind | Critical | None | None | *Entirely absent; closest analog is behavioral interviewing, not instruction* |
| Directing AI Agents | Critical | None | None | *No cert addresses the judgment of directing AI-produced work — the modern differentiator* |
| Observability & Alert Design | High | None | Low | *AZ-104 covers Azure Monitor basics; alert lifecycle and signal-to-noise absent* |
| MV DevOps (Git/Containers/K8s) | High | None | Low | *AZ-104 touches AKS; operational triage and Git discipline absent* |
| MV Database Administration | Medium | Low | None | *Server+ covers basic DB concepts; backup semantics and log growth absent* |

*The pattern is consistent: the domains where bad judgment causes the most damage — identity, security reasoning, change discipline, and certificate management — are the ones with the least coverage in existing exams. The three domains with no cert coverage at all (Change Management, Theory of Mind, Reasoning Frameworks) are the ones most responsible for the difference between technically competent and professionally effective.*

# Framework Overview

This framework has three components, each serving a different purpose. They are designed to work together but can be used independently.

| Competency Map | Defines eighteen competency domains, the four-level skill taxonomy within each, and the reasoning behind the coverage decisions. This document. |
| --- | --- |
| Assessment Module | Scenario-based diagnostic exercises and conceptual probes that produce a capability profile across all eighteen domains. Emphasis on applied reasoning, not recall. |
| Learning Paths | Targeted content mapped to assessment gaps. Structured as: mental model explanation, worked example, practice problem. Designed to respond to a capability profile, not to be consumed linearly. |

## How to Use This Document

This document is long. Most readers do not need to read all of it before getting value from it. The right entry point depends on what you are trying to do.

| If you are... | Start with... | Then... |
| --- | --- | --- |
| An individual working on your own development | The Preface, Coverage Gap matrix, and Skill Level Taxonomy | *Read domains in document order. For each domain, work through the assessment exercises before reading the Watch For notes. Return to domains where you find gaps.* |
| A team lead designing development plans | The Coverage Gap matrix and Domain level definitions | *Use the level definitions to calibrate where your team members sit. Use the assessment exercises as development conversations, not tests. Domain 13 (Synthesis) gives you a vocabulary for discussing reasoning patterns across domains.* |
| A hiring manager evaluating a candidate | Domain level definitions for roles relevant to the position | *Use the Audit-level assessment exercises as structured interview questions. The Watch For notes in each exercise describe what distinguishes candidates who have internalized a domain from candidates who have memorized its vocabulary.* |
| An educator or curriculum designer | The Preface and Domain 13 (Frameworks as Tools — Synthesis) | *The design notes companion document describes the pedagogical decisions behind each domain. The assessment exercise format — scenario plus Watch For — is the structural unit this framework uses throughout and can be adapted to other delivery formats.* |

## What a Full Assessment Run Looks Like

Each domain contains 3–5 assessment exercises. A complete assessment run covers all eighteen domains, typically over multiple sessions. Each exercise presents a scenario or transcript and a Watch For note that describes what distinguishes candidates at different reasoning levels. The output is a capability profile: a per-domain level estimate based on observed reasoning, not right/wrong scoring.

The assessment is diagnostic, not evaluative. Wrong answers are more informative than correct ones — they reveal where a candidate's mental model diverges from the domain's reasoning framework and point to specific development work. A candidate who consistently applies the right framework to the wrong problem has a different gap than one who applies no framework at all.

*Sample profile: a candidate scores Level 2 in Domains 1 (Scripting), 2 (Identity), and 3 (Networking); Level 1 in Domains 4–8; and is unassessed in Domains 9–14. How to read this: the candidate can identify risks in existing scripts and configurations but cannot yet specify requirements well enough to direct production work. Their networking and identity foundations are solid. They have not been assessed on operational domains (change management, backup, log reading) or the extended domains. A development plan would focus on Domains 4 (PKI) and 8 (Security Reasoning) as natural next steps given the Domain 2 and 3 foundations, and introduce Domain 9 (Change Management) early because its patterns appear across all subsequent work.*

Domain 14 (Theory of Mind) uses a different exercise format — transcript analysis rather than scenario response — and its full assessment requires live simulation with a human or AI playing the counterpart role. The transcript exercises in the document test the analytical layer; the application layer requires the friction of real interaction. This is noted in the domain and should be factored into assessment planning.

# Skill Level Taxonomy

All domains use the same four-level taxonomy. The levels are cumulative — Level 3 implies Levels 1 and 2. This taxonomy is deliberately different from the traditional 'can write code / can't write code' axis. The organizing question at each level is not 'what can you produce?' but 'what can you reason about?'

Each level is defined by its **work product** — the artifact a practitioner at that level produces that a third party could review. Describing levels as work products keeps cross-domain comparability honest: an L3 in scripting and an L3 in security reasoning produce different artifacts, but both produce a commission artifact that specifies requirements well enough to direct production work and evaluate what comes back.

| Level | Label | Work product | What it means |
| --- | --- | --- | --- |
| Level 1 | Literacy | A description | Can read and describe. Given a configuration, a script, or a log file, can explain in plain English what it does, what state it implies, and what would change if it were different. No production or modification required. |
| Level 2 | Audit | A risk assessment | Can identify risks, gaps, and failure modes. Given a script, a firewall rule set, or a GPO, can identify specific problems — destructive operations, privilege assumptions, silent failure modes, scope creep. Can assess severity accurately. |
| Level 3 | Commission | A specification | Can specify requirements well enough to direct production. Can write a clear, constrainted specification for a task — including safety requirements, failure behavior, idempotency expectations, and test criteria — and evaluate whether a delivered artifact meets it. |
| Level 4 | Adaptation | A defensible judgment under constraints | The domain-appropriate expert level. In most domains this is **adaptation** — making targeted, understood modifications to existing work, taking a correct implementation and safely adapting it to a different context. In domains where the expert skill is judgment rather than modification, it is **arbitration or design** — making defensible tradeoff decisions under organizational pressure and competing constraints (e.g. Security Arbitration, Detection Design). Each domain names its own L4 variant; the common thread is that L4 work is defensible, not just correct — a third party reviewing it can follow the reasoning that produced it. |

*Level 4 is where traditional scripting and deep technical knowledge matter most. Levels 1–3 are where AI-assisted workflows live — and where current training almost universally fails to prepare candidates.*
