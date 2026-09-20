"""
strategy_selector.py

Purpose:
Maps function classification categories to obfuscation pass lists
and configuration. Each category (simple_helper, crypto, license_check,
key_derivation, sensitive_algo) gets a tailored protection stack.

Architectural Role:
Second stage of the classification pipeline. After FunctionClassifier
labels each function, StrategySelector produces the pass list and
per-pass config that the pipeline executor will apply. STRATEGY_MAP
is the central policy table.

Security Relevance:
The strategy map encodes domain knowledge about what protections are
appropriate for each function type. For example, key_derivation gets
ROP gadget chains (strongest protection), while simple_helper gets
only light AST renaming. Tuning this map directly affects the
security/overhead trade-off.
"""

from typing import Dict, List


STRATEGY_MAP = {
    'simple_helper': {
        'passes': ['ast_obfuscate'],
        'config': {
            'ast_obfuscate': {
                'rename_vars': True,
                'remove_comments': True,
                'remove_docstrings': True,
                'strip_metadata': True,
            },
        },
        'description': 'Light AST obfuscation only',
    },
    'crypto': {
        'passes': ['ast_obfuscate', 'vm_compile'],
        'config': {
            'ast_obfuscate': {
                'rename_vars': True,
                'remove_comments': True,
                'remove_docstrings': True,
                'opaque_predicates': True,
                'mba_subs': True,
                'cfg_flatten': True,
            },
            'vm_compile': {
                'full_vm_wrapping': True,
                'custom_opcodes': True,
                'bytecode_encryption': True,
            },
        },
        'description': 'Full VM wrapping',
    },
    'license_check': {
        'passes': ['ast_obfuscate', 'jit_compile'],
        'config': {
            'ast_obfuscate': {
                'rename_vars': True,
                'remove_comments': True,
                'remove_docstrings': True,
                'opaque_predicates': True,
            },
            'jit_compile': {
                'jit_at_runtime': True,
                'encrypted_template': True,
                'ephemeral_code': True,
            },
        },
        'description': 'JIT-generated ephemeral code at runtime',
    },
    'key_derivation': {
        'passes': ['ast_obfuscate', 'rop_compile'],
        'config': {
            'ast_obfuscate': {
                'rename_vars': True,
                'remove_comments': True,
                'remove_docstrings': True,
                'opaque_predicates': True,
                'mba_subs': True,
                'cfg_flatten': True,
                'bogus_exceptions': True,
            },
            'rop_compile': {
                'rop_gadget_chains': True,
                'max_protection': True,
                'target_functions': [],
            },
        },
        'description': 'ROP gadget chain execution (max protection)',
    },
    'sensitive_algo': {
        'passes': ['ast_obfuscate', 'oram_compile'],
        'config': {
            'ast_obfuscate': {
                'rename_vars': True,
                'remove_comments': True,
                'remove_docstrings': True,
                'opaque_predicates': True,
                'mba_subs': True,
                'cfg_flatten': True,
                'bogus_exceptions': True,
                'fragment_strings': True,
            },
            'oram_compile': {
                'oblivious_ram': True,
                'memory_obfuscation': True,
                'access_pattern_hiding': True,
                'num_blocks': 256,
            },
        },
        'description': 'Fragmented ORAM-backed execution',
    },
}


class StrategySelector:
    """
    Maps a classification category to its protection strategy.

    Uses STRATEGY_MAP as the lookup table. Falls back to
    'simple_helper' for unknown categories to ensure every
    function gets at least minimal protection.
    """

    def select(self, category: str) -> List[str]:
        """
        Return the list of protection passes for a category.

        Falls back to simple_helper if category is unknown.
        """
        entry = STRATEGY_MAP.get(category, STRATEGY_MAP['simple_helper'])
        return list(entry['passes'])

    def get_config(self, category: str) -> Dict:
        """
        Return the per-pass configuration dict for a category.

        Config includes boolean flags like rename_vars, opaque_predicates,
        mba_subs, cfg_flatten, etc. that control pass behaviour.
        """
        entry = STRATEGY_MAP.get(category, STRATEGY_MAP['simple_helper'])
        return dict(entry['config'])

    def get_description(self, category: str) -> str:
        """
        Return a human-readable description of the protection strategy.
        """
        entry = STRATEGY_MAP.get(category, STRATEGY_MAP['simple_helper'])
        return entry['description']
