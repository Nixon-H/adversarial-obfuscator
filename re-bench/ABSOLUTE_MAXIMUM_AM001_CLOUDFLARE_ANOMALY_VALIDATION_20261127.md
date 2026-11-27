# Anomaly-detection live validation (2026-11-27)

Validation of alert-only anomaly detection in the real Workers runtime
(`pywrangler dev`/wrangler, python_workers). Soft-authenticator produced real
WebAuthn wire shapes; RP-ID `localhost`; velocity window configured at
max 2 approvals per 600s for the test.

## Results: 11/11 passed

| Check | Result |
|---|---|
| enrolment succeeds | PASS |
| first pending item annotated novel-function | PASS |
| first approval executes | PASS |
| second approval executes | PASS |
| after first approval annotation loses novel tag when window not full | PASS |
| velocity annotation appears in list once window full | PASS |
| velocity approval still executes (alert-only) | PASS |
| audit log contains anomaly events | PASS |
| anomaly audit mentions novel-function | PASS |
| anomaly audit mentions high-velocity | PASS |
| anomaly audits leak no argument values | PASS |

## Design notes validated

- Novel-function flags exactly the first approval of a function, then goes
  quiet once operator-vouched; denials leave the function novel.
- Velocity flags once approvals in the window reach the configured threshold;
  detection precedes recording so bursts are judged against prior history.
- Alert-only: anomalous approvals still execute — detection never blocks.
- Audit events carry fixed tags only; no arguments or secret material.
- Annotations appear both in direct pending lists and in the refreshed lists
  embedded in decision responses (the path the page actually renders).
