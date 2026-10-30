# RETRACTED: the `except*` "defect" was invalid input

**Retracted in round 102, one round after it was reported.**

## What I reported

That the obfuscator inserts a `return` into an `except*` handler and produces
`SyntaxError: 'break', 'continue' and 'return' cannot appear in an except*
block`, as a seventh defect.

## What was actually true

**The stress module I wrote was not valid Python.** I had put the `return`
inside the handler myself:

```python
    except* ValueError:
        return 0          # illegal in any source, obfuscated or not
```

The obfuscator received invalid input, could not compile it, and reported the
same error the interpreter gives for the file as written:

```
$ python3 -c "compile(open('corpus/stress.py').read(), 'x', 'exec')"
SOURCE IS INVALID: 'break', 'continue' and 'return' cannot appear in an except* block
```

So the failure was correct behaviour. There is no seventh defect.

## Fixed

The module now assigns in the handler and returns after the try/except, with a
comment recording why. It compiles and imports at all three build indices, and
`async`, generators, descriptors, `functools.wraps`, walrus, `match` on classes
and `except*` all survive obfuscation.

## The process failure

I wrote a test module, saw a failure, and attributed it to the system under test
without first checking that the test itself was valid. That is the same error as
rounds 39, 51, 52, 56 and 87 — **the instrument was broken and its output looked
like an answer** — and it is the eighth time in this programme.

The check that would have caught it costs one line:

```
compile(source_of_the_fixture, "<fixture>", "exec")
```

and it now belongs in any future stress module. A corpus entry that does not
compile is not a test of the obfuscator.
