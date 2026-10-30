"""Vendored for the artefact gate (MIT, more-itertools).

Only the two modules the gate connects are included. The package exists so
relative imports resolve the way they do upstream -- single-file ingestion could
not gate these modules at all (see corpus-ingestion-limits.md).
"""
from .recipes import *
from .more import *
