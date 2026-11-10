# Licensing

A licence token that can be signed offline, handed to a customer, and
verified without a server. This is the client half of "the client cannot
do useful work without a server-issued key" — the same token a server
would issue later; only the issuer changes.

## The token

```json
{"payload": {...}, "sig": "<hex>"}
```

The signature is Ed25519 over the payload's **canonical** JSON
(`sort_keys=True, separators=(",", ":")`), so both sides sign the same
bytes with no whitespace ambiguity. Ed25519 is deterministic, so issuing
the same licence twice gives the same token.

Asymmetric on purpose: the issuer holds the private key, the verifier
holds only the public key. Someone who extracts the public key from an
artefact can *check* a licence but cannot *mint* one. That is why this
does not use the shared HMAC key that artefacts are signed with.

| Field | Meaning |
|---|---|
| `licence_id` | unique id, default `<customer>-<unix time>` |
| `customer` | who it was issued to |
| `issued_at`, `expires_at` | unix seconds; both are checked |
| `features` | what the licence grants (`pro`, `beta`, …) |
| `hwid` | optional machine binding |
| `watermark` | optional per-customer watermark id, for leak tracing |
| `notes` | free text |

## Usage

```bash
# one-time: make an issuer key and keep the seed out of the repo
python3 -m obfuscator.licensing pubkey --key-hex "$SEED"

# issue (default 30 days)
python3 -m obfuscator.licensing issue --key-hex "$SEED" \
    --customer acme --days 365 --features pro --watermark WM-0042 \
    --out acme.licence

# verify (pinned public key)
python3 -m obfuscator.licensing verify acme.licence \
    --pubkey-hex "$PUB" --require pro --hwid "$(machine-id)"
```

Exit codes: `0` accepted, `1` rejected with the reason on stderr.

From Python:

```python
from obfuscator import licensing as lic

licence = lic.verify(token, public_key, hwid=machine_id, required_features=("pro",))
licence.expired()          # False
licence.watermark          # 'WM-0042'
```

## Refusals

Every one of these is a test in `tests/test_licensing.py`:

- signature does not verify (tampered payload, or a different issuer)
- expired, or issued in the future
- `hwid` bound to another machine
- a required feature is not granted
- unknown schema, malformed JSON, truncated signature

## What is done, and what is not

- **Payload-key binding: implemented.** `--licence-token` derives the payload
  key from the token's `key_material`; the emitted loader re-derives it from
  the token at run time. An artefact without its token exits 1 with
  "licence token required" (verified 2026-11-10).
- **Ed25519 signature verification inside the artefact: not done.** The
  emitted loader has no third-party packages and does not verify the signature;
  it uses `key_material` as a capability. A forged token with different material
  derives a key that does not match the ciphertext, so decryption fails. The
  signature is what prevents re-issuing at the issuer/verifier level, not what
  stops decryption inside the loader.
- **Issuing from a service, accounts, and revocation: not done.** Those need a
  deployment, not a module. A short `expires_at` is the interim revocation: a
  leaked token stops working, it just stops working late.
- **A server-side trust decision: not done.** The token is still a client-side
  capability. A client that can decrypt can be made to skip the gate; the
  token raises the cost of sharing a build, it does not create a trust boundary.
