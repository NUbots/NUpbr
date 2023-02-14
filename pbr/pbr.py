#!/usr/local/bin/blender -P

import os
import sys
import random
import bpy
import re
import json

# Add our current position to path to include package
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

# Make sure the python dependencies for this script are installed
import ensure_dependencies

from math import pi, sqrt, ceil

from config import output_config as out_cfg
from config import scene_config

from scene import environment as env
from scene.ball import Ball
from scene.field import Field
from scene.goal import Goal
from scene.camera import Camera
from scene.shape import Shape
from scene.camera_anchor import CameraAnchor
from scene.shadowcatcher import ShadowCatcher
from scene.robot import Robot

# TODO: Reimplement field uv generation with Scikit-Image

import util


def main():
    ##############################################
    ##              ASSET LOADING               ##
    ##############################################

    hdrs, balls, grasses = util.load_assets()

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

    # Create robots to fill the scene
    robots = [
        Robot(
            "r{}".format(ii),
            scene_config.resources["robot"]["mask"]["index"],
            scene_config.resources["robot"],
        )
        for ii in range(scene_config.num_robots + 1)
    ]

    # Construct our shadowcatcher
    shadowcatcher = ShadowCatcher()

    # Generate a new configuration for field configuration
    config = scene_config.configure_scene()

    # Construct our grass field
    field = Field(scene_config.resources["field"]["mask"]["index"])

    # Construct cameras
    cam_l = Camera("Camera_L")
    cam_r = Camera("Camera_R")

    # Set left camera to be parent camera
    # (and so all right camera movements are relative to the left camera position)
    cam_r.set_stereo_pair(cam_l.obj)

    # Mount cameras to eye sockets
    cam_l.set_robot(robots[0].obj)
    cam_r.set_robot(robots[0].obj)

    # Create camera anchor target for random field images
    anch = CameraAnchor()

    # Add randomly generated shapes into scene
    shapes = [Shape("s{}".format(ii), 0) for ii in range(scene_config.num_shapes)]

    ##############################################
    ##               SCENE UPDATE               ##
    ##############################################

    for frame_num in range(1, out_cfg.num_images + 1):
        # Generate a new configuration
        config = scene_config.configure_scene()

        cam_l.update(config["camera"])
        cam_l.obj.keyframe_insert(data_path="location", frame=frame_num)
        cam_l.obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

        # Update shapes
        for ii in range(len(shapes)):
            shapes[ii].update(config["shape"][ii])
            shapes[ii].obj.keyframe_insert(data_path="location", frame=frame_num)
            shapes[ii].obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

        # Select the ball, environment, and grass to use
        hdr_data = random.choice(hdrs)
        ball_data = random.choice(balls)
        grass_data = random.choice(grasses)

        # Load the environment information
        with open(hdr_data["info_path"], "r") as f:
            env_info = json.load(f)

        is_semi_synthetic = (
            not env_info["to_draw"]["goal"] or not env_info["to_draw"]["field"]
        )

        # In that case we must use the height provided by the file
        if is_semi_synthetic:
            config["robot"][0]["position"] = (
                0.0,
                0.0,
                env_info["position"]["z"] - 0.33,
            )

        # Calculate camera location
        camera_loc = (0.0, 0.0, env_info["position"]["z"])
        # Only move camera robot if we're generating the field
        robot_start = 1 if is_semi_synthetic else 0

        points_on_field = util.point_on_field(
            camera_loc, hdr_data["mask_path"], env_info, len(robots) + 1
        )

        for ii in range(robot_start, len(robots)):
            # If we are autoplacing update the configuration
            if (
                config["robot"][ii]["auto_position"]
                and is_semi_synthetic
                and len(points_on_field) > 0
            ):
                # Generate new ground point based on camera (actually robot parent of camera)
                config["robot"][ii]["position"] = (
                    points_on_field[ii][0],
                    points_on_field[ii][1],
                    env_info["position"]["z"] - 0.33
                    if ii == 0
                    else config["robot"][ii]["position"][2],
                )
            # Update robot (and camera)
            robots[ii].update(config["robot"][ii])
            robots[ii].obj.keyframe_insert(data_path="location", frame=frame_num)
            robots[ii].obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

        # Update ball
        # If we are autoplacing update the configuration
        if (
            config["ball"]["auto_position"]
            and is_semi_synthetic
            and len(points_on_field) > 0
        ):
            # Generate new ground point based on camera (actually robot parent of camera)
            config["ball"]["position"] = (
                points_on_field[0][0],
                points_on_field[0][1],
                config["ball"]["position"][2],
            )

        # Apply the updates
        field.update(grass_data, config["field"])
        field.obj.keyframe_insert(data_path="location", frame=frame_num)
        field.obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

        ball.update(ball_data, config["ball"])
        ball.obj.keyframe_insert(data_path="location", frame=frame_num)
        ball.obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

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
        goals[0].obj.keyframe_insert(data_path="location", frame=frame_num)
        goals[0].obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

        goals[1].move(
            (
                -config["field"]["length"] / 2.0,
                0,
                config["goal"]["height"]
                + goal_height_offset * config["goal"]["post_width"],
            )
        )

        goals[1].obj.keyframe_insert(data_path="location", frame=frame_num)
        goals[1].obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

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
        # cam_l.set_tracking_target(tracking_target)
        robots[0].update_main_robot(tracking_target)
        cam_l.update(
            config["camera"],
            targets={
                "robot": {
                    "obj": robots[0].obj,
                    "left_eye": bpy.data.objects["r0_L_Eye_Socket"],
                },
                "target": tracking_target,
            },
        )
        # robots[0].set_tracking_target(tracking_target)

        print(
            '[INFO] Frame {0}: ball: "{1}", map: "{2}", target: {3}'.format(
                frame_num,
                os.path.basename(ball_data["colour_path"]),
                os.path.basename(hdr_data["raw_path"]),
                tracking_target.name,
            )
        )

        # Updates scene to rectify rotation and location matrices
        bpy.context.view_layer.update()

        # Set frame number for current scene
        bpy.context.scene.frame_set(frame_num)

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
