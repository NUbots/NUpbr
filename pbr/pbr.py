#!/usr/local/bin/blender -P

import os
import sys
import random
import bpy
import re
import json

# Add our current position to path to include package
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from math import pi, sqrt, ceil

from config import output_config as out_cfg
from config import scene_config
from scene import environment as env
from scene.ball import Ball
from scene.field import Field
from scene.goal import Goal
from scene.camera import Camera
from scene.camera_anchor import CameraAnchor
from scene.shadowcatcher import ShadowCatcher

# TODO: Reimplement field uv generation with Scikit-Image

import util


def main():
    ##############################################
    ##              ASSET LOADING               ##
    ##############################################

    hdrs, balls = util.load_assets()

    ##############################################
    ##             ENVIRONMENT SETUP            ##
    ##############################################

    with open(hdrs[0]["info_path"], "r") as f:
        env_info = json.load(f)
    render_layer_toggle, world = util.setup_environment(hdrs[0], env_info)

    ##############################################
    ##            SCENE CONSTRUCTION            ##
    ##############################################

    # Construct our default UV sphere ball
    ball = Ball("Ball", scene_config.resources["ball"]["mask"]["index"], balls[0])

    # Construct our goals
    goals = [
        Goal(scene_config.resources["goal"]["mask"]["index"]),
        Goal(scene_config.resources["goal"]["mask"]["index"]),
    ]

    # Construct our shadowcatcher
    shadowcatcher = ShadowCatcher()

    # Generate a new configuration for field configuration
    config = scene_config.configure_scene()

    # Construct our grass field
    field = Field(scene_config.resources["field"]["mask"]["index"])
    field.update(config["field"])

    # Construct cameras
    cam_l = Camera("Camera_L")
    cam_r = Camera("Camera_R")

    # Set left camera to be parent camera
    # (and so all right camera movements are relative to the left camera position)
    cam_r.set_stereo_pair(cam_l.obj)

    # Create camera anchor target for random field images
    anch = CameraAnchor()

    ##############################################
    ##               SCENE UPDATE               ##
    ##############################################

    for frame_num in range(1, out_cfg.num_images + 1):

        # Generate a new configuration
        config = scene_config.configure_scene()

        # Select the ball and environment to use
        hdr_data = random.choice(hdrs)
        ball_data = random.choice(balls)

        # Load the environment information
        with open(hdr_data["info_path"], "r") as f:
            env_info = json.load(f)

        # Update camera
        cam_l.update(config["camera"])
        cam_r.move((config["camera"]["stereo_camera_distance"], 0, 0))

        # Update ball
        # If we are autoplacing update the configuration
        if config["ball"]["auto_position"] and not env_info["to_draw"]["field"]:
            ground_point = util.point_on_field(
                cam_l.obj, hdr_data["mask_path"], env_info
            )
            config["ball"]["position"] = (
                ground_point[0],
                ground_point[1],
                config["ball"]["position"][2],
            )

        # Apply the updates
        ball.update(ball_data, config["ball"])

        # Update goals
        for g in goals:
            g.update(config["goal"])
        goals[1].rotate((0, 0, pi))
        goal_height_offset = -3.0 if config["goal"]["shape"] == "square" else -1.0
        goals[0].move(
            (
                config["field"]["length"] / 2.0,
                0,
                config["goal"]["height"]
                + goal_height_offset * config["goal"]["post_width"],
            )
        )
        goals[1].move(
            (
                -config["field"]["length"] / 2.0,
                0,
                config["goal"]["height"]
                + goal_height_offset * config["goal"]["post_width"],
            )
        )

        # Hide objects based on environment map
        ball.obj.hide_render = not env_info["to_draw"]["ball"]
        field.hide_render(not env_info["to_draw"]["field"])
        goals[0].hide_render(not env_info["to_draw"]["goal"])
        goals[1].hide_render(not env_info["to_draw"]["goal"])

        # Update anchor
        anch.update(config["anchor"])

        # Set a tracking target randomly to anchor/ball or goal
        valid_tracks = []
        if env_info["to_draw"]["ball"]:  # Only track balls if it's rendered
            valid_tracks.append(ball)
        if env_info["to_draw"]["goal"]:  # Only track goals if they're rendered
            valid_tracks.append(random.choice(goals))
        if env_info["to_draw"][
            "field"
        ]:  # Only pick random points if the field is rendered
            valid_tracks.append(anch)

        tracking_target = random.choice(valid_tracks).obj
        cam_l.set_tracking_target(tracking_target)

        print(
            '[INFO] Frame {0}: ball: "{1}", map: "{2}", target: {3}'.format(
                frame_num,
                os.path.basename(ball_data["colour_path"]),
                os.path.basename(hdr_data["raw_path"]),
                tracking_target.name,
            )
        )

        # Updates scene to rectify rotation and location matrices
        bpy.context.scene.update()

        ##############################################
        ##                RENDERING                 ##
        ##############################################

        filename = str(frame_num).zfill(out_cfg.filename_len)

        if out_cfg.output_depth:
            # Set depth filename
            render_layer_toggle[2].file_slots[0].path = filename + ".exr"

        # Render for the main camera only
        bpy.context.scene.camera = cam_l.obj

        # Use multiview stereo if stereo output is enabled
        # (this will automatically render the second camera)
        if out_cfg.output_stereo:
            bpy.context.scene.render.use_multiview = True

        # Render raw image
        util.render_image(
            isMaskImage=False,
            toggle=render_layer_toggle,
            shadowcatcher=shadowcatcher,
            ball=ball,
            world=world,
            env=env,
            hdr_path=hdr_data["raw_path"],
            strength=config["environment"]["strength"],
            env_info=env_info,
            output_path=os.path.join(out_cfg.image_dir, "{}.png".format(filename)),
        )

        # Render mask image
        util.render_image(
            isMaskImage=True,
            toggle=render_layer_toggle,
            shadowcatcher=shadowcatcher,
            ball=ball,
            world=world,
            env=env,
            hdr_path=hdr_data["mask_path"],
            strength=1.0,
            env_info=env_info,
            output_path=os.path.join(out_cfg.mask_dir, "{}.png".format(filename)),
        )

        if out_cfg.output_depth:
            # Rename our mis-named depth file(s) due to Blender's file output node naming scheme!
            if out_cfg.output_stereo:
                os.rename(
                    os.path.join(out_cfg.depth_dir, filename) + "_L.exr0001",
                    os.path.join(out_cfg.depth_dir, filename) + "_L.exr",
                )
                os.rename(
                    os.path.join(out_cfg.depth_dir, filename) + "_R.exr0001",
                    os.path.join(out_cfg.depth_dir, filename) + "_R.exr",
                )
            else:
                os.rename(
                    os.path.join(out_cfg.depth_dir, filename) + ".exr0001",
                    os.path.join(out_cfg.depth_dir, filename) + ".exr",
                )

        # Generate meta file
        with open(
            os.path.join(out_cfg.meta_dir, "{}.yaml".format(filename)), "w"
        ) as meta_file:
            # Gather metadata
            meta = config

            meta.update({"rendered": env_info["to_draw"]})

            # Add basic camera information
            meta["camera"]["focus"] = tracking_target.name
            meta["camera"]["lens"] = {}
            meta["camera"]["lens"]["sensor_height"] = cam_l.cam.sensor_height
            meta["camera"]["lens"]["sensor_width"] = cam_l.cam.sensor_width

            # Add the final camera matrices
            if not out_cfg.output_stereo:
                meta["camera"]["matrix"] = util.matrix_to_list(cam_l.obj.matrix_world)
            else:
                template = meta["camera"]
                meta["camera"] = {
                    "left": {
                        **template,
                        "matrix": util.matrix_to_list(cam_l.obj.matrix_world),
                    },
                    "right": {
                        **template,
                        "matrix": util.matrix_to_list(cam_r.obj.matrix_world),
                    },
                }

            meta["environment"]["file"] = os.path.relpath(
                hdr_data["raw_path"], scene_config.res_path
            )

            # Write metadata to file
            json.dump(meta, meta_file, indent=4, sort_keys=True)


if __name__ == "__main__":
    main()
