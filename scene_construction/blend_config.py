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
    'material': {
        'mapping': {
            'translation': (0., 0.05, 0.),
            'rotation': (0., -90., 0.),
            'scale': (1., 0.6, 1.),
        },
        'mix_lower_grass': {
            'inp1': (0.02, 0.188, 0.05, 1.),
            'inp2': (0.110, 0.066, 0., 1.),
        },
        'mix_upper_grass': {
            'inp1': (0.335, 0.549, 0.006, 1),
            'inp2': (0.272, 0.175, 0.002, 1),
        },
        'noise': {
            'inp': [5., 2., 0.],
        },
        'hsv': {
            'inp': [0., 0., 1.9, 1.],
        },
        'mix_up_grass_hsv': {
            'inp0': 0.455,
        },
        'mix_low_grass_field_lines': {
            'inp0': 0.4,
        },
        'diffuse': {
            'inp1': 0.217,
        },
        'mix_ao_transluc': {
            'inp0': 0.827,
        },
        'mix_shaders': {
            'inp0': 0.273,
        },
    },
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
    'noise': {
        'type': 'VORONOI',
        'contrast': 0.5,
        'noise_scale': 0.1,
        'nabla': 0.03,
        'mapping_coords': 'ORCO',
        'influence': {
            'use_hair_length': True,
            'hair_length_factor': 0.8,
        }
    },
}