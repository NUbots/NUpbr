from config import scene_config as cfg
from PIL import Image, ImageDraw

def draw_shape(
        image,
        bounds,
        shape='rectangle',
        width=cfg.field['field_line_width'] * cfg.field_uv['pixels_per_metre'],
        colour='white',
        antialias=4
):
    # Create a new mask image for our shape to be drawn on
    mask = Image.new('L', [int(dim * antialias) for dim in image.size])
    draw = ImageDraw.Draw(mask)

    # draw outer shape in white (color) and inner shape in black (transparent)
    for offset, fill in ((2 * width) / -2.0, 'white'), ((2 * width) / 2.0, 'black'):
        left, top = [(value + offset) * antialias for value in bounds[0]]
        right, bottom = [(value - offset) * antialias for value in bounds[1]]
        if (shape == 'rectangle'):
            draw.rectangle([left, top, right, bottom], fill=fill)
        elif (shape == 'ellipse'):
            draw.ellipse([left, top, right, bottom], fill=fill)

    # Draw mask back onto original image
    mask = mask.resize(image.size, Image.LANCZOS)
    image.paste(colour, mask=mask)

# Convert measurements in metres into pixel distances
def get_px_measurements(d):
    field_px = {}
    for f in d:
        if type(d[f]) is int or type(d[f]) is float:
            field_px[f] = d[f] * cfg.field_uv['pixels_per_metre']
        elif type(d[f]) is dict:
            field_px[f] = get_px_measurements(d[f])

    return field_px

# Calculates positions for rectanges for each feature and draws them
def draw(field_img):
    # Calculate centre of image; centre = [x, y]
    centre = [dim / 2 for dim in field_img.size]

    w = (255, 255, 255, 255)

    # Calculate field measurements in pixels
    field_px = get_px_measurements(cfg.field)

    # Calculate centre marker rectangle
    centre_marker_coord = [(centre[0] - 2 * field_px['field_line_width'], centre[1] - field_px['field_line_width']),
                           (centre[0] + 2 * field_px['field_line_width'], centre[1] + field_px['field_line_width'])]

    # Calculate centre circle rectangle boundary
    centre_circle_coord = [(centre[0] - field_px['centre_circle_radius'], centre[1] - field_px['centre_circle_radius']),
                           (centre[0] + field_px['centre_circle_radius'], centre[1] + field_px['centre_circle_radius'])]

    # Calculate centre line rectangle
    centre_line_coord = [(centre[0] - field_px['field_line_width'], centre[1] - field_px['width'] / 2.),
                         (centre[0] + field_px['field_line_width'], centre[1] + field_px['width'] / 2.)]

    # Calculate horizontal and vertical penalty marker rectangle coordinates
    # Horizontal
    l_pen_coord_horz = [(
        centre[0] - field_px['length'] / 2. + field_px['penalty_mark_dist'] - 2 * field_px['field_line_width'],
        centre[1] - field_px['field_line_width']
    ), (
        centre[0] - field_px['length'] / 2. + field_px['penalty_mark_dist'] + 2 * field_px['field_line_width'],
        centre[1] + field_px['field_line_width']
    )]
    r_pen_coord_horz = [(x + field_px['length'] - 2 * field_px['penalty_mark_dist'], y) for (x, y) in l_pen_coord_horz]
    # Vertical
    l_pen_coord_vert = [(
        centre[0] - field_px['length'] / 2. + field_px['penalty_mark_dist'] - field_px['field_line_width'],
        centre[1] - 2 * field_px['field_line_width']
    ), (
        centre[0] - field_px['length'] / 2. + field_px['penalty_mark_dist'] + field_px['field_line_width'],
        centre[1] + 2 * field_px['field_line_width']
    )]
    r_pen_coord_vert = [(x + field_px['length'] - 2 * field_px['penalty_mark_dist'], y) for (x, y) in l_pen_coord_vert]

    # Calculate border coordinates for top left and bottom right corners
    border_coord = [
        (centre[0] - field_px['length'] / 2., centre[1] - field_px['width'] / 2.),
        (centre[0] + field_px['length'] / 2., centre[1] + field_px['width'] / 2.),
    ]

    # Calculate goal box coordinates for both goals
    l_goal_box_coord = [
        (
            centre[0] - field_px['length'] / 2.,
            centre[1] - field_px['goal_area']['width'] / 2.,
        ),
        (
            centre[0] - field_px['length'] / 2. + field_px['goal_area']['length'],
            centre[1] + field_px['goal_area']['width'] / 2.,
        ),
    ]
    r_goal_box_coord = [(x + field_px['length'] - field_px['goal_area']['length'], y) for (x, y) in l_goal_box_coord]

    # Calculate goal interior coordinates for both goals
    goal_px = get_px_measurements(cfg.goal)
    l_goal_int_coord = [
        (
            centre[0] - field_px['length'] / 2. - goal_px['depth'],
            centre[1] - goal_px['width'] / 2.,
        ),
        (
            centre[0] - field_px['length'] / 2.,
            centre[1] + goal_px['width'] / 2.,
        ),
    ]
    r_goal_int_coord = [(x + field_px['length'] + goal_px['depth'], y) for (x, y) in l_goal_int_coord]

    # Create our drawing context
    draw = ImageDraw.Draw(field_img)

    # Draw centre circle
    draw_shape(field_img, centre_circle_coord, shape='ellipse', width=field_px['field_line_width'])

    # Draw centre marker, centre line and penalty lines
    for rect in [
            centre_marker_coord,
            centre_line_coord,
            l_pen_coord_horz,
            l_pen_coord_vert,
            r_pen_coord_horz,
            r_pen_coord_vert,
    ]:
        draw.rectangle(rect, fill=(255, 255, 255, 255))

    # Draw border, goal boxes and goal interiors
    for rect in [border_coord, l_goal_box_coord, r_goal_box_coord, l_goal_int_coord, r_goal_int_coord]:
        draw_shape(field_img, rect, shape='rectangle', width=field_px['field_line_width'])

    return field_img