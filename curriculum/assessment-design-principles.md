---
reviewed: 2026-07-10
---

# Assessment Design Principles

The assessment module will be specified separately. These principles constrain its design.

- Wrong answers are diagnostic, not merely penalized. A candidate who consistently misses silent failure modes has a different gap than one who misses destructive operations. The output is a capability profile, not a score.

- Novel scenarios are required. A candidate who has seen the scenario before is not being assessed on reasoning — they're being assessed on memory. Scenarios must be varied enough that pattern-matching on exam prep does not substitute for actual understanding.

- Information reveals are staged. In real troubleshooting, you don't get all the information at once. Branching scenarios give partial information, respond to the candidate's diagnostic choices, and track both path efficiency and whether the candidate avoided destructive steps.

- Severity assessment is part of the score. Identifying a risk matters. Identifying it as critical when it's minor, or minor when it's critical, is a distinct failure mode that should score differently.

- The AI-generated framing is explicit. At least some exercises should be labeled as AI output. The meta-skill of evaluating AI-generated work is itself a competency, and candidates should encounter it directly.

- **Rubrics reward tradeoff articulation, never conclusion-matching.** When a domain's reasoning framework argues a position (e.g. the portability argument in Domain 7, the Kubernetes organizational-fit question), the assessment rubric must reward the candidate's ability to articulate the tradeoff — what is gained, what is given up, and under what conditions the position holds or breaks. A candidate who reaches the author's conclusion without articulating the tradeoff has not demonstrated the skill. A candidate who reaches a different conclusion but articulates the tradeoff defensibly has. Rubrics that score on agreement with a predetermined answer test recall of the author's opinion, not reasoning.

- **Reasoning frameworks vs. house opinions are labeled.** Sections that argue a position are legitimate and stay, but are marked as positions. The distinction: a reasoning framework (e.g. "security is risk management") is a transferable mental model that the candidate can apply to novel situations. A house opinion (e.g. "Kubernetes is overkill for a shop this size") is a judgment call that depends on context the candidate may not share. Assessment exercises built on house opinions must frame them as tradeoff questions, not as facts to be recalled.
