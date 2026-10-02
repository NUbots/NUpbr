#!/usr/local/bin/blender -P

import os
import sys
import random
import bpy
import re
import json
import argparse
import yaml

# Add our current position to path to include package
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))


from math import pi

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
from scene.misc_robot import MiscRobot

# TODO: Reimplement field uv generation with Scikit-Image

import util


def parse_args():
    # Blender passes its own arguments before a "--", with any script-specific arguments after it
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--images-per-ball",
        type=int,
        default=None,
        help="Generate this many images for each ball found in the ball resource directory, "
        "cycling through them in order. Overrides num_images and the --images-per-ball value "
        "in output_config.py.",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()
    images_per_ball = (
        args.images_per_ball if args.images_per_ball is not None else out_cfg.images_per_ball
    )

    ##############################################
    ##              ASSET LOADING               ##
    ##############################################

    hdrs, balls, grasses = util.load_assets()

    num_images = images_per_ball * len(balls) if images_per_ball is not None else out_cfg.num_images

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

    misc_robots = [
        MiscRobot(
            "r{}".format(len(robots) + ii),
            scene_config.resources["misc_robot"]["mask"]["index"],
            *scene_config.choose_misc_robot(),
        )
        for ii in range(scene_config.num_misc_robots)
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

    # Create camera anchor target for random field images
    anch = CameraAnchor()

    # Add randomly generated shapes into scene
    shapes = [Shape("s{}".format(ii), 0) for ii in range(scene_config.num_shapes)]

    ##############################################
    ##               SCENE UPDATE               ##
    ##############################################

    for frame_num in range(1, num_images + 1):
        # A scene configuration is retried (all positions re-rolled) if it would leave a
        # robot or the ball visible on screen without a bounding box annotation - see the
        # visibility check below.
        for attempt in range(out_cfg.max_frame_retries):
            # Generate a new configuration
            config = scene_config.configure_scene()

            cam_l.update(config["camera"])

            if out_cfg.output_imperfections:
                composition_nodes = bpy.context.scene.node_tree.nodes
                env.randomise_imperfections(
                    composition_nodes["Blur"],
                    composition_nodes["RGB Curves"],
                    composition_nodes["Mix"],
                    composition_nodes["Exposure"],
                )

            # Update shapes
            for ii in range(len(shapes)):
                shapes[ii].update(config["shape"][ii])
                shapes[ii].obj.keyframe_insert(data_path="location", frame=frame_num)
                shapes[ii].obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

            # Select the ball, environment, and grass to use
            hdr_data = random.choice(hdrs)
            if images_per_ball is not None:
                # Cycle deterministically through each ball, images_per_ball images at a time
                ball_data = balls[(frame_num - 1) // images_per_ball]
            else:
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
            print("Points on field: \n", points_on_field)
            # Generate new world points for the robots and use this to update their location
            world_points = util.generate_moves(scene_config.field_dims)
            for ii in range(robot_start, len(robots)):
                # If we are autoplacing update the configuration
                if (
                    config["robot"][ii]["auto_position"]
                    and is_semi_synthetic
                    and len(points_on_field) > 0
                ):

                    # Generate new ground point based on camera (actually robot parent of camera)
                    config["robot"][ii]["position"] = (
                        world_points[ii - 1][0],
                        world_points[ii - 1][1],
                        (
                            world_points[ii - 1][2]
                            if ii == 0
                            else config["robot"][ii]["position"][2]
                        ),
                    )
                # Update robot (and camera)
                robots[ii].update(config["robot"][ii])
                robots[ii].obj.keyframe_insert(data_path="location", frame=frame_num)
                robots[ii].obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

            num_robots = len(robots) - 1

            for ii in range(len(misc_robots)):
                config["misc_robot"][ii]["position"] = (
                    world_points[ii + num_robots][0],
                    world_points[ii + num_robots][1],
                    misc_robots[ii].get_height(),
                )
                misc_robots[ii].update(config["misc_robot"][ii])
                misc_robots[ii].obj.keyframe_insert(data_path="location", frame=frame_num)
                misc_robots[ii].obj.keyframe_insert(
                    data_path="rotation_euler", frame=frame_num
                )

            # Restrict this frame to at most two distinct jersey colours across all robots
            jersey_palette = [util.random_jersey_colour() for _ in range(2)]
            for robot in robots[1:]:  # Skip robots[0], the camera-mounting robot
                robot.set_jersey_colour(*random.choice(jersey_palette))
            for misc_robot in misc_robots:
                misc_robot.set_jersey_colour(*random.choice(jersey_palette))

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

            # Update the camera then insert the rotation keyframe after rotating the camera
            # Updates scene to rectify rotation and location matrices and set the frame number for the current scene
            cam_l.obj.keyframe_insert(data_path="location", frame=frame_num)
            cam_l.obj.keyframe_insert(data_path="rotation_euler", frame=frame_num)

            bpy.context.scene.frame_set(frame_num)

            cam_l.set_tracking_target(tracking_target)

            # Render for the main camera only - set this before the visibility check below,
            # since it projects geometry through this camera
            bpy.context.scene.camera = cam_l.obj

            bpy.context.view_layer.update()

            # Compute each robot/ball's bounding box once per attempt and reuse it below, both
            # for the retry check and (once accepted) for the meta file - avoids redoing the
            # underlying raycasts twice.
            robot_bboxes = [
                (robot, util.write_annotations(robot.obj))
                for robot in robots[1:]  # Skip robots[0], the camera-mounting robot
            ]
            misc_bboxes = [
                (misc_robot, util.write_annotations(bpy.data.objects[misc_robot.name + "_Torso"]))
                for misc_robot in misc_robots
            ]
            ball_bbox = util.write_annotations(ball.obj)

            num_visible_robots = sum(1 for _, bbox in robot_bboxes + misc_bboxes if bbox is not None)

            # Re-roll everything and try again if this configuration would either:
            #  - leave something visible on screen without a bounding box annotation (e.g.
            #    clipped at the frame edge, or occluded so only a sliver shows), or
            #  - not have between 1 and 4 robots actually visible in frame.
            # rather than write out an image that doesn't meet those requirements.
            needs_retry = (
                any(
                    util.is_visible_but_unannotated(robot.obj, is_robot=True)
                    for robot in robots[1:]
                )
                or any(
                    util.is_visible_but_unannotated(
                        bpy.data.objects[misc_robot.name + "_Torso"], is_robot=True
                    )
                    for misc_robot in misc_robots
                )
                or util.is_visible_but_unannotated(ball.obj, is_robot=False)
                or not (1 <= num_visible_robots <= 4)
            )

            if not needs_retry:
                break

            print(
                f"[INFO] Frame {frame_num}: attempt {attempt + 1} rejected "
                f"({num_visible_robots} robots visible), re-rolling scene"
            )
        else:
            print(
                f"[WARN] Frame {frame_num}: still didn't meet requirements after "
                f"{out_cfg.max_frame_retries} attempts, rendering the last attempt anyway"
            )

        print(
            '[INFO] Frame {0}: ball: "{1}", map: "{2}", target: {3}'.format(
                frame_num,
                os.path.basename(ball_data["colour_path"]),
                os.path.basename(hdr_data["raw_path"]),
                tracking_target.name,
            )
        )

        ##############################################
        ##                RENDERING                 ##
        ##############################################

        filename = str(frame_num).zfill(out_cfg.filename_len)

        if out_cfg.output_depth:
            # Set depth filename
            render_layer_toggle[2].file_slots[0].path = filename + ".exr"

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

        ##############################################
        ##              META GENERATION             ##
        ##############################################

        # Ball/robot identifiers with their pixel-space bounding box, reusing the visibility
        # check computed above (no separate annotations folder). Anything not actually visible
        # this frame (hidden, occluded, out of frame, ...) is left out entirely.
        ball_id = os.path.basename(os.path.dirname(ball_data["colour_path"]))

        robot_meta = []
        for robot, bbox in robot_bboxes:
            if bbox is not None:
                robot_meta.append(
                    {
                        "id": robot.name,
                        "model": "nugus",
                        "jersey_colour": robot.jersey_colour,
                        "bbox": list(bbox),
                    }
                )

        for misc_robot, bbox in misc_bboxes:
            if bbox is not None:
                robot_meta.append(
                    {
                        "id": misc_robot.name,
                        "model": misc_robot.model,
                        "jersey_colour": misc_robot.jersey_colour,
                        "bbox": list(bbox),
                    }
                )

        meta = {"robots": robot_meta}

        if ball_bbox is not None:
            meta["ball"] = {"id": ball_id, "bbox": list(ball_bbox)}

        with open(
            os.path.join(out_cfg.meta_dir, "{}.yaml".format(filename)), "w"
        ) as meta_file:
            yaml.dump(meta, meta_file, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    main()
