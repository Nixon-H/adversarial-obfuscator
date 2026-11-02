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
