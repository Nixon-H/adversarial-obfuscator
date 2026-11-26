# ABSOLUTE MAXIMUM benchmark methodology and acceptance status

Date: 2026-11-26. This report records the current benchmark methodology controls and the exact reason the benchmark remains incomplete.

## Controls implemented

1. **Strict evidence separation.** Provider quota, harness syntax, timeout, malformed answer, static-only policy violation, and over-tool-limit records are invalid evidence. They are never scored as resistance.
2. **Fixed artifact identity.** The authoritative artifact pair is hash-fixed and must not be overwritten. Current source fixes are not retroactively attributed to those artifacts.
3. **Model-lane separation.** Records remain separated by authorised lane:
   - `opencode/hy4-flash-free`
   - `tokenharbor/deepseek-v4.1-flash:free`
   - `tokenharbor/deepseek-v4.1-flash-1017`
   No unauthorised model substitution occurred.
4. **Credential isolation.** Sandboxes run without provider/host credentials; TokenHarbor traffic is brokered by a host-side Unix proxy and sensitive runtime values are redacted.
5. **Attempt accounting.** The watchdog scans existing evidence before launching jobs and uses unused attempt numbers, preserving invalid evidence rather than overwriting it.
6. **AI-RE-003 product control.** Unvalidated benchmark scores cannot silently control release/preset selection. The control gate is implemented in `scripts/benchmark/score_control.py` and wired into adaptive paths; regression tests passed 17/17.

## Scoring validity boundary

The scorer has regression coverage and deterministic accounting rules, but there is still no independent golden corpus with known attacker outcomes large enough to validate quantitative predictive accuracy. Therefore the benchmark score remains diagnostic evidence, not a release gate. This is the correct conservative resolution of AI-RE-003, not a loophole.

## Current evidence snapshot

The final verification summary was regenerated after the continuation work. The authoritative state remains incomplete because provider lanes are externally unavailable:

- `opencode/hy4-flash-free`: valid attempts exist, but provider free-limit cooldown is active.
- `tokenharbor/deepseek-v4.1-flash:free`: HTTP 429; provider reports reset on 2 Dec 2026 at 15:07 UTC.
- `tokenharbor/deepseek-v4.1-flash-1017`: HTTP 402 pass-allowance exhausted.

A corrected multi-lane watchdog was restarted after direct isolated probes showed that `opencode/hy4-flash-free` can return HTTP 200 when the local OpenCode startup state is minimal. Historical free-limit records are no longer treated as proof of current unavailability; the watchdog probes first and uses provider cooldown only after a fresh quota failure. Internal subagent lanes remain qualitative local evidence only: they do not replace or statistically complete the authorized external-model benchmark lanes.

## Acceptance rule now in force

No release gate may use a benchmark score unless all of the following are true:

1. the scorer version is identified;
2. the score inputs are complete enough for the declared comparison;
3. invalid evidence is excluded under the strict rules;
4. the artifact identities are fixed and disclosed;
5. model lanes are not conflated;
6. the score has validation evidence appropriate to the decision being made.

Until then, benchmark results may inform engineering priorities but cannot pass or fail a release.
