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

- **Payload-key binding: implemented.** `--licence token=` derives the payload
  key from the token's `key_material`; the emitted loader re-derives it from
  the token at run time. An artefact without its token exits 1 with
  "licence token required" (verified 2026-11-10).
- **Environment-only token lookup: implemented.** `--licence env-only`, used
  with `--licence token=`, makes the loader read only `NIXON_LICENCE` and skip
  `licence.json` / `licence.licence` beside the artefact. Verified: a local token
  file is ignored, the environment token runs the payload, a forged 64-hex token
  fails with `Magic Mismatch`, and the token's `key_material` is absent from the
  artefact. Do not ship the token in `dist/`.
- **Bootstrap string-table encryption: implemented.** `--licence bootstrap-encrypted`,
  used with `--licence token=`, encrypts the loader's string table with a
  token-derived key. The artefact therefore cannot decode its own bootstrap
  strings without the token. Verified on a 502 KB build: no token, a local
  token file, and a forged token all fail; the environment token runs the
  payload.
- **Signed-token pinning: implemented.** The build verifies the Ed25519 token
  signature and pins the canonical payload hash into the loader. At runtime the
  loader refuses any token whose canonical payload does not match the pinned
  hash. A forged token with the same `key_material` but changed metadata is
  therefore rejected. The build requires `NIXON_LICENCE_PUBLIC_KEY` to contain
  the issuer's Ed25519 public key.
- **On-chain identity gate: implemented.** `--licence chain`, used with
  `--licence token=`, requires signed chain metadata in the token and performs a
  read-only `eth_call` to verify that the ERC-721 owner still matches the signed
  owner. No transaction is sent and no testnet is required; the RPC endpoint is
  signed into the token. The signed `chain_id` is checked first, then the
  owner. A mismatch stops the loader with `licence chain owner mismatch`; an
  unreachable RPC or malformed metadata stops it with
  `licence chain verification failed: <cause>` — never the generic
  "licence token required", which is reserved for a missing token.
- **Unified flags: `--licence` and `--web3` (the only interface).**
  `--licence token=acme.licence env-only bootstrap-encrypted chain` is the
  licence gate; `--web3 rpc=… contract=… shards=a,b deploy deploy-rpc=…
  explorer=…` is the Web3 configuration. The former per-knob spellings
  (the `licence-` prefixed flags; contract/rpc/shards/auto-deploy/
  deploy-rpc/explorer) were **removed 2026-11-12** — the unified flags are
  the only interface, and the sub-option sets above are the complete set:
  there are no other licence or Web3 knobs.
- **Legacy Web3 flags are not the licence gate.** The former `--contract`,
  `--rpc`, `--shards`, `--auto-deploy`, `--deploy-rpc`, and `--explorer`
  spellings were removed 2026-11-12; their machinery lives under `--web3`.
  `--licence … chain` is the licence identity gate and reads its signed chain
  metadata from the token; the `--web3` sub-options drive the other Web3
  machinery (runtime `eth_call` licence check, Shamir key-shard fetch,
  contract deployment).

  Issue a chain-bound token with:

  ```bash
  python3 -m obfuscator.licensing issue ... \
    --chain contract=0x... token-id=1 owner=0x...
  ```

  Optional fields are `rpc=https://...` and `chain-id=1`. If `rpc` is omitted,
  the token uses a public Ethereum mainnet RPC endpoint.

  `--licence chain` makes the artefact require network access at run time. The
  build verification gate also runs the artefact, so a build with
  `--licence chain` fails unless the configured chain and token are reachable.
- **The first binding was a presence gate, not a key binding (fixed).** A
  forged token with `00`-material still ran the payload. The pack-time and
  runtime `k_dec` derivations now apply the token mask; the regression test is
  in `tests/test_licence_binding.py`.
- **Runtime Ed25519 signature verification: not done.** The loader pins the
  exact signed payload hash instead. The signature itself is verified during
  the build by `obfuscator.licensing`; the loader does not reimplement Ed25519.
  This still rejects metadata tampering, but it does not create a server-side
  trust boundary.
- **Issuing from a service, accounts, and revocation: not done.** Those need a
  deployment, not a module. A short `expires_at` is the interim revocation: a
  leaked token stops working, it just stops working late.
- **A server-side trust decision: not done.** The token is still a client-side
  capability. A client that can decrypt can be made to skip the gate; the
  token raises the cost of sharing a build, it does not create a trust boundary.
