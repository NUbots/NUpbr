# Blender-specific Configuration Settings

from math import pi

render = {
    "render_engine": "CYCLES",
    "render": {"cycles_device": "GPU"},
    "dimensions": {"resolution": [1280, 1024], "percentage": 100.0},
    "sampling": {"cycles_samples": 256, "cycles_preview_samples": 16},
    "light_paths": {
        "transparency": {"max_bounces": 1, "min_bounces": 1},
        "bounces": {"max_bounces": 1, "min_bounces": 1},
        "diffuse": 1,
        "glossy": 1,
        "transmission": 1,
        "volume": 0,
        "reflective_caustics": False,
        "refractive_caustics": False,
    },
    "performance": {
        "render_tile": [512, 512],
        "threads": {"mode": "FIXED", "num_threads": 8},
    },
    "layers": {"use_hair": False},
}

scene = {"units": {"length_units": "METRIC", "rotation_units": "DEGREES"}}

layers = {"denoising": {"use_denoising": False}}

field = {
    "material": {
        "mapping": {
            "translation": (0.0, 0.05, 0.0),
            "rotation": (0.0, -pi / 2.0, 0.0),
            "scale": (1.0, 0.6, 1.0),
        },
        "mix_lower_grass": {
            "inp1": (0.000, 0.012, 0.00076, 1.0),
            "inp2": (0.020, 0.011, 0.0, 1.0),
        },
        "mix_upper_grass": {
            "inp1": (0.247, 0.549, 0.0, 1),
            "inp2": (0.257, 0.272, 0.0, 1),
        },
        "noise": {"inp": [5.0, 2.0, 0.0]},
        "hsv": {"inp": [0.0, 0.0, 1.9, 1.0]},
        "mix_up_grass_hsv": {"inp0": 0.455},
        "mix_low_grass_field_lines": {"inp0": 0.4},
        "mix_grass": {"inp0": 0.391},
        "principled": {"specular": 0.225, "roughness": 0.625},
    },
    "lower_plane": {
        "colour": (0.003, 0.04, 0.0, 1.0),
        "principled": {"specular": 0.225, "roughness": 1.0},
        "mapping": {"scale": (0.1, 0.1, 1.0)},
    },
}

ball = {
    "initial_cond": {"segments": 16, "ring_count": 10, "calc_uvs": True},
    "material": {"metallic": 0.0, "roughness": 0.35},
    "subsurf_mod": {"levels": 1, "rend_levels": 4},
}

goal = {
    "initial_cond": {"vertices": 32, "calc_uvs": True},
    "corner_curve": {"fill": "FULL"},
    "material": {"metallic": 0.0, "roughness": 0.35, "colour": (0.8, 0.8, 0.8, 1.0)},
    "subsurf_mod": {"levels": 1, "rend_levels": 4},
}

robot = {"material": {"specular": 0.742, "metallic": 0.0, "roughness": 0.9}}
