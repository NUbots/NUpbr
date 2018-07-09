import os

##############################################
##            USER CONFIGURATION            ##
##############################################

# Number of images
num_images = 1

# Stereo output
output_stereo = False

# Absolute output directory to hold the directories for output images and segmentation masks
output_dir = os.path.join(
    os.path.abspath(os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir), os.pardir)),
    'outputs'
)

# Directory names for both the RGB image outputs and the pixel-level segmentation masks
# (Outputs will be stored in <output_dir>/<image_dirname> and <output_dir>/<mask_dirname>)
image_dirname = 'raw'
mask_dirname = 'seg'

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