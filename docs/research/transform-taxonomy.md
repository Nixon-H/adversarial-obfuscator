# Transformation Taxonomy: what each pass actually changes (2026-09-28)

Rule: a transformation counts toward *structural diversification* only if
it changes an attacker-visible representation relevant to at least one
attack class. Renaming 500 identifiers is not equivalent to changing
control-flow topology.

Classes: LEX (lexical) · EXPR (AST-local expression) · CFG (control flow)
· DATA (data/literal representation) · REP (code representation) ·
EXEC (execution model) · INT (integrity, not obfuscation) · NOOP.

## Pass inventory (option key → class → structural class)

| Pass (option) | Class | Structural class | Attacker-visible change | Targets |
|---|---|---|---|---|
| symbol_rename | SymbolRenamer | LEX | identifier spellings | name recovery |
| unicode_ids | UnicodeIdentifierEncoder | LEX | identifier glyphs | name recovery |
| strip_meta | TypeHintStripper, MetadataStripper | LEX | annotations/docstrings gone | signature recovery |
| builtin_alias | BuiltinAliaser | LEX | call-target spellings | name recovery |
| fragment_strings | StringLiteralObfuscator | DATA | literal encoding/encryption | constant recovery |
| unfold_constants | ConstantUnfolder | EXPR | constant expression shape | constant recovery |
| mba_subs | InstructionSubstitutor (L1-L3) | EXPR | arithmetic expression shape | symbolic simplification |
| obf_calls | CallGraphObfuscator | CFG | call indirection via table | call-graph recovery |
| bogus_exceptions | BogusExceptionHandler | CFG | fake exception paths | CFG recovery |
| opaque_predicates | OpaquePredicateInjector | CFG | bogus branches | CFG recovery |
| cfg_flatten | ControlFlowFlattener | CFG | state-dispatch loop | CFG recovery |
| exception_flow | ExceptionFlowTransformer (sources.py) | CFG | exception edges | CFG recovery |
| split_vars | VariableSplitter | DATA | value splitting (int consts) | data-flow recovery |
| break_decompiler | ExtendedArgBreaker | REP | decompiler-hostile constructs | tool-based recovery |
| code_checksums | CodeChecksumInjector | INT | integrity checks | tamper (not RE) |
| dynamic_code | DynamicCodeGenerator | REP | exec-wrapped functions | static analysis |
| enhanced_junk | EnhancedJunkInserter + ASTMutator junk | LEX | dead statements | noise filtering |
| attention_poison/decoy/adaptive | various | LEX | decoy content | LLM/reasoning attacks |
| stego/minify/residue | various | LEX | formatting/packaging | — |
| **vm** (legacy pass name) | **NONE — no consumer (verified)** | **NOOP** | *nothing; pass name silently ignored* | — |
| vm_dispatch a/b (`obfuscator/vm_dispatch.py`, opt-in) | VMDispatchTransformer | EXEC | function → stack-VM bytecode + dispatcher (switch vs threaded) | boundary/CFG recovery |

Verified 2026-09-28: no transformer, phase, or pipeline branch reads a
`vm` option (`grep` over obfuscator/ + scripts/). Every G2 hetero
pass-set containing `"vm"` believed it enabled virtualization. The
`generate_poly_vm`/TITAN_VM machinery exists but is not wired to this
pass name.

## Why diversity ≈ 0.1 (explains G2 pilot)

Count the hetero pass-sets by what actually executes:

- Set A (rename, dead_code, mba, cfg_flatten, vm): LEX + LEX + EXPR + CFG + NOOP
- Set B (rename, dead_code, opaque_pred, string_encode, vm): LEX + LEX + CFG + DATA + NOOP
- Set C (rename, mba, cfg_flatten, opaque_pred, string_encode, vm): LEX + EXPR + CFG + CFG + DATA + NOOP

Differences between sets are real (opaque vs MBA vs strings) but each is
a *local* change on small programs: a 4-function script gains a few
branches or rewritten expressions. AST node-type histograms barely move
(measured 0.97–1.00 similarity); CFG moves only when flatten fires on a
qualifying function. Nothing changes representation or execution model.
Hence: configuration diversity without structural diversity — exactly
the Koo-warning shape (randomized-but-inferrable structure).

## Missing families (required for genuine heterogeneity)

- **Representation**: block split/merge, dispatcher variation, alternate
  VM instruction sets / handler layouts, container-representation
  changes, fragmented state. (DynamicCodeGenerator's exec-wrapping is
  the only REP pass and is probabilistic + shallow.)
- **Execution-model**: selective virtualization that actually executes
  (wire the VM machinery or remove the `vm` pass name so configs stop
  claiming it).
- **Data-flow-changing**: dependency reordering, not just value
  splitting.
- **Anti-analysis targeted**: anti-DSE predicates (hash-based,
  path-explosion), solver-hardened constants.

## Correctness notes from the battery (2026-09-28)

- Module statement reorder fixed (defs must precede module-level uses).
- Binding/use desyncs fixed: except-as, match captures (both renamers),
  lambda params, class-body stores.
- Junk/sandbox interleaving gated on `enhanced_junk` (O0 contract).
- `tests/test_renamer_semantics.py`: 19 differential cases, all green.
