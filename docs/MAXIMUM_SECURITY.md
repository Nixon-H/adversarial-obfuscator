# Maximum Security Configuration

**Status:** current investigation, 2026-11-10; **commands and addendum
updated 2026-11-20** (§5.3 below and the 2026-11-20 addendum at the end of
this file). The title is a question, not a claim: this document establishes
the **strongest configuration whose relevant protections were actually
built and run**, and states what remains unmeasured. The 2026-11-10
measurement matrix below is kept as history; the 2026-11-20 measured
profiles live in `pydeobsbench/run.py` and the research log
(`docs/research/pydeobsbench-2026-11-18.md`, §5o–§5q).

The short answer: **enabling every flag is not maximum security.** It is a
build-time and size explosion, it includes inert and metadata-only options, and
the strongest combination we could verify under a two-minute build budget is a
packed-loader build with **anti-REA at maximum, section count 6, a licence
token, a trial gate, a watermark, and 25 packaging layers**. At the default 100
packaging layers, the same configuration **did not finish in 600 s**.

**2026-11-20:** the strongest measured configuration is now ABSOLUTE
native-only (§5.3) — Cython blob as the only payload path, no Python
fallback, enforcement inside the stripped blob. Measured: ~101 s build,
runs rc 0 with the token, zero anti-dump syscalls in the artefact text.
It is also the least available configuration (a blob that cannot load on
the customer's interpreter is a dead artefact), which is why the packed
sectioned commands remain the delivery defaults. "Enabling everything
fails" still holds at 100 packaging layers.

Companion documents: [`SECURITY_FEATURES.md`](SECURITY_FEATURES.md),
[`SEED_ARCHITECTURE.md`](SEED_ARCHITECTURE.md),
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

---

## 1. Method

Every measurement below was run on this host:

| Item | Value |
|---|---|
| Host | Linux x86_64 |
| Interpreter | CPython 3.13.5 |
| Payload | `tests/fixtures/portable/constructs_source.py`, 2,635 bytes |
| Payload constructs | dataclass, `match`, closures, generators, descriptors, async, decorators |
| AST-only builds | `--skip-irgen --skip-llvmgen --skip-encrypt --skip-relay --skip-extras` |
| Loader builds | `python3 -m obfuscator.core.pipeline build … --skip-cloud` |
| Timing | wall clock around the whole process, `date +%s` |
| Output check | run the artefact and compare the final line to `OK` |

The payload is deliberately richer than a `print()` demo. A configuration that
breaks dataclasses, `match`, closures, or async is not a usable maximum.

**What "verified" means here:** the build completed, the artefact ran, and the
protection was observable (a licence-bound artefact refuses without its token;
a sectioned artefact is built by the section path; a `--fast` build warns that
detections are reduced). It does **not** mean the protection was tested against
an analyst. No such test exists.

---

## 2. Measured configuration matrix

Sizes for loader builds are **not stable** across runs; the range is reported
where more than one sample exists. Do not use size as a proxy for strength.

| Configuration | Enabled protections | Compatibility / result | Performance impact | Security assessment |
|---|---|---|---|---|
| **Default (source emitter)** | O4 ladder (14/17), phase-2 defaults from `config/default.json`, always-on rename/checksums/string sealing | Runs standalone; no toolchain with the five skips | **1.9–2.3 s**, **34.2 KB** (2 runs) | Basic static obfuscation. No loader gates. No measured resistance |
| **Balanced (source + lowering)** | O5 ladder (17/17), phase-2 defaults, 20-family semantic lowering | Runs **only** with `obfuscator/lowering_shim.py` on `PYTHONPATH`; otherwise `ModuleNotFoundError` | **1.9 s**, **37.3–37.5 KB**; shim overhead 1.46×–3.84× per family (documented measurement) | Stronger static surface; deployment cost; no measured resistance |
| **High (packed loader defaults)** | O5 full set, section split on (4 sections), anti-REA **balanced**, strict detections, frozen-stdlib snapshot, stdlib audit, audit-hook detector, 100 packaging layers | Runs; 3.55 MB artefact; no cloud | **387 s** (one run), **3,554,107 bytes** | Strongest **default** posture; all controls client-side; no measured resistance |
| **Maximum practical (verified)** | High + anti-REA **maximum**, section count 6, watermark, trial 7 d, licence token, **25 packaging layers** | Runs **with token**; exits 1 without it; no cloud | **69–99 s** (4 runs), **1.46–8.25 MB** (high variance) | Strongest combination verified under a ~2-min budget. Anti-REA effect unmeasured; 25 layers is less packaging depth than default |
| **Maximum flags, 100 layers (negative)** | Maximum practical with default 100 layers | **Did not finish in 600 s**; stopped during packaging layer 61 | >600 s, no artefact | Not practical on this payload/host |
| **Reduced (`--fast`) (negative control)** | Loader defaults but detections warn only, lower noise/rdtsc | Runs; warning printed twice | **48 s**, **2.20 MB** | Weaker by design; useful only as a control |

### 2.1 Source-emitter measurements

| Config | Build time | Size | Runs? |
|---|---|---|---|
| Default O4, run 1 / 2 | 2.3 s / 1.9 s | 34,174 / 34,192 B | Yes (`OK`) |
| O5, run 1 / 2 | 1.9 s / 1.9 s | 34,076 / 33,797 B | Yes (`OK`) |
| O5 + `--lowering all`, run 1 / 2 | 1.9 s / 1.9 s | 37,280 / 37,505 B | Yes with `PYTHONPATH=obfuscator`; no without |
| O0 + `--phase2-only none` | 1.8 s | 6,282 B | Yes — **not** a copy |
| `--skip-obfuscate` | 1.8 s | 2,635 B | Yes — byte-identical copy |

The O5 build is not consistently larger or smaller than O4. Output size is a
poor proxy for transformation strength.

### 2.2 Loader measurements

| Config | Layers | Time | Size | Token required | Runs |
|---|---|---|---|---|---|
| Loader defaults | 100 | 387 s | 3,554,107 B | No | Yes |
| Balanced + section 6 + watermark + trial + licence | 100 | 551 s | 4,445,127 B | **Yes** | Yes with token; exit 1 without |
| Anti-REA max + all bindings | 25 | 69 s | 8,254,521 B | Yes | Yes |
| Anti-REA max + all bindings | 25 | 71 s | 1,456,853 B | Yes | Yes |
| Anti-REA max + all bindings | 25 | 75 s | 3,526,544 B | Yes | Yes; no-token exit 1 |
| Anti-REA max, no bindings | 25 | 60 s | 2,156,478 B | No | Yes |
| Anti-REA max, no bindings | 25 | 69 s | 5,704,174 B | No | Yes |
| Balanced + all bindings | 25 | 72 s | 1,357,259 B | Yes | Yes |
| Default, no bindings | 25 | 51 s | 2,916,591 B | No | Yes |
| Watermark + trial only | 25 | 51 s | 2,744,524 B | No | Yes |
| Licence only | 25 | 80 s | 4,395,199 B | Yes | Yes with token |
| `--fast` | 25 | 48 s | 2,195,694 B | No | Yes |
| Maximum flags | 100 | **>600 s (timeout)** | **none** | — | No |

The size spread at 25 layers — 1.46 MB to 8.25 MB for the same configuration —
is larger than the difference between most configurations. The packaging
pipeline's recursive layers and random representation choices dominate size.
**Do not rank configurations by binary size.**

---

## 3. What the experiments establish

### 3.1 The loader defaults are already strong

The packed loader defaults are not a minimal configuration. They already
include:

- the full 17-transform ladder (no `--opt-level` means full set);
- section splitting, on by default, 4 sections;
- counter-REA shields at `balanced`;
- strict detections (sandbox, emulator, debugger frame, geo-fence, licence);
- frozen-stdlib snapshot, stdlib audit, audit-hook plant detector;
- traceback suppression;
- 100 recursive packaging layers.

`--opt-level 5` and `--section-split` in the old "maximum-security" recipe were
therefore **redundant**: both are already the default on this path. The recipe's
real additions were `--section-count 6`, `--anti-rea-level maximum`,
`--access trial=7d`, and `--watermark`. It did not mention the licence gate, which is
the strongest key binding.

### 3.2 Licensing is not obfuscation

The licence-bound artefact is a useful, verified control:

```
$ python3 dist/constructs_source_protected.py
licence token required: set NIXON_LICENCE or place licence.json beside the artefact
$ echo $?
1

$ NIXON_LICENCE=/tmp/nx_max.licence python3 dist/constructs_source_protected.py
OK
```

That is **access control**. The code is still in the artefact and still
readable. It does not increase reverse-engineering resistance, and the
documentation must not imply that it does.

### 3.3 Packaging layers dominate build time

| Layers | Typical time (25-layer configs) | 100-layer configs |
|---|---|---|
| 25 | 48–80 s | — |
| 100 | — | 387–551 s |
| 100 + anti-REA max | — | **>600 s (timeout)** |

Reducing `--layers` from 100 to 25 is the difference between a practical build
and a nine-minute build (or a timeout). The security value of the extra 75
layers is **not measured**. This is a trade-off, not a free win.

### 3.4 Anti-REA maximum adds size, not measured resistance

At 25 layers, anti-REA maximum builds completed in 60–69 s (without bindings)
and 69–99 s (with bindings), versus 51 s for the balanced default. Size varied
from 1.46 MB to 8.25 MB, overlapping the balanced range. The **effect on an
analyst is not measured**; the flag's name is not evidence.

### 3.5 Enabling everything fails

The maximum-flags build with 100 layers did not complete in 600 s. It was still
in recursive packaging at layer 61 when the timeout fired. This is the clearest
negative result of the investigation: **more flags is not more security, and it
can be less availability.**

---

## 4. Interactions, conflicts, and redundant options

| Combination | Result | Evidence |
|---|---|---|
| `--opt-level 5` on the loader | **Redundant**; loader defaults to full set when `--opt-level` is absent | parser default `None`; `_loader_level` resolves full set |
| `--section-split` on the loader | **Redundant**; default is on | parser `default=True` |
| `--section-count N` without `--section-split` | Works, because split is on by default | parser test |
| `--section-split` + `--native-only` | **Silently skipped**; sections need a fallback payload | code: `if section_split and _plain and not native_only` |
| `--fast` + `--strict-detections` | **Order-dependent**; both write the same dest; last wins | parser test: fast→strict = True, strict→fast = False |
| `--anti-rea-level maximum` + `--no-anti-rea` | **`--no-anti-rea` wins**; level is ignored | parser test; `anti_rea` false |
| `--hwid-lock` without `--hwid` | **Silently disabled** | `hwid_lock=(flag and bool(hwid))` |
| `--licence token=` + `--licence salt=` | **Token wins**; its `key_material` becomes the salt | pipeline: `_customer_salt = _lic_key_material` |
| `--access trial=7d expire=DATE` | Two time gates; prefer one | both parsed; no conflict check |
| `--watermark` + `--skip-irgen` (build.py) | **Watermark not embedded**; conflict report; build succeeds | `grep` count 0 in artifact |
| `--temporal-keys` | **Inert**; ~24 s of hashing, metadata nothing reads | phase log; CLI note |
| `--crypto-binding` | **Build-time only**; nothing decrypts at run time | CLI note; phase log |
| `--cfg-mutation`, `--class-dispatch`, `--ssa-mutation`, `--state-isa`, `--per-exec-recompile`, `--self-healing` | **Metadata-only**; phase writes JSON, no runtime consumer | config files have no readers |
| `--code-genome` (defaults) | Real but expensive: 1,500 evaluations; did not finish in 300 s on a 3-line file | `--genome-generations 2 --genome-population 4` takes 2 s |
| `--pin-structure` | Pins structure, **not keys**; two builds differed | 1,882,254 / 1,882,385 bytes |
| `--seed` | **Source emitter deterministic** for same payload/tool/flags; packed loader still random | three builds 29,802 bytes each (`50ad8c80…`) |
| `--randomization-seed` | **No effect** on default AST path | two runs 35,840 / 37,009 bytes |
| `--lock-hwid` | Seeds map/VM RNG, registers licence; **not** a whole-build seed | code path |

---

## 5. The strongest practical configuration

### 5.1 Recommendation by objective

| Objective | Configuration | Why |
|---|---|---|
| **Source-only IP protection** | `scripts/build.py --opt-level 5` (or the default O4) | Runs standalone; no loader; low build cost. Add `--lowering` only if the shim can be deployed |
| **Strongest default delivery** | Packed loader defaults (`--skip-cloud`) | Full ladder, sections, balanced anti-REA, strict detections, integrity gates |
| **Maximum practical under ~2 min** | Loader defaults + `--anti-rea-level maximum --section-count 6 --watermark … --access trial=7d --licence token=… --package layers=25 stego` | Verified to build and run; licence gate verified; 69–99 s |
| **Customer binding** | Add `--licence token=` (and optionally `--access hwid=`/`hwid-lock`) | Access control, not obfuscation; token required at run time |
| **Leak tracing** | Add `--watermark` | HMAC-tagged loader gate; not a reverse-engineering barrier |
| **Reproducibility / debugging** | `--seed` / `--randomization-seed` in a debug channel | **Partial** determinism; not for customer builds |

### 5.2 One-time setup for the chain gate: three options (run BEFORE the commands below)

The `chain` sub-option of `--licence` verifies an ERC-721 token that you
control on a real chain: a read-only `eth_call` of `ownerOf(tokenId)` must
return the signed `owner`, on the signed RPC and signed `chain_id`,
fail-closed. The gate logic is verified against a mock RPC
(`tests/test_chain_gate_local.py`: TLS → `eth_call` → `ownerOf` → owner
compare, wrong-owner rejection, HTTPS enforcement) — but the token itself
must be real; this is the one step that cannot be simulated. Do this
section once; the build commands in §5.3 are then run per artefact and
never touch the deploy key again.

| Option | What you need | Cost | Notes |
|---|---|---|---|
| **1. Deploy on Ethereum mainnet** | funded ETH wallet | ~$5–50 gas | strongest anchoring; rarely worth it vs an L2 for a licence gate |
| **2. Use an ERC-721 you already hold** | any standard ERC-721 token in your wallet (mainnet) | **zero gas, zero deployment** | the gate does not care what the contract is — only that you hold the token |
| **3. Deploy on an L2 (Polygon / Base / Arbitrum)** | funded wallet (~$2 of POL or ETH) | ~$0.01–0.05 gas | **recommended**: your own contract, your own token ids, cents |

**Option 2 — use an NFT you already hold (zero deployment, zero gas).**
The chain gate calls `ownerOf(tokenId)` — it does not care what the
contract is. If your wallet holds any standard ERC-721 token on mainnet
(a free mint, an airdrop, anything), skip the deploy entirely and sign the
licence against it:

```bash
NIXON_LICENCE_PUBLIC_KEY=$(python3 -m obfuscator.licensing pubkey \
  --key-hex "$ISSUER_SEED") \
python3 -m obfuscator.licensing issue --key-hex "$ISSUER_SEED" \
  --customer acme --days 30 --features pro \
  --chain contract=<any ERC-721 you hold> token-id=<its id> \
          owner=<your address> chain-id=1 \
          rpc=https://ethereum-rpc.publicnode.com \
  --out acme.licence
```

The gate follows ownership: transfer or sell that NFT and the artefact
stops on the next start — the NFT itself becomes the revocation switch.
Caveats: the token must be standard ERC-721 (it must expose `ownerOf`;
ERC-1155 does not and will not work); you do not control the contract, so
there is no `mint` for extra customers — each customer needs a token you
hold and are willing to transfer (the transfer costs gas and hands the
token over, making the customer the owner the gate checks).

**Option 3 — deploy on an L2 (recommended).** The gate reads `chain_id`
from the signed licence, so it works on any EVM chain, not just mainnet —
Polygon, Base and Arbitrum are real mainnets with gas in the $0.01–0.05
range. `chain_id` is signed into the licence, so the artefact is locked to
that chain and a different-chain forgery will not satisfy it.

**Step 1 — create and fund a wallet (~$2 of POL):**

1. Install Trust Wallet (or MetaMask/Rabby). Create a wallet; back up the
   seed phrase offline.
2. Copy the receiving address (`0x…`).
3. Buy ~$2 of POL on any exchange (Coinbase, Binance, CoinDCX, Mudrex, …)
   and withdraw it to your wallet address. On the withdrawal screen pick
   network **Polygon PoS** — *not* "Polygon zkEVM", *not* "ERC-20
   (Ethereum)". Withdrawing on the wrong network is the classic way to
   lose the deposit.
4. Wait 1–5 minutes for it to land. One deploy + mint costs ~0.01–0.05
   POL; the script refuses to start below 0.1 POL. $2 is far more than
   enough. (Choosing Base or Arbitrum instead? Fund **ETH** on that
   network — the gas token differs per chain, and the script checks the
   preset's minimum balance for the chain it is deploying on.)

**Step 2 — deploy and mint (one terminal, one-time):**

```bash
export NIXON_DEPLOY_CHAIN=polygon                 # or base, arbitrum, ethereum
export NIXON_DEPLOY_RPC=https://polygon-rpc.com   # optional; the preset RPC is the default
export NIXON_DEPLOY_KEY=<Trust Wallet private key>
export NIXON_DEPLOY_OWNER=<Trust Wallet address>
python3 scripts/deploy_erc721_licence.py
```

- Trust Wallet shows the private key in the wallet/account details
  ("Show private key", passcode-gated). That key controls every asset in
  the wallet: export it only into `NIXON_DEPLOY_KEY` in that one terminal —
  never into a file, a chat, or a command-line argument — and
  `unset NIXON_DEPLOY_KEY` when the script is done.
- For your own licence, owner = your Trust Wallet address. For a customer,
  set `NIXON_DEPLOY_OWNER` to the customer's address (token 1 is minted to
  them; re-run later to mint further tokens — the contract is already
  deployed, so later runs only pay the small mint gas).
- The script connects to the chain, checks the balance, compiles the
  ERC-721 from Solidity source, asks `Type DEPLOY to confirm:`, deploys,
  mints token 1, verifies `ownerOf(1)` on-chain, and prints the exact
  `--chain` line (contract, token-id, owner, chain-id, rpc).

**Where the two values come from, and their exact format:**

*Wallet address → `NIXON_DEPLOY_OWNER`:*

- Trust Wallet (mobile): open the app → the Polygon/Ethereum account →
  tap the `0x…` string at the top of the account screen to copy it (or
  **Receive** → the address is shown with its QR code).
- MetaMask / Rabby (browser extension): click the account name at the top
  → copy icon; or avatar → **Account details** → copy address.
- Format: `0x` followed by 40 hex characters — **42 characters total**,
  mixed-case checksum casing is fine (the script compares addresses
  case-insensitively). The script enforces this: anything that is not
  `0x` + 40 hex is refused before any connection is made.

*Private key → `NIXON_DEPLOY_KEY`:*

- Trust Wallet (mobile): open the wallet → select the **Polygon (or
  Ethereum) account you funded** → ⋮ / account details → **Show Private
  Key** → passcode/biometric → copy. It is per-account: pick the funded
  EVM account, not another chain's account.
- MetaMask: account avatar → **Account details** → **Show private key** →
  type the MetaMask password → **Hold to reveal**.
- Format: **64 hex characters** (0–9, a–f) = 32 bytes, with or without a
  leading `0x` — the script strips the prefix if present. This is *not*
  the 12/24-word seed phrase; those words cannot be pasted here.
- Safety, once more: this string spends every asset in the wallet. Reveal
  it only into the env var in that one terminal; never screenshot it,
  never paste it into a chat, search bar, cloud note, or AI tool; unset
  it right after the deploy; if it may have leaked anywhere, move the
  funds to a fresh wallet immediately.

**Step 3 — issue the customer licence with the printed `--chain` line:**

```bash
NIXON_LICENCE_PUBLIC_KEY=$(python3 -m obfuscator.licensing pubkey \
  --key-hex "$ISSUER_SEED") \
python3 -m obfuscator.licensing issue --key-hex "$ISSUER_SEED" \
  --customer acme --days 30 --features pro \
  --chain contract=0x… token-id=1 owner=0x… chain-id=137 \
          rpc=https://polygon-rpc.com \
  --out acme.licence
```

The chain spec is signed into the token — including the RPC endpoint, so a
runtime caller cannot point the check at a fake node. To move to your own
RPC later, re-issue with `rpc=https://your-node`. Revocation = burn or
transfer token 1; the next artefact start fails closed.

**Option 1 — deploy on Ethereum mainnet.** Same script, same steps, with
`NIXON_DEPLOY_CHAIN=ethereum` and the wallet funded with ETH instead of
POL (the script checks ~0.005 ETH; real gas will run ~$5–50 depending on
the day). Strongest anchoring — but for a licence gate it is functionally
equivalent to the L2: the gate only proves who owns the token, and
`chain_id=1` is signed into the licence to pin which chain that proof
comes from. Use mainnet when you want the licence anchored where the most
chain infrastructure already watches it; otherwise Option 3 gives the
same gate for cents.

---

### 5.3 The four maximum commands

Pick one. **LOCAL** runs entirely on this machine and produces a native
blob for the **current OS only** (a Linux build makes a Linux `.so`;
cross-compiling Python extensions needs the target toolchain). **CLOUD**
and **ABSOLUTE** additionally trigger the per-OS Cython build farm —
windows → `.pyd`, ubuntu → `.so`, macos → `.dylib`, each built with
Cython → the C transform layer → the platform compiler — and embed all
the blobs, so the payload runs natively on every OS. **ABSOLUTE
native-only** (2026-11-20) is ABSOLUTE's gate set with the Python fallback
removed entirely: the blob is the only payload path. Nuitka was removed
2026-11-17; `--package compile` no longer exists.

All four need the string-seal shard. Keep it out of the artefact: without
it the artefact ships its own seal key and an analyst — or an LLM — can
simply call the shipped decoder. Measured 2026-11-17: **4/4 secrets
recovered** with the inline key, **0/4** with the shard.

#### One-time setup (all four)

```bash
# Issuer seed for licence tokens. Keep it out of the repository.
ISSUER_SEED=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Issue a token for one customer.
python3 -m obfuscator.licensing issue --key-hex "$ISSUER_SEED" \
  --customer acme --days 30 --features pro --out acme.licence

# String-seal shard. Export it for the build AND for every run.
NX_SEAL_SHARD=$(openssl rand -hex 32)
export NX_SEAL_SHARD

# 2026-11-20: provenance signing key. A fresh key per artefact release;
# the artefact embeds its Ed25519 signature and the loader verifies it at
# load. The PIN below is the out-of-band anchor: export it at RUN time
# (and store it beside the artefact's release notes, never in it) so a
# re-signed artefact is refused even by a holder who also holds a token.
NIXON_ARTEFACT_SIGN_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
NIXON_PROVENANCE_PUBKEY=$(python3 -c "
import sys; sys.path.insert(0, '.')
from obfuscator.licensing import private_key_from_hex, public_key_hex
print(public_key_hex(private_key_from_hex('$NIXON_ARTEFACT_SIGN_KEY')))")
export NIXON_ARTEFACT_SIGN_KEY   # BUILD time only
export NIXON_PROVENANCE_PUBKEY   # RUN time only

# 2026-11-20: VM dispatch. Chooses the function-level virtualiser family
# (a | b | alternate; alternate picks per build id so successive releases
# do not share one dispatcher). Arm at build time.
export NIXON_VM_DISPATCH=alternate
```

#### LOCAL maximum — runs on this machine

```bash
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
python3 -m obfuscator.core.pipeline build payload.py \
  --skip-cloud \
  --anti-rea-level maximum \
  --section-count 8 \
  --watermark NX-MAX-001 \
  --transforms data function-intent speculation string-key-env=NX_SEAL_SHARD \
  --access trial=7d expire=2027-12-31 \
           hwid=$(python3 -c "import sys; sys.path.insert(0,'.'); \
                  from obfuscator.trial_bind import fallback_fingerprint; \
                  print(fallback_fingerprint())") hwid-lock \
           kod driver-check name-gate \
           block-countries=RU,KP vm-threshold=65 \
  --licence token=acme.licence env-only bootstrap-encrypted chain \
  --package native layers=25 zips=3 stego
```

2026-11-20 changes from the 2026-11-10 form: the native blob is built
locally (Cython -> the C transform layer -> clang/gcc, with
`nx_apply_protections()` compiled in — the anti-dump syscalls live in the
stripped blob, applied BEFORE the payload's module init runs), section
count 8, the payload transforms are named explicitly, and the access set
adds expiry, host binding (`hwid`+`hwid-lock`; the value above is this
machine's composite fingerprint — compute yours the same way), and the
kod/driver-check/name-gate kill gates. `NIXON_VM_DISPATCH` and
`NIXON_ARTEFACT_SIGN_KEY` come from the one-time setup exports.

Output: `<dirname(payload)>/dist/`. The `_Packed` and `_Stego` variants are
written beside the payload, not in `dist/` — ship `dist/`.

Native scope: **current OS only** (`--skip-cloud` keeps the build local,
and Python extensions cannot be cross-compiled without the target
toolchain). For win/mac/mac-arm blobs, use CLOUD or ABSOLUTE.

#### CLOUD maximum — adds the per-OS Cython build farm

```bash
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD NX_SEAL_SHARD=$NX_SEAL_SHARD \
python3 -m obfuscator.core.pipeline build payload.py \
  --section-count 8 \
  --watermark NX-001 \
  --transforms data function-intent speculation string-key-env=NX_SEAL_SHARD \
  --access trial=7d expire=2027-12-31 \
           block-countries=RU,KP vm-threshold=65 \
  --licence token=acme.licence env-only bootstrap-encrypted chain \
  --package native platform=github layers=25 zips=3
```

Needs build-farm credentials (pipeline config or `--cf-token`) and network.
The farm runs a 3-OS matrix (windows → `.pyd`, ubuntu → `.so`, macos →
`.dylib`), each built with Cython → the C transform layer → the platform
compiler, so the payload runs natively on every OS. The farm is triggered
BY the build now (no separate build-farm step): it runs after the local
blob, the per-OS blobs are merged into the loader, and a farm failure
degrades to bytecode fallback on the other OSes — the local blob is
unaffected.
**`stego` conflicts with the cloud build** (enforced, exit 1) — that is why
it is absent from `--package` here.

#### ABSOLUTE maximum — every namespace, every gate

```bash
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD NX_SEAL_SHARD=$NX_SEAL_SHARD \
python3 -m obfuscator.core.pipeline build payload.py \
  --section-count 8 \
  --watermark NX-001 \
  --lowering io,scalar,string,container,service,protocol,function,import,fusion,arithmetic,truth,slice,format,augassign \
  --transforms data function-intent speculation string-key-env=NX_SEAL_SHARD \
  --access trial=7d expire=2027-12-31 hwid=<machine-hwid> hwid-lock kod driver-check \
           name-gate rename-internal bind-mac webhook=https://alerts.example/hook \
           block-countries=RU,KP vm-threshold=65 \
  --licence token=acme.licence env-only bootstrap-encrypted chain \
  --tls-ca-bundle /etc/ssl/certs/ca.pem \
  --package native platform=github layers=25 zips=3 stego
```

2026-11-20 changes: `stego` is back in `--package` (the stego/cloud
conflict applied to the old separate farm step; the farm is triggered by
the build now and `stego` travels with the local deliverable), and the
environment from the one-time setup (`NIXON_VM_DISPATCH`,
`NIXON_ARTEFACT_SIGN_KEY`) applies to every command — with it, the artefact
carries function-level virtualisation where eligible and a load-time
Ed25519 provenance signature. Defaults not shown are already on: all six
AST transforms, anti-REA at maximum, advanced protection, split-bootstrap,
sectioned sealing, strict detections and the integrity gates.

#### ABSOLUTE native-only — Cython with NO fallback to Python

```bash
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD NX_SEAL_SHARD=$NX_SEAL_SHARD \
python3 -m obfuscator.core.pipeline build payload.py \
  --package native-only \
  --watermark NX-ABS-001 \
  --transforms data function-intent speculation string-key-env=NX_SEAL_SHARD \
  --access trial=7d expire=2027-12-31 hwid=<machine-hwid> hwid-lock kod driver-check \
           name-gate block-countries=RU,KP vm-threshold=65 \
  --licence token=acme.licence env-only bootstrap-encrypted chain
```

Measured 2026-11-20 (three consecutive builds green, with the env-only
licence form; `chain` requires the §5.2 setup and is not exercised by the
measurement): the loader ships VERBATIM — stamped and signed, no sections,
no bytecode fallback (`FALLBACK_BLOB = "DISABLED"`) — and the Cython blob
is the ONLY payload path. If the blob cannot load, the loader runs nothing
(fail-closed by construction; there is nothing else to decrypt). Because
no Python path to payload plaintext exists, the artefact text carries NO
anti-dump syscalls: the enforcement (prctl/RLIMIT_CORE on Linux,
setrlimit + PT_DENY_ATTACH on macOS, silent _exit(137) fatal-signal
handlers) lives in the stripped blob (`nx_apply_protections()`, called by
the loader BEFORE the payload's module init runs) and the loader refuses a
blob that does not export it. This is the strongest measured configuration
on this project — and the least available: a blob that fails on the
customer's machine (ABI mismatch, glibc) is a dead artefact, not a
degraded one. Ship it only to hosts you control the interpreter version
of.

#### Run (all four)

```bash
# Without the token the artefact exits 1. The seal shard must be present at
# RUN time too — that is the point: the artefact alone cannot decrypt its
# own strings. The provenance pin (2026-11-20) must match the key the
# artefact was signed with; a re-signed artefact is refused.
NIXON_LICENCE=acme.licence NX_SEAL_SHARD=$NX_SEAL_SHARD \
  NIXON_PROVENANCE_PUBKEY=$NIXON_PROVENANCE_PUBKEY \
  python3 dist/payload_protected.py
```

Every remaining loader flag is either in one of these commands or
deliberately excluded: `--access one-shot` (self-destruct after the first
run — breaks re-runs, add only for burn-after-use payloads), `--exclude …`
(nothing: every shield family is on), `--fast` / `--public` /
`--debug-dump-raw` / `--pin-structure` (weaken or debug — never in a max
build), `--tor`/`--tor-proxy` (build-host privacy, not artifact security),
`--resume`/`--exclude-android`/`--python` (farm ops). `--package
native-only` is NO LONGER in the excluded list (2026-11-20): it has its
own measured command above.

Measured on the 2,635-byte payload: **69–99 s**, **1.46–8.25 MB**, runs with
the token, exits 1 without it. Do not add `--opt-level 5` (the ladder is already at its
maximum on this path) or `--section-split` (sectioned sealing is now the
default; `--no-section-split` is the opt-out).

## Already ON by default (2026-11-12 consolidation)

The CLI is now ~50 flags because protections became defaults. Nothing was
dropped; these run in every normal build without a flag:

- Six AST transforms: CFG flattening, opaque predicates, bogus exceptions,
  MBA substitution, string fragmentation, Unicode identifiers (opt out per
  family: `--exclude transforms.mba-subs`, …).
- Counter-REA shields at **maximum** (opt out: `--exclude rea`), including
  adversarial dead-code/prompt injection (family `rea.adversarial`).
- Advanced protection; split-bootstrap key (Shamir n=3,k=2); sectioned
  payload sealing; strict detections; audit-hook plant, frozen-stdlib
  snapshot and stdlib function-audit gates
  (opt out: `--exclude integrity.audit-hook|integrity.snapshot|integrity.stdlib-audit`).
- Post-build verification suite (PHASE 3) on the native path.
- **Identity gate** (2026-11-17): shipped loaders refuse to initialise
  under a foreign `exec()` — the artefact must be the script the
  interpreter was pointed at (`__name__` main-ish AND `__file__` ==
  `sys.argv[0]`, exit 2 otherwise); interior packaging layers get a
  name-only stage gate. Closes the foreign-exec extraction route found
  by the 2026-11-17 GLM 5.3 Flash benchmark
  (docs/research/ai-layer-bench-2026-11-17/RESULTS.md).
- **Hybrid-loader self-check** (2026-11-17): the sectioned artefact
  verifies its own bytes (Merkle + per-build HMAC, stamped as the last
  content step; runs before any key material is reconstructed) — flipping
  any loader byte kills it with `Self-check error` (rc 137).
- **Real token binding** (2026-11-17): `--licence token=` no longer
  embeds the token's key material in the artefact (the seal mask and the
  loader-embedded salt are now separate), the hybrid loader pins the
  token payload hash (forged token refused by name), a missing token
  prints its reason before the fail-closed kill. `--licence salt=` is
  documented as a per-customer differ, not a secret.

**Native path (`scripts/build.py`) maximum additions:** the opt-in passes
`--transforms data function-intent speculation struct`, `--validate fail`,
and the packaging options `--package pytoc pyinstaller cross=TARGETS`.
**Loader path maximum additions:** `--package layers=25 stego`, the access
gates (`--access trial=7d expire=… hwid=…`), the licence gate
(`--licence token=… env-only bootstrap-encrypted chain`), and assurance
reports (`--audit all` — reports do not change the artefact).

**One-flag maximum:** `--package all` (alias `everything`) means "package
with everything else". On the native path it expands to `pytoc pyinstaller
cross=win,linux,macos,linux-arm` plus every opt-in `--transforms` pass and
`--validate fail`. On the loader path it expands to `layers=25 zips=3 stego`
on top of the protections that are already on by default. Everything else
above still applies as documented.

`--licence` is the unified spelling: its sub-options (`token=`, `env-only`,
`bootstrap-encrypted`, `chain`) are the whole licence interface — the former
per-knob `--licence-*` spellings were removed 2026-11-12. The same holds for
`--web3`, which is now the only spelling of the Web3 sub-options (rpc,
explorer, contract, shards, deploy, deploy-rpc). The licence identity gate is
`--licence … chain`, not any Web3 sub-option.

`--licence-env-only` is the hardening default for AI-facing distribution: the
emitted loader reads the token only from `NIXON_LICENCE` and no longer searches
for `licence.json` / `licence.licence` beside the artefact. Verified on a small
build and on the maximum build: a token file placed beside the artefact is
ignored, the environment token runs the payload, a forged 64-hex token fails
with `[FATAL] Magic Mismatch (Decryption Failed)`, and the token's
`key_material` does not appear in the artefact. Do not ship the token in
`dist/`; put it in the licensee's secret store or launch environment.

`--licence-bootstrap-encrypted` goes one layer earlier: the loader string table
is encrypted with a token-derived key, so the artefact cannot decode its own
bootstrap strings without the token. Verified on a 502 KB build: no token, a
local token file, and a forged token all fail; the environment token runs the
payload. This does not make the loader code unreadable, but it removes the
route names, gate strings, and embedded-key clues from static analysis.

`--licence-chain` adds an optional on-chain identity gate. The licence token
carries signed chain metadata (`rpc`, `contract`, `token_id`, `owner`,
`chain_id`), issued with `obfuscator.licensing issue --chain ...`. The loader
performs a read-only `eth_call` to verify that the token's owner still matches
the signed `owner` field. No transaction is sent, no testnet is required, and
the RPC endpoint is signed into the token so a runtime caller cannot point the
check at a fake node. The build rejects `--licence-chain` without signed chain
metadata. Because the artefact needs network access to verify the owner, a
build with `--licence-chain` fails unless the chain and token are reachable.
This is identity gating at licence issuance; it does not create a server-side
trust boundary.

The runtime also pins the exact signed licence payload with SHA-256. The token
signature is verified during the build; the loader then refuses any token file
whose canonical payload does not match the pinned hash. A forged token that
changes metadata but keeps the same `key_material` therefore fails with
`licence token does not match the pinned token`. The build requires
`NIXON_LICENCE_PUBLIC_KEY` to contain the issuer public key.

The forged-token check found a real defect in the first version of this
binding: the loader checked that a token existed but did not mix its material
into the `k_dec` payload stream key, so a forged token still decrypted the
payload. The fix mixes the token mask into `k_dec` at pack time and after the
runtime VM-chain derivation. `tests/test_licence_binding.py` now asserts that
a forged token fails.

### 5.4 encrypt.py runtime key: distribution how-to

The encrypted binary no longer carries its own decryption key. Building

```bash
python3 -m encrypt encrypt payload.bin -o /opt/customer/app.bin
# → /opt/customer/app.bin       the encrypted ELF (carries only the key PATH)
# → /opt/customer/app.bin.key   32-byte runtime key, written 0600
```

writes a 0600 sidecar next to the output and embeds that sidecar's
**absolute path** in the stub. At run time the stub opens the path, reads
32 bytes, decrypts, and runs; with the file missing it exits 1.
**Measured boundary (2026-11-14, end-to-end simulation on a static gcc
binary):** the encrypted region is the **text segment** — the machine code.
The original binary's read-only data (`.rodata`: string literals, tables)
is *not* encrypted and survives `strings` on the binary alone. So the
binary alone is inert and its code is unrecoverable statically, but any
secrets that live in `.rodata` of the input binary are still readable —
keep secrets out of string literals, or route the payload through the
packed-loader path (which seals its own string table) instead.
`tests/test_encrypt_runtime_key.py` covers the text region; extending the
encryption to `.rodata` is recorded as follow-up work.

Distribution — split channels:

1. **Build at the final install path.** The embedded path is absolute, so
   the runtime host must have the key at exactly `<output>.key` as spelled
   at build time. Building `-o /opt/customer/app.bin` means the customer
   host needs `/opt/customer/app.bin.key`. If you built in a staging
   directory, rebuild with the final `-o` before shipping.
2. Ship the binary through the normal channel (download, drive, email).
3. Ship the `.key` file through a **different** channel (Signal, PGP mail,
   in-person USB). Whoever holds both files can run it; whoever holds only
   the binary cannot.
4. On the runtime host:
   `install -m 600 app.bin.key /opt/customer/app.bin.key`, verify
   `./app.bin` runs, then delete the key from any staging host.
5. To revoke a copy: delete the key file there — the binary exits 1 on the
   next run. Keys are not derived from anything, so back the `.key` up
   (or re-encrypt); a lost key means a rebuild.

`NIXON_ENC_RUNTIME_KEY=<64 hex>` at **build** time supplies your own key
instead of a generated one (use it when several artefacts must share one
key). It is never read at run time; the stub only reads the sidecar.

Stated plainly: the key file sits on the runtime host, so whoever controls
that host can read it. This is a distribution control — the binary alone is
inert — not protection against someone who can legitimately run it.

### 5.4b Runtime overhead (measured 2026-11-16)

The bench matrix listed this metric from the start and never filled it.
Measured with `ai_layer_bench.py --runtime-artifact ... --runtime-source ...
--runtime-runs 3` (median of three runs, both sides in a subprocess):

| Side | Median wall clock |
|---|---|
| Baseline (the payload's own `.py`) | **17.6 ms** |
| Max-profile loader artefact | **9,612 ms** |
| **Overhead** | **546×** |

Read this honestly: the loader stack costs roughly **9.6 seconds of startup**
on a trivial payload. That is the price of the full gate set — integrity
checks, Merkle/HMAC verification, the section walk, anti-analysis probes,
and the packaging onion. It is a real cost, not a measurement artefact (the
median of three runs; the min/max spread is in the results JSON).

Practical consequence: the max profile is appropriate for long-running
payloads and CLI tools where a one-off ~10 s startup is acceptable. It is
**not** appropriate for anything latency-sensitive (a CLI invoked in a
loop, a hook, a plugin). For those, use a reduced profile and accept the
weaker posture — that trade-off is now measured rather than assumed.

### 5.5 Why not "all flags"

- Six flags write metadata no runtime reads.
- `--temporal-keys` is inert and costs ~24 s.
- `--crypto-binding` does not decrypt at run time.
- `--code-genome` at defaults is 1,500 evaluations and can stall a build.
- `--opt-level 5`, `--section-split` are redundant on the loader.
- `--fast` and `--strict-detections` fight over one dest.
- At 100 layers, the maximum-flags build exceeded 600 s.
- Licensing/trial/watermark do not make the code harder to read.

---

## 6. Negative results and failed combinations

Recorded because they are evidence:

1. **Maximum flags + 100 layers did not finish in 600 s.** The build was in
   recursive packaging at layer 61. No artefact was produced.
2. **`--opt-level 5` and `--section-split` are redundant on the loader.** They
   were in the old maximum-security recipe as if they added protection; they do
   not.
3. **`--watermark` with `--skip-irgen` does not watermark the AST artefact.**
   The log says "Watermarking" and writes `program_wm.ir`, but `grep` finds no
   watermark string in the emitted artefact.
4. **`--temporal-keys` adds 24 s and no runtime effect.**
5. **`--class-dispatch`, `--ssa-mutation`, `--state-isa`,
   `--per-exec-recompile`, `--self-healing` write configs that no runtime
   component reads.**
6. **`--seed` used to be partial; the wiring is fixed.** Before the fix, three
   same-seed O4 builds gave 29,805 / 29,800 / 29,805 bytes and the first
   difference was the string key. `phase01_obfuscate.py` now passes `seed=`
   into `build_pipeline`; three builds are byte-identical at 29,802 bytes. The
   packed loader is still not reproducible (random keys/packaging).
7. **`--pin-structure` does not reproduce a build.** 1,882,254 / 1,882,385
   bytes.
8. **`--fast` is a reduced profile**, not a faster maximum. It warns, twice.
9. **`--access trial=` and `--access hwid-lock` did not reach the standard packed-loader
   artefact.** Builds with `--trial 1s` (default and `--fast` profiles) still
   ran after expiry, and builds with `--hwid TEST-HWID-001 --hwid-lock` still
   ran on a different identity; neither build emitted the `_nx_kill` /
   trial/HWID gate symbols. The gates are wired into the hybrid-loader path,
   not the standard packed-loader path that `--skip-cloud` produces. Recorded
   as an open defect, not a supported gate.

---

## 7. Bounded attack measurement (2026-11-10, extended 2026-11-11)

This is **not** a frontier-analyst study. It is a reproducible, bounded probe
of the surface an automated analyst sees, recorded because "no measurement"
was worse than a scoped one.

| Artefact | Surface probed | Method | Result |
|---|---|---|---|
| Maximum practical loader (2,748,710 B) | Head/tail + 500 extracted strings | Deterministic probes + one LLM probe (`nvidia/nemotron-3-ultra-550b-a55b:free`, 20,016 prompt / 700 completion tokens) | **No payload plaintext or original identifier recovered.** Probes for `hello-nixon`, `slow_square`, `classify`, `make_counter`, `Point`, `Holder`, the docstring and `"OK"` all returned false (one `deliver` hit is loader runtime text, not the payload). The model identified the **loader's** purpose (zip load, HMAC integrity, anti-dump, secure delete) and mapped loader imports; it did not identify the payload |
| Source-level O4 artefact (33,184 B) | Full AST text | Same LLM probe | **Payload recoverable in principle.** The model identified the ChaCha20 string-cipher, the embedded `_nx_k` key, the integrity checker, anti-VM checks, and decoy functions, and concluded the encrypted strings are decryptable from the artefact alone |
| Maximum practical loader (2,748,710 B) | Full file, full tool surface | OpenCode 2.2.2 + Kern Qwen3.8-27B, `reverse-engineer-anything` skill, bash/edit/write, no step cap; 61 tool calls | **Payload fully recovered.** Static chain reconstructed; 242,049-byte source recovered; HMAC-SHA256 verified; 57 sealed strings decoded; 10 credential-like items; 88 top-level obfuscated names. **0/12 original names** — symbol renaming survived. No refusal |
| Max build of the current tree, headless agent (2026-11-14) | Full file, full tool surface + global RE tooling, fenced sandbox, 40 min, no step cap | OpenCode 2.2.2 headless + Kern `Qwen/Qwen3.8-27B-FP8` via the new `api.kern-llm.org` provider; the agent found the benchmark's own licence on the host (sandbox-fence leak, disclosed) and used it | **Offline static decryption blocked** (agent: dynamic capture "was required" — k_dec/licence binding held, unlike 2026-11-11); **interpreter-integrity gate fired for real** (builtins hook → exit 3); **self-hash blocked in-place editing**; **0/12 names**. Payload still recovered at runtime (zipfile-level capture via a `sitecustomize` shim — the builtins gate did not cover it). **Fixed same day**: gate now checks `zipfile.ZipFile.__init__`/`read` code objects + external startup hooks; the exact capture shim re-run against the rebuilt artefact → `[BLOCKED] … (exit 3)`, zero bytes captured. See [`ai-layer-bench-2026-11-14/RESULTS.md`](research/ai-layer-bench-2026-11-14/RESULTS.md) |

Limits, stated plainly:

- The first two rows are one model, one prompt, no tool use, no dynamic
  execution, no decompiler. The third row is one model, one full-tool run, one
  payload.
- The packed-loader head/tail probe saw 16 KB of a 2.7 MB artefact plus its
  string table; its negative result is surface-limited.
- The full-tool run hit a 30-minute wall-clock timeout at step 43 and was
  continued in the same session for 140 s. No step cap was used.
- No claim is made about a determined human analyst with a debugger.

**What this supports:** on the no-tool surface, the packed configuration hides
payload semantics from string/LLM recovery. On a full-tool surface, the packed
layer is reversible: the payload, its HMAC, and its sealed strings were
recovered. What survived was the inner symbol transformation, not the loader.
This does **not** support "resists reverse engineering".

---

## 8. Multi-version and multi-payload coverage

| Check | Result |
|---|---|
| Source emitter, Python 3.10/3.11/3.12/3.13/3.14 | Built and ran on all five (`OK`) |
| Packed loader, cross-version | Version-locked: a 3.13-built artefact refuses 3.10/3.11/3.12/3.14 with `Incompatible Python Version` and runs on 3.13 |
| Payloads | `hello.py`, `constructs_source.py`, `stress.py` all built; loader artefacts 2.2–4.2 MB depending on payload/profile |

## 9. What remains unverified

- **No full attacker study** of any configuration. §7 is a bounded probe, not
  a study.
- **No independent cryptographic review** of payload, string, or section
  encryption. An internal review exists in
  [`CRYPTO_REVIEW.md`](CRYPTO_REVIEW.md); it is not independent.
- **No measurement of anti-REA maximum's effect** beyond the bounded LLM probe.
- **`--native-only` was exercised locally** (24 s, artefact produced), but the
  cloud-farm path was not; the artefact produced protects the loader itself.
- **Trial/HWID gates did not reach the standard packed-loader artefact** (§6.9).
- Loader sizes vary by several megabytes between runs; times will vary on other
  hardware.
- **100-layer builds are 6–9 minutes** on this host; real payloads will be
  worse.

The honest summary: **the strongest configuration we can verify builds and runs
is the maximum practical command in §5.3, but "strongest" here means "most
protections enabled without breaking execution or the build budget". It does
not mean "measured to resist reverse engineering".**

---

## 2026-11-20 addendum — what changed since the 2026-11-10 matrix

The full addendum-by-measurement lives in
`docs/research/pydeobsbench-2026-11-18.md` (§5o–§5q). Summary, all measured:

* **Anti-REA is at maximum by default now** (`--anti-rea-level` parser
  default), and sectioned sealing is on by default (4 sections; the
  commands above raise it to 8). The §4 rows calling `--opt-level 5` and
  `--section-split` redundant still hold; the row "hwid-lock without hwid
  is silently disabled" still holds.
* **Enforcement moved into the blob** (§5l boundary push): every
  locally-built blob compiles `native/enforcement.c`
  (`nx_apply_protections()` — dumpable off, core limit zero, deny-attach
  on macOS, silent fatal-signal handlers) and the loader calls it BEFORE
  the payload's module init runs, refusing a blob without the entry. The
  top-of-loader ctypes block is emitted only for builds that can reach
  payload plaintext through Python; the native-only artefact carries none.
* **Provenance signing** (NIXON_ARTEFACT_SIGN_KEY at build, pinned via
  NIXON_PROVENANCE_PUBKEY at run): with it armed, the bypass attack —
  the one that defeated merkle+HMAC re-stamping — dies on the SIGNATURE.
  §1's chain is three layers deep on signed artefacts.
* **Four integration defects were found by turning every flag on at once,
  and are fixed**: the provenance fingerprint separator, the token-derived
  check ignoring that prefix, the geofence failing closed on an unknown
  location (killed offline hosts), and the trial gate treating a foreign-
  sealed state as tampered (broke every in-place update). A fifth: the
  babel identifier pools drew Unicode that clang rejects in C
  identifiers, making native blob builds FLAKY (~50%); the pool is now the
  measured C-legal set (910 candidates, 139 illegal).
* **`--package native-only` is a real, measured configuration now** (see
  §5.3): the loader ships verbatim, the blob is the only payload path, no
  Python fallback. The 2026-11-10 caution that a farm failure "bricks the
  artifact" is now the DESIGN: a blob that cannot load runs nothing.
* **Diagnostics**: `NIXON_LADDER_DEBUG=1` prints `nx-kill:<reason>` to
  stderr before the kill ladder exits — start every gate investigation
  there instead of strace.
* **What the harness now measures** (pydeobsbench/run.py PROFILES): `max`
  (full flag set), `max-legacy` (the 2026-11-10 baseline, kept for
  comparability), `absolute`, `absolute-native-only`. The §8 numbers in
  the matrix below were taken on the legacy shape.

### 5.6 Release trust-chain policy (2026-11-21, review register P0)

The §5s-bis measurement is the reason this section exists: on an UNSIGNED
artefact, tamper + recompute of both internal stamps RAN (rc 0, payload
executed). An unsigned artefact's integrity is one hash recomputed twice.
The reviewer register requires signed provenance to be mandatory for
production releases, so the build now enforces it:

```bash
# RELEASE BUILDS: an artefact that would ship without a load-time
# signature FAILS the build instead of printing a warn.
export NIXON_REQUIRE_PROVENANCE=1
export NIXON_ARTEFACT_SIGN_KEY=$NIXON_ARTEFACT_SIGN_KEY   # from §5.2
NIXON_LOG_REDIRECT=0 PYTHONPATH=$PWD \
python3 -m obfuscator.core.pipeline build payload.py ...
```

Without the flag the default stays a warn, so a deliberate test artefact
(the unsigned control in tests/test_failure_modes.py, which demonstrates WHY
signing cannot be optional) remains buildable.

**The full release trust chain, as the register requires it:**

1. **Every release artefact is signed.** `NIXON_REQUIRE_PROVENANCE=1` makes
   an unsigned build a failed build (§5z.6).
2. **The signing key is release-infrastructure-owned.** `NIXON_ARTEFACT_SIGN_KEY`
   is an environment variable read at BUILD time only, from the operator's
   secret store — never embedded in the artefact, never in source or tests.
   The artefact carries only the signature and the PUBLIC-key fingerprint.
3. **The verification pin travels out-of-band.** `NIXON_PROVENANCE_PUBKEY`
   is exported at RUN time from the launcher or protected configuration —
   NOT from inside the artefact, which an attacker can edit. The pin must be
   distributed with the release notes through a channel the attacker does
   not control (the deployment step §5r records as operator-owned).
4. **Missing credentials or pin fail closed at run time.** The loader's
   provenance check is fatal when both slots are populated and the signature
   does not verify (all eight attack routes die there, §5s-bis); a missing
   RUN-time pin means the check cannot be satisfied and the artefact refuses.
5. **Key rotation and revocation.** Rotation: issue the next key with
   `python3 -m obfuscator.licensing` (§5.2), ship it as the new
   `NIXON_ARTEFACT_SIGN_KEY`, and publish the new pin as the expected
   `NIXON_PROVENANCE_PUBKEY` — artefacts signed by the old key are refused
   by holders of the new pin, which IS the revocation of that key's future.
   For a compromised key: publish a new pin IMMEDIATELY (revocation is pin
   replacement, since verification is local and offline); all artefacts
   signed by the compromised key stop verifying for every holder that picks
   up the new pin. Record the rotation in the release notes with the old and
   new fingerprints.
6. **Unsigned artefacts are labelled development/test-only.** The build
   prints the warn with exactly that meaning; manifests record
   `signed: false`; the provenance slots ship empty. A release artefact
   marked `signed: false` in its build manifest must not be distributed to
   customers — that is checkable from the artefact's own manifest.

7. **OFFLINE REVOCATION IS NOT GLOBAL REVOCATION** (review register, second
   pass, item 3). Verification is local and offline BY DESIGN — which means
   a disconnected client cannot learn that a previously trusted key has been
   compromised until it receives a trust-store update (a new
   `NIXON_PROVENANCE_PUBKEY`) or another authenticated policy update.
   Revocation propagates at the speed of pin distribution, not instantly.
   The consequence the operator must plan for: artefacts signed with the
   compromised key KEEP VERIFYING on a client that has not updated its pin.
   Mitigations, in order of reach: out-of-band pin updates with the release
   channel; a short "expected pin fingerprint" published in the release
   notes so a holder can compare; and, where the deployment allows it, an
   online licence-chain check (licensing.chain_owner_of) as a secondary
   signal — knowing that path itself depends on the signature-gated RPC.
   The build manifest binds the source commit and the dependency-lock
   digest, so post-incident auditing of WHICH artefacts were signed by the
   compromised key is answerable from the artefacts themselves.
