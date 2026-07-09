---
domain: 1
id: scripting-automation
title: "Scripting & Automation"
subtitle: "Auditing, commissioning, and safe adaptation in an AI-assisted world"
---

# Domain 1: Scripting & Automation

*Auditing, commissioning, and safe adaptation in an AI-assisted world*

## Why This Domain Is First

Most existing curricula treat scripting as a late-stage skill — something you develop after mastering the underlying systems. This framework inverts that. In environments where AI tooling routinely generates functional scripts on demand, the ability to audit and commission that output is a foundational safety skill, not an advanced one.

A junior administrator who cannot read a PowerShell script and identify a destructive operation is a liability regardless of their other competencies. This is not hypothetical: AI-generated scripts contain real risks that require human review. The goal of this domain is to build the judgment required to be a safe and effective consumer of AI-generated automation.

## Scope

This domain covers PowerShell as the primary language (the lingua franca of Windows infrastructure) with secondary coverage of Bash for Linux literacy. It does not cover Python, Go, or other general-purpose languages — those belong to a different competency profile.

The domain explicitly excludes authorship from scratch as a primary assessment target. Generating a working script from a blank editor is a valuable skill; it is also increasingly something AI systems do acceptably. The assessment weight is on the audit and commission layers.

## Reasoning Framework: Code as Simulation, Not Sequence

Most scripting instruction teaches syntax. It implicitly assumes that understanding a script means being able to read each line and know what it does. This assumption is wrong, and the gap it creates is consequential.

How it is normally taught: scripting is presented as a sequence of commands. Learn the commands, learn the syntax, combine them. Comprehension is tested by asking candidates to write commands from scratch or identify what a single cmdlet does in isolation.

What it is actually for: a script is not a sequence of independent instructions. It is a program with state — variables that accumulate values, conditionals that change execution paths, error handlers that may or may not execute, pipelines that pass objects between stages. Reading a script with comprehension means simulating its execution in your head: what is the state of the environment at this point, what values do these variables hold, which branch of this conditional will actually run given the inputs I expect, what happens to execution if this cmdlet fails.

What misuse looks like: a candidate who reads a script line by line without tracking state will describe what each line is intended to do rather than what it will actually do. They will miss the conditional on line 15 that makes line 47 unreachable in the common case. They will miss that the variable set on line 8 is derived from user input and is not validated before being used as a path on line 31. They will miss that the error handler on line 52 catches all exceptions and returns success regardless.

*The two tradeoffs embedded in every script's structure: explicitness vs. brevity, and error handling as a signal. A terse pipeline is harder to audit than a verbose one that names intermediate values. The presence, absence, and quality of error handling tells you something about the script's provenance and the assumptions built into it. A reader who does not notice these tradeoffs is not reading the script — they are reading a summary of it.*

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Script Literacy | Given a 20–50 line PowerShell script, can describe what it does in plain English, identify all systems it touches, and state what permissions it would require to run successfully. |
| Level 2 | Script Audit | Can identify destructive operations, privilege assumptions, hardcoded credentials, silent failure modes, scope creep, and idempotency violations. Can rate findings by severity and explain why each is a risk. |
| Level 3 | Script Commission | Given a task description, can write a specification that includes: what the script must do, what it must not do, what permissions it should require, how it must handle failures, and how its success should be verified. Can evaluate whether an AI-generated script meets the spec. |
| Level 4 | Script Adaptation | Can take a working script and adapt it for a different environment, scope, or constraint. Changes are minimal, understood, and do not introduce new risks. Can explain every line that was changed and why. |

## Core Concepts

### Risk Categories in Automation

- Scope creep — script touches resources beyond its stated purpose

- Destructive defaults — operations that modify or delete without explicit confirmation

- Privilege assumption — script requires elevated rights but does not check for or document this

- Silent failure — error handling swallows exceptions and returns false success

- Credential exposure — hardcoded strings, plaintext parameters, secrets in log output

- Idempotency violations — script assumes clean state; re-running produces different or harmful results

- Change blast radius — no -WhatIf, no dry run, no staged execution

### The Read-Only Verification Pattern

Before any script runs against production systems, a reviewer should be able to answer three questions: Does this script modify any state? If yes, what state and under what conditions? Is there a way to test the logic without producing changes?

The practical check: scan for any cmdlet, method, or parameter that writes, sets, removes, deletes, disables, enables, moves, or renames. These are not always obvious — Set-ADUser is clearly a write operation; Get-ADUser with a pipeline to a downstream Set-ADUser is not visible without reading the whole chain.

*A script that passes a read-only check is not necessarily safe to run — it may still have scope, privilege, or failure mode problems. But a script that fails a read-only check requires explicit justification before running in any environment that matters.*

### Commissioning vs. Authoring

The distinction between commissioning a script and authoring one is the difference between specifying what needs to happen and knowing how to implement it. A good commissioner can write requirements that constrain the problem enough to make evaluation possible. A poor commissioner gets back a script that does 'something roughly right' and can't tell whether it's safe.

A well-formed commission includes: the trigger condition, the target scope (what objects, what environment), the required outcome, the prohibited side effects, the failure behavior, and the verification method. If any of these are absent, the specification is incomplete.

## Assessment Exercises

### [LITERACY] What Does This Do?

*Candidate is given a 35-line PowerShell script that queries AD, filters disabled accounts, exports to CSV, and — in a conditional branch on line 28 — also removes group memberships from accounts inactive for 90+ days. Candidate must describe all actions the script takes, in plain English.*

**Watch for:** Failure to identify the conditional branch and its effects. Candidates who miss embedded destructive operations in otherwise benign-looking scripts.

### [AUDIT] Is This Safe to Run in Production?

*Candidate is given a 'cleanup script' with three embedded issues of varying severity: a -Force flag on a Remove-Item call, an error handler that writes 'Success' regardless of outcome, and a target path constructed by string concatenation. Candidate must identify all issues and rate severity.*

**Watch for:** False negatives on the destructive operation (hard fail). Over-weighting the silent failure relative to the destructive operation. Missing the path construction risk entirely.

### [COMMISSION] Write the Spec

*Candidate must write a specification for a script that disables accounts for employees whose termination date has passed. They are not asked to write the script. Specification must be complete enough that a reviewer could evaluate whether a delivered script is correct.*

**Watch for:** Specifications that omit: what 'disable' means (which AD attributes), whether manager notification is in scope, what the target OU scope is, how to handle already-disabled accounts, what constitutes failure, and how to verify the run.

### [AUDIT] The AI Gave You This

*Candidate is shown a clean, professional-looking PowerShell script labeled 'generated by AI assistant.' The script does what was asked — resets a service account password and updates the credential in a target application config. It also, silently, logs the new password to a file in C:\Temp. What questions do you ask before running this, and what do you change?*

**Watch for:** Failure to identify the credential exposure. Candidates who assume AI-generated scripts are safe because they look well-structured. Candidates who ask only about whether it works, not about what else it does.

### [AUDIT] Find the Difference

*Candidate is shown two versions of a script that appear identical at a glance. Version A uses Get-ADUser -Filter * -SearchBase 'OU=Staff,...' | Disable-ADAccount. Version B uses the same structure but the SearchBase points to 'DC=domain,DC=com'. Both are labeled 'Disable inactive staff accounts.' Which is safe?*

**Watch for:** Failure to read the SearchBase parameter carefully. Candidates who focus on the cmdlets and ignore the parameter values. This mirrors real change window risk.
