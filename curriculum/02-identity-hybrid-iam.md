---
domain: 2
id: identity-hybrid-iam
title: "Identity & Hybrid IAM"
subtitle: "Active Directory, Entra ID, and the hybrid realities most organizations actually live in"
reviewed: 2026-07-10
---

# Domain 2: Identity & Hybrid IAM

*Active Directory, Entra ID, and the hybrid realities most organizations actually live in*

## Why This Domain Is Critical

Identity is the spine of every other domain. A misconfigured firewall rule causes an outage. A misconfigured identity allows unauthorized access to everything the affected account could reach. The blast radius of identity mistakes is disproportionately large, and the most dangerous mistakes are the ones that work fine until they don't — overprivileged accounts, stale access, tiering violations, authentication policy gaps.

The hybrid reality is what current certs consistently miss. AZ-104 covers Entra ID reasonably well in isolation. Server+ covers on-premises AD in isolation. Neither covers the integration layer — UPN routing, password hash sync, pass-through authentication, hybrid join, the behavior of SSPR against on-prem write-back — with any depth. This is precisely where most mid-size organizations actually live.

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Identity Literacy | Can read and describe an AD structure, a user object, a group policy link order, or an Entra conditional access policy. Can explain what each component does without being able to build one from scratch. |
| Level 2 | Identity Audit | Can identify misconfigured permissions, tiering violations, stale access, overprivileged service accounts, and missing MFA coverage. Can evaluate a policy against a stated security intent and identify gaps. |
| Level 3 | Identity Commission | Can specify requirements for an identity change: what the change is, what it affects, what it must not affect, how to verify it worked, and how to revert it. Can evaluate whether a delivered implementation meets the spec. |
| Level 4 | Identity Implementation | Can make targeted changes to AD structure, group policy, Entra conditional access, or hybrid configuration with full understanding of side effects. Changes are minimal, tested, and documented. |

## Core Concepts

### Active Directory Foundations

- Objects and attributes — users, computers, groups, OUs, and the schema that defines what attributes exist

- Group Policy — processing order, inheritance, blocking, enforcement, and the difference between computer and user policy

- Kerberos and NTLM — when each is used, why NTLM is the fallback that attackers target, what Pass-the-Hash requires

- AdminSDHolder and Protected Users — why privileged account management has specific constraints

- Replication — what USN rollback means, how sysvol replication works, what a journal wrap is

### Enterprise Access Model Principles

The tiered access model (Control Plane, Management Plane, Workload) exists because credential theft in one tier should not enable access to higher tiers. The most common violation is administrators using their privileged accounts for email and web browsing. The second most common is service accounts with domain admin rights.

- Tier 0 — Domain controllers, AD administration, certification authority. Credentials must never touch internet-exposed systems.

- Tier 1 — Member servers and applications. Admin accounts dedicated to this tier, never used at Tier 2.

- Tier 2 — Workstations and user devices. Helpdesk accounts at this tier should have no server access.

### Hybrid Identity Architecture

- UPN routing — why users need a routable UPN suffix and what happens when they don't have one

- Password Hash Sync vs. Pass-Through Authentication — the security and availability tradeoffs of each

- Hybrid join — what it requires, what it enables, and why a device can appear joined but not be functional

- Exchange hybrid — why orphaned mailboxes happen and how to detect them

- SSPR with writeback — what the on-premises requirements are and what breaks if writeback is unavailable

## Reasoning Framework: The Tiering Model as Blast Radius Tool

How it is normally taught: the Enterprise Access Model is presented as a diagram with three tiers and a rule that credentials should not cross tier boundaries. Candidates learn the tier names, learn which systems belong to which tier, and learn that mixing tiers is bad.

What it is actually for: the tiering model is a blast radius calculation tool. The question it is designed to help you answer is not 'which tier does this account belong to?' but 'if this credential is stolen, what can an attacker reach from here?' Each tier boundary is a containment line. A credential compromised at Tier 2 should not be able to reach Tier 1 systems. A credential compromised at Tier 1 should not be able to reach Tier 0. The model's value is in thinking about lateral movement paths before they are exploited.

What misuse looks like: candidates who have memorized the tier model treat tiering violations as compliance findings rather than risk calculations. They can identify that a service account with Domain Admin membership violates the model, but they cannot articulate what an attacker could do with that account, why the blast radius extends to the entire domain, or why this is categorically different from a service account with local admin on a single server. The violation is not interesting. The reachable surface is.

*The practical test for any identity configuration: draw the blast radius from a compromised credential. If a single stolen password or ticket gives an attacker access to domain controllers, certification authorities, or backup infrastructure, the containment model has failed — regardless of whether the tier labels are technically correct.*

## Sample Assessment Exercises

### [LITERACY] Describe the Token

*Candidate is shown a decoded Kerberos ticket (simplified) and asked to explain what access it grants, what system issued it, and when it expires. Secondary question: under what conditions would NTLM be used instead?*

**Watch for:** Confusion about what the ticket represents vs. what the account has permission to access. Inability to identify the conditions that force NTLM fallback.

### [AUDIT] Find the Tiering Violation

*Candidate is given a summary of four accounts: a service account for a monitoring tool with Domain Admin membership 'for ease of setup,' a Tier 0 admin account on a user workstation in a shared Outlook profile, a helpdesk account with the ability to reset passwords in all OUs including Domain Controllers. Candidate must identify violations and explain the risk each presents.*

**Watch for:** Treating tiering violations as theoretical rather than operational risks. Missing the shared Outlook profile as a credential exposure vector. Underrating the Domain Controller OU password reset access.
