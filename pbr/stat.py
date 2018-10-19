import os
import json
import matplotlib.pyplot as plt
import numpy as np
from math import sqrt
from scipy import ndimage

from config import scene_config as scene_cfg
from config import output_config as out_cfg

def get_data(filepath):
    data = []

    metadata_files = os.listdir(filepath)

    # Collect data
    for file in metadata_files:
        with open(os.path.join(out_cfg.meta_dir, file), 'r') as f:
            contents = json.load(f)
            data.append(contents)

    return data

def plot_positions(data):

    # Ball and camera position containers
    ball = {'x': [], 'y': []}
    camera = {'left': {'x': [], 'y': []}, 'right': {'x': [], 'y': []}}

    # Distance from ball to cam container
    dist = []
    N_BINS = 10
    dist_histogram = []

    # Flag to set if stereo dataset
    is_stereo = False
    max_norm = None

    for d in data:
        # Get ball measurements
        ball_pt = d['ball']['position']
        ball['x'].append(ball_pt[0])
        ball['y'].append(ball_pt[1])
        cam_point = []

        # Get camera measurements
        if 'left' in d['camera']:
            is_stereo = True

            # Left camera
            l_cam_pt = d['camera']['left']['position']
            camera['left']['x'].append(l_cam_pt[0])
            camera['left']['y'].append(l_cam_pt[1])

            # Right camera
            r_cam_pt = d['camera']['right']['position']
            camera['right']['x'].append(r_cam_pt[0])
            camera['right']['y'].append(r_cam_pt[1])

            ball_to_l_cam_vec = (ball_pt[0] - l_cam_pt[0], ball_pt[1] - l_cam_pt[1], ball_pt[2] - l_cam_pt[2])
            ball_to_r_cam_vec = (ball_pt[0] - r_cam_pt[0], ball_pt[1] - r_cam_pt[1], ball_pt[2] - r_cam_pt[2])
            ball_to_cam_vec = (
                ball_to_l_cam_vec[0] + ball_to_r_cam_vec[0] / 2.,
                ball_to_l_cam_vec[1] + ball_to_r_cam_vec[1] / 2.,
                ball_to_l_cam_vec[2] + ball_to_r_cam_vec[2] / 2.,
            )
        else:
            cam_pt = d['camera']['position']
            camera['left']['x'].append(cam_pt[0])
            camera['left']['y'].append(cam_pt[1])

            ball_to_cam_vec = (ball_pt[0] - cam_pt[0], ball_pt[1] - cam_pt[1], ball_pt[2] - cam_pt[2])

        norm = sqrt(ball_to_cam_vec[0]**2 + ball_to_cam_vec[1]**2 + ball_to_cam_vec[2]**2)
        if not max_norm or norm > max_norm:
            max_norm = norm
        dist.append(norm)

    dist_increment = max_norm / N_BINS
    if (dist_increment != None):
        for inc in range(0, N_BINS):
            dist_histogram.append(
                len([x for x in dist if x > dist_increment * inc and x <= (dist_increment * (inc + 1))])
            )

    ## Figure 1: Positions
    fig1, ax1 = plt.subplots()
    plt.title('Distribution of Ball and Camera Positions')
    plt.xlabel('x (m)')
    plt.ylabel('y (m)')
    plt.ylim(-scene_cfg.field['width'] / 2., scene_cfg.field['width'] / 2.)
    plt.xlim(-scene_cfg.field['length'] / 2., scene_cfg.field['length'] / 2.)

    rot = 90 if scene_cfg.field_uv['orientation'] == 'portrait' else 0
    field_uv = ndimage.rotate(
        plt.imread(
            os.path.join(scene_cfg.field_uv['uv_path'], scene_cfg.field_uv['name'] + scene_cfg.field_uv['type'])
        ),
        rot,
    )

    # Draw Ball and Camera Positions
    ax1.set_facecolor('#38ff01')
    ax1.imshow(
        field_uv,
        extent=[
            -scene_cfg.field['length'] / 2.,
            scene_cfg.field['length'] / 2.,
            -scene_cfg.field['width'] / 2.,
            scene_cfg.field['width'] / 2.,
        ]
    )

    ax1.scatter(ball['x'], ball['y'], color='#ff6701', label='Ball')
    l_cam_label = 'Camera'
    if len(camera['right']['x']) > 0:
        l_cam_label = 'L Camera'
        ax1.scatter(camera['right']['x'], camera['right']['y'], color='#5500ff', label='R Camera')
    ax1.scatter(camera['left']['x'], camera['left']['y'], color='#0479ff', label=l_cam_label)
    ax1.grid(True)
    ax1.legend()

    ## Figure 2: Distances
    fig2, ax2 = plt.subplots()
    x = np.arange(N_BINS) * dist_increment
    # Setup xticks for distance ranges
    xticks = []
    for i in range(0, N_BINS):
        if (i + 1 < N_BINS):
            xticks.append('{0:.3} - {1:.3}'.format(x[i], x[i + 1]))
        else:
            xticks.append('>{0:.3}'.format(x[i]))

    plt.title('Distribution of Distance from Ball to Camera')
    plt.xlabel('Distance Range (m)')
    plt.ylabel('Number of Instances')
    plt.xticks(x, xticks)

    ax2.bar(x, dist_histogram)
    ax2.grid(True)
    ax2.set_axisbelow(True)

    plt.show()

def main():
    data = get_data(out_cfg.meta_dir)

    plot_positions(data)

if __name__ == '__main__':
    main()
