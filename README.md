# NUpbr

This repository holds code to generate a configurable, Physically Based Rendered (PBR) football field.

See NUbook for a more detailed documentation of this project: <https://nubook.netlify.app/system/tools/nupbr>.

![Field Example](./docs/outputs/goals_example.gif)

# Prerequisite

Before starting, download and install [Blender 2.93 LTS](https://www.blender.org/download/lts/2-93/).

# Usage

## Setting Up

- Clone this repo
- Change into the cloned `NUpbr` directory, then into `pbr`
- Install dependencies by running `ensure_dependencies.py` _using the Python binary installed with Blender_. You may have to run it twice: first to install Pip, and then to install the dependencies.
- Download the [resources.zip](http://10.1.0.223:8080/share.cgi?ssid=a65f6f07d4e441d9847192ca8a9bec44) file from the NUbots NAS and copy the `resources` directory from it into the `NUpbr` root directory. **_NOTE:_** to access the download, you need to be in the NUbots lab and connected to the local network.

## Building a Scene

To generate a scene with default field UV map, do the following:

- Run `pbr.py` using Blender's Python API: `blender --python pbr/pbr.py`
- To run the script without the Blender UI, use: `blender -b --python pbr/pbr.py`

This will create a scene, rendering a ball, goals and a field depending on the HDR metadata. The output files will be placed in `output/run_#` where `#` is the auto-generated run number.

The ball UV map, grass texture, and HDRI environment image are randomly selected from the directories configured in [`scene_config.py`](./pbr/config/scene_config.py).

### Generating a Fixed Number of Images Per Ball

By default, `num_images` images are generated (configured in [`output_config.py`](./pbr/config/output_config.py)), with a ball randomly chosen each frame from the ball resource directory.

To instead generate a fixed number of images for *each* ball found in the ball resource directory (cycling through them in order), either set `images_per_ball` in `output_config.py`, or pass it on the command line:

```sh
blender -b --python pbr/pbr.py -- --images-per-ball 100
```

This overrides `num_images` — the total number of images generated will be `images_per_ball * <number of balls found>`.

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
| `location` | Optional value. Specifies the location of the environment. Adjusting the 'z' variable can be used to move the environment map up and down, to make the background in proportion to the rest of the scene. |

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


## Robot Jerseys

The torso of every robot (both the main `Robot` type and the `MiscRobot` types) is tinted with a random jersey colour, re-rolled every frame. Each frame is restricted to at most two distinct jersey colours across all robots in the scene — every robot's jersey is randomly assigned one of two colours picked fresh that frame — though which (if either) of those two actually end up visible depends on which robots are in frame. The colour is recorded as a `#rrggbb` hex string in the `jersey_colour` field of each robot's entry in the meta YAML (see [Metadata](#metadata) below), so it can be used as part of that robot's identifier.

## Metadata

Each frame's `meta/<frame>.yaml` file records the ball and robots that are actually visible in that frame, each with an identifier and its pixel-space bounding box (there is no separate annotations folder — the box is embedded directly here). For example:

```yaml
robots:
  - id: r1
    model: nugus
    jersey_colour: '#3fae6d'
    bbox: [412, 210, 498, 401]
  - id: r4
    model: darwin
    jersey_colour: '#c23b3b'
    bbox: [802, 340, 861, 455]
ball:
  id: ball_003
  bbox: [640, 480, 671, 511]
```

- `id` for a robot is its scene object name (`r1`, `r2`, ...); `id` for the ball is the name of the ball's resource sub-directory (e.g. `ball_003`).
- `model` is `nugus` for the main robots, or the misc-robot type name (`darwin`, `wolfgang`, `nao`, etc.) otherwise.
- `bbox` is `[x_min, y_min, x_max, y_max]` in integer pixel coordinates, origin top-left (standard image convention).
- The camera-mounting robot (`r0`) is excluded, since it isn't a visible target.
- Anything not actually visible this frame — hidden via the HDR's `to_draw` settings, occluded, out of frame, or too small/large to be a plausible detection — is left out of the file entirely rather than included with no box.

### How bounding boxes are computed

Boxes are computed directly from each object's geometry and projected using either a rectilinear or equisolid (fisheye) projection, matching the camera type used for that frame. An object only gets a box if:

- it is actually being rendered this frame (not hidden via the HDR's `to_draw` settings),
- its reference point (the ball's centre, or the robot's root/torso) is in front of the camera and inside the frame,
- it isn't occluded by another object (a robot's own limbs don't count as occlusion), and
- the resulting box isn't implausibly large (`bounding_boxes.max_bbox_size` in `scene_config.py`) — this guards against fisheye edge-case artifacts, e.g. a single limb poking just into frame from behind the camera producing a box that spans almost the whole image.

Otherwise, the object is left out of the meta file for that frame rather than emitting a bad box — but if a robot or the ball would still be visibly on screen despite failing that gate (e.g. clipped at the frame edge, or occluded so only a sliver shows), the entire frame's configuration is re-rolled (all positions, camera target, HDR and ball choice) and retried, up to `max_frame_retries` (in `output_config.py`), rather than write out an image with an unlabelled object in it. If every attempt still leaves something unannotated, the last attempt is rendered anyway and a warning is printed.

The same re-roll also applies if the frame doesn't end up with **between 1 and 4 robots actually visible** (counting both `Robot` and `MiscRobot` instances, still excluding the camera-mounting `r0`) — a frame with 0 or more than 4 visible robots is retried rather than kept.

### Field Line Intersections & Goal Posts (currently unused)

`util.write_goal_post_annotations_from_mask` and `util.write_intersection_annotations_from_mask` can extract segmentation-mask-based bounding boxes for goal posts and field line intersections, but as of the ball/robot-only metadata format above, nothing in `pbr.py` calls them. If you want that output back, they still work the same way and don't integrate well with the segmentation side unless the HDR has blobs on the intersections in the following colours:

- L: magenta [255, 0, 255]
- T: cyan [0, 255, 255]
- X: darker orange [255, 100, 0]

The goal posts must be solid yellow [255, 255, 0] with just the posts and not the top bar or any other part of the goals.