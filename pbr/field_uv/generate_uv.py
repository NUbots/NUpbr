import sys
import os
import re

#############################################
## ADD PYTHON SITE-PACKAGES TO SYSTEM PATH ##
#############################################

# (As Blender can change to custom python install)
LIB_ROOT = ['/usr/local/lib', '/usr/lib']
python_paths = []

for root in LIB_ROOT:
    lib_paths = os.listdir(root)
    for path in lib_paths:
        result = re.search('python3.?[0-9]?', path, re.I)
        if result is not None:
            for s in ['site-packages', 'dist-packages']:
                if os.path.isdir(os.path.join(root, path, s)):
                    for subdir in os.listdir(os.path.join(root, path, s)):
                        result = re.search('Pillow', subdir, re.I)
                        if result is not None:
                            python_paths.append(os.path.join(root, path, s))

# If using the binary without Blender, add project directory to system path
(head, _) = os.path.split(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, head)

#################
## GENERATE UV ##
#################

from config import scene_config as cfg
from field_uv import draw_field

from PIL import Image
from os import path


# Function for checking errors which would make the UV map unrealisable
def error_check():
    isError = False
    if cfg.field['border_width'] < cfg.goal['depth']:
        print('Config Error: goal depth exceeds border strip width')
        isError = True
    # TODO: Make this recursive for sub dictionaries
    if len([
            x for x in draw_field.get_px_measurements(cfg.field).values()
            if (type(x) is int or type(x) is float) and x <= 0
    ]) > 0:
        print(
            'Config Error: one or more measurements equal to or less than zero'
        )
        isError = True

    if isError:
        exit(-1)


def main():
    # Check our config file for errors
    error_check()

    # Determines image size based on field dimensions and image resolution
    image_size = {
        'width': (2 * cfg.field['border_width'] + cfg.field['width']) *
        cfg.field_uv['pixels_per_metre'],
        'height': (2 * cfg.field['border_width'] + cfg.field['length']) *
        cfg.field_uv['pixels_per_metre'],
    }

    # Create our new image
    field_img = Image.new(
        cfg.field_uv['mode'],
        (int(image_size['height']), int(image_size['width'])))

    # Draw our field lines
    draw_field.draw(field_img)

    # Modify image depending on desired orientation
    if cfg.field_uv['orientation'] == 'portrait':
        field_img = field_img.rotate(90, expand=True)

    # Store our field image
    field_img.save(
        path.join(cfg.field_uv['uv_path'],
                  cfg.field_uv['name'] + cfg.field_uv['type']))
