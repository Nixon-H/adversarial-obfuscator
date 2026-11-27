# AM-001 server-side split remediation validation — 2026-11-27

## Scope

This record validates the implemented opt-in architectural remediation for
AM-001: module-level functions explicitly marked `@remote` are removed from
the client before native compilation, AST mutation, farm upload, or loader
embedding. The client carries only a self-contained authenticated call stub;
the implementation exists only in the operator bundle.

This does **not** retroactively change the fixed benchmark artifacts under
`re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/builds/`, and it is not a universal fix
for arbitrary client-side payload logic. It applies only to logic the developer
explicitly moves server-side.

Machine-readable evidence: `ABSOLUTE_MAXIMUM_AM001_REMOTE_SPLIT_VALIDATION_20261127.json`.

## Validated security properties

1. **Implementation removed before packing.** The generated client contained no
   `SECRET_COEFFICIENT`, no hexadecimal coefficient, no decimal coefficient, and
   no `obfuscator.remote_exec` import. The operator bundle contained the
   implementation and was owner-only.
2. **Native path validated.** The split client was compiled through the real
   local Cython/native path. The resulting `payload_module.so` imported and
   printed the expected remote result through the live reference relay. The
   native object did not contain the coefficient name or coefficient values.
3. **Packed artifact validated.** The packed artifact built successfully with
   the pipeline's own verification suite (`PASS` / `VALID` / `MATCH` for debug
   and silent variants) and printed the expected remote result through the live
   relay.
4. **Fail-closed configuration.** Without `NIXON_REMOTE_URL` and
   `NIXON_REMOTE_SECRET`, the packed artifact exited nonzero instead of using a
   local fallback or returning a plausible default.
5. **Authenticated live protocol.** Against the live Rust relay, a valid request
   succeeded; tampered arguments failed with `remote request signature
   mismatch`; a stale timestamp failed with `remote request expired`; a reused
   nonce failed with `remote request replayed`.
6. **Production-shaped relay startup.** After regenerating the relay's runtime
   baseline for the rebuilt binary, the service started with normal runtime
   initialization and integrity baseline `0x9cba7a4a`; `--no-init-runtime` was
   not needed for the final validation.

## Key artifact evidence

| file | SHA-256 | result |
|---|---|---|
| original test payload | `2f23cfeb0b9277544afcd8d0bc3f173491a4cc2074598c70f1ff92a2d88c5e4f` | contains the test implementation |
| split client | `cc61d36561579afe97484fdad6c5137b01e1cedd6175b607c5fca9a430b6142e` | implementation absent |
| operator bundle | `ff7e0f0fae52bf947f4f00558bef663022a164013eb99c7110dd66fb2dc3a53d` | implementation present, owner-only |
| native Cython blob | `e49d34ecb505eba448d4394555cc14f3b8c1e78591fdb9bf370ca68f9e387593` | coefficient absent; remote call succeeds |
| packed artifact | `4ee42f5693dab86c7485dd92f29b745b775bac2b69f6821142000cfd61071b20` | coefficient absent; remote call succeeds |

The native blob still contains the public function name `hidden_pricing`. That
name is not the confidential algorithm; the coefficient and implementation are
absent. If the function name itself is sensitive, ordinary renaming remains a
separate transform.

## Test evidence

- Python focused lane: **37 passed**
- Rust relay remote lane: **26 passed**
- Ruff/`make lint`: **passed**
- Relevant partitions: distributed-network **186 passed**; build-native-loader **562 passed, 4 skipped**
- Live valid response: `remote-result 864409510`
- Tampered arguments: `remote request signature mismatch`
- Stale timestamp: `remote request expired`
- Replayed nonce: `remote request replayed`

## Honest residual boundary

This is a real architectural remediation for marked functions, not a magical
client-side confidentiality primitive:

- unmarked client-side logic remains extractable under the AM-001 boundary;
- the customer-held `NIXON_REMOTE_SECRET` authenticates requests but is not a
  confidentiality boundary against the customer-machine attacker;
- while valid client configuration exists, that attacker can invoke the service
  as an oracle;
- the operator service must therefore enforce account identity, rate limits,
  billing/quotas, revocation, logging, and abuse policy;
- network deployments must use HTTPS. Plain HTTP is accepted only for the
  loopback reference relay.
