# Portable artefact fixture

`secure_demo_protected.py` is a **generated** 597 KB artefact from the 1,108-byte
`secure_demo_source.py`, built with:

```
ai-obf build secure_demo_source.py --portable --section-split --section-count 6 \
    --zips 2 --opt-level 5 --skip-cloud --watermark nixon-sec-2026
```

It is committed unmodified, on purpose: the CI job `.github/workflows/portable-artefact.yml`
runs **this exact file** on Linux, Windows and macOS. The claim being tested is "one file runs on
every OS with no native library", and that can only be tested by running the same bytes
everywhere. Rebuilding in CI would test the builder, not the artefact.

Do not edit it. To regenerate, rebuild from the source with the command above; the output is
deterministic for a given build seed only in the sense that it is a function of that seed, so a
rebuild will not be byte-identical — commit the new file if the protection changes.

## Why `.gitattributes` marks this file `-text`

The artefact hashes **its own bytes** and refuses to run if they change (exit 137). Git's default
on Windows rewrites LF to CRLF on checkout, which changes every offset, so the self-check fails and
the artefact dies. The first CI run of this fixture showed exactly that: `ubuntu-latest` passed,
`windows-latest` exited 137. `-text` keeps the committed bytes intact on every platform.

## Configuration matrix (audited)

The portability audit has been run against more than one build configuration. Repeating one
configuration tells you it is stable; a different configuration tells you the *builder* is.

| configuration | size | audit |
|---|---|---|
| `--section-count 6 --zips 2 --opt-level 5` (the committed fixture) | 660,152 | 12/12, 30 passes |
| `--section-count 8 --zips 1 --opt-level 4` | 436,216 | 12/12 |
| `--section-count 2 --zips 3 --opt-level 3` | — | 12/12 |

Every configuration is `--portable`: no native core, so the same file runs on any OS.

**The audit has been shown to fail on demand**: pointed at a file that prints the wrong thing, all
12 checks fail (CI job `audit has teeth`). Without that, a green audit and a check that cannot fire
look identical.
