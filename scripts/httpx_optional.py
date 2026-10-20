"""Optional import of the httpx HTTP client.

``httpx`` is needed only by the LLM evaluation tools.  It is not a
dependency of the obfuscator, the build pipeline, or the test suite.

The guard used to be copy-pasted into each tool, which meant a fourth
tool would have to remember it.  This module is the one place the
pattern lives, and it matches ``scripts/z3_optional.py``: when httpx is
installed it is the real module; when it is not, the stand-in raises a
clear error the moment anything uses it, so the tool fails with a
message that says what to install rather than an ``AttributeError`` on
``None``.

Usage::

    from scripts.httpx_optional import httpx

    with httpx.Client(...) as client:
        ...
"""
try:
    import httpx
except ImportError:  # pragma: no cover - exercised by the absence test
    class _MissingHttpx:
        """Stand-in for httpx when the optional dependency is absent."""

        def __getattr__(self, name):
            raise RuntimeError(
                "httpx is required for the LLM evaluation tools. "
                "Install it with: pip install -r requirements-ai.txt")

        def __bool__(self):
            return False

    httpx = _MissingHttpx()

__all__ = ["httpx"]
