# AM-001 Cloudflare request-bound phone approval validation (2026-11-27)

## Scope

End-to-end validation of the request-bound phone-approval architecture added
to the generated Cloudflare remote-execution Worker. The design replaces typed
TOTP for enrolled customers: the phone holds a non-extractable WebCrypto
ECDSA P-256 key, the Worker verifies request-bound approval signatures
server-side, and nothing reusable ever transits the customer machine.

Validation ran against the real local Cloudflare Python Workers runtime
(`pywrangler dev` / wrangler local workerd runtime). No public Cloudflare
deployment occurred and no real authenticator devices were enrolled; the phone
was simulated with independent ECDSA keys and correct WebCrypto-compatible
P1363 signatures driven over HTTP.

## Result: all 33 checks passed

Machine-readable evidence:
`ABSOLUTE_MAXIMUM_AM001_CLOUDFLARE_APPROVAL_VALIDATION_20261127.json`.

### Enrolment

- valid single-use token enrols a device key (`enrol_valid_token`)
- enrolment tokens are single-use (`enrol_token_single_use`)
- bad proof of key possession rejected (`enrol_bad_proof_rejected`)
- invalid token rejected (`enrol_invalid_token_rejected`)
- a second device enrols with a fresh token (`second_device_enrolment`)

### Approval flow

- the approval page is served over GET with the enrolment/signing surface
  (`approval_page_served`)
- unenrolled customers still use the direct dual-TOTP path
  (`unenrolled_direct_totp_executes`)
- once enrolled, RPC submissions pend without any typed TOTP codes
  (`enrolled_rpc_pends_without_totp`)
- the phone pending list shows function, customer, and request binding
  (`phone_pending_lists_request`)
- polling before decision reports pending (`poll_before_decision_pending`)
- approval executes and returns the correct result (`approve_accepted`,
  `approved_result_correct`: result 1012 = 991 + 7 * 3)
- results are delivered exactly once (`result_delivered_exactly_once`)
- denial is terminal for the client (`deny_accepted`, `denied_poll_error`)

### Binding and misuse resistance

- approvals are bound to the exact stored request hash
  (`hash_mismatch_rejected`); a mismatched approval records nothing
  (`mismatch_leaves_pending`) and the correct approval still works afterwards
  (`proper_approve_after_mismatch`)
- invalid approval signatures are rejected (`invalid_signature_rejected`)

### Administration

- wrong admin secret rejected (`admin_wrong_secret_rejected`)
- operator can list enrolled keys (`admin_list_keys`)
- dynamic customer disable blocks requests and enable restores them
  (`admin_disable_customer`, `disabled_customer_blocked`,
  `admin_enable_customer`, `enabled_customer_pends_again`)
- revoking a phone key stops both pending-list access and approvals
  (`admin_revoke_key`, `revoked_key_cannot_poll`,
  `revoked_key_cannot_approve`)

### End-to-end embedded client

- the generated split client submitted a request, polled while the simulated
  phone approved out-of-band, and returned the correct result
  (`e2e_phone_approval_happened`, `e2e_embedded_client_result`)

### Audit hygiene

- worker logs contained no master secret, customer HMAC secret, TOTP seeds,
  enrolment tokens, admin secret, or phone public-key coordinates
  (`worker_logs_avoid_secrets`)
- metadata-only audit events for enrolment and approval lifecycle were present
  (`audit_events_present`)

The served page's exact JavaScript signature construction (WebCrypto P1363
output over `parts.join("\x00")` UTF-8 bytes) was additionally reproduced in
Node.js and verified against the server-side verification for enrolment,
approval, and pending-poll messages, including rejection of a tampered
decision. The page JavaScript is therefore byte-compatible with the Worker.

## What this validation does not prove

- browser IndexedDB key persistence behaviour of the served page on real
  phones was not exercised end-to-end; the page uses standard WebCrypto and
  IndexedDB only, but operators should enrol one test device before production
  reliance
- host attestation remains absent; approval proves possession of the enrolled
  phone key, not the integrity of the customer machine
- a legitimate user can still approve a malicious operation; the page displays
  function, customer, time, and argument preview so the decision is informed
