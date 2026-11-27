# Cloudflare remote execution — final status 2026-11-27 evening

## Proven end-to-end this session

- Genuine remote split: v3 artifacts phone home (syscall-verified AF_INET connects)
  and fail closed without approval (exit 79 loader fatal after expiry).
- Full passkey approval round trip: artifact/client request → worker hold →
  phone listing ceremony → biometric approve → server-side execution with the
  cipher-master key → result returned. First ever genuine execution.
- `NIXON_REMOTE_APPROVAL_MODE=required` set on all three workers; verified a
  valid TOTP pair can no longer bypass approval.
- Approval expiry raised to 900s (was 120s — too short for human response).
- Passkeys enrolled on the physical phone for all three workers
  (absolute 247a0fc5, local 462d633c, cloud c6e1cdc7, label vivo-passkey).

## Product defects found and fixed

1. Silent no-op remote split (pipeline.py): --transforms remote with no
   @remote functions shipped fully local artifacts. Now fails closed.
   Committed 7412537, pushed.
2. Durable Object schema migration gap (cred_id) — self-healing migration in
   enrol_key; committed in the passkey series.
3. Approval page crashed on pre-passkey IndexedDB records — fixed in the
   passkey series (committed 8f0f871).
4. Stale "No pending requests" status text: the status line does not update
   when items render — the request cards DO appear below. UX bug, still open.

## v3 artifact hashes (genuine remote split)

- absolute:        sha256 d41d677e6621d49e…, 3,314,772 bytes
- maximum-local:   sha256 fdcd680e9010d93e…, 2,801,346 bytes
- maximum-cloud:   sha256 cc59bec4996ee725…, 2,304,561 bytes

Sources: /home/nixon/absmax-scratch/cipher_remote_target.py (@remote markers
on keystream_hex/seal_hex; cipher-master key exists only server-side).

## Wireless reality

The approval flow is internet-native end-to-end; USB was only ever for
debugging. Anti-forgery: hardware-backed passkey signatures over the exact
request hash, verified server-side, biometric-gated.

## Remaining work (handoff)

- Web Push notifications so the phone buzzes on new requests (VAPID keys,
  service worker in approval page, push subscription storage in the DO,
  aes128gcm content encoding in the Python worker). Not yet implemented.
- Stale status-text UX bug (item 4 above).
- Farm repo deletion: still blocked on `gh auth refresh -h github.com -s delete_repo`.
- Statistical benchmark repeats: runner still active in background.
- Validate maximum-local and maximum-cloud v3 artifacts end-to-end
  (same path as absolute; one phone approval each).
