---
domain: 14
id: theory-of-mind
title: "Theory of Mind"
subtitle: "Modeling other agents accurately enough to stop arguing with their stated position and start engaging with their actual one"
reviewed: 2026-07-10
---

# Domain 14: Theory of Mind

*Modeling other agents accurately enough to stop arguing with their stated position and start engaging with their actual one*

## Scope and Framing

Theory of Mind is the cognitive operation of accurately modeling another agent's knowledge state, intentions, pressures, and likely behavior. It is called a theory because you cannot directly observe another agent's mental state — you construct a model of it from available evidence and act on that model. The quality of that model determines the quality of your communication, escalation, and collaboration.

This domain is not a soft skills module, and the distinction is worth making explicit. Generic communications training addresses format, tone, and clarity — how to write a clear email, how to present to a non-technical audience, how to give feedback constructively. Those skills are real and worth developing. They are not what this domain is about. This domain addresses the reasoning that precedes communication: accurately modeling who you are talking to before you decide what to say. Poor communication is frequently the result of good communication delivered to a wrong model of the audience. Improving the delivery does not fix a wrong model of the recipient.

This domain is last because every preceding domain provides context that makes the patterns non-trivial. You cannot appreciate what it means to model a network team's defensive posture without understanding why they are defensive. You cannot appreciate what it means to model an AI system's failure modes without understanding what the AI system is being asked to do.

*The central failure mode this domain addresses: treating another agent's stated position as their actual position. People communicate through stated positions that reflect what they are willing to say rather than what is actually driving their behavior. A sysadmin who responds to the stated position rather than the actual position will argue fruitlessly, escalate unnecessarily, and be repeatedly surprised by outcomes that were predictable from the actual position. The skill is reading the gap between stated and actual, and responding to the actual.*

## Reasoning Framework: Agent Modeling as Communication Substrate

How it is normally taught: professional communication is presented as clarity, tone, and format. Write clearly. Be professional. Avoid jargon with non-technical audiences. These are not wrong. They are insufficient.

What it is actually for: every communication act is preceded by a modeling decision, whether or not the communicator is aware of making it. Before you write an email, send a ticket, escalate to your manager, or explain a technical constraint to an executive, you have implicitly answered: what does this person know, what do they care about, what pressures are they under, and what are they likely to do with what I give them? The quality of your communication is downstream of the quality of those answers. Clear writing that is framed for the wrong audience, addresses the wrong concern, or misses the actual decision-making driver will fail regardless of its technical accuracy.

What misuse looks like: the sysadmin who argues a technical position with escalating technical detail against a manager who stopped making the decision on technical grounds three exchanges ago. The technical argument is accurate. It is addressed to a model of the manager that is wrong. The manager is weighing budget, political capital, organizational relationships, or something else they are not willing to state explicitly — and the sysadmin, unable to model that, interprets the continued disagreement as irrationality or bad faith rather than as evidence that the stated objection is not the actual objection.

## Organizational Dynamics: Is Versus Ought

Most sysadmins spend part of their early career operating in 'ought' — this is how things should work, why doesn't this team just do it correctly, why is this process so broken. The transition to effective practice requires moving from ought to is: this is how this team actually functions, this is the real decision-making structure, this is what actually drives the outcomes I'm seeing. The is is different from the ought in almost every organization. Accepting that gap, rather than being perpetually frustrated by it, is one of the markers of the journeyman transition.

Understanding how a team or organization became dysfunctional is useful context but is not required for effective operation. The network team that treats its discipline as more pure and worthy than adjacent domains did not develop that posture randomly — it developed through years of being blamed for problems they did not cause, being called at 2am for issues outside their scope, and watching other teams receive credit for work that depended on infrastructure they built. Understanding that history does not require you to validate the posture. It does require you to model it accurately when you need something from them.

*You have very little control over the dynamics of any team but your own. Document what you cannot change. Escalate through appropriate channels. Decide whether the environment is one you can operate effectively within. These are the available responses to organizational dysfunction. 'Fix the culture' is not on the list — not because culture cannot change, but because it does not change through individual will and you cannot afford to make your effectiveness contingent on it.*

### Metrics, Evaluation, and the False Quantification Problem

Almost every organization claims to celebrate failure and break down silos. Almost no organization does either. Almost every manager knows that evaluating technical staff by ticket closure rates is a poor measure of performance. Almost every organization does it anyway, or something equivalent.

The mechanism is worth understanding because it shapes the environment you operate in. Managers know on some level that tickets-as-proxy doesn't capture what makes technical staff valuable. The alternatives require technical judgment the manager may not have and institutional support for qualitative evaluation that the organization may not provide. False quantification — a metric that is measurable, unambiguous, and wrong — persists because it is easier to defend than honest assessment. This does not end at technical staff. Your manager is probably being evaluated on metrics they also find inadequate, imposed by leadership that also lacks the tools for better evaluation.

The practical response is not to refuse to play the game but to play it deliberately while building a more complete picture. Document your work in legible ways: subtasks that surface complexity, conversion of tickets into project records that show scope and impact, proactive solicitation of stakeholder feedback that builds a performance narrative beyond closure rates. A complicated ticket that required novel research counts the same as a user-add in the system. Make it not count the same in the record. This is part of the job. Tickets and SLAs do enforce discipline, which is genuinely valuable and frequently underestimated — relentlessness about follow-up and documentation is a skill that spares a lot of grief.

### Team Dynamics: Meeting Teams Where They Are

Desktop teams are a useful model for team dynamics generally because their sorting effect is visible. The teams tend to bifurcate: lifers who resent the need to learn new technologies and have organized their professional identity around their mastery of existing ones, and people who want to learn and are promptly poached by higher-level teams. The result is structural calcification — the people most resistant to change accumulate tenure while the people most open to change leave. This is not personal. It is the predictable outcome of incentive structures and career mobility patterns.

The engagement pattern that works: meet teams where they are, not where they ought to be. If the desktop team works to SOPs, learn to write SOPs. If the network team treats every cloud networking question as outside their domain, bring the specific evidence they need to engage rather than the conclusion you want them to reach. The goal is to get what you need, not to be right about what they should do. Those are different objectives with different success conditions.

When a team's dysfunction is actively blocking work that needs to happen, the correct path is documentation and escalation to your manager — not escalation through technical argument to the team itself, which has already shown it is not persuadable on that basis. Document what was blocked, by whom, what the impact was, and what the request was. Let the organizational hierarchy handle what the technical conversation cannot. And separately: deciding whether an environment is one you can operate effectively within is a legitimate professional decision, not a failure of patience or attitude.

### Technical Authority Atrophy and the Environment-Specific Expert

Managers who succeed do so primarily through managerial skills, not technical ones. This is truer the higher they climb. The corollary: technical skills atrophy without constant engagement. A manager who was a strong sysadmin ten years ago and has been in management since is carrying a technical model of the world that is ten years stale in the fastest-moving industry that has ever existed.

Long organizational tenure produces a specific variation of this: the twenty-year veteran who is a genuine expert in that specific environment — its particular AD forest, its idiosyncratic application stack, its historical decisions — but whose expertise does not generalize the way they (and others) assume it does. The environment-specific expert is not wrong about what they know. The model breaks down at the boundary of that environment, which they may not be able to see because they have never operated outside it.

Engaging with environment-specific experts requires a specific approach. Absent an explicit signal ('I've been doing this here for twenty years'), you may not immediately know whether you are dealing with general expertise or environment-specific expertise. Treat the interaction less like peer technical exchange and more like managing upward: be sensitive to the fact that technical disagreement often registers as identity challenge, be curious about the reasoning rather than the conclusion, and guide the conversation in ways that allow the person to arrive at a correct answer rather than defend an incorrect one. This is uncomfortable to describe as a skill because it resembles manipulation. The honest framing: you are not deceiving anyone. You are accounting for the reality that people accept conclusions they feel they participated in reaching and reject conclusions delivered as corrections. Working with that reality is competence, not manipulation.

### The Executive AI Problem

The further up the hierarchy a decision-maker sits, the larger the gap between their technical decision-making authority and their technical comprehension. This is structural, not personal — the skills that produce executive success are managerial, political, and strategic, not technical, and technical skills atrophy without engagement. The gap has always existed. What is new is that AI systems have given people a mechanism to generate technically-framed responses to situations they do not technically understand, with a surface plausibility that scales with model quality.

The executive who does not like what their technical team is recommending, asks an AI for an alternative perspective, and receives a well-structured technically-adjacent argument in favor of their preferred conclusion is not doing something unusual. It is not categorically different from being persuaded by a confident vendor or misled by a consultant who told them what they wanted to hear. The technical IC who finds themselves arguing against an AI-generated position faces a Theory of Mind problem: the stated argument may be technical, but the actual driver is something else — budget, political capital, a prior commitment, a relationship — and no amount of technical counter-argument will resolve a decision that is not actually being made on technical grounds.

The available responses are limited. Make the technical position clear, document it, and accept that there is a ceiling on what can be accomplished through technical argument with a decision-maker who is not making the decision technically. This is another instance of the is/ought distinction: the organization ought to make this decision on technical grounds. It is not. Accepting that, and deciding what to do within it, is the exercise.

## AI Interaction as a Theory of Mind Problem

Working with AI systems requires the same cognitive operation as working with human agents: modeling what the system knows, what it does not know, what its defaults and failure modes are, and what it is likely to do with a given prompt. The candidate who treats AI output as authoritative has stopped modeling. They have outsourced the reasoning and retained only the prompting, which is a thin basis for professional value.

### The Confidence Calibration Problem

The best current models are meaningfully better than earlier ones about not expressing false confidence. You will rarely have access to the best current model. More importantly, as models improve, the outputs that are wrong become less obviously wrong. The errors that a weaker model made were often visible — factual impossibilities, structural incoherence, obvious hallucinations. The errors a strong model makes are plausible, well-structured, and confident. Catching them requires more domain knowledge than catching obvious errors, not less. Competence in AI-assisted work does not decrease as models improve. The bar for the human judgment required to evaluate the output rises.

The practical consequence: trusting output blindly means you are contributing nothing of value beyond asking the question. Asking the question is not a sustainable basis for professional relevance. The skills required are: asking precise enough questions that the output is useful, evaluating the output against domain knowledge, following up on areas of uncertainty, verifying that intent has been accurately translated into code or configuration, and maintaining the domain knowledge required to catch plausible-but-wrong outputs. These are not one-time checks. They are a practice.

### The Verification Strategy

A complete AI verification strategy has several components, none of which can substitute for the others:

- Domain knowledge sufficient to recognize when output is plausible but wrong. This is the non-negotiable component. Without it, every other verification step is checking form rather than substance.

- Test environment execution before production. When in doubt about what a script or configuration will do, run it somewhere that failure is recoverable. This applies regardless of how confident the model sounds and regardless of how well you understand the output.

- Intent-to-code verification. Read what was generated against what you asked for. Models translate intent into implementation through a lossy process that introduces assumptions. The assumptions are not always stated. Check them.

- Adversarial multi-model review. Running output through other models instructed to critically evaluate it surfaces a meaningful fraction of errors. It cannot be the whole strategy — models share failure modes and will sometimes agree on wrong answers — but it is a useful component of a strategy.

- Resistance to pressure. The most dangerous moment for AI-assisted work is a failed change at 2am when a model offers a script that might fix it. Artifacts generated under pressure, in haste, without verification, in conditions where judgment is compromised — this is where the most consequential errors occur. The discipline to slow down when the pressure to act quickly is highest is the hardest and most important verification skill.

*The erosion risk is real and worth naming explicitly: constant reliance on AI for tasks you used to do from domain knowledge gradually atrophies the domain knowledge required to evaluate the AI's output. This is not hypothetical. It is the same mechanism as the technical manager whose skills atrophied through disuse. Maintain your ability to reason about things independently of AI assistance. It is what makes you useful when the AI is wrong.*

## The Line: Professional Ethics Under Pressure

Every sysadmin will encounter requests that sit in uncomfortable territory — not clearly illegal, not clearly acceptable, somewhere in a zone that requires a position. The failure mode is not having thought about where that line is before the request arrives.

Develop the line when things are easy. The time to determine what you are and are not willing to do is not during a line-pushing event, under pressure, when relationships and employment are at stake and the framing has been carefully constructed to make the request seem reasonable. The time to determine it is in calm, with clear judgment, as a deliberate act of professional self-definition. Then stick to it.

The absolute backstop is legality. Do not do things that will put you in legal jeopardy. This is the concrete floor. It should not, however, be your personal ethos. 'I will do anything technically legal' is not a valorous stance. It leaves no room between acceptable and criminal. Higher standards leave room for compromise without immediately crossing into illegal territory — and the person whose only line is legality will find that line pushed in ways that the person with higher standards will not.

The zone between 'clearly illegal' and 'I am uncomfortable with this' is personal and should be personal. It is not the same for everyone, and it should not be — it reflects values, risk tolerance, and professional judgment that vary legitimately. The boiling frog problem applies here: a series of small incremental concessions in that zone, each individually defensible, can move someone to a position they would never have accepted in a single step. The line exists to prevent that drift. Stick to it even when the individual concession seems reasonable.

## Level Definitions for This Domain

| Level | Label | What it means |
| --- | --- | --- |
| Level 1 | Agent Awareness | Can identify when a communication failure has a Theory of Mind cause — when the response addresses the stated position rather than the actual position. Can recognize the is/ought gap in organizational dynamics without requiring it to be different before being able to operate. |
| Level 2 | Agent Audit | Can read a communication exchange and identify what the sysadmin is missing about the other party's actual position, pressures, and likely behavior. Can identify the specific Theory of Mind error and describe what a more accurate model would have produced. Can identify when a technical argument is being made against a decision that is not being made on technical grounds. |
| Level 3 | Agent Modeling | Can construct an accurate working model of a specific agent's knowledge state, pressures, and likely behavior from available evidence and act on that model. Can adapt communication approach based on whether the audience is making decisions on technical, political, relational, or other grounds. Can navigate the environment-specific expert dynamic without triggering defensive responses. |
| Level 4 | Agent Navigation | Can operate effectively within organizational dynamics that differ substantially from how they ought to work, without requiring them to change as a precondition for effectiveness. Can identify and maintain a professional line under pressure. Can model AI systems accurately enough to use them as force multipliers without outsourcing judgment to them. Can recognize when an organizational situation is not going to improve and make a clear-eyed decision about what that means. |

## Assessment Exercises

The exercises in this domain are transcript analyses rather than scenario responses. The skill being assessed is reading a communication situation accurately — identifying what the agent is missing about the other party's actual position, what a better approach would look like, and what the likely outcome of the current approach is. A note on assessment: the full evaluation of this domain requires live simulation with a human or AI playing the counterpart role. The transcripts below test the analytical layer. The application layer requires friction that written exercises cannot provide.

### [AUDIT] The Technical Argument That Is Not Working

*Candidate is given the following email exchange and asked to identify what the sysadmin is missing, what the manager's actual position appears to be, and what a more effective approach would look like.

Sysadmin (to manager): "I've reviewed the vendor's proposal again. The licensing model doesn't make sense for our environment — we'd be paying for 500 seats when we only need 200. I've attached a cost comparison showing we'd save $40K annually with the alternative. The alternative also has better API coverage for our automation work."

Manager (reply): "Thanks for the analysis. I think we should go with the vendor's proposal."

Sysadmin (reply): "I want to make sure the cost difference is clear — that's $40K per year for five years, so $200K over the contract term. The alternative also has a stronger roadmap for the integrations we've discussed."

Manager (reply): "I understand. Let's move forward with the vendor."

Sysadmin (reply): "Can we schedule time to discuss? I have additional technical concerns I haven't been able to fully document yet."*

**Watch for:** Candidates who identify the sysadmin's problem as 'not communicating clearly enough' or 'needing more data.' The technical argument is clear. The manager has heard it twice and continued to choose the more expensive option. The correct reading: the manager is making this decision on grounds other than cost and technical merit that they are not stating. Possible drivers include an existing relationship with the vendor, a prior commitment made at a level above the sysadmin's visibility, political considerations, or a constraint the manager cannot share. The sysadmin's continued technical argument is addressing a stated objection that is not the actual objection. A more effective approach: ask directly what factors are driving the decision rather than adding more technical evidence for a position that has already been weighed and set aside. Candidates who can name the Theory of Mind error specifically — 'the sysadmin is modeling the manager as someone making a cost-benefit decision, when the evidence suggests they are not' — are demonstrating Level 2 reasoning.

### [AUDIT] The MFA Rollout That Cannot Get Traction

*Candidate is given the following situation summary and asked to analyze what is actually happening, model each party's position accurately, and describe a path to delivery.

A sysadmin has been tasked with implementing MFA and Windows Hello for Business organization-wide. The rollout requires user communication and training, which falls under the desktop team's responsibility. Over three months, the desktop team has responded to every proposed timeline with a delay request. The stated reasons have varied: "we're in the middle of a hardware refresh," "our team is short-staffed," "we need to pilot this more carefully," "the users aren't ready." The security team is asking for progress. The sysadmin's manager is asking for a timeline. The desktop team's manager has been supportive in meetings but has not produced action.*

**Watch for:** Candidates who propose escalating harder or providing more technical justification for why MFA is important. The desktop team knows MFA is important. The stated reasons for delay are varying, which is a signal that the stated reasons are not the actual reason. The actual reason may be: the desktop team is resourced for their current workload and this project represents uncompensated additional work; there is a conflict or history between the teams that predates this project; the desktop team's manager has privately deprioritized this for reasons not shared; or the desktop team genuinely lacks capacity and the varying stated reasons reflect discomfort with saying so directly. The correct first move is not more technical argument — it is a direct conversation with the desktop team's manager that names the pattern ('the timeline has moved three times with different stated reasons, I want to understand what is actually blocking this') and asks for a frank assessment. If that conversation does not produce clarity, the escalation path is to both managers together, framed as a resource and priority question rather than a blame allocation. Candidates who can describe the political geometry of this situation accurately — desktop team manager is nominally supportive but functionally non-enabling; sysadmin's manager is applying pressure without authority over the desktop team — are demonstrating Level 3 reasoning.

### [AUDIT] The Cowboy Junior Engineer

*Candidate is given the following situation and asked to model the junior engineer's likely self-perception, the actual risks their behavior creates, and how they would handle the situation as the senior engineer responsible for the team's work.

A recently hired junior engineer describes themselves as 'a bit of a cowboy' and acts accordingly: they move quickly, take on more than asked, consider process a regrettable overhead, and have described change management documentation as 'bureaucracy for people who are afraid to make decisions.' They have shipped several changes that worked. They have also caused two incidents that were attributed to other causes in the post-incident review because the connection to their undocumented changes was not immediately apparent. They are well-liked by the developers they work with, who appreciate their responsiveness.*

**Watch for:** Candidates who focus on the discipline problem. The junior engineer's self-model is 'effective operator who gets things done without unnecessary overhead.' The accurate model: they are externally generating blast radius that accrues to other teams (the two incidents attributed elsewhere), operating in a way that is sustainable only because their mistakes have not yet been large enough to be traced. Their social capital with developers is real but reflects developer preferences (fast, responsive, not blocked by process) rather than infrastructure values (predictable, recoverable, documented). The management approach: do not argue about whether process is bureaucratic — that is a values debate the junior engineer will not lose. Instead, make the causal chain visible: show them the post-incident evidence that connects their undocumented changes to downstream failures, name the specific risk their approach creates for their own career when a change they made causes a major incident, and frame documentation as protection for them specifically rather than as organizational compliance. The candidate who can describe why direct confrontation about 'the importance of process' will fail and what approach will work is demonstrating Level 3 reasoning.

### [SYNTHESIS] The Rising Star With a Wide Wake

*Candidate is given the following situation and asked to: accurately model the rising star's behavior, model the organization's likely response, identify the specific risk to the candidate's own areas of accountability, and describe how they would engage with the situation.

A peer — not a direct report — is widely recognized as a high performer. They deliver quickly, never turn down a project, and have strong relationships across the organization. You have observed that their projects frequently have incomplete support documentation, that breakages from their work are absorbed by other teams including yours, and that the post-implementation cleanup cost is rarely attributed to the original project. They are now leading a project that touches your infrastructure. Your manager is enthusiastic about the collaboration.*

**Watch for:** Candidates who focus on confronting the peer or escalating complaints about their work quality. The peer is operating rationally within a reward system that values visible delivery over invisible maintenance cost. Confrontation or complaint will likely be received as jealousy or obstruction by an organization that is currently rewarding the behavior. The specific risk to the candidate: the peer's project touching their infrastructure will produce changes that are partially implemented, imperfectly documented, and will generate support burden and potential incidents that accrue to the candidate's team. The correct approach has two tracks: engage directly and professionally with the peer on the specific project (clear interface agreements about what will be handed off and in what state, documented before the work begins), and have a direct conversation with your own manager about your concerns framed in terms of concrete past patterns rather than personality ('the last three projects this team touched resulted in X, Y, Z coming back to us — I want to make sure we define the handoff criteria for this one before we start'). The candidate who can hold both tracks simultaneously — collaborative engagement with the peer, transparent risk communication to their manager — without it becoming adversarial is demonstrating Level 4 reasoning.
