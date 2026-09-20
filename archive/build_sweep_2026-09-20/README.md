# build_sweep_2026-09-20 — adversarial-loop sweep outputs (2026-09-20 08:20–09:03)

13× `tmp*_obfuscated.py` regenerables from the adversarial-loop sweep
(`feedback_history.json` in `build/` records the run; `manifest.json`,
`classification_report.txt`, `program.ir`, `*_config.json` stay in `build/`).

Regenerable via `adversarial_loop.py`. Nothing in the pipeline imports
these files by path. Kept (not deleted) because the sweep they came from
is still under analysis.
