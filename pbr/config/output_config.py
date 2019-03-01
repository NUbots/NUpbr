import os

##############################################
##            USER CONFIGURATION            ##
##############################################

# Number of images to generate
num_images = 1000

# Stereo output
output_stereo = False
output_depth = False

# Absolute output directory to hold the directories for output images and segmentation masks
output_dir = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir)), 'outputs'
)

# Filename length (characters)
filename_len = 10

# Directory names for both the RGB image outputs, the pixel-level segmentation masks, the pixel-level depth image,
# and the meta files
# (Outputs will be stored in <output_dir>/<image_dirname> and <output_dir>/<mask_dirname>)
image_dirname = 'raw'
mask_dirname = 'seg'
depth_dirname = 'depth'
meta_dirname = 'meta'

# Maximum depth for normalized depth map (metres)
max_depth = 20

##############################################
##         CONFIGURATION PROCESSING         ##
##############################################

# Create directories
if not os.path.isdir(output_dir):
    os.mkdir(output_dir)

image_dir = os.path.join(output_dir, image_dirname)
if not os.path.isdir(image_dir):
    os.mkdir(image_dir)

mask_dir = os.path.join(output_dir, mask_dirname)
if not os.path.isdir(mask_dir):
    os.mkdir(mask_dir)

depth_dir = os.path.join(output_dir, depth_dirname)
if not os.path.isdir(depth_dir):
    os.mkdir(depth_dir)

meta_dir = os.path.join(output_dir, meta_dirname)
if not os.path.isdir(meta_dir):
    os.mkdir(meta_dir)
