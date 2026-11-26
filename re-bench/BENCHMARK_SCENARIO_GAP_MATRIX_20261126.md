# Benchmark scenario coverage matrix — corrected 2026-11-27

This file supersedes the earlier gap matrix written before the final OpenCode Go DeepSeek campaign. The previous statements that source-assisted scenarios, `maximum-local`, and `maximum-cloud` were missing are now historical and no longer describe the benchmark matrix.

## Final variant coverage

| variant | artifact exists | final artifact SHA-256 |
|---|---:|---|
| `maximum-packed` | yes | `77768b84dff54e4aace072db248d4a94e08c9e6ed3b9a2a31f4406a84856b778` |
| `maximum-local` | yes | `118ae2ed15e617926ad050ddbfebaced6bd4d4b59644772257f74dbbb285a396` |
| `maximum-cloud` | yes | `f9c5256d796c57fccc81e0eff0064b5743a1768e2dc203dfa3fc91651965a395` |
| `absolute` | yes | `5382e72af5cce267fa2ec0379b6c3910b0bc33f7ac645a5ad2c88bc011ce0fbe` |
| `absolute-cloud` | yes | `9bfdadef9414f9f79b0529f16bfa9591423f6f93bc53a5f9dbea83e1e6330dc0` |
| `absolute-native-only` | yes | `28630cc945e883151761b4752db1d9a7e59a7dbb29bc9e93b381e75ba2898032` |

## Key/source coverage

| requested condition | final benchmark scenarios | status |
|---|---|---|
| with key/runtime secrets, no source | `legitimate-runtime-secrets` | covered |
| without key/runtime secrets, no source | `runtime-secrets-withheld` and non-secret static/dynamic scenarios | covered |
| with key/runtime secrets, with source | `source-assisted-runtime-secrets` | covered as control |
| without key/runtime secrets, with source | `source-assisted-secrets-withheld` and `source-assisted-static` | covered as controls |
| cloud maximum profile | `maximum-cloud`, `absolute-cloud` | covered with validated cloud-final4 artifacts |
| local maximum profile | `maximum-local`, `maximum-packed` | covered |
| absolute maximum profile | `absolute`, `absolute-native-only` | covered |

## Final execution status

The final OpenCode Go DeepSeek lane executed all 6 variants × 19 scenarios: 114/114 active records are structurally valid after retry. This is one attempt per cell and is therefore broad diagnostic evidence only, not statistical completion under the five-valid-attempt acceptance standard.

Authoritative final report: `re-bench/ABSOLUTE_MAXIMUM_DEEPSEEK_FINAL_REPORT_20261126.md`.
