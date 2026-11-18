"""PyDeObsBench: adversarial reconstruction benchmark for protected artefacts.

This package is deliberately INDEPENDENT of the protection compiler: it never
imports the pipeline's own scoring or verification code, so the protection
system cannot become its own judge.

Components
----------
targets.py         ground-truth payloads (source, secrets, names, algorithm)
static_probes.py   what an analyst gets without executing the artefact
dynamic_probes.py  runtime output, temp files, memory maps, Z3 on predicates
ai_probe.py        DeepSeek V4.1 Flash via Mistral reconstruction attempt
run.py             builds artefacts and orchestrates every probe
"""

__version__ = "0.1.0"
