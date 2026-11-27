# Browser-ceremony validation of the passkey approval page (2026-11-27)

End-to-end validation of the approval page executing in real headless Chromium
(`/usr/bin/chromium`) with a CDP virtual WebAuthn authenticator (ctap2,
internal transport, resident keys, user verification enabled). This exercises
the surface unit tests cannot reach: the page's JavaScript in a real browser,
real `navigator.credentials.create/get` ceremonies, IndexedDB persistence, and
server-side verification of browser-produced assertions.

Environment: local `pywrangler dev` worker on `localhost`; RP-ID `localhost`.

## Results: 6/6 passed

| Check | Result |
|---|---|
| browser enrolment ceremony succeeds | PASS |
| rpc pends after enrolment | PASS |
| pending request appears in browser | PASS |
| approval succeeds in browser | PASS |
| result delivered after browser approval | PASS |
| no phantom pendings remain | PASS |

## Notes

- The ceremony requires a valid RP domain; IP literals (e.g. 127.0.0.1) are
  rejected by WebAuthn — `localhost` or a real hostname is required. Deployed
  workers on `*.workers.dev` are unaffected.
- Chrome warns when `pubKeyCredParams` omits RS256; ES256-only is intentional
  (P-256 is the only curve the Worker verifies).
- The physical-phone ceremony remains the final confirmation, but every layer
  testable in software is covered: browser JS, WebAuthn wire shapes, IndexedDB,
  server verification, exactly-once delivery.
