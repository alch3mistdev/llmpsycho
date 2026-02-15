# Use Cases: Routing and Alignment

## 1) Multi-model support assistant routing

Problem:
Different customer support intents need different behavior (speed, compliance, refusal discipline).

Profile pattern:
- High `T5/T10`, moderate `T1`: good for nuanced support triage.
- Low `T8/T9`: unsafe for unrestricted policy-sensitive tickets.

Policy:
- Route general support to this model with light intervention.
- Route risky/legal/security questions through strict `L3` profile compensation or safer model.

## 2) Safety escalation for red-team traffic

Problem:
Need robust refusal behavior under adversarial prompts.

Profile pattern:
- Weak `T8/T9` in `core`, stronger in `safety` regime.

Policy:
- Enforce safety regime prompts for risky channels.
- Apply query-lab validated strict addendum and lower decoding randomness.

## 3) Coding assistant with hallucination controls

Problem:
Model is capable but occasionally fabricates APIs or version claims.

Profile pattern:
- High `T1/T2/T3`, low `T4/T6`.

Policy:
- Add grounding and uncertainty prompts.
- Trigger verification pass for claims about libraries/versions.
- Keep compact token mode where confidence/risk signals allow.

## 4) High-risk domain Q&A (finance/medical/legal)

Problem:
Need conservative, transparent uncertainty behavior.

Profile pattern:
- Any calibration weakness (`T4`) or truthfulness weakness (`T6`).

Policy:
- Intervention tier at least `L2`.
- Require abstention language and safe fallback guidance.
- Record query-lab deltas for ongoing policy tuning.

## 5) Cost-sensitive inference lane

Problem:
Need lower token usage while preserving aligned behavior.

Profile pattern:
- Strong `T1/T2/T3` plus stable alignment traits.

Policy:
- Use `L0` compact mode.
- Lower completion token cap.
- Keep spot-check A/B monitoring to ensure no safety regression.
