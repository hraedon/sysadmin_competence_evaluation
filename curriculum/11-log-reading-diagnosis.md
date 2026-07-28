---
domain: 11
id: log-reading-diagnosis
title: "Log Reading & Diagnosis"
subtitle: "Logs as timeline reconstruction tools — not search engines for known error codes"
reviewed: 2026-07-10
---

# Domain 11: Log Reading & Diagnosis

*Logs as timeline reconstruction tools — not search engines for known error codes*

## Scope and Domain Boundaries

This domain covers the mechanics of finding relevant information in real log data. Domain 8 (Security Reasoning) established the boundary: Domain 8 owns what to look for and why — what attacker behavior looks like in infrastructure terms, what an indicator of compromise means conceptually. This domain owns how to look — the mechanics of reading event chains, correlating timestamps across sources, distinguishing symptom events from cause events, and navigating unfamiliar log formats.

The boundary is deliberately porous at Level 2 and above. A candidate working Domain 11 at Level 2 or higher is expected to draw on Domain 8's threat model vocabulary to interpret what they are reading. The exercise that asks a candidate to read a sequence of authentication failures and identify a credential stuffing pattern is a log mechanics exercise that requires security reasoning to complete. Trying to purge all threat-pattern recognition from Domain 11 exercises would produce exercises that are less realistic, not more rigorous. The coupling is intentional — it reflects the reality that log reading without a threat model produces narrative without meaning.

The domain also owns the log infrastructure layer: what gets collected, how it gets collected, how long it gets kept, and the tradeoffs that determine whether logs are useful for investigation or serve primarily as a paper trail after the fact. These are decisions that most organizations make implicitly, and this domain makes them explicit.

*This domain requires working with actual log data — real or realistic — in ways that earlier domains do not. Assessment exercises in this domain embed log fragments that candidates must read and reason about. A candidate who cannot work from actual log output has not developed the skill this domain is building, regardless of their conceptual knowledge.*

## Reasoning Framework: Logs as Timeline Reconstruction, Not Search

How it is normally taught: log reading is presented as knowing which event IDs to look for. Event ID 4625 is a failed logon. Event ID 7045 is a new service installed. Memorize the important ones, know where to find them, search for them when something is wrong.

What it is actually for: a log is a partial record of what happened on a system, in temporal sequence. Reading it correctly means reconstructing the timeline of events — what happened, in what order, with what context — not retrieving individual data points. The event that is visually prominent (the error, the failure, the alert) is frequently not the cause. It is a symptom. The cause is in the events that preceded it, often on a different system, in a different log, minutes or seconds earlier.

What misuse looks like: the candidate who opens the event log, searches for error events, finds one that looks relevant, and stops. They have found the symptom event and called it the cause. They have not read the log — they have searched it. The investigation that follows from a symptom mistaken for a cause will pursue the wrong remediation, fail to identify the actual issue, and produce no lasting resolution.

*The binary search parallel to Domain 3 applies directly: just as OSI layer isolation gives you a principled method for narrowing where in a communication stack a failure is occurring, temporal event sequence gives you a principled method for narrowing when a failure originated and what triggered it. Work backward from the symptom event, not forward from the beginning of the log.*

The parallel to Domain 10 is also direct: the backup that had been failing for three months generated ninety unread failure notifications. The log that would have revealed a compromise was never read because no investigation was triggered. In both cases, the information existed and was not used. The domain is building the skill of using it.

## Log Infrastructure: The Tradeoff Triangle

Log collection is a constant tradeoff between three competing constraints: coverage (what is collected), cost (storage, compute, licensing, and operational overhead), and actionability (whether what is collected can actually be used to detect or investigate events). No organization achieves all three simultaneously. The decisions made about this tradeoff determine what role logs play — detective or corrective — and what failure modes remain invisible.

### The Detective Role: Syslog and Basic Aggregation

Coverage: medium. Cost: low. Actionability: low — high-frequency, low-signal monitoring stream.

A syslog server or basic log aggregation solution collects logs at low cost with minimal infrastructure. The failure mode is actionability: logs exist, they are not easily queryable in real time, correlation across sources requires manual effort, and the system is most useful after an incident when you know what you are looking for and can grep through files. This is the detective role — useful for reconstruction after the fact, limited for prevention or early detection.

Most small and medium organizations operate here, often without explicitly acknowledging it as a choice. The risk implication: events that would have triggered an alert in a more capable system go unnoticed until something breaks. The organization discovers problems rather than preventing them.

### The Middle Ground: Structured Aggregation Without SIEM

Coverage: medium-high. Cost: medium. Actionability: medium — achievable with ongoing operational investment, degrades without it.

Solutions like Elastic Stack, Graylog, or Azure Monitor with structured ingestion provide queryability and cross-source correlation without the cost of enterprise SIEM. The failure mode is operational investment: these systems require meaningful effort to maintain and tune. An implementation set up once and never revisited produces alerts that nobody trusts because the signal-to-noise ratio has degraded as the environment changed. The tool is present. The detection capability it was supposed to provide has quietly eroded.

### Full SIEM: Coverage and Operational Cost

Coverage: high. Cost: high. Actionability: high when properly operated, low when not — the gap between potential and actual capability is largest at this tier.

A SIEM with broad ingestion, properly tuned, with analysts reviewing output is genuinely effective. The failure modes are cost and the tool-gap pattern from Domain 8: the SIEM gets bought, data gets ingested, the tuning never happens because it requires domain expertise and ongoing effort, the analysts who should be reviewing output do not exist, and the organization has paid for the appearance of detection capability rather than detection capability itself. A SIEM does not detect anything. Detection happens when tuned rules are reviewed by someone with enough context to distinguish signal from noise.

*The right answer to 'what log infrastructure does this organization need' is not a product category. It is a function of threat model, operational capacity, and budget. What can be assessed is whether the candidate understands what each tier of investment provides and what it does not — and can evaluate whether a described logging posture is appropriate for the described environment and threat model.*

### The Bespoke Language Problem

Every backup solution, every SIEM, every log aggregation platform, and every network device has its own interface and query language for accessing historical log data. They share concepts and differ in every specific. Veeam's backup job history, Rubrik's event log, Splunk's search syntax, Elastic's KQL, and Windows Event Viewer's filter interface are all tools for answering the same class of questions through completely different mechanisms.

The skill being developed is not fluency in any particular product but the ability to navigate an unfamiliar logging interface to answer a specific question. The conceptual map — what am I looking for, what time window, what systems, what event types — transfers across every product. The specific syntax and navigation do not. Assessment exercises in this domain present realistic but product-agnostic log output rather than asking candidates to recall product-specific commands.

### Retention as a Separate Decision

Collecting logs and retaining them are separate decisions with separate cost and compliance implications. An organization that collects extensively but retains for only 30 days cannot investigate an incident that began 45 days ago. An organization that retains for a year but stores logs in a location accessible with production credentials has logs that an attacker can destroy or tamper with.

Retention decisions should be driven by two requirements: the maximum lookback period an investigation might need (typically 90–180 days for security investigations in most environments), and any compliance framework minimums that apply to the organization. These are frequently longer than what cost-minimizing decisions would produce. Log retention is also where tamper-evidence matters: a log that can be modified after the fact by a compromised account is not a reliable record of what happened. The Assess the Logging Posture exercise later in this domain specifically tests retention reasoning — candidates are asked to identify what evidence is available given a stated retention policy before they can assess anything else about the incident.

## Core Log Reading Skills

### Event Chains and the Symptom/Cause Distinction

An event chain is the sequence of log entries that, read together, tells the story of what happened. A single event entry is rarely the whole story. The failed authentication event says a login failed. The event chain says: the account attempted to log in from an unusual source IP, the attempt used NTLM rather than Kerberos suggesting it originated from outside the domain, the failure was preceded by five similar failures in the previous three minutes, and the account was used successfully from a different location four hours earlier.

Distinguishing symptom events from cause events is the core skill. A symptom event is what the system recorded when it experienced the effect of something. A cause event is what the system recorded when the thing that produced the effect occurred. In many investigations, the cause event is on a different system, in a different log, at a slightly earlier timestamp. The candidate who reads only the symptom event has the wrong starting point for the investigation.

- Application crash events are almost always symptoms. The cause is in the events that preceded the crash — resource exhaustion, a failed dependency call, a configuration change, a software update.

- Service failure events are often symptoms of upstream failures. The service failed because a resource it depends on became unavailable — which is a different event, on a different system, that may have occurred seconds or minutes before the service failure was recorded.

- Authentication failure events can be either cause or symptom depending on context. A single authentication failure is usually noise. Authentication failures in a pattern — specific account, specific source, specific timing — are a symptom of something happening upstream.

### Cross-Source Correlation and the Timestamp Problem

A complete picture of what happened frequently requires correlating events across multiple log sources: authentication events on the domain controller, process creation events on the endpoint, network connection events on the firewall, application events in the application log. These sources have different event formats, different levels of verbosity, and different clock sources.

The timestamp problem: logs from different systems reflect different clock states. NTP failures, timezone misconfigurations, and systems that log in local time when everything else logs in UTC produce event sequences that appear impossible or out of order when naively correlated. A sysadmin reconstructing an incident timeline from logs with a one-minute clock skew between sources can misidentify which event caused which. Verifying timestamp provenance — confirming that the clocks on the relevant systems were synchronized and what timezone each source uses — is a required step before trusting any cross-source correlation.

The verbosity gap: not all systems log at the same level of detail. A firewall may record that a connection was permitted; it will not record what data crossed that connection. An endpoint detection tool may record that a process was created; it will not record the network connections that process made. The absence of a log entry does not mean an event did not occur — it may mean the system was not configured to log at that level of detail.

### Filtered Logs and the Missing Evidence Problem

Many logging pipelines filter events before they reach storage — at the agent level, the collector level, or the ingestion rule level. The event that would have revealed a compromise was filtered because it did not match any known alert pattern and the organization was managing storage costs. The investigation that follows discovers that the relevant event category was not being collected.

A log that shows no relevant events is not the same as a log that confirms the absence of relevant events. Before concluding that a specific event did not occur, the investigator needs to confirm that the logging configuration would have captured it if it had. This is a configuration question, not a log reading question — but it must be asked before the log reading conclusion can be trusted.

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Log Literacy | Can read a log extract and describe what it records in plain English. Can identify the timestamp, source system, event type, and relevant attributes of individual log entries. Can navigate to the correct log source for a given type of event on a Windows system. Does not require cross-source correlation or causal analysis. |
| Level 2 | Log Audit | Given a log extract around a known event, can identify which entries are relevant, which are noise, and which represent symptoms versus causes. Can identify the gap between what the log shows and what would be needed to fully understand the event. Can recognize when a log extract is incomplete because events are missing that should be present given the system configuration. |
| Level 3 | Log Correlation | Can correlate events across multiple log sources to reconstruct a timeline of what happened. Can identify timestamp discrepancies and account for clock skew in cross-source analysis. Can identify the specific log sources that would need to be examined to answer a given investigative question, and can assess what filtering or retention gaps would prevent those sources from providing a complete answer. |
| Level 4 | Detection Design | Can assess an organization's logging posture against its threat model and identify the gaps that would leave specific incident types invisible. Can specify the log sources, retention period, collection architecture, and alert tuning required to move from a detective to a corrective logging capability. Can evaluate whether a described logging infrastructure actually provides the detection and investigation capability it is assumed to provide. |

## Assessment Exercises

### [LITERACY] Read the Chain

*Candidate is given the following log extract from a Windows domain controller (simplified). They must describe what happened in plain English and identify which event represents the symptom and which represents the most likely cause:

  [08:14:32] Event 4625 — Logon failure. Account: jsmith. Source IP: 10.4.22.18. Logon type: 3 (Network). Error: Unknown username or password.
  [08:14:33] Event 4625 — Logon failure. Account: jsmith. Source IP: 10.4.22.18. Logon type: 3. Error: Unknown username or password.
  [08:14:34] Event 4625 — Logon failure. Account: jsmith. Source IP: 10.4.22.18. Logon type: 3. Error: Unknown username or password.
  [08:14:51] Event 4740 — Account lockout. Account: jsmith. Caused by: WORKSTATION-04.
  [08:15:02] Event 4625 — Logon failure. Account: administrator. Source IP: 10.4.22.18. Logon type: 3. Error: Unknown username or password.*

**Watch for:** Candidates who identify Event 4740 (the lockout) as the primary finding without noting that it is the symptom of the rapid authentication failures that preceded it. The lockout is the effect. The pattern of failures from 10.4.22.18 against multiple accounts is the cause — and the shift from jsmith to administrator after the lockout is the most significant signal, indicating an automated credential stuffing attempt rather than a user who forgot their password. Candidates who can articulate why the IP, the logon type, the timing, and the account enumeration pattern together constitute a specific threat pattern are demonstrating Level 2 reasoning.

### [AUDIT] The Timestamp Problem

*Candidate is given two log extracts from different systems, both recording events around a service failure. They must identify whether the timeline can be trusted and what would need to be verified before drawing conclusions about causation:

  [Firewall log — UTC] 14:22:15 — Connection from 192.168.10.45 to 10.0.0.8:443 PERMITTED
  [Firewall log — UTC] 14:23:44 — Connection from 192.168.10.45 to 10.0.0.8:443 RESET

  [Application server log — local time, timezone unspecified] 10:23:41 — SSL handshake timeout. Client: 192.168.10.45
  [Application server log] 10:23:42 — Connection terminated.*

**Watch for:** Candidates who correlate the firewall RESET at 14:23:44 with the application timeout at 10:23:41 without noting the timezone discrepancy. The application server is logging in a timezone that appears to be UTC-4, but this has not been confirmed. If the server is logging in Eastern time (UTC-4 during EDT), the events align. If the clock is wrong or the timezone is different, they do not. The correct answer is: the events may be correlated but the timestamp provenance must be verified before the correlation can be trusted. A four-hour offset is a common mistake with UTC/local time mismatches.

### [AUDIT] What Is Missing

*A sysadmin is investigating a suspected lateral movement event. They have reviewed the Windows Security log on the target server and found no unusual authentication events in the relevant time window. They conclude that lateral movement did not occur via this server. Candidate must identify what is wrong with this conclusion and what additional evidence would be required to support or refute it.*

**Watch for:** Candidates who accept the absence of Security log events as evidence of absence. The correct answer requires understanding that: Windows Security log authentication events are only generated for certain logon types and may not be generated for pass-the-hash or token impersonation attacks; the Security log audit policy may not be configured to capture the relevant event categories; the log may have been cleared; the attacker may have used a different access method that does not generate standard authentication events. The conclusion requires confirming that the audit policy would have captured lateral movement via the expected method before treating the absence of events as meaningful.

### [AUDIT] Assess the Logging Posture

*Candidate is given a description of an organization's logging infrastructure: Windows event logs on each server retained locally for 7 days with no central collection, syslog from network devices retained for 90 days on a server that receives logs but has no query interface, email alerts from backup software sent to a shared mailbox checked weekly, no endpoint detection tooling. The organization's compliance framework requires 180-day log retention for authentication events. The organization experienced what may have been a security incident three weeks ago and is trying to reconstruct what happened. Candidate must: (1) identify what evidence is and is not available given the retention policy, (2) assess what the current posture can and cannot tell them about the three-week-old incident, (3) identify the compliance gap, and (4) describe what would need to change to move from a detective to a corrective logging capability.*

**Watch for:** Candidates who look for Windows Security logs from three weeks ago — those logs are definitively gone. The 7-day local retention means endpoint authentication evidence from the incident window does not exist. The only available evidence is 90 days of network device syslog, which may show connection patterns but cannot show what happened on individual endpoints. Candidates who recognize this immediately and pivot to 'what can the syslog tell us' are demonstrating correct prioritization. The compliance gap — 180-day retention required, 7-day retention implemented for the most relevant log source — is a second finding that should be surfaced. The forward-looking recommendation should be specific about what log sources need central collection and what retention periods are required, without defaulting to 'buy a SIEM' as the only path to compliance.
