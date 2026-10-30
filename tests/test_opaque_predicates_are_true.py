"""Every opaque predicate must be TRUE, or it deletes the code it wraps.

The injector wraps a whole function body in a predicate it believes is
always true:

    pred = random.choice(self.predicates)()
    opaque_if = ast.If(test=pred, body=node.body.copy(), orelse=[ast.Pass()])
    node.body = [opaque_if]

If the predicate is false, the body never runs and the function silently
returns None. That is not obfuscation, it is deletion, and it is silent: the
module imports, the call succeeds, and the answer is None.

Two builders shipped unsatisfiable predicates:

  * `(x*x + x) % 2 == x % 2` -- false for every odd x, i.e. half the time;
  * an elliptic-curve check comparing y**2 against a re-derivation from x
    that the fallback had already changed -- false in 200 of 200 samples.

Together they corrupted about one build in twelve when combined with
dead-code insertion, and it took five rounds to attribute because it looked
like an attacker failure, then an ambiguous task, then a dropped function.

This test evaluates every builder many times and fails if any sample is not
True. It is cheap and it would have caught both defects before release.
"""

import ast

import pytest

from obfuscator.core.transforms import OpaquePredicateInjector

SAMPLES = 200


def _builders():
    inj = OpaquePredicateInjector()
    return [(n, getattr(inj, n)) for n in dir(inj) if n.startswith("_math_predicate")]


def test_there_are_predicate_builders_to_check():
    assert len(_builders()) >= 10, "predicate builders disappeared or were renamed"


@pytest.mark.parametrize("name,fn", _builders())
def test_every_predicate_is_always_true(name, fn):
    false = []
    for _ in range(SAMPLES):
        expr = ast.unparse(fn())
        try:
            value = eval(expr)  # noqa: S307 - evaluates generated arithmetic only
        except Exception as exc:
            false.append("%s -> %s" % (expr[:60], type(exc).__name__))
            continue
        if value is not True:
            false.append("%s -> %r" % (expr[:60], value))
    assert not false, (
        "%s produced %d non-true predicates in %d samples; wrapping a body in "
        "one of these deletes the body. First: %s"
        % (name, len(false), SAMPLES, false[0])
    )
