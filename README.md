# NUpbr

This repository holds code to generate a configurable, Physically Based Rendered (PBR) football field.

See NUbook for a more detailed documentation of this project: <https://nubook.netlify.app/system/tools/nupbr>.

![Field Example](./docs/outputs/goals_example.gif)

# Prerequisite

Before starting, download and install [Blender 2.79](https://www.blender.org/download/previous-versions/).

# Usage

## Setting Up

- Clone this repo
- Change into the cloned `NUpbr` directory, then into `pbr`
- Install dependencies by running `ensure_dependencies.py` _using the Python binary installed with Blender_. You may have to run it twice: first to install Pip, and then to install the dependencies.
- Download the [resources.zip](http://10.1.0.223:8080/share.cgi?ssid=05GE7Tx) file from the NUbots NAS and copy the `resources` directory from it into the `NUpbr` root directory. **_NOTE:_** to access the download, you need to be in the NUbots lab and connected to the local network.

## Building a Scene

To generate a scene with default field UV map, do the following:

- Run `pbr.py` using Blender's Python API: `blender --python pbr/pbr.py`
- To run the script without the Blender UI, use: `blender -b --python pbr/pbr.py`

This will create a scene, rendering a ball, goals and a field depending on the HDR metadata. The output files will be placed in `output/run_#` where `#` is the auto-generated run number.

The ball UV map, grass texture, and HDRI environment image are randomly selected from the directories configured in [`scene_config.py`](./pbr/config/scene_config.py).

## Specifying Custom Resources

The following resources are used for texturing the scene:

| Resource             | Default path         | Config key            |
| :------------------- | :------------------- | :-------------------- |
| Ball                 | `resources/balls`    | `ball["path"]`        |
| Field UV (file type) | `.png`               | `field["type"]`       |
| Field UV (file path) | `resources/field_uv` | `field["uv_path"]`    |
| Field UV (file name) | `default`            | `field["name"]`       |
| Environment          | `resources/hdr`      | `environment["path"]` |

The path to those resources can be configured in the [`pbr/config/scene_config.py`](./pbr/config/scene_config.py) file.

### Field UV

The field UV map is a transparent image with white pixels where the field lines are. Currently, it is created offline, with the file path specified in the config file at `field["uv_file"]`.

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

Each HDRI image should be placed in a sub directory with the corresponding JSON metadata, mask, and raw HDRI files. For example:

- `resources/hdr/hdr_001/001.json` (must match the metadata file type configured at `environment["info_type"]`)
- `resources/hdr/hdr_001/001_mask.png` (optional; if present, must match the mask file types configured at `environment["mask_types"]`)
- `resources/hdr/hdr_001/001_raw.hdr` (must match the HDRI file types configured at `environment["hdri_types"]`)

The `resources.zip` file described in the [Set Up](#set-up) section above has a sample HDRI image.

The HDR JSON metadata file may have the following fields:

| Field                     | Description                                                                                                                                           |
| :------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rotation`                | Specifies the rotation of the environment. Used to rotate the environment map in Blender, and used when projecting points to the ground.              |
| `position`                | Used to place the camera and the robot in the scene. Specifically uses `position["z"]` for the camera height and the robot position along the z axis. |
| `to_draw`                 | Specifies which objects (ball, goal, field) to draw. Objects set to `true` are drawn, and those set to `false` are not.                               |
| `ball_limits["position"]` | Specifies a region in which the ball can be randomly placed.                                                                                          |

<details>
<summary>View example HDR metadata file</summary>

```json
{
  "rotation": {
    "roll": 1.86842,
    "pitch": 0.557895,
    "yaw": 4.5
  },
  "position": {
    "x": 0,
    "y": 0,
    "z": 1.2
  },
  "to_draw": {
    "ball": true,
    "goal": false,
    "field": false
  },
  "ball_limits": {
    "position": {
      "x": [-4.6, 4.46],
      "y": [-2.76, 3.45],
      "z": [0.095, 0.1]
    }
  }
}
```

</details>
