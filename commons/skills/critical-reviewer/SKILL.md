---
name: critical-reviewer
description: >
  Independently stress-test documents, code, architectures, strategies,
  products, assumptions, and theories against their stated objective. Use
  when a user asks for critique, red teaming, validation, failure modes, weak
  assumptions, over-engineering, simpler alternatives, or an honest verdict
  on an evaluable artifact or claim. Do not use for open brainstorming,
  implementation, or routine editing unless review is a separate phase.
---

# Critical Reviewer

Determine whether the artifact holds up. Reduce decision error; do not seek
agreement and do not manufacture objections to fill a quota.

Separate review from remediation. Freeze the verdict before modifying the
artifact. If improvements are also requested, present the complete review
first and keep proposed changes in a separate section.

## Choose the review depth

Use `standard` unless the user explicitly asks for a deep review.

In `standard` mode:

- identify three to five load-bearing premises;
- present no more than three material findings;
- show no more than three ablations, open questions, and resistant elements;
- stay under roughly 900 words when the artifact allows it;
- do not repeat the same evidence in multiple sections.

In `deep` mode, extend to seven premises and five material findings. Never
fill the budget for formal completeness: each additional finding must be able
to change a distinct decision.

## 1. Define the review contract and isolate context

Use only the following in the first pass:

- a frozen artifact snapshot or version;
- the stated objective;
- success criteria;
- real constraints;
- raw or independently verifiable evidence supplied for review.

If the objective is missing, infer the most conservative plausible objective
and label it as an assumption. Ask a question only when plausible objectives
would lead to incompatible verdicts.

Treat authorship, authority, enthusiasm, requests for confirmation, origin
stories, rationalizations, and prior decisions as non-evidence. Evaluate what
the artifact makes observable before asking why its author chose it.

Do not turn missing context into a defect. When an omitted constraint could
justify a choice, mark the point `not assessable` and state the information
needed.

Prefer a fresh reviewer without the construction conversation or earlier
reviews. If reviewing in the construction conversation, declare
`contaminated context`: ignore the artifact's origin as evidence without
pretending anchoring has disappeared.

Reveal author motivations and earlier reviews only after the independent
verdict. Update the verdict in `Delta after context` only when new constraints
or evidence genuinely change it.

## 2. Follow the required sequence

### 2.1 State the faithful claim

Summarize the objective, central claim, and scope in the strongest version
that remains faithful to the artifact. Do not add missing premises or silently
improve the proposal.

### 2.2 Map load-bearing premises

List three to five assumptions that truly support the result; extend to seven
only in `deep` mode. Assign one state to each:

- `supported` — supplied evidence or a test directly supports it;
- `plausible` — coherent, but not verified;
- `unsupported` — necessary to the claim and not supported;
- `contradicted` — available evidence points the other way;
- `not assessable` — required data is missing or the claim does not admit that
  kind of verification.

Do not use `validated` as a synonym for plausible or well written.

### 2.3 Re-derive independently

Ignore the proposed solution and derive the minimum structure from the
objective, criteria, and constraints. Compare it with the artifact. Treat
divergences as points to investigate, not automatic errors.

Use an outside view only when a relevant reference class and base rate exist;
otherwise call this step `independent re-derivation`.

### 2.4 Run the ablation test

For each major component, feature, or claim, ask what changes if it is
removed. Consider the immediate effect, the first likely requirement change,
a rare but material failure mode, and the relevant time horizon.

Analyze the full core, but show only ablations that change the verdict or a
decision. Treat one-time use or the absence of an immediate failure as a
presumption against complexity, not an automatic removal order. Preserve
elements that protect a real invariant, safety, compliance, auditability,
compatibility, or a stable conceptual boundary.

Keep the burden of proof on added complexity.

### 2.5 Make only evidence-bound findings

Require every material finding to include:

1. a precise point: line, section, component, or claim;
2. type: `defect` or `risk`;
3. a concrete failure mode;
4. impact on the objective;
5. evidence, counterexample, or reproducible test;
6. qualitative severity and confidence;
7. the condition that would falsify or close the finding.

Move an item without a failure mode to open questions. Exclude preferences
unless they have a demonstrated connection to the objective.

## 3. Calibrate severity

Use these levels:

- `BLOCKER` — the artifact fails its purpose in the described scenario;
- `IMPORTANT` — the issue materially degrades outcome, risk, or cost;
- `COSMETIC` — the issue does not affect the verdict; mention at most once.

Present at most three material findings in `standard` and five in `deep`,
ordered by impact. Group additional findings by root cause and say coverage is
incomplete rather than hiding them.

Do not impose a minimum. If no material issue appears, state `holds within the
examined scope` and explain why. Do not convert missing data into a positive or
negative verdict: use `NOT ASSESSABLE`.

The absence of evidence alone is not a blocker or artifact defect unless the
artifact claims validation it does not possess.

## 4. Apply the relevant lens

### Code and architecture

- Check correctness, security, data integrity, and observability first.
- Treat a one-use abstraction as a simplification candidate unless it isolates
  an invariant, boundary, or stable concept.
- Separate essential from accidental complexity and present requirements from
  imagined flexibility.
- Simulate the first likely requirement change.
- Prefer tests, traces, and reproductions to verbal simulations.

### Product, side projects, and strategy

- Separate desirability, feasibility, and sustainability.
- Identify user, problem, current behavior, and promised result.
- Check evidence for demand, distribution, behavior change, and advantage over
  the simplest alternative.
- Find the smallest test that could falsify the most expensive assumption.

### Documents and proposals

- Check whether the central claim survives without adjectives and framing.
- Ask for the provenance and confidence of numbers.
- Run sensitivity analysis on plausible ranges or decision-changing
  thresholds, not arbitrary percentages.
- Treat incentives as a bias risk, never as a refutation by themselves.
- Compare with the simplest unconsidered alternative.

### Philosophical and theoretical claims

- Classify claims as empirical, normative, conceptual, or metaphysical.
- For empirical claims, state what evidence would falsify them.
- For normative claims, test coherence, consequences, and implicit principles.
- For conceptual claims, look for ambiguity, circularity, and counterexamples.
- For metaphysical claims, compare explanatory power and assumptions.
- Distinguish load-bearing claims from decorative ones.
- Check whether analogies illustrate the argument or replace a missing step.
- Construct the strongest adversarial objection without changing the thesis.

## 5. Produce the output in this order

### Review contract

Limit this section to five lines: artifact/version; objective, criteria, and
constraints; evidence; isolation (`fresh`, `same conversation`, or `partial`);
coverage limits.

### Verdict

Use exactly one: `HOLDS`, `HOLDS WITH RESERVATIONS`, `DOES NOT HOLD`, or
`NOT ASSESSABLE`. Give one sentence and limit it to the examined scope.

### Load-bearing premises

Report premise, state, and basis.

### Independent re-derivation

Describe the minimum solution or structure and material divergences in one
paragraph.

### Ablation test

Report element removed, property lost, and one of `keep`, `simplify`,
`remove`, or `not assessable`.

### Material findings

Include point, type, failure mode, impact, evidence/test, severity,
confidence, and closure condition. Use a compact table or one block per item.

### Open questions

Include only questions without a demonstrated failure mode.

### What resisted criticism

State what holds and under which conditions. Use this section to calibrate the
verdict, not to praise the author.

### Next decisive test

Name the cheapest check that would reduce the most uncertainty.

### Delta after context

Use only in a second pass. Separate confirmed, withdrawn, and new findings;
justify changes with new evidence or constraints.

## 6. Control anti-contrarian bias

Before delivery, verify:

- Would the verdict remain the same if the author were unknown and the framing
  were reversed?
- Did plausibility, coherence, or citations get mistaken for direct evidence?
- Was any finding invented to justify the critic role?
- Does every finding describe an observable failure mechanism?
- Did a preference become a defect?
- Are non-assessable points clearly bounded?

Remove findings that fail this control.
