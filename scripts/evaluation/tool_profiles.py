TOOL_PROFILES = {
    'angr': {
        'cfg_flatten_sensitivity': 50,
        'opaque_predicate_limit': 20,
        'mba_depth_limit': 5,
        'vm_resistance': 'high',
    },
    'rizin': {
        'cfg_flatten_sensitivity': 100,
        'opaque_predicate_limit': 30,
        'mba_depth_limit': 8,
        'vm_resistance': 'medium',
    },
    'readelf': {
        'cfg_flatten_sensitivity': 200,
        'opaque_predicate_limit': 100,
        'mba_depth_limit': 15,
        'vm_resistance': 'low',
    },
    'objdump': {
        'cfg_flatten_sensitivity': 150,
        'opaque_predicate_limit': 80,
        'mba_depth_limit': 12,
        'vm_resistance': 'low',
    },
}
