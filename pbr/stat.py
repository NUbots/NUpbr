import os
import matplotlib.pyplot as plt
import json

from config import scene_config as scene_cfg
from config import output_config as out_cfg

def main():
	data = []

	# Initialise window limits
	ball = {
		'x' : [],
		'y' : []
	}

	camera = {
		'left' : {
			'x' : [],
			'y' : []
		},
		'right' : {
			'x' : [],
			'y' : []
		}
	}

	metadata_files = os.listdir(out_cfg.meta_dir)

	# Collect data
	for file in metadata_files:
		with open(os.path.join(out_cfg.meta_dir, file), 'r') as f:
			contents = json.load(f)
			data.append(contents)
			# Get ball measurements
			ball['x'].append(contents['ball']['position'][0])
			ball['y'].append(contents['ball']['position'][1])

			# Get camera measurements
			camera['left']['x'].append(contents['camera']['left']['position'][0])
			camera['left']['y'].append(contents['camera']['left']['position'][1])
			camera['right']['x'].append(contents['camera']['right']['position'][0])
			camera['right']['y'].append(contents['camera']['right']['position'][1])

	print(ball)
	print(camera)

	# Plot
	fig, ax = plt.subplots()
	ax.scatter(ball['x'], ball['y'], label='Ball')
	ax.scatter(camera['left']['x'], camera['left']['y'], label='L Camera')
	ax.scatter(camera['right']['x'], camera['right']['y'], label='R Camera')
	ax.grid(True)
	ax.set_ylim()
	ax.legend()

	plt.show()


if __name__ == '__main__':
    main()
