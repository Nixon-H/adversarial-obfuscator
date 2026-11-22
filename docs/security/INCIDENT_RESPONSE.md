# Incident response and key-compromise runbook

Review register, P2: "Incident-response and key-compromise exercises". The
register lists six procedures — signing-key compromise, emergency pin
replacement, manifest-key rotation, old-artefact retirement, compromised
dependency discovery, and release revocation with client recovery.

This document is the procedure, and every step that CAN be checked in code is
checked by `tests/test_incident_response.py`, so a step that stops being true
fails a test rather than rotting quietly. Steps that require a human
(notifying customers, updating a protected environment) are marked
**[operator]** and are deliberately not simulated — a drill that fakes the
human step proves nothing about whether the human step is documented.

## The two keys, and why this matters

Two independent signing keys exist and a release MUST set both:

| variable | signs | verified by |
|---|---|---|
| `NIXON_ARTEFACT_SIGN_KEY` | the loader's provenance slots (`_NX_PROV_SIG` / `_NX_PROV_PK`) | the loader, against `NIXON_PROVENANCE_PUBKEY` |
| `NIXON_BUILD_MANIFEST_KEY` | `<artefact>.build-manifest.json` | `verify_manifest`, against `NIXON_BUILD_MANIFEST_PUBKEY` |

They are separate on purpose: compromising one does not forge the other, and
the acceptance check detects a half-signed artefact (signed manifest, empty
provenance slot, or the reverse). Any response below must therefore ask WHICH
key was compromised before choosing the procedure.

## 0. Triage: answer "which artefacts?" from the artefacts themselves

**Do not start from a build database.** The manifest records
`signed_key_fingerprint` — the same value as `signature.key_fingerprint`, but
carried at TOP LEVEL and therefore inside the signed body — so the affected
set is derivable from the released files:

```python
# for each released artefact
m = json.load(open(art + ".build-manifest.json"))
m["signed_key_fingerprint"]          # which key signed it (SIGNED copy)
m["build"]["commit"]                 # which source
m["build"]["dependency_lock_digest"] # which dependency set
m["protection_level"]                # which generation
```

Read `signed_key_fingerprint`, not the nested copy: only the top-level value
is covered by the signature. `verify_manifest` refuses a manifest whose two
copies disagree, so an artefact claiming two different keys fails outright.

An artefact whose `signed` is `false`, or whose fingerprint matches the
compromised key, is in scope. **Verified by**
`test_the_fingerprint_scopes_the_affected_set` and
`test_the_signed_fingerprint_cannot_be_re_attributed`.

## 1. Signing-key compromise

Order matters: revocation is **pin replacement**, because verification is
local and offline (§5.6 item 5 of `MAXIMUM_SECURITY.md`).

1. Generate the replacement key out of band:
   `python3 -m obfuscator.licensing` (§5.2). **[operator]**
2. Publish the new pin as `NIXON_PROVENANCE_PUBKEY` in the release channel,
   and record BOTH fingerprints in the release notes: the retired one and
   the new one. **[operator]**
3. Rebuild and re-sign affected artefacts with the new
   `NIXON_ARTEFACT_SIGN_KEY`. Every rebuilt artefact must be signed; a build
   with the variable unset produces `signed: false`, which must not ship.
4. Announce the retirement. **The offline limit is real**: a disconnected
   client keeps verifying the compromised key's signature until it receives
   the new pin. State that in the notice rather than implying instant global
   revocation.

**Verified by** `test_a_retired_key_is_refused_under_the_new_pin` and
`test_an_unupdated_client_still_accepts_the_old_key` — the second is the
limitation, asserted as a measurement rather than claimed away.

## 2. Emergency pin replacement

The pin is read from the environment at verification time, so replacement is
distribution, not re-issuance:

1. Ship the new `NIXON_PROVENANCE_PUBKEY` value to holders. **[operator]**
2. Under release policy (`NIXON_REQUIRE_PROVENANCE=1`) a missing pin is a
   REFUSAL, never a fallback — so a client that loses the variable fails
   closed instead of silently trusting the embedded key.
3. An explicit key that disagrees with the pin is also a refusal: the pin is
   the authority, and the explicit key cannot override it.

**Verified by** `test_a_missing_pin_is_a_refusal_under_release_policy` and
`test_an_explicit_key_cannot_override_the_pin`.

## 3. Manifest-key rotation

Independent of §1 because the keys are independent:

1. New `NIXON_BUILD_MANIFEST_KEY` out of band. **[operator]**
2. New `NIXON_BUILD_MANIFEST_PUBKEY` pin published.
3. Old manifests stop verifying for any client holding the new pin. That IS
   the retirement of the old manifest key's future.

**Verified by** `test_rotating_the_manifest_pin_retires_the_old_manifests`.

## 4. Old-artefact retirement

Retirement is expressed two ways, and both are enforced:

* **protection level** — `protection_level` sits inside the signed manifest
  body. Lowering it breaks the signature, so an attacker cannot lower a
  level to make an old artefact acceptable again.
* **high-water mark** — `.nx-rollback-mark`, MAC'd with the build key and a
  raw bytes HMAC key. `read_mark` verifies the MAC on READ and returns 0 for
  anything it cannot authenticate, so an edited mark is treated as a fresh
  install rather than obeyed. `check_rollback` raises `refusing to downgrade`
  when the artefact's level is below the mark.

**Verified by** `test_lowering_the_protection_level_breaks_the_signature` and
`test_a_forged_high_water_mark_is_not_trusted`.

## 5. Compromised dependency discovery

The manifest binds `build.dependency_lock_digest` = sha256 of the lock file
BYTES actually used, not a version label that can drift. Given an advisory
naming a package version:

1. Determine the digest of the affected lock set. **[operator]**
2. Match it against released manifests. Every artefact whose
   `dependency_lock_digest` matches was built under the affected set.
3. Rebuild from a corrected lock, which changes the digest, so the new
   artefacts are distinguishable from the old by their own manifests.

**Verified by** `test_the_lock_digest_distinguishes_dependency_sets`.

## 6. Release revocation and client recovery

1. Revoke by pin replacement (§1 step 2). There is no online revocation list:
   the design is local and offline, and inventing a list would add a network
   trust dependency the loader does not otherwise have.
2. Clients recover by receiving the new pin and a rebuilt artefact.
3. If a deployment cannot update pins promptly, the documented mitigation is
   an online licence-chain check (`licensing.chain_owner_of`) as a SECONDARY
   signal — knowing that path itself depends on the signature-gated RPC.

**Verified by** `test_revocation_is_pin_replacement_not_a_list` — asserts
that no revocation-list file or network call exists in the verification path,
so the documented mechanism is the one actually implemented.

## What is NOT covered here

* The protected production environment and the actual promotion of a release
  candidate are **[operator]** steps in a GitHub environment with required
  reviewers. Configuring it is outside this repository.
* Authenticode and Apple Developer ID identities are external purchases, and
  without them the Windows and macOS artefacts are unsigned by a CA — which
  §5.6 records rather than glosses.
* An independent cryptographic review of the pack-v2 construction has not
  been performed. Passing the tamper matrix shows particular attacks were
  rejected; it does not establish cryptographic security.

Those three are register rows that cannot close from inside this repository,
and this runbook says so instead of implying coverage it does not have.
