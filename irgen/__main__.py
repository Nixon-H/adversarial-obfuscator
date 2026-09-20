"""
__main__.py

Purpose:
CLI entry point for `python -m irgen`. Delegates to irgen.__init__.main()
for compiling Python source files to IR.

Architectural Role:
Module-level CLI dispatcher.
"""

from .__init__ import main

main()
