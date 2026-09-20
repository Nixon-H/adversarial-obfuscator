"""
__init__.py

Purpose:
Package initializer for the function classification module. Exports the
FunctionClassifier and StrategySelector used to categorize functions
and select obfuscation strategies.

Architectural Role:
Bridge between static analysis (classifier) and the protection pipeline
(strategy selection). Determines which protections apply to each function.

Security Relevance:
Correct classification is the first step in targeted protection.
Misclassification can leave crown-jewel functions unprotected or
apply heavy protections to trivial functions, wasting overhead budget.
"""

from .function_classifier import FunctionClassifier
from .strategy_selector import StrategySelector, STRATEGY_MAP
