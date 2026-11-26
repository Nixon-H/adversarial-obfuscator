# ABSOLUTE MAXIMUM cross-platform build, packaging, signing, and trust status

Date: 2026-11-26. This is an evidence-bound status report, not a claim of production release readiness.

## Platform/build matrix

| Platform / architecture | Status | Evidence boundary | Required completion action |
|---|---|---|---|
| Linux x86-64 Python-packed artifact | COMPLETED AND LOCALLY VERIFIED | Authoritative artifact pair executes locally; hashes in `ABSOLUTE_MAXIMUM_BUILD_MANIFEST.json`; runtime probes under `ABSOLUTE_MAXIMUM_RAW_RESULTS/runtime_probe_final_native_lowering_*.json` | Rebuild only after freezing later source changes; do not mutate authoritative artifacts |
| Linux x86-64 native payload | COMPLETED AND LOCALLY VERIFIED for current artifact pair | Extracted ELF objects and runtime/direct-import evidence under `ABSOLUTE_MAXIMUM_RAW_RESULTS/native_final_lowering/` | Same rebuild caveat |
| Cross-OS pure-Python portable artifact | IMPLEMENTED AND CI-TESTED historically | portable workflow matrices exist for Linux/Windows/macOS CPython 3.13/3.14 | Current workflow edits require a fresh CI run |
| Windows x86-64 native payload | PARTIALLY COMPLETED | cloud farm evidence exists, but it is externally produced and not locally reproducible | rerun farm after runner-attestation upload fix; validate artifact sidecars and Windows runtime |
| macOS universal native payload | PARTIALLY COMPLETED / weakest trust row | cloud farm evidence exists; no local signature/notarisation validation | macOS runner, Developer ID signing, notarisation, `spctl` validation |
| Linux ARM64 | NOT STARTED / unsupported | no measured native payload | implement/build/run on ARM64 runner before claiming |
| Windows ARM64 | NOT STARTED / unsupported | no measured native payload | implement/build/run on ARM64 runner before claiming |

## Signing and trust matrix

| Requirement | Repository implementation state | External dependency | Exact administrator validation |
|---|---|---|---|
| Windows Authenticode mechanism | Implemented in `obfuscator/authenticode.py`; signature verifier and negative tests exist | Trusted Windows certificate; private-key custody; timestamping service; Windows runner | sign real artifact, then run `signtool verify /pa payload.pyd` on Windows; verify digest and chain |
| Authenticode timestamping | Not implemented as an integrated repository feature | RFC 3161 timestamp authority | use operator signing process with `/tr <timestamping-url>` / `/td sha256` through `signtool` or equivalent |
| Windows public certificate-chain trust | Not completable in repository | publicly trusted certificate issuance | verify chain on a clean Windows host without importing a private root |
| Windows CET compatibility | probe/build machinery exists | Windows runner/toolchain | inspect PE extended characteristics and do not represent compatibility as runtime enforcement |
| Windows strict shadow-stack enforcement | Not proven | Windows host, supported CPU, OS policy | query process mitigation policy on Windows and test strict mode behavior; repository cannot fabricate this evidence |
| Apple Developer ID signing | Not implemented end-to-end | Apple Developer account, Developer ID Application certificate, macOS signing host/tooling | `codesign --options runtime --timestamp --sign "Developer ID Application: …" payload.dylib` |
| Apple Hardened Runtime | parser/validation logic exists; no real signed production artifact locally | macOS signing with `--options runtime` | inspect with `codesign -dv --verbose=4`; verify hardened runtime flags |
| Apple library validation | parser/validation logic exists | Hardened Runtime signing | verify `CS_RESTRICT`/library validation in signature or platform output |
| Apple notarisation | Not implemented | Apple notary credentials/account | `xcrun notarytool submit <artifact> --keychain-profile <profile> --wait` |
| Apple stapling | Not implemented | successful notarisation | `xcrun stapler staple <artifact>` |
| macOS Gatekeeper validation | Not implemented locally | macOS host | `spctl -a -vv <artifact>` and documented negative control |
| Production release signing controls | dry-run acceptance workflow exists; ephemeral keys prove mechanics only | protected GitHub environment, required reviewers, persistent publisher key custody, branch/tag protections | verify GitHub environment protection settings outside the repository before real publish |

## Required operational rules

1. Never report a self-signed Authenticode certificate as public Windows trust.
2. Never report CET compatibility as runtime shadow-stack enforcement.
3. Never report an ad-hoc or unsigned Mach-O as Developer ID signed, hardened, or notarised.
4. Never treat farm output as locally reproducible evidence; classify it as externally produced measured evidence.
5. Do not publish a production artifact until the protected GitHub environment, persistent signing identity, administrator approvals, and platform-native validation are complete.

## Repository-side state after this continuation

The repository already has meaningful implementation and test coverage for Authenticode signing/verification, Mach-O hardening parsing, farm attestation, artifact sidecars, and release acceptance. This continuation fixed farm attestation upload coverage and release/provenance acceptance defects. The remaining gaps are primarily external trust/platform validation rather than additional local code.
