---
domain: 9
id: change-management-discipline
title: "Change Management Discipline"
subtitle: "The domain most responsible for self-inflicted outages — and the one with zero coverage in any certification"
---

# Domain 9: Change Management Discipline

*The domain most responsible for self-inflicted outages — and the one with zero coverage in any certification*

## Why This Domain Exists

Uncontrolled changes are the leading cause of self-inflicted outages. Not hardware failures. Not software bugs. Not external attacks. The most common way organizations break their own infrastructure is by changing it without adequate thought about what could go wrong.

The formal justification for change management is risk reduction and auditability. The honest justification is simpler: forcing someone to write down what they intend to do before they do it makes them think through the change more carefully than they would otherwise. Even a bad change process is better than no change process, because the act of documentation surfaces assumptions that would otherwise remain invisible until they produce an outage.

This domain has zero coverage in technical certifications. Server+ does not test it. AZ-104 does not test it. The ITIL framework covers it extensively at a theoretical level, but ITIL knowledge is not sysadmin knowledge — knowing the definition of a Change Advisory Board is not the same as knowing how to write a change plan that will survive contact with production. Organizations train for this internally or not at all. A junior administrator who has internalized change discipline is worth significantly more than one who has not, and there is currently no external signal for this.

## Reasoning Framework: Blast Radius and Reversibility as Pre-Commitment Tools

How it is normally taught: change management is presented as a process — fill out the form, get the approval, execute the steps, document the results. The implicit model is that following the process is the skill.

What it is actually for: change management is a pre-commitment mechanism. Its value is not in the paperwork. Its value is in forcing the person making the change to think through specific questions before they are in the middle of a change window with time pressure, partial information, and sunk cost bias working against good judgment. The process exists to do cognitive work in advance that cannot be done well in the moment.

The two axes that determine how much pre-change rigor is warranted:

- Blast radius — how much could go wrong if this change fails or has unintended effects. A change to a single user account has a small blast radius. A change to a Group Policy Object that applies to all computers in the domain has a large blast radius. A change to a domain controller has the largest blast radius of any routine infrastructure change. Blast radius is not the same as probability of failure — a low-risk change can have a large blast radius, which is exactly why the blast radius calculation matters.

- Reversibility — how easily the change can be undone, and at what cost. A feature flag that can be toggled in thirty seconds is highly reversible. A schema migration that modifies millions of rows is not reversible without a restore. A firewall rule addition is reversible. A firewall rule deletion that other rules depend on is less reversible than it appears. Reversibility is a property of the change and the environment, not of whether a rollback document exists.

A change with small blast radius and easy reversibility can be made with minimal ceremony. A change with large blast radius and low reversibility requires the full weight of the process. The misuse of change management is treating all changes as equivalent — applying identical process to updating a config comment and to a domain controller migration. This produces process fatigue that eventually leads people to bypass the process for everything, including the changes that genuinely warrant it.

*'I have a rollback plan' is not the same as 'this change is reversible.' A rollback plan that requires four hours of work during a maintenance window that is already overrunning is not equivalent to a change that can be backed out in thirty seconds. Evaluating reversibility means evaluating the actual cost and feasibility of the rollback procedure, not whether a rollback document exists.*

## Why Organizational Change Management Usually Fails

### The CAB as Approval Theater

The Change Advisory Board or Change Review Board is the formal oversight mechanism most organizations use. In theory it provides expert review of proposed changes before they are executed. In practice it frequently devolves into approval theater: a meeting in which changes are presented, nobody objects, everything is approved, and the documented approval provides organizational cover if something goes wrong.

The failure mode has a consistent structure. The board exists to provide oversight, which requires time and attention from people who have other jobs. The board meets regularly, which creates a queue of changes waiting for approval. The queue creates pressure to approve quickly. The volume of changes means nobody has time to review each one carefully. The norm becomes approval unless there is an obvious objection. The obvious objections are the ones the submitter already thought of, so the review adds nothing. The board is now a rubber stamp with extra steps.

The organizational function the board is actually serving in this degenerate form is not risk reduction — it is accountability diffusion. If the change goes wrong, the documentation shows that multiple people reviewed and approved it, distributing the organizational cost of failure across a group rather than leaving it with the individual who made the change. This is a real organizational function. It is not the same function as preventing bad changes.

*The tell for an approval-theater CAB: ask how often it rejects or substantially modifies a proposed change. An effective review process rejects or substantially modifies some percentage of what it reviews. A process with a near-zero rejection rate is not reviewing — it is documenting approvals.*

### The Absence of Review

Most organizations perform post-mortems on significant incidents — outages, security events, data loss. Most organizations do not perform any systematic review of changes that succeeded, including changes that succeeded unexpectedly or required significant deviation from the plan during execution. This is a structural learning failure.

A CAB that never reviews successful changes cannot develop calibration about what makes a change actually risky versus what makes it appear risky on paper. The formal risk indicators — number of systems affected, complexity of the change, time in the maintenance window — may or may not correlate with actual change outcomes, and the only way to know is to review the outcomes. Without that feedback loop, the risk assessment process is never corrected against reality.

A CAB that never reviews failed changes cannot learn from them. The post-mortem on an incident identifies what went wrong during execution. The change review would identify what was wrong with the plan, the approval process, or the risk assessment that allowed the change to proceed. These are different failure modes and they require different interventions. Reviewing only incidents produces improvements to execution. Reviewing the change process itself produces improvements to planning.

The specific case worth examining: a change that succeeded but required significant deviation from the approved plan during execution. This change is almost never reviewed. From the organization's perspective, it succeeded — no incident, no ticket, no post-mortem. From a learning perspective, it is the most valuable data point available: the plan was wrong in a way that the executor had to recover from in real time. Understanding what was wrong about the plan, and why the review process did not catch it, is exactly the feedback the change management process needs.

### The Process as Documentation Ritual

In organizations where change management has fully degraded, the process becomes a documentation ritual: changes are executed, then documented, then submitted for retrospective approval. The documentation describes what was done rather than what was planned. The approval is granted because the change is already complete. The process has inverted — instead of thinking before acting, the organization is documenting after acting and calling it change management.

This failure mode is partly structural — aggressive maintenance windows, emergency changes, and the operational reality that some things need to happen faster than any formal process allows — and partly cultural. Organizations that punish failed changes produce incentives to change first and ask permission later. Organizations that treat change management as a compliance exercise rather than a risk reduction tool produce people who know how to fill out the form without internalizing why the form exists.

## When the Plan Doesn't Survive Contact with Production

### The Value and Limits of Pre-Change Documentation

A rigorous change management process requires producing something close to a standard operating procedure for the work to be done: each step, its expected outcome, the verification method, and the abort criterion if the outcome is not as expected. This document has real value. It also will not survive contact with production intact.

The value of the pre-change document is not that it correctly anticipates every step. It is that writing it forces the author to think through the change at a level of detail that reveals assumptions they did not know they were making. The question 'what is the expected output of step 4' cannot be answered without thinking through step 4 carefully enough to know what it should produce. The question 'what is the abort criterion for step 4' cannot be answered without thinking through what could go wrong at step 4. These questions surface unknown unknowns before the change window, which is the only time when surfacing them is useful.

The failure mode of over-rigid plan adherence: the executor follows the plan even when production reality makes clear that following the plan will produce a bad outcome. This is the bureaucratic failure mode — treating procedure compliance as the goal rather than as a means to an end. A plan that encounters reality and is clearly wrong at step 3 should not be executed through to step 10 because it was approved. The plan was approved on the basis of assumptions that have now been falsified. The approval does not survive the falsification of its assumptions.

The failure mode of undocumented deviation: the executor adapts to production reality — correctly — but does not document the adaptation as it happens, planning to reconstruct it afterward. Afterward the change window has ended, the pressure is off, the details are fuzzy, and the documentation describes a version of what happened that is close enough to file but not accurate enough to rely on. The production environment now differs from the documented state in ways that will matter at the worst possible time.

*The correct behavior when production reality diverges from the plan: document the deviation as it happens, even if the documentation is rough notes that get cleaned up later. The rough notes exist. The cleaned-up notes that were never taken do not. A production environment whose actual state can be reconstructed from rough change window notes is better than one whose state must be inferred from what should have happened according to an approved plan that wasn't followed.*

### The Abort Decision

The abort decision — whether to continue a change that is not proceeding according to plan, adapt to production reality, or back out entirely — is made under the worst possible conditions. The change window is running. The maintenance window has a hard end. Stakeholders may be watching. The executor has invested hours of work to reach this point. Every cognitive bias points toward continuing: sunk cost, optimism bias, social pressure not to fail, the sense that the next step might fix the current problem.

The pre-commitment mechanism for the abort decision is the abort threshold: specific, observable conditions established in the change plan that trigger the abort decision automatically, before the change window, before the pressure exists. Not 'if things look bad' — that judgment cannot be made reliably under change window conditions. Instead: 'if service X is not responding within 10 minutes of completing step 3, execute rollback procedure Y and notify the on-call team.' The abort threshold removes the decision from the moment of maximum cognitive impairment by making it before that moment arrives.

The symmetric failure modes of the abort decision:

- Aborting too early — backing out at the first unexpected behavior without assessing whether the unexpected behavior is a problem. Some deviation from the expected path is normal. An executor who aborts every change that produces any unexpected result will never complete complex changes. The abort threshold should be calibrated to distinguish between unexpected and unacceptable.

- Aborting too late — continuing past the point where it was clear the change was not proceeding as planned, hoping that the next step would correct the previous one. This is the most common failure mode and produces the worst outcomes: an environment that is neither the pre-change state nor the intended post-change state, with a rollback that may no longer be clean.

- The rollback quality problem — the rollback plan was written at the same time as the forward plan and has the same epistemic problem: it was written before production reality was known. The rollback plan also must be more conservative than the forward plan, because it will be executed under maximum time pressure with no opportunity to adapt. A rollback plan that requires steps of equal complexity to the forward plan is not a safe backstop — it is a second opportunity for the same class of problems.

The decision to abort should be made by the executor, but the criteria for making it should have been established by the change plan. When those criteria are triggered, the abort is not a failure of the change — it is the pre-commitment mechanism working correctly. Organizations that treat an aborted change as a failure create incentives to continue past abort thresholds, which produces the late-abort failure mode.

### The Pre-Mortem as a Planning Tool

The pre-mortem is the exercise of imagining, before the change is executed, that the change has failed — and working backward from that imagined failure to identify what caused it. It is the most consistently underused technique in change planning and one of the most reliably valuable.

The cognitive mechanism it exploits: the person planning a change is committed to making it succeed. Their mental model is oriented toward success. Optimism bias causes them to underestimate the probability of failure and to discount failure scenarios that feel unlikely. The pre-mortem explicitly asks them to inhabit failure, bypassing the optimism bias by making failure the starting assumption rather than a possibility to be weighed.

A pre-mortem that produces useful output surfaces risks that the forward-planning orientation would miss. The question is not 'what could go wrong' — planners answer that question in risk assessment sections and systematically underweight unlikely scenarios. The question is 'given that this has already failed, what failed?' The past-tense framing changes what scenarios feel plausible and which details feel worth examining.

The connection to the abort threshold: a pre-mortem that identifies specific failure scenarios at specific steps produces the raw material for the abort criteria. If the pre-mortem surfaces 'step 3 could fail to complete within the expected time window if the target system is under load,' the abort criterion for step 3 writes itself. The pre-mortem and the abort threshold are complementary tools that together address the cognitive work that cannot be done well during the change window.

### Iterative Changes and Baseline Drift

Organizations that do change management badly tend to do iterative changes very badly, for a specific structural reason: the change management process evaluates individual changes against a documented baseline. If the baseline itself has been changed repeatedly in ways that were not fully documented, or in ways that each passed review individually but collectively produced an environment that matches no known state, the baseline is fiction.

The specific failure patterns that produce baseline drift:

- The permanent temporary fix — a change made outside the normal process because it was urgent, documented as temporary, never reversed, and now load-bearing infrastructure that subsequent changes have been built on top of. The environment contains a hidden dependency not in any documentation because the change that created it was never properly entered into the change management system.

- Incremental configuration drift — a configuration modified in small increments over time, each individually benign, to a state collectively very different from the documented baseline. No individual change was large enough to trigger rigorous review. The cumulative change is significant. No one knows exactly when the current state diverged from the documented state.

- Undocumented dependency chains — a series of changes that each touched a single component but whose combined effect created a dependency between components that was never explicitly designed. Each individual change plan was accurate. No change plan knew about the others' effects. The interaction between them was discovered in production.

- The emergency change that became the standard — a procedure developed under emergency conditions, documented minimally because there was no time, used again because it worked the first time, and now the de facto process for that type of change without the safety checks the normal process would have required.

The remediation is not more process applied to drift that has already accumulated. More process applied to a broken baseline produces better-documented drift rather than less drift. The remediation is periodic baseline reconciliation: deliberately comparing the documented state of the environment against the actual state, identifying divergences, and either updating the documentation to match reality or remediating the environment to match the documentation. Most organizations do neither on any schedule. The divergence accumulates until something fails in a way that exposes it.

## Changing Systems You Don't Fully Understand

The implicit model in most change management training is that the person executing the change has complete knowledge of the system they are changing. The change plan is written from a position of full information. The abort criteria are calibrated against a known baseline. The pre-mortem imagines failure scenarios in a system the planner understands.

The actual condition is that the planner frequently does not fully understand the system. They inherited it. The person who built it left three years ago. The documentation is absent or wrong in ways they haven't discovered yet. The system has been modified incrementally and the current state reflects decisions that made sense at the time and are now invisible except through their effects. This is not a failure of the sysadmin. It is the job. Every experienced practitioner knows this. No training addresses it directly.

### Known Unknowns and Unknown Unknowns as Planning Inputs

Known unknowns — things you know you don't know — are the ones the change plan can address, however imperfectly. You know the documentation for this subsystem is incomplete, so you add a verification step. You know you have never tested this particular failover path, so you schedule a test before the change window. You know the original design decisions are undocumented, so you budget time to reverse-engineer the relevant piece before proceeding. Known unknowns produce specific risk items in the change plan.

Unknown unknowns — things you don't know you don't know — cannot be directly addressed. What you can do is create conditions that surface them with minimum blast radius: execute in a representative test environment first. Stage the change on a subset of affected systems before full rollout. Build verification windows longer than the happy path requires. Treat the first execution of any change on an inherited system as reconnaissance as much as execution, with the explicit expectation that the change plan may need revision before full deployment.

The posture shift this requires: on a system you built and understand completely, the change plan is a specification — this is what will happen. On an inherited system with incomplete documentation, the change plan is a hypothesis — this is what I believe will happen, here is how I will verify that belief, and here is what I will do when the belief turns out to be wrong in specific ways.

The documentation obligation under uncertainty: when you execute a change on a system you don't fully understand and it succeeds, you know more about the system than you did before. That knowledge exists in your head and nowhere else unless you record it. The post-change documentation obligation is not just to record what was done — it is to record what was learned. What dependencies were discovered. What assumptions were falsified. What the system does that the documentation doesn't describe. Organizations that treat change documentation as a compliance step — fill in the fields, close the ticket — systematically discard this knowledge. The next change on the same system starts from the same epistemic position as the first one.

### Test Environments Are Fake and Will Lie to You

A test environment that perfectly replicates production is production. A test environment that does not perfectly replicate production will surface some failure modes and not others, and the ones it does not surface are precisely the ones that will be discovered in production at the worst possible time. Treating successful test execution as evidence that a production change is safe is a category error.

The specific ways test environments produce false confidence:

- Data fidelity — test environments run with synthetic or anonymized data, or a subset of production data, or a point-in-time snapshot. Production has accumulated edge cases, legacy formats, corrupted records, and boundary conditions that no synthetic dataset anticipates. Changes that process data in any way will find cases in production that testing missed.

- Scale — test environments are almost universally smaller than production. Changes that work at test scale can fail at production scale due to timeout conditions, lock contention, memory pressure, or simply taking longer than expected and running into downstream dependencies with hard time constraints. A database migration that completes in ten minutes in test and takes three hours in production has produced a very different change window than the plan anticipated.

- Integration fidelity — test environments rarely replicate the full integration surface of production. The downstream system the target integrates with may be a stub, a mock, or absent entirely. Hidden dependencies surface in production when the downstream system responds differently than the stub did, or when the timing of the integration at production scale differs from what testing revealed.

- State — production systems have history. They have been running for months or years, accumulating state that reflects every operator who touched them. Test environments are typically provisioned clean or from a recent snapshot. The failure modes that only manifest after extended runtime — growing lock tables, filling log partitions, stale cached state — are invisible in a clean test environment.

*Test environment success is necessary but not sufficient evidence that a production change is safe. The value of test execution is not 'this will work in production.' It is 'I have ruled out the failure modes this environment can surface, and I now have better information about the failure modes it cannot.' The change plan should explicitly identify which categories of risk test execution addresses and which remain open after testing.*

### Sandbagging Is Your Friend

In change management, sandbagging means building margins into estimates and windows that are larger than the happy path requires, specifically because you are operating under uncertainty. A change the happy path suggests will take thirty minutes gets a ninety-minute maintenance window. A rollback that should take fifteen minutes gets forty-five minutes in the plan. The organizational pressure against sandbagging is real: maintenance windows have cost, stakeholders want minimal disruption, and a change that completes in thirty minutes when ninety were requested looks like poor planning. This pressure produces the failure mode of fitting the window to the happy path — which produces changes that regularly overrun when anything unexpected happens.

The argument for sandbagging is not that you expect to use the extra time. It is that the cost of not having it when you need it is catastrophically higher than the cost of occasionally not using it. The specific places where margin is most valuable:

- Maintenance window duration — long enough for the change, the full verification, and a clean rollback with time remaining. Not verification or rollback. Both, simultaneously, with margin. A window that fits only the forward path is a window that has no recovery capacity.

- Rollback time estimation — rollback procedures are almost always estimated on the happy path from a known clean state. The rollback in an environment that has partially changed, under time pressure, with cascading effects from a failed step, will not proceed as cleanly. Build margin that reflects actual rollback conditions, not ideal ones.

- Verification time — successful completion of change steps is not the end of the change window. Discovering a problem during verification is better than discovering it after the window closes and the team disperses. Verification steps need their own time allocation, not whatever is left over.

- Communication buffer — changes affecting users require communication before, during, and after. The all-clear, the initial questions, the confirmation with key stakeholders all have time cost that is frequently unbudgeted.

### Dependency Mapping and the Organizational Memory Gap

Changes fail in unexpected ways because systems have dependencies the change planner did not know about. The mitigation is not better guessing — it is deliberately surfacing dependencies before the change window through a structured step in the planning process. For any change with significant blast radius: what systems call this system, what systems does this system call, what would break if this system were unavailable for thirty minutes, and are there time-sensitive operations — batch jobs, scheduled tasks, integration polling cycles — that could be affected by a brief interruption during the change window.

The companion problem is organizational memory. Change management produces documentation. Documentation accumulates. Nobody reads old documentation systematically before planning a new change. The knowledge that a previous change to this system produced an unexpected interaction with a downstream dependency exists somewhere in the ticket system and is operationally inaccessible. The specific intervention: require a search of the change management system for previous changes to the same system or component before any change plan is finalized, and review any that resulted in unexpected outcomes. This takes fifteen minutes and frequently surfaces directly relevant information. It is almost never done because it is not required and the planner does not know what they do not know about the system's history.

### Communication Structure and the Handoff Problem

Change windows with unclear authority structures produce a specific failure mode: multiple people with partial information giving contradictory guidance to the executor under time pressure. The executor either freezes waiting for consensus or follows the loudest voice rather than the most informed one. The change plan should specify, before the window opens: who is the single decision-maker for abort decisions above the executor's authority, what the escalation path is, and who is responsible for stakeholder communication so the executor is not simultaneously executing steps and fielding status questions from a manager who wants updates every five minutes.

Changes that span multiple people or teams have an additional failure mode at handoff points. Person A completes their steps and hands off to Person B. Person A's mental model of the current system state is not fully captured in the handoff documentation. Person B proceeds with an incomplete model of what Person A actually did, what state the system is in, and what anomalies Person A observed that did not rise to the level of a formal note but would have affected Person B's decisions. The mitigation is building explicit overlap into handoffs: Person A should remain available while Person B executes the first steps after the handoff, not just be reachable in an emergency.

The post-change observation window deserves explicit treatment as a distinct phase rather than an afterthought. A change is not complete when the last step executes. It is complete when the system has been verified to be behaving correctly under real load, for long enough to have confidence that the silent failure modes have not been triggered. The change plan should specify an explicit observation window with defined success criteria — not 'monitor for issues' but specific, observable conditions that confirm correct behavior — and the team should remain engaged until those conditions are confirmed.

## Off-Hours Changes: The Default Condition and Its Consequences

High-impact changes are scheduled off-hours to minimize user disruption. This is sometimes correct and is sometimes a false economy that trades a known cost — disrupting users during business hours — for a less-visible cost: executing a complex change with degraded escalation paths, reduced cognitive performance, and limited access to the expertise that would make a bad outcome recoverable.

The off-hours condition is not an edge case. It is the default environment for changes with significant blast radius. Every element of the change management discipline discussed in this domain applies with additional force when the change happens at 2am on a Saturday.

### Degraded Escalation Paths

Every escalation path that exists during business hours has a degraded or unavailable version off-hours. Your manager is asleep. The network team's on-call may or may not know the specific system involved. The vendor's support tier that actually understands your environment — not the tier-1 call center, the tier-3 engineer who has worked with your configuration — is not available until Monday. The colleague who built this system and whose number you have for genuine emergencies is a call you can make once before that relationship changes.

The vendor insisting on business-hours changes is communicating something real about their own support model. Their off-hours engineers are not the same engineers who handle complex issues during the day. Their off-hours support contract may explicitly exclude certain escalation categories. A change that requires vendor involvement — firmware upgrade, licensing change, configuration touching vendor-managed infrastructure — executed off-hours may encounter a situation where the vendor cannot authorize or execute the remediation that business-hours support could. The change enters an indeterminate state that persists until Monday.

*The explicit question the change plan should answer: what is the worst-case scenario for this change, what expertise would be required to address it, and is that expertise available at the scheduled change time? If the answer to the last question is no, that is a risk item requiring conscious acceptance — not a reason to automatically reschedule, but a risk that needs to be acknowledged by someone with authority to accept it.*

### Cognitive Performance Under Off-Hours Conditions

Fatigue affects judgment, increases error rates, reduces the ability to hold complex state in working memory, and impairs exactly the risk assessment and decision-making the change management discipline is designed to support. The person executing a change at 3am after a full workday is not operating at the same cognitive level as the person who wrote the change plan at 2pm. This is physiological, not a character failing, and it should be a planning input.

The practical implications: abort thresholds should be calibrated down for off-hours changes — trigger earlier, require more certainty before proceeding — because the cost of a judgment error is higher when cognitive capacity is reduced and help is less available. Verification steps should be more conservative because the person doing the verification is less likely to catch subtle anomalies. Sandbagging is even more important off-hours because the margin that absorbs unexpected events is also the margin that absorbs the slower execution pace that fatigue produces.

Complex changes that require sustained judgment should not be scheduled at 3am if there is any alternative. The user disruption cost of a business-hours change is visible and predictable. The execution risk cost of a 3am change with a fatigued executor and degraded escalation paths is less visible and less predictable — which tends to cause it to be systematically underweighted in scheduling decisions.

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Change Literacy | Can read a change plan and describe what it proposes to do, what it will affect, and what the rollback procedure is. Can identify whether a change plan contains the minimum required elements: pre-change state, proposed steps, expected outcomes, rollback procedure, abort criteria, and success criteria. Does not require being able to write one. |
| Level 2 | Change Audit | Can identify gaps in a change plan: missing blast radius assessment, rollback that is not actually reversible, abort criteria absent or too vague to trigger reliably, test results that do not address production-specific risk categories, scope broader than described, off-hours scheduling without acknowledged escalation path degradation. Can identify when a documented baseline may not match actual environment state. |
| Level 3 | Change Commission | Can write a complete change plan including blast radius assessment, step-by-step procedure with expected outcomes and verification steps, rollback procedure with honest feasibility assessment, abort criteria specific enough to trigger reliably, pre-mortem identifying likely failure scenarios, dependency map, communication plan, explicit observation window with success criteria, and acknowledgment of what is unknown and how that uncertainty is being managed. |
| Level 4 | Change Arbitration | Can make the abort decision under time pressure with incomplete information using pre-committed criteria. Can document deviations as they happen. Can assess cumulative environment state when the documented baseline may not match reality. Can evaluate whether off-hours scheduling is justified given the available escalation paths. Can identify when a change process has degraded to approval theater and articulate what would restore its function. |

## Assessment Exercises

### [AUDIT] What Is Wrong With This Plan

*Candidate is given a change plan for a domain controller operating system upgrade. The plan has eight steps, each with a description of the action. It does not include expected outputs for each step, has no abort criteria, describes the rollback as 'restore from backup if needed' without specifying which backup or how long the restore would take, does not identify the authentication impact during cutover, is scheduled for 2am on a Sunday, and notes that the vendor's support case has been opened but not escalated. Candidate must identify all gaps and assess the severity of each.*

**Watch for:** Candidates who focus on formatting completeness rather than risk. Critical findings: no abort criteria, rollback that is not viable under change window conditions, undisclosed authentication blast radius, and off-hours scheduling with an unescalated vendor case that means vendor expertise is unavailable if something goes wrong. The off-hours scheduling is not automatically a problem — it is a problem in combination with the unescalated support case, because the change has a vendor dependency and no viable escalation path if the vendor's involvement is needed.

### [COMMISSION] Write the Pre-Mortem

*Candidate is given a change plan for migrating a file server to a new VLAN as part of a network segmentation project. The plan appears complete. Candidate must write a pre-mortem: assume the change has failed, identify the three most likely causes, and for each cause identify the observable indicator that would have signaled it during the change window and the abort criterion it implies.*

**Watch for:** Pre-mortems that identify only 'the server does not respond' without identifying the specific failure scenarios that produce that symptom for different reasons. The three most likely failure modes: DNS records still pointing to the old segment, dependent systems with the old IP hardcoded rather than using DNS, and firewall rules that apply to the old VLAN that were not updated for the new segment. Each has a different observable indicator and implies a different abort criterion. Candidates who can map failure scenarios to specific observables to specific abort criteria are demonstrating pre-mortem skill.

### [AUDIT] The Change Is Not Going to Plan

*A candidate is midway through a storage migration at 1am. Step 4 was supposed to take 15 minutes and is at 45 minutes with no sign of completion. The maintenance window has 90 minutes remaining. The change plan has no abort criteria. The on-call storage vendor support has been reached but says they cannot escalate to the engineer familiar with this configuration until business hours. Candidate must: assess whether to continue, adapt, or abort; identify what information they need to make that decision; write the abort threshold they should have defined before the change window; describe what they document before the window closes; and assess what the off-hours vendor situation implies about whether this change should have been scheduled now.*

**Watch for:** Candidates who make the continue/abort decision without identifying the information gap. The off-hours vendor situation is load-bearing: the change has a dependency on vendor expertise that is not available, which changes the risk profile of any indeterminate state. The correct answer includes recognizing that the worst-case scenario — a storage issue requiring vendor escalation — cannot be addressed until business hours, and that this should have been a risk item in the change plan. Candidates who address both the in-the-moment decision and the planning failure that created this situation are at Level 4.

### [AUDIT] Assess the CAB

*Candidate is told that an organization's Change Advisory Board meets weekly, reviews an average of 15 changes per meeting, has rejected or substantially modified fewer than 3 changes in the past year, has never conducted a review of change outcomes, and has never specifically reviewed a change that required significant deviation from the approved plan. Candidate must assess whether this CAB is functioning as a risk management mechanism, identify the specific indicators that it is not, and describe what changes to the process would restore its function versus what changes would be purely cosmetic.*

**Watch for:** Candidates who treat the low rejection rate as the primary indicator without addressing the absence of outcome review. The diagnosis is that the board has no feedback loop — it cannot calibrate risk assessments against actual outcomes because it never reviews outcomes. Cosmetic fixes include more documentation requirements or reducing changes per meeting. Functional fixes include reviewing a sample of approved changes at each subsequent meeting, specifically reviewing changes that required significant deviation from the approved plan, and tracking correlation between the board's risk assessment and actual change outcomes over time.

Culminating exercise — spans all four levels. A Level 1 candidate can describe what pre-change discovery steps are needed. A Level 2 candidate can identify what the stale test environment cannot tell them. A Level 3 candidate can write a complete plan that treats uncertainty as a planning input. A Level 4 candidate can articulate what each discovery step reveals, how the findings change the plan, and what they would do if critical unknowns surface during execution. Real-world readiness is most visible here because the scenario does not provide complete information — which is the actual condition of most infrastructure work.

### [SYNTHESIS] The Inherited System

*Candidate must plan a change to a production authentication service they inherited three months ago. The original architect left before they arrived. Documentation covers the happy path but not failure modes. The service has never had a change executed during their tenure. Test environment exists but was last refreshed eight months ago. The change is scheduled for 2am on a Saturday and the vendor's tier-3 support for this product is business-hours only. Candidate must write the pre-change discovery steps they would complete before writing a reliable change plan, identify what the test environment results can and cannot tell them, specify how they would stage the change to surface unknown dependencies before full execution, assess what the off-hours scheduling and vendor support situation implies for the abort criteria and rollback margins, and describe what they would document after the change regardless of outcome.*

**Watch for:** Plans that treat the test environment result as sufficient validation. Plans with no staging step. Plans that accept the documentation without verification. Plans that do not address the off-hours vendor situation as a risk item requiring conscious acceptance. The rubric rewards candidates who treat uncertainty as a planning input — specifically those who can articulate what they do not know, how their plan manages that uncertainty, and what the off-hours condition changes about the risk profile. A candidate who produces a plan appropriate for a fully-understood system under ideal conditions has not understood the scenario.
