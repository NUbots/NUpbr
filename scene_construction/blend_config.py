render = {
    'render_engine': 'CYCLES',
    'render': {
        'cycles_device': 'GPU',
    },
    'dimensions': {
        'resolution': [1920, 1080],
        'percentage': 50.0,
    },
    'sampling': {
        'cycles_samples': 32,
        'cycles_preview_samples': 16,
    },
    'light_paths': {
        'transparency': {
            'max_bounces': 1,
            'min_bounces': 1,
        },
        'bounces': {
            'max_bounces': 1,
            'min_bounces': 1,
        },
        'diffuse': 1,
        'glossy': 1,
        'transmission': 1,
        'volume': 0,
        'reflective_caustics': False,
        'refractive_caustics': False,
    },
    'performance': {
        'render_tile': [512, 512],
    },
}

scene = {
    'units': {
        'length_units': 'METRIC',
        'rotation_units': 'DEGREES',
    }
}

field = {
    'particle': {
        'use_adv_hair': True,
        'type': 'HAIR',
        'emission': {
            'count': 5000,
            'hair_length': 0.2,
            'emit_from': 'FACE',
            'emit_random': False,
            'even_dist': False,
        },
        'physics': {
            'type': 'NEWTON',
            'brownian_factor': 0.03,
            'timestep': 0.04,
            'subframes': 1
        },
        'render': {
            'emitter': False,
            'parents': True,
        },
        'children': {
            'child_type': 'INTERPOLATED',
            'child_num': 0,
            'rendered_children': 100,
            'length': 0.5,
        },
        'cycles_hair': {
            'shape': 0.12,
            'root': 0.03,
            'tip': 0.0,
            'scaling': 0.05,
            'close_tip': True,
        }
    },
}