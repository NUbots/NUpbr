# NUpbr

This repository holds code to generate a configurable, Physically Based Rendered (PBR) football field.

![Field Example](./docs/outputs/goals_example.gif)

# Requirements

-   [Blender](https://www.blender.org/download/) (2.79)

# Usage

## Set Up

-   Clone this repo
-   Change into the cloned `NUpbr` directory, then into `pbr`
-   Install dependencies by running `ensure_dependencies.py` _using the Python binary installed with Blender_. You may have to run it twice: first to install Pip, and then to install the dependencies.
-   Download the latest [resources.zip](https://github.com/NUbots/NUpbr/releases) file from Releases and copy the `resources` directory from it into the `NUpbr` root directory. More resources are available on the NUbots NAS.

## Building a Scene

To generate a scene with default field UV map, do the following:

-   Change into the `pbr` directory
-   Run `pbr.py` using Blender's Python API: `blender --python pbr.py`
-   To run the script without the Blender UI, use: `blender -b --python pbr.py`

This will create a scene, rendering a ball, goals and a field depending on the HDR metadata. The output files will be placed in `output/run_#` where `#` is the run number.

The ball UV map, grass texture, and HRDI environment image are randomly selected from the directories configured in [`scene_config.py`](./pbr/config/scene_config.py).

## Custom Resources

The following resources are used for texturing the scene:

| Resource    | Default path         | Config key               |
| :---------- | :------------------- | :----------------------- |
| Ball        | `resources/balls`    | `ball["path"]`           |
| Field UV    | `resources/field_uv` | `field["uv_file"]`       |
| Field grass | `resources/grass`    | `field["grass"]["path"]` |
| Environment | `resources/hdr`      | `environment["path"]`    |

The path to those resources can be configured in the [`pbr/config/scene_config.py`](./pbr/config/scene_config.py) file.

### Field UV

The field UV map is a transparent image with white pixels where the field lines are. Currently, the it is created offline, with the file path specified in the config file at `field["uv_file"]`.

The default field UV map is available in the `resources.zip` file described in the [Set Up](#set-up) section above.

### Field Grass

Custom field grass textures to be considered for selection when generating the scene can be placed in the grass directory (by default `resources/grass`).

Each grass asset should be placed in a sub directory with the corresponding bump, diffuse, and normal files. For example:

- `resources/grass/grass_001/grass_001_bump.jpg` (name must include `bump`)
- `resources/grass/grass_001/grass_001_diffuse.jpg` (name must include `diffuse`)
- `resources/grass/grass_001/grass_001_normal.jpg` (name must include `normal`)

The `resources.zip` file described in the [Set Up](#set-up) section above has a sample grass texture.

### Ball

Custom UV maps to be considered for selection when generating the scene can be placed in the ball UV directory (by default `resources/balls`).

Each ball asset should be placed in a sub directory with the corresponding color, mesh, and normal files. For example:

- `resources/balls/ball_001/ball_001_color.png` (name must include `color` or `colour`)
- `resources/balls/ball_001/ball_001_mesh.fbx` (extension must match the mesh file types configured at `ball["mesh_types"]`)
- `resources/balls/ball_001/ball_001_normal.png` (name must include `normal`)

The `resources.zip` file described in the [Set Up](#set-up) section above has a sample ball texture.

### Environment

Similarly to the ball UV maps, a random HDRI environment image is selected from the pool of images within the scene HDR directory (by default `resources/hdr`).

Each HDRI image should be placed in a sub directory with the corresponding JSON info, mask, and raw HDRI files. For example:

- `resources/hdr/hdr_001/001.json` (must match the info file type configured at `environment["info_type"]`)
- `resources/hdr/hdr_001/001_mask.png` (must match the mask file types configured at `environment["mask_types"]`)
- `resources/hdr/hdr_001/001_raw.hdr` (must match the HDRI file types configured at `environment["hdri_types"]`)

The `resources.zip` file described in the [Set Up](#set-up) section above has a sample HDRI image.
