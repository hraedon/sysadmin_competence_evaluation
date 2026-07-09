---
domain: 10
id: backup-recovery-resilience
title: "Backup, Recovery & Resilience"
subtitle: "The infrastructure that is irrelevant until it is the only thing that matters"
---

# Domain 10: Backup, Recovery & Resilience

*The infrastructure that is irrelevant until it is the only thing that matters*

## Why This Domain Has a Different Character

Every other domain in this framework addresses systems that are in the critical path of production operations. A failed authentication system is noticed immediately because users cannot log in. A misconfigured firewall rule produces immediate connectivity failures. A certificate expiry breaks applications the moment it occurs. These failures announce themselves.

Backup systems fail silently. A backup job that stopped working three months ago has not affected production. The monitoring alert that would have caught it has been processed as noise alongside hundreds of identical success notifications. The restore test that would have validated recoverability was deferred because production demands were higher priority. The failure accumulates invisibly until the moment the backup is needed — which is the worst possible time to discover it does not work.

This fundamental property of backup infrastructure shapes every element of the domain. The discipline being developed is not how to configure backup software. It is how to maintain vigilance for a system that will not tell you it has failed and will not affect production until the day it becomes the only thing standing between the organization and catastrophic data loss.

*The backup system is the ultimate instance of a control that only matters when it is needed — and is not in the critical path of anything that would cause it to be noticed when it fails. Every practice in this domain is a response to that property.*

## Reasoning Framework: RPO and RTO as Design Constraints, Not Descriptions

How it is normally taught: RPO (Recovery Point Objective) and RTO (Recovery Time Objective) are presented as metrics that describe a backup solution — 'our backup runs nightly, so our RPO is 24 hours.' Candidates learn the definitions and move on.

What it is actually for: RPO and RTO are business requirements that constrain backup architecture design. The direction of causality runs from requirement to architecture, not from architecture to description. An organization that runs nightly backups and calls the result a 24-hour RPO has not made a tradeoff — it has chosen an architecture and labeled the consequence. The correct sequence is: the business defines how much data it can afford to lose (RPO) and how long it can afford to be unavailable (RTO), and the backup architecture is designed to meet those requirements.

What misuse looks like: the RPO conversation that happens after the backup solution is chosen, to describe what the solution provides rather than to define what the business requires. The RTO estimate based on a clean restore of a single system in controlled conditions, applied to a real disaster recovery scenario involving multiple systems on degraded infrastructure with a real team under pressure. The organization that adjusts its stated requirements to match its backup capabilities rather than its backup capabilities to match its requirements.

*The diagnostic question for any backup architecture: if the worst plausible failure occurred right now, could you restore to a working state within RTO, losing no more data than RPO allows, using the actual backup media and tooling you have, executed by the actual team you have? If the honest answer is no, the backup architecture does not meet the business requirement — regardless of what the RPO and RTO documentation says.*

## What a Backup Is and Is Not

The most consequential misunderstandings in backup practice come from confusing mechanisms that provide some protection against some failure modes with mechanisms that provide recovery from data loss. These are not the same thing.

### What a Backup Is Not

- RAID is not a backup. RAID protects against disk failure. It does not protect against accidental deletion, ransomware, logical corruption, or any failure mode that affects all disks simultaneously. A RAID array that is fully operational can contain corrupted, encrypted, or deleted data. The data loss has already occurred — RAID has simply ensured that the bad data is consistently replicated across all disks.

- A snapshot is not a backup. A snapshot is a point-in-time copy that lives on the same storage as the original data. A storage failure that destroys the original data destroys the snapshots. A ransomware attack that has access to the storage layer destroys the snapshots along with the production data. Snapshots are valuable for fast recovery from accidental changes or software failures, but they are not a substitute for a backup that exists on separate storage with separate access controls.

- A replica is not a backup. A synchronously replicated copy ensures that when data is written to the primary, it is simultaneously written to the replica. This means that when data is corrupted, deleted, or encrypted on the primary, the replica immediately reflects that corruption, deletion, or encryption. Replication protects against hardware failure. It does not protect against data loss events that propagate through the replication relationship.

- A backup stored on the same storage as production is not a backup. Operational separation requires physical separation. A backup repository on the same SAN as production data, or on a share accessible with the same credentials as production systems, is not a backup — it is a second copy of data that will be affected by the same events that affect the first copy.

- An untested backup is functionally equivalent to no backup. A backup that has never been restored may be unrestorable. The backup software may have been misconfigured. The backup media may have degraded. The backup may not include all required data. The restore procedure may have undocumented dependencies. None of these failures will be visible until a restore is attempted. An untested backup provides the administrative comfort of appearing to have a backup without providing the operational protection of having one.

*The 3-2-1 rule is the minimum architecture worth discussing: three copies of the data, on two different media types, with one copy offsite. This is a floor, not a ceiling, and it addresses physical failure modes. It does not by itself address the credential separation and immutability requirements that ransomware scenarios demand.*

### The Credential Separation and Immutability Requirement

A backup that can be destroyed with the same credentials used to access production systems is not meaningfully separated from production. In a ransomware scenario, the attacker who has compromised production credentials will enumerate accessible storage and destroy or encrypt backup repositories before triggering the payload. This is standard ransomware operator procedure, and it is effective against organizations that store backups in locations accessible with production credentials.

Immutability — the property of a backup that prevents modification or deletion by any credential with access to production systems — is the specific control that survives this attack pattern. An immutable backup cannot be encrypted by ransomware running under a compromised production account, cannot be deleted by a malicious insider who has domain admin, and cannot be accidentally overwritten by a misconfigured backup job. Immutability requires that the backup system be on a separate trust boundary from production — the credential that writes backups cannot delete them, and the credential that manages production cannot reach the backup repository.

The tiering model from Domain 2 applies directly: the backup infrastructure should be on a separate trust tier from the systems it backs up. A domain admin account that has full access to every system in the environment should not have the ability to delete backup data. The blast radius of a compromised domain admin credential should not extend to the backup repository.

## The Restore Test Is the Only Meaningful Validation

### What a Real Restore Test Looks Like

A backup job that completes successfully every night and has never been restored is an untested backup. The monitoring that confirms the job ran is not a restore test. The email that says the backup succeeded is not a restore test. The only validation that matters is demonstrating that data can be recovered from the backup to a working state within the stated RTO.

A real restore test includes: locating the backup from the system and tooling that would actually be used in a recovery scenario, not from memory or a familiar interface. Authenticating to the restore system with the credentials that would be available during a real event — not elevated credentials that would not ordinarily be used. Transferring the data across the infrastructure that would actually be used. Verifying that the restored data is complete and consistent. Confirming that the restored system operates correctly, not just that files are present.

Most restore tests that do happen are partial or ideal-condition tests: a single file restored from a recent backup, or a full VM restore to a test environment that is not representative of recovery conditions. These tests validate that the backup software is functioning and that recent backups contain the expected data. They do not validate that the full recovery procedure works under real conditions.

### Application-Level Restore Scope

A successful VM restore proves that the VM came back. It says nothing about whether the application running on that VM is in a working state.

Application-level restore failures that a VM-level success would not catch: the application tier restored to a snapshot taken before a schema migration was applied to the database — the application cannot talk to the database. The DNS records that service discovery depends on were not in the backup scope. The application restored but its certificate expired during the period since the backup was taken. The configuration that points the application at the correct backend references an IP address that changed when the system was restored to different infrastructure.

Defining 'working state' for an application requires documenting what working looks like before the test: which functions should work, which integrations should be passing data, what the expected authentication flow is, what the acceptable response times are. That documentation has to exist before the test and has to be testable without impacting production. The second requirement is the one that defeats most organizations: a meaningful application-level restore test requires a production-equivalent environment to restore into. Most organizations do not have one and do not invest in maintaining one, which means they do not know whether their backup actually works until they need it.

### Alert Fatigue and the Backup Monitoring Problem

Backup status emails are the canonical example of monitoring that starts as useful information and becomes noise through volume, repetition, and the absence of consequences for ignoring it. Backup jobs run every night. Every night the email arrives. Most nights it says success. The human who receives it develops a pattern-matching heuristic: email arrives, glance at subject, move on. This is the rational response to a high-frequency, low-signal monitoring stream.

The problem is that when the status changes from success to failure, the same heuristic applies. The failure is processed the same way as the successes that preceded it. The backup that stopped working three months ago has generated ninety failure notifications, each of which was processed as noise. Alert fatigue is not a discipline problem — it is a systems design problem. Humans cannot maintain indefinite vigilance for low-frequency signals embedded in high-frequency noise.

- Route backup failure notifications differently than success notifications: different channel, different urgency, different recipient who is expected to act rather than archive.

- Treat a backup that has not run as a failure, not as silence. Absence of a success notification is itself a signal that requires the same response as an explicit failure.

- Require acknowledgment of backup failures with a documented resolution or an accepted risk decision. A failure that ages out of the queue without acknowledgment is operationally identical to a failure that was never noticed.

- The security dimension: an attacker who wants to ensure that backup destruction goes unnoticed has a ready mechanism in any organization where backup failures are routinely ignored. The alert fatigue problem is a security surface, not just an operational one.

- The detection layer connection: every backup monitoring failure is also a detection failure. The question 'what would have surfaced this earlier?' should be part of every backup audit — not as a retrospective complaint but as a design prompt for building monitoring that produces signal rather than noise.

## Recovery Complexity and the RTO Reality Check

The RTO estimate that appears in a backup policy document is almost never the time it will actually take to recover in a real scenario. The gap between the documented RTO and the actual recovery time is not random — it has specific, predictable causes that can be identified in advance and addressed in the recovery architecture.

What the RTO estimate does not include: the time to confirm that a recovery is actually needed and is not a false alarm. The time to convene the recovery team, which may include people who are asleep, traveling, or unavailable. The time to locate the backup documentation and confirm the recovery procedure. The time to provision or configure the target environment if it does not already exist. The time to verify that the restored system is actually working rather than just that it is running. Most RTO estimates count only the restore transfer time. The full recovery timeline is frequently two to three times that figure.

Live-fire recovery versus clean-room testing: the RTO validated by a controlled restore test is not the RTO achievable during an actual disaster recovery. The differences are specific and compound:

- Degraded infrastructure — in a disaster recovery scenario you may be operating on infrastructure that is partially failed or under unexpected load. Network paths running on failover connections with lower bandwidth. Storage operating at reduced redundancy. Switches handling traffic patterns they were not provisioned for. Every throughput estimate from clean-room testing assumed fully-functional infrastructure.

- Collective versus individual RTOs — you may have validated that each system can be recovered within RTO in isolation. What you have not validated is whether all systems can be recovered within RTO simultaneously, with the real team, on real infrastructure under real stress. Recovery teams are coordinating across multiple workstreams, making decisions under pressure, encountering unexpected dependencies, and discovering that the documented recovery order does not match actual application dependencies. The collective RTO is routinely two to four times what the sum of individual RTOs would suggest.

- Runbook knowledge versus runbook execution — the person who wrote the recovery runbook and the person executing it during a real event are often not the same person. The runbook contains implicit knowledge that was obvious to the author and is ambiguous under pressure. Steps that seemed clear in calm planning require judgment calls during execution. Real recovery exposes runbook gaps that clean-room testing by familiar personnel does not surface.

- Scope discovery — a real disaster recovery frequently reveals that the scope of what needs to be recovered is larger than documented. The system that was not considered critical turns out to be a dependency for three systems that were. The recovery planned for twenty systems requires twenty-six because the dependency map was incomplete.

*The honest test of disaster recovery readiness is not 'can we restore each system within RTO in a controlled test' — it is 'can we restore all required systems to a working state, within the collective RTO, using the team and infrastructure we would actually have, under conditions that are degraded in ways we cannot fully predict.' Very few organizations have tested this honestly.*

## Retention Policy and the Ransomware Timing Problem

What backups you keep and for how long is a separate question from whether backups exist. Organizations often have excellent recent backups and nothing older — because retention policy is set to minimize storage cost rather than to meet the business requirement for how far back recovery might need to reach.

The specific scenario: ransomware that was dormant for 45 days before triggering. The organization has excellent 30-day backup retention and has been faithfully backing up every night. Every backup in retention is a backup of already-encrypted data. The clean backup is 46 days old and outside the retention window. The retention policy was designed to minimize cost. It was not designed with the possibility that every backup in retention could be compromised simultaneously.

Retention policy should be derived from two requirements: the maximum lookback period the business might need for recovery (which drives the retention floor) and the ransomware dwell time that the organization is prepared to defend against (which drives the retention depth specifically for immutable offsite copies). These are different requirements and they produce different retention architectures. A 30-day retention policy that minimizes cost may satisfy the first requirement and completely fail the second.

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Backup Literacy | Can describe what a backup is and is not: can explain why RAID, snapshots, replicas, and same-storage copies do not constitute backups for purposes of data loss recovery. Can describe RPO and RTO as concepts and explain the difference between the two. Can identify the minimum required elements of a backup architecture. |
| Level 2 | Backup Audit | Can assess a described backup architecture against stated RPO and RTO requirements and identify where the architecture fails to meet them. Can identify credential separation gaps, retention policy risks, monitoring that conflates job success with restore readiness, and restore test procedures that do not validate application-level recovery. Can identify the specific failure modes that snapshot, replication, and same-storage copy arrangements would not protect against. |
| Level 3 | Backup Commission | Can write a specification for a backup architecture that meets stated RPO and RTO requirements: what is backed up, how frequently, to what destination, with what retention policy, with what credential separation, with what immutability controls, and with what restore test procedure. Can write a restore test plan that defines application-level success criteria and specifies how the test will be conducted without impacting production. |
| Level 4 | Recovery Architecture | Can design a restore test that reflects actual recovery conditions rather than ideal ones. Can identify the gap between individual system RTO and collective recovery time under degraded conditions. Can assess an organization's backup monitoring posture and identify where alert fatigue has eroded the monitoring signal. Can define a retention policy that addresses both operational recovery requirements and the ransomware timing problem. Can specify the credential separation and immutability controls required by a given threat model. |

## Assessment Exercises

### [LITERACY] Is This a Backup?

*Candidate is given five data protection configurations and must classify each as a backup or not a backup, with explanation: (1) nightly snapshot to a separate volume on the same SAN, (2) synchronous replication to a DR site with separate infrastructure, (3) daily backup to a share on the file server being backed up, accessible with domain admin credentials, (4) weekly full backup to tape stored offsite, never tested, (5) nightly backup to cloud storage using a dedicated backup account that cannot delete objects but can write them. Candidate must explain what failure modes each configuration protects against and what it does not.*

**Watch for:** Candidates who classify replication as a backup because it is offsite, or cloud backup as fully protected without noting the write-only credential limitation (cannot delete backups is good; has the backup account been verified to actually be immutable against the threat model?). Configuration 2 protects against site failure but not against data corruption that propagates through replication. Configuration 4 is technically a backup but the 'never tested' qualifier means it is functionally equivalent to no backup. Candidates who can articulate the specific failure modes each configuration addresses and fails to address are demonstrating Level 2 reasoning.

### [AUDIT] The RTO Claim

*An organization states their RTO is four hours. Their restore test procedure is: restore a single VM from the most recent backup to a test environment, verify the VM boots and responds to ping, mark the test successful. The test has been run quarterly for two years and always passes in under two hours. Candidate must identify the gap between the test and the stated RTO, explain what the test does and does not validate, and describe what a test that actually validates the four-hour RTO would look like.*

**Watch for:** Candidates who accept the test as sufficient because it passes within the RTO. The test validates that recent backups are restorable and that a single VM can be recovered in isolation under ideal conditions. It does not validate application-level working state, collective recovery of all required systems, recovery under degraded infrastructure conditions, or recovery by the actual team following the actual runbook under realistic pressure. A test that validates the four-hour RTO would restore all required systems to application-level working state, using the actual recovery team, following the documented runbook without guidance from the author, under conditions that simulate realistic infrastructure degradation.

### [AUDIT] The Backup That Wasn't

*A ransomware event has occurred. The organization has nightly backups with 30-day retention. Investigation reveals: (1) the ransomware has been dormant for 38 days, (2) the backup repository is a share on a domain member server accessible with domain admin credentials, (3) the backup monitoring sends a nightly email to a shared mailbox that is checked weekly, (4) the last restore test was 14 months ago and tested only file-level recovery. Candidate must identify each gap, explain what it means for the recovery options, and describe what a functional backup architecture for this threat model would have required.*

**Watch for:** Candidates who focus on a single gap without addressing all four. Each gap compounds the others: the 38-day dormancy defeats the 30-day retention, the credential accessibility means the attacker likely destroyed the backups before triggering, the alert fatigue means the destruction may have gone unnoticed, and the outdated restore test means even if backups exist they are of unknown recoverability. A functional architecture for this threat model requires: immutable offsite backups with retention beyond expected ransomware dwell time, credential separation at a separate trust tier from domain admin, monitoring that distinguishes failure from success and requires acknowledgment, and regular restore tests that validate full recovery not just file presence.

### [COMMISSION] The Application Restore

*Candidate must write a restore test plan for a three-tier web application (load balancer, application servers, database). The plan must define: what 'successfully restored' means at the application level rather than the infrastructure level, how the test will be conducted without affecting production users, what the test will validate that a VM-level boot test would not, and what would constitute a test failure beyond 'the VMs did not boot'.*

**Watch for:** Test plans that define success as 'all VMs are running and responding to ping.' The application-level success criteria should include: users can authenticate, core application workflows function end-to-end, the database contains the expected data and is in a consistent state, integrations are passing data correctly, and the application is performing within acceptable parameters. The test plan should also address the production isolation problem explicitly — if the test environment is not production-equivalent, the plan should identify what gaps exist and what failure modes those gaps leave unvalidated.
