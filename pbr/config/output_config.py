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
output_base = os.path.join(
    os.path.abspath(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir)
    ),
    "outputs",
    "run_{}",
)

# Find an output directory that isn't already taken
output_dir_no = 0
while os.path.isdir(output_base.format(output_dir_no)):
    try:
    output_dir_no += 1
output_dir = output_base.format(output_dir_no)
        os.makedirs(output_dir, exist_ok=False)
        break
    except:
        pass  # Directory already exists

# Filename length (characters)
filename_len = 10

# Directory names for both the RGB image outputs, the pixel-level segmentation masks, the pixel-level depth image,
# and the meta files
# (Outputs will be stored in <output_dir>/<image_dirname> and <output_dir>/<mask_dirname>)
image_dirname = "raw"
mask_dirname = "seg"
depth_dirname = "depth"
meta_dirname = "meta"

# Maximum depth for normalized depth map (metres)
max_depth = 20

##############################################
##         CONFIGURATION PROCESSING         ##
##############################################

# Create directories
image_dir = os.path.join(output_dir, image_dirname)
mask_dir = os.path.join(output_dir, mask_dirname)
meta_dir = os.path.join(output_dir, meta_dirname)

os.makedirs(image_dir, exist_ok=True)
os.makedirs(mask_dir, exist_ok=True)
os.makedirs(meta_dir, exist_ok=True)

if output_depth:
    depth_dir = os.path.join(output_dir, depth_dirname)
    os.makedirs(depth_dir, exist_ok=True)
