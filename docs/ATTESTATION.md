# Attestation protocol ownership

Two components touch "attestation"; each owns a different scope.
Rule: **new attestation logic goes in `runtime/src/sw_attestation.rs`**.

- `runtime/src/sw_attestation.rs` (canonical): payload integrity
  challenges — the response binds the running payload bytes.
- `relay/src/attestation.rs` (launcher scope): challenge issuance for
  the launcher process liveness only — not payload attestation.
- `native/attestation.c` (DELETED 2026-09-20): was an unwired
  experimental sim with known defects (always-false compare,
  `srand`/`rand` self-attesting region). Removed, not gated — the
  NIXON_EXPERIMENTAL shim is gone with the file.

Wire diagram:

```
payload ──challenge/response──> runtime/src/sw_attestation.rs (canonical)
launcher ──challenge issuance─> relay/src/attestation.rs (liveness only)
native/attestation.c ──X── (deleted; was deprecated sim, unwired)
```

Do not add new protocols elsewhere; extend the canonical module.
