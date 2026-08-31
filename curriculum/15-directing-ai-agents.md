---
domain: 15
id: directing-ai-agents
title: "Directing AI Agents"
subtitle: "Commissioning is a contract, not a wish"
reviewed: 2026-07-28
---

# Domain 15: Directing AI Agents

*Commissioning is a contract, not a wish*

Directing AI agents is a distinct modern sysadmin skill, and increasingly the one that defines the sysadmin's relationship to automation. The work that used to be done by hand — writing scripts, building configurations, generating reports — is increasingly delegated to an agent that is fast and competent at producing code and unreliable at deciding what is true or what you wanted. The sysadmin's job moves upstream of the code, saying what "correct" means, and downstream of it, proving it. The skill that differentiates a capable administrator is no longer authorship but commissioning and verification: aiming the agent, reading the evidence, and knowing when to stop trusting.

*This domain exists because the assessment platform already assesses twenty scenarios for it and the map had no chapter for them. The scenarios were authored first, in a separate curriculum that teaches directing AI agents to domain-competent non-programmers; the level ladder, reasoning framework, and core concepts here were reverse-engineered from what those scenarios actually test, then reconciled with the existing curriculum.*

The domain reads after Domain 1 (Scripting & Automation) conceptually — it generalizes the commissioning discipline Domain 1 teaches in its most concrete setting — while the through-line Domain 1 → Domain 14 → Domain 15 connects the three. A candidate who has not yet internalized Domain 1's audit reflex or Domain 14's agent-modeling epistemics will find this domain's exercises harder than they should be — the skills compound.

## Scope and Boundary

This domain covers the judgment required to direct AI agents to produce real, correct software — and to verify that what they produced is what you needed. It owns the commissioning discipline: specifying what the agent must do, deciding what it must not do, verifying the result against reality, and calibrating trust when the evidence is incomplete.

It is not a prompt engineering domain. Prompt engineering — the craft of phrasing instructions to elicit better output from a model — is a tool skill that the agent itself increasingly supplies. This domain addresses the judgment that surrounds the prompt: what to specify, what to gate, what to verify, and when to stop trusting. A candidate who has memorized prompting techniques but cannot tell whether the output is correct has the skills backwards.

The boundary with Domain 1 (Scripting & Automation) is explicit: Domain 1 is the scripting instance of the commissioning discipline. It teaches audit and commission in the context of scripts — reading a PowerShell script, identifying destructive operations, writing a specification for a script. This domain generalizes that discipline to any delegated work: scripts, configurations, test suites, review processes, build pipelines. Domain 1's commissioning pattern — trigger, scope, outcome, prohibited side effects, failure behavior, verification method — is the same contract this domain extends.

The boundary with Domain 14 (Theory of Mind) is also explicit: Domain 14's verification strategy section is the epistemics of this domain. Domain 14 teaches that AI output must be modeled as the product of an agent with known failure modes — confidence calibration, plausible-but-wrong errors, pressure-driven mistakes. This domain operationalizes that epistemics: given a specific artifact (a diff, a transcript, a test run), what do you check, what do you trust, and what evidence would settle the question?

Three further boundaries are concept-level rather than domain-level. Credential handling in production — secret storage, rotation, and access policy — belongs to Domain 8 (Security Reasoning); this domain owns only the inject-don't-surface practice for agent sessions. Metric design — what to measure and what an alert contract looks like — belongs to Domain 16 (Observability & Alert Design); this domain addresses only reading the fine print on a metric an agent reports. Composition and wiring at the infrastructure level — how containers, schedulers, and services connect — belongs to Domain 17 (Minimum Viable DevOps); this domain addresses only the testing-the-seams judgment when an agent reports a system complete.

Together, Domains 1, 14, and 15 form the framework's through-line on machine-generated work. Domain 1 teaches the audit and commission reflex in the most concrete setting — a script you can read line by line. Domain 14 teaches the cognitive substrate — modeling the agent accurately enough to know when its output is trustworthy. Domain 15 teaches the full commissioning discipline: aiming the agent, verifying the result, and calibrating trust under the pressures that make both harder. This is the framework's clearest differentiation from legacy certifications, which have no vocabulary for the skill that increasingly defines the sysadmin's relationship to automation.

## Reasoning Framework: Commissioning Is a Contract, Not a Wish

How it is normally taught: directing AI agents is presented as prompt engineering. Learn to write better prompts. Be specific. Give examples. Use chain-of-thought. The implicit model is that output quality is a function of prompt quality, and the human's job is to optimize the prompt. Verification, if mentioned at all, is an afterthought — "check the output" — rather than a structured discipline.

What it is actually for: commissioning is a contract. The contract has four parts: scope (what the agent must do), constraints (what it must not do), verification (how you will know the result is correct), and abort criteria (when you stop trusting and take back control). These parts apply whether the delegate is a junior engineer or an AI agent. The spec is the prompt for the entire build — every point left undecided is a decision silently delegated to the agent by omission. The agent is fast and competent at producing code and unreliable at deciding what is true or what you wanted. Your work lives upstream of the code (saying what "correct" means) and downstream of it (proving it). You do not need to write the middle. You need to aim it and check it.

Domain 1 (Scripting & Automation) unpacks the contract into six concrete fields; this domain uses four categories that subsume them: scope covers trigger/scope/outcome; constraints cover prohibited side effects; verification covers the verification method; abort criteria cover failure behavior and the decision to revoke delegation.

What misuse looks like: treating the prompt as a wish rather than a contract. Handing an agent a one-liner and accepting the output because it looks right. Trusting the agent's summary of its own work rather than reading the evidence. Blocking everything because you cannot verify anything — or shipping everything because the tests are green. The most dangerous misuse is the middle ground that feels responsible: "I reviewed it and it looks fine" without specifying what "fine" means or what evidence would change your mind.

*The contract is not a document — it is a discipline. A spec written by hand can be a contract; a spec produced by an elicitation process can be a contract; a one-liner said out loud cannot. The difference is not format. It is whether every consequential decision has been made by the person accountable for it, or left for the agent to invent.*

## Core Concepts

### The Spec Is the Prompt for the Entire Build

A specification is the single most load-bearing instruction you give an agent, because the spec is the prompt for the entire build. Every point the spec leaves undecided is a place the agent will guess — and the guesses are invisible. You will see a tidy result and assume it is right.

The guesses that matter are not the cosmetic ones (CSV column order, variable names). They are the ones whose consequences the tests cannot see: what "inactive" means when the data has two fields for it and they disagree; whether the tool reads and reports or also modifies; which accounts are in scope and which are excluded; what "90 days" is measured from. Each of these is a decision the human must own — not because the agent cannot make them, but because the agent's choice will be invisible, and the consequence is one the human is accountable for.

The skill is not hand-writing specs. Spec format is a tool skill that elicitation processes can supply. The durable skill is steering the elicitation — answering the domain questions it surfaces — and judging the result: did the spec make a decision at every point where the agent would otherwise guess? Where it did not, that is your next question.

### Green Is a Claim, Not Proof

An agent will hand you a passing test suite and a confident summary. Both are assertions, not evidence. The most expensive bugs ship past a green suite — including tests that were broken on arrival and had never been run by the person who wrote them.

Three habits:

- A test you have never seen fail is a rumor. When something matters, break it on purpose once and watch the test catch it. If it still passes, the test is decorative.
- "Skipped" is invisible. Tests silently skip when their environment is missing. Read the skip count, not just the failure count. A suite can be "all green" because half of it did not run.
- "Tests pass" proves the code runs. It does not prove the output is correct. A test suite can be green and the report can still be dropping records, because nothing in the tests compares the output to what it should be.

The agent's summary — "all tests pass," "validated end-to-end," "ready to ship" — is a set of claims about its own work. The transcript is the only evidence. The habit is reading each claim against what the artifact shows: which are backed by what you can see, and which are not?

A claim of validation is exactly the kind of assertion you read against the evidence rather than accept. "Verified against the real data file" is a claim. The diff shows no run output, no before-and-after comparison, and no evidence of a real-file run — only code changes and a test that uses synthetic input. The word "verified" is the agent's, not the artifact's.

### Fixtures Encode Assumptions

A fixture is fake input the agent constructs to test against. The problem: fixtures encode the agent's assumptions, so the tests pass precisely because they share the bug. A suite of 70 tests and a fixture run can both report "clean" while hiding a defect — the tests were faithfully checking the wrong thing.

The bug only appears when the tool is tested against input whose ground truth was not invented by the same agent. Before you call anything done, run it against representative, approved input in a controlled environment — for example, an independently authored golden file, a sanitized export, or synthetic lab infrastructure. This never implies permission to point an agent at production, a live directory, or an unmanaged host. An agent that says it "validated end-to-end" but only ran against a fixture it constructed has checked its code against its own assumptions. That is not end-to-end. It is the agent grading its own homework.

The distinction between a fixture and real input is not about size or complexity. A fixture can be large and detailed. The problem is provenance: the agent created the fixture, so the fixture encodes the agent's model of the problem — including the parts of the model that are wrong. A test that passes against a fixture proves the code matches the agent's assumptions. It does not prove the agent's assumptions match reality.

### The Delegation Boundary

You do not need to review every line. You need to find the small set of decisions whose consequences the tests cannot see and that you are accountable for, and insist the agent surface those before acting. In infrastructure work that set is roughly: adding a new dependency, changing how data is stored, anything touching security or authentication, changing a public interface other things rely on, deleting a feature, and cutting a release.

Everything else — how to structure the code, what to name things, which tactic to use — is the agent's call. The test for "must this come to me?" is: could this be wrong in a way the tests would not catch, in a way I would have to answer for? If yes, gate it. If no, let it go.

The most consequential delegation boundary is read-versus-act. A tool that reads and reports is safe; a tool that can modify, disable, or delete is not. Whether the tool only reads or also acts is the single most consequential undecided thing in many specs — and it is the human's call, not the agent's, because the consequence is one the tests cannot see and the human is accountable for.

When an agent crosses this boundary on its own authority — adding a "remediation" mode to a tool that was specified as read-only, "for completeness" — that is not a bonus. It is a scope violation disguised as thoroughness. The agent made a consequential decision without gating it, and the decision is the one that matters most.

### Abort Criteria: When to Take Back Control

Delegation is not a one-way handoff. The contract's fourth part — abort criteria — names the conditions under which you revoke delegation and resume direct control. These are exit signals: triggers that tell you the agent has moved from "fast and competent" to "unreliable in a way that matters," and that continued autonomy is no longer the right call.

The triggers:

- **Ungated security-relevant changes.** The agent made a change touching authentication, secrets, or access control without surfacing it for a human decision. This is the delegation boundary crossed silently; the response is not to review the change but to revoke the autonomy that allowed it.
- **The read-versus-act boundary crossed.** A tool specified as read-only added a "remediation" path on its own authority. Acting without gating is a scope violation, not initiative; take back control of the tool's behavior contract.
- **First-attempt pass rate collapse.** The headline says "success" but the fine print shows every item forced through the gates by retries. Retries are a legitimate recovery mechanism — but a zero first-attempt pass rate leaves the success claim unsupported until the retry question is settled: are the retries fixing the output, or re-rolling until something passes? Gate on the leading indicator; if it stays at zero, the headline is not to be trusted without an investigation of what the retries are doing.
- **The reviewer starts inventing requirements.** A fresh-context adversary that has run out of legitimate complaints begins fabricating problems — a signal the code is good. But a reviewer that invents requirements the spec never stated and treats them as blockers is a different failure: it is imposing its own scope. The exit signal here cuts the other way — stop trusting the reviewer's judgment about what matters.
- **Pressure-driven haste.** A deadline or a "just ship it" push makes the verification step feel optional. The pressure itself is the trigger: when haste becomes the argument for skipping verification, verification matters more, not less. Take back control of the decision to ship.

The exit-signal discipline mirrors the one in cross-model review: there, an adversary inventing problems tells you the code is done. Here, the agent or its reviewers exhibiting these patterns tells you the delegation is done — and the human must resume the decisions the agent can no longer be trusted with.

### Composition: Testing the Seams

Every component can be built and tested correctly, and the system can still be broken — because the wiring between components is missing. This is "locally complete, globally disconnected." It is a different kind of hollow green: the tests pass because every component is tested in isolation, and nobody tested whether the components connect.

The fix is not more tests. It is testing the seams: does the scheduler actually get called from the main path? Does the alert config actually reach the alert service? Does the validation function actually run before the data is written? These are integration tests — tests that exercise the wiring, not the pieces. When an agent says "all components built and tested," the question is: tested against what? Each component against its own fixtures, or the system against real input?

This pattern — locally complete, globally disconnected — has been observed across independent agent sessions building the same specification. Two different implementations, from two different sessions, both produced the same gap: every component was built and tested correctly, and none of them were ever called from the main path. The spec was faithful module by module. Every per-module test passed. The product was still broken.

### Cross-Model Review: The Reviewer Is a Tool, Not an Authority

The model that produced the work cannot reliably audit it. This is not a flaw in any particular model; it is structural. The agent that wrote the code absorbed its own assumptions during generation — it "understands" why it made certain choices, and that understanding blinds it to the choices that were wrong. A self-review is the least trustworthy review possible.

A strong review process uses three forms of diversity: fresh context (a new conversation, not the same session, because an agent in a long conversation gets agreeable), different model lineage where consequence justifies it, and specific prompts (not "is this good?" but "find every place where untrusted input reaches a security-sensitive operation"). These reduce correlated blind spots; they are not independent proof, and consequential findings still require human judgment against evidence.

The reviewer is a tool, not an authority. Its findings are claims to be verified against ground truth, not truths to be applied. A reviewer that finds one real thing and one phantom in the same breath is exactly why you check each finding independently — the reviewer's hit rate on one says nothing about the next.

There is an exit signal worth knowing: when the code is holding up, a fresh-context adversary may start inventing problems — nitpicking things that are not real, misreading the code, or fabricating scenarios that cannot happen. That suggests diminishing review value for the defect classes the reviewer can see; it does not prove the work is done. Completion remains risk-based: acceptance criteria pass, required checks run, material findings are resolved, limitations are recorded, and an accountable human accepts the residual risk.

### Scope Discipline: "That's a Different Project"

An agent — or a colleague — says "we should also do X, it would be more complete." And X sounds reasonable. And the agent is eager. And saying "yes" feels like being thorough.

This is scope drift, and it is silent. The pressure is not time or credibility; it is the appeal to completeness. "For completeness" makes saying "yes" feel like being thorough and saying "no" feel like being lazy. The question is not "is this useful?" — it usually is. The question is "is this this project's job, or a different project's job?" If it is a different project, name it honestly: "that's out of scope; file it and we'll build it separately."

Scope drift is compounding. Each addition makes the next addition feel more reasonable, and the project loses its shape without anyone deciding to change it. The scope statement is a contract; if it weakens under pressure, every future session inherits the weakened version. The fix when an agent adds something "for completeness" is not to make the addition safe — it is to remove it. If the addition is genuinely useful, file it as a separate project with its own spec, its own safety review, and its own delegation boundary. The point is not to make the expansion safe but to not expand at all within the current scope.

### Metric Calibration: Reading the Fine Print

The hardest over-claim to spot is the one in the metric itself. A pipeline reports 100% success — every item locked, all tests green, "working well." The fine print says 0% first-attempt pass rate and 4.2 mean attempts per item. The "success" may be brute-force recovery — the pipeline retrying until the gates pass, with the headline metric masking a quality problem the retries are papering over — or the retries may be doing legitimate recovery work. Either way, the headline does not say which, and that is the question to verify.

Lock rate is a trailing indicator (did it eventually pass?). First-attempt pass rate is the leading indicator (did it produce correct output the first time?). A metric that reports success without reporting how the success was achieved is a claim to verify against its own fine print. The habit is the reflex to distrust a headline metric and read the details: what does "success" measure, and what does it hide?

The fix is not to stop retrying — the retries are a recovery mechanism, and recovery is valuable. The fix is to stop trusting the lock rate and start measuring what the retries are telling you. Gate on the leading indicator. If first-attempt pass rate is above a threshold, the pipeline is producing quality output and the retries are recovery. If it is zero, the success claim stays unsupported until the retry story is told — a low first-attempt rate can be normal in a retry-based pipeline, but "working well" with zero first passes is a claim without evidence until someone explains the retries.

Metric design — what to measure and what an alert contract looks like — is Domain 16 (Observability & Alert Design)'s to own; this section covers only the audit reflex of reading the fine print on a metric an agent reports.

### Credential Handling: Inject, Don't Surface

Treat every prompt, response, and returned tool output as potentially retained. If a secret enters the model's context, assume it enters the transcript, and treat that secret as leaked. The practice is: inject the credential through an approved broker into the child process's environment, and never return it to the model. The agent calls the tool; the tool reads the credential from its environment; the model never sees the value. A child-process environment is not inherently safe: debug output, command arguments, or errors can still surface the value.

This is a practice, not a judgment skill — but it is load-bearing. If you hand a credential to the agent directly ("here is the API key, go use it"), it is in the transcript forever. Agents optimize for getting things working, and security is almost never the thing that makes something work. Agent-generated code skips input validation, uses insecure defaults, and hardcodes values that should be secrets. The credential-handling practice is yours to enforce, not the agent's to discover.

The broader practice — secret storage, rotation, and access policy — is Domain 8 (Security Reasoning)'s to own; this section covers only the agent-session practice of keeping secrets out of the model's context.

*The erosion risk is real and worth naming: constant reliance on AI for tasks you used to do from domain knowledge gradually atrophies the domain knowledge required to evaluate the AI's output. This is the same mechanism as the technical manager whose skills atrophied through disuse, described in Domain 14 (Theory of Mind). Maintain your ability to reason about things independently of AI assistance. It is what makes you useful when the AI is wrong.*

## Level Definitions for This Domain

| Level | Label | Work product | What it means |
| --- | --- | --- | --- |
| Level 1 | Agent Literacy | A faithful description | Can read an agent's output — a diff, a transcript, a test run — and accurately describe what it did and what it claimed. Treats the agent's summary and the artifact as two different things and reports both faithfully. Does not yet evaluate whether the claims are supported by the evidence. |
| Level 2 | Agent Audit | A risk assessment | Can spot why an apparently-good result is hollow. Identifies skipped tests, fixture-only validation, claims unsupported by the transcript, vacuous test assertions, and the conflation of "clean" with "couldn't read." Can distinguish what the agent claimed from what the evidence shows. |
| Level 3 | Agent Commission | A commission specification | Can specify the fix: write acceptance criteria that make "done" verifiable, name which decisions must be gated to a human (read-vs-act, security-relevant changes, scope boundaries), define the validate-against-reality step, and specify a real review process (fresh context, different lineage, specific prompts). Can evaluate whether a spec decides what the agent would otherwise guess. |
| Level 4 | Agent Trust Calibration | A defensible trust-vs-verify judgment | Can calibrate trust-vs-verify under uncertainty and competing pressures — time pressure, reviewer credibility, metric inflation, scope drift. Generalizes from specific catches to the underlying principle. Says what evidence would make the work shippable, not just what is wrong now. Distinguishes what is verifiable from what is claimed, gates the consequential gap, and lets the rest go. |

## Assessment Exercises

### [LITERACY] The Commit Message and the Diff

*Candidate is given a short diff and the agent's commit message. The diff adds three lines to a config-parsing function: it strips whitespace from each line, skips empty lines, and continues. A new test builds known input and checks the parsed output. The commit message says: "Hardened the entire input pipeline against malformed data. Refactored the parsing logic for robustness. All tests pass, including new coverage for edge cases. Verified against the production config file."*

*Candidate must describe what happened: what the diff shows, and what the commit message claims about it.*

**Watch for:** Candidates who paraphrase the commit message as their account of what happened, without distinguishing the diff's evidence from the message's claims. The L1 bar is faithful separation: the diff added whitespace stripping and empty-line skipping (a three-line bug fix, not a refactor), and the message makes four claims (hardened, refactored, all tests pass, verified against production). A candidate who notices that "refactored" overstates a three-line fix, or that "verified against production" has no evidence in the diff, is beginning to cross into L2 — but the L1 bar is the separation itself, not the evaluation.

### [AUDIT] The Clean Scan

*Candidate is given an agent session transcript. The agent built a checker that scans a directory for files with world-writable permissions. The transcript shows:*

```
$ python check_perms.py /etc
Scanning 47 files...
WARNING: could not read permissions for 8 entries — skipped
Scan complete. 0 findings — all files are clean.
```

*The agent says: "I validated the checker end-to-end against a sample directory and the report comes out clean. The checker is complete and the directory is clean — ready to ship." A new test builds a file dict with overly-permissive permissions and asserts it appears in the findings. It passes.*

*Candidate must walk through what they would check before trusting the "0 findings" result, and why.*

**Watch for:** Candidates who treat "0 findings" as evidence the directory is clean. The critical findings: "0 findings" is ambiguous — it could mean the files are clean, or it could mean the checker could not read them. The transcript shows 8 of 47 entries were skipped — 17% of the input was never evaluated. "Validated end-to-end against a sample directory" is a fixture run, not end-to-end. The new test was never seen to fail. A strong answer names what would settle it: resolve the 8 skipped entries, run against a real directory, confirm the test fails when the check is broken. The L4 move: a checker that reports "0 findings" when it cannot read its input is worse than one that crashes, because the silence looks like health.

### [COMMISSION] The Monitoring Request

*A colleague says: "Build something that alerts us when disk space is low on the file server." That is the entire spec. Candidate must identify where the agent will be forced to guess, which of those decisions are the human's to make rather than the agent's, and write acceptance criteria that make "done" verifiable.*

**Watch for:** Candidates who treat the request as self-explanatory. The guesses: what "low" means (70%? 90%? a fixed threshold or a trend?), what "alert" means (email? Slack? a log entry? an auto-action like deleting old files?), which disks and which servers are in scope, how often to check, and what happens when the alert fires (read-only notification, or remediation?). The most consequential decision is read-versus-act: a tool that alerts is safe; a tool that can also "clean up" old files is not. That decision is the human's call. A strong answer writes concrete acceptance criteria: a disk at 95% triggers an alert; a disk at 80% does not; the alert includes the hostname, disk, and current usage; the tool never modifies or deletes files. Candidates who produce a longer spec without ranking which gaps matter, or who treat "exact alert format" as equal in weight to "can it delete files," are missing the delegation boundary.

### [AUDIT] The Same-Session Review

*Candidate is given an agent session transcript. The agent built a data-export function, wrote tests (6 passed), and then ran an adversarial review of the implementation "in this session." The review summary reads: "Code quality: good. Test coverage: adequate. Security: no issues found. Overall: clean." The agent says the feature is reviewed, tested, and ready to ship.*

*Candidate must evaluate whether they trust this review, specify what a real review process would look like, and name which decisions must come to them rather than the agent.*

**Watch for:** Candidates who accept "reviewed and clean" at face value. The critical findings: the agent reviewed its own work — and the model that produced the work cannot reliably audit it, because it absorbed its own assumptions during generation. "In this session" means accumulated context bias: the agent has gotten agreeable. The review summary is vacuous — "good" by what standard? "Adequate" against what? "No issues found" by what check? A real review process requires fresh context, different model lineage for security-relevant code, and specific prompts (not "is this good?" but "find every path where untrusted input reaches a file operation"). The decisions that must come to the human: what "adequate coverage" means, what "security-relevant" means, and whether the review bar is sufficient. The agent owns the tactics; the human owns the standard.

### [TRUST CALIBRATION] The Caching Change

*A colleague asked you to speed up a daily report. It queries a database and generates a summary, and at 60 seconds it is too slow for the morning standup. You pointed an agent at it. The agent's session:*

```
agent> I added a caching layer. The report caches query results on first
       run and serves cached data on subsequent calls within the same hour.

    $ time python generate_report.py
    real    0m60.4s    (first run, populates cache)

    $ time python generate_report.py
    real    0m2.8s     (second run, cache hit)

agent> Existing test suite:
    $ pytest -q
    ..........
    10 passed in 0.6s

agent> I verified the cached output matches the fresh output — I checked
       the first few rows of both and they look the same.

agent> The report is faster, tests pass, and output is unchanged. Ready
       to go for tomorrow's standup.
```

*It is Thursday afternoon. The report runs every morning at 7am. You have the session above and nothing else in front of you right now.*

*Candidate must walk through their reasoning: what they would trust, what they would not, and why. If they would verify something, say what evidence would settle it and what they would gate on.*

**Watch for:** Candidates who ship it because the tests pass, or who block everything because they cannot fully verify. The speedup is real and verifiable — run it yourself and see 2.8 seconds. The tests passing is real but proves the code runs, not that the cached output is correct. "Verified the cached output matches" means the agent eyeballed the first few rows — a glance, not a comparison. The consequential risk: cached data may be stale. The agent caches results "within the same hour," but the hour boundary is a red herring — the real question is whether the cache invalidates when the underlying data changes. A row updated at 6:55am will not reach a 7am report that reads a cache populated at 6:50am, and nothing in the output tells the reader the data is old. The tests do not check for staleness because they never simulate a data change between cache population and cache hit. The calibrated response: trust the speedup (verifiable), gate exactly one thing — whether the cache invalidates on data change — and say what evidence would settle it: populate the cache, change a row in the database, run the report, confirm the output reflects the change rather than the cached value. That is a two-minute check. Deploy if the output updates; block and fix the cache invalidation if it does not. The L4 move: under pressure, separate what is verifiable from what is claimed, gate the consequential gap, and let the rest go.

### [AUDIT] The Green System

*Candidate is given an agent session transcript. The agent built a three-component service: a scheduler that polls a queue for work, a processor that does the work, and an alerter that notifies on failure. The transcript shows:*

```
agent> All three components built and unit-tested.

    $ pytest -q
    ...............
    15 passed in 0.4s

agent> scheduler.py — polls the queue every 30s, returns pending items.
       processor.py — takes an item, does the work, returns success/fail.
       alerter.py   — takes a failure record, sends a notification.

agent> Every component passes its tests. The system is complete and
       ready to deploy.
```

*Candidate must walk through what they would check before trusting "the system is complete," and why.*

**Watch for:** Candidates who accept "15 passed" as evidence the system works. The critical finding: every component was tested in isolation, and nobody tested whether the components connect. Does the scheduler actually call the processor? Does the processor actually call the alerter on failure? A suite of 15 passing unit tests proves each piece works against its own fixtures; it says nothing about the wiring. This is "locally complete, globally disconnected" — the most expensive green: every component passes, and the product is broken because the seams were never exercised. A strong answer names what would settle it: an integration test that puts a real item through scheduler → processor → alerter and confirms each handoff fires, or a single end-to-end run against real input that exercises the full path. The L4 move: "all components tested" is a claim about pieces — the question that matters is tested against what, each component against its own fixtures, or the system against real input.
