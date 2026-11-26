#!/usr/bin/env python3
"""Spawn-safe pytest entry point.

Multiprocessing spawn children cannot reload a ``<stdin>`` pytest main program.
Keeping this as a real file lets tests spawn Python workers while still using the
environment's importable-but-not-executable pytest installation.
"""
from __future__ import annotations

import sys

import pytest


if __name__ == "__main__":
    raise SystemExit(pytest.main(sys.argv[1:]))
