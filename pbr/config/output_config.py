import os

##############################################
##            USER CONFIGURATION            ##
##############################################

# Number of images to generate
num_images = 1000

# If set, generate this many images for *each* ball found in the ball resource directory
# (resources["ball"]["path"]), cycling through them in order, instead of using num_images with
# a randomly-chosen ball each frame. Overrides num_images when set.
# Can also be set from the command line, e.g.:
#   blender -b --python pbr/pbr.py -- --images-per-ball 100
images_per_ball = None

# If a scene configuration would leave a robot or the ball visible on screen but without a
# bounding box annotation (e.g. clipped at the frame edge, or occluded so only a sliver
# shows), re-roll all positions and try again, up to this many attempts, before giving up
# and rendering the last attempt anyway.
max_frame_retries = 5000

# Stereo output
output_stereo = False
output_depth = False

output_imperfections = True

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
while True:
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
