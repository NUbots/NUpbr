#!/usr/bin/env python3
"""
Interactive Image Viewer with Bounding Box Annotations

This tool displays images from a folder with their corresponding bounding box annotations.
Supports YOLO format annotations and provides interactive navigation.

Usage:
    python visualise_bboxes.py --images <image_folder> --annotations <annotation_folder> [--config <yaml_file>]

Controls:
    - Right Arrow / Space: Next image
    - Left Arrow: Previous image
    - Q / Escape: Quit
    - S: Save current image with annotations
    - H: Show/hide help overlay
"""

import argparse
import os
import sys
import cv2
import glob
import yaml
from pathlib import Path

class BBoxVisualiser:
    def __init__(self, image_folder, annotation_folder, config_file=None):
        self.image_folder = Path(image_folder)
        self.annotation_folder = Path(annotation_folder)
        self.config_file = config_file
        self.current_index = 0
        self.show_help = False
        
        # Default class names and colors
        self.class_names = {
            0: "ball",
            1: "goal_post", 
            2: "robot",
            3: "L_intersection",
            4: "T_intersection",
            5: "X_intersection"
        }
        
        # Color palette for different classes (BGR format)
        self.colors = [
            (0, 255, 0),    # Green for ball
            (255, 0, 0),    # Blue for goal_post
            (0, 0, 255),    # Red for robot
            (255, 255, 0),  # Cyan for L_intersection
            (255, 0, 255),  # Magenta for T_intersection
            (0, 255, 255),  # Yellow for X_intersection
        ]
        
        # Load configuration if provided
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
        
        # Get list of images
        self.image_files = self.get_image_files()
        if not self.image_files:
            raise ValueError(f"No images found in {self.image_folder}")
        
        print(f"Found {len(self.image_files)} images")
        print("Controls: Arrow keys to navigate, 'q' to quit, 's' to save, 'h' for help")
    
    def load_config(self, config_file):
        """Load class names from YAML config file"""
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                if 'names' in config:
                    self.class_names = config['names']
                    print(f"Loaded {len(self.class_names)} classes from config")
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
    
    def get_image_files(self):
        """Get sorted list of image files"""
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']
        image_files = []
        for ext in extensions:
            image_files.extend(glob.glob(str(self.image_folder / ext)))
        return sorted(image_files)
    
    def load_annotations(self, image_path):
        """Load bounding box annotations for an image"""
        image_name = Path(image_path).stem
        annotation_file = self.annotation_folder / f"{image_name}.txt"
        
        annotations = []
        if annotation_file.exists():
            try:
                with open(annotation_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            parts = line.split()
                            if len(parts) >= 5:
                                class_id = int(parts[0])
                                center_x = float(parts[1])
                                center_y = float(parts[2])
                                width = float(parts[3])
                                height = float(parts[4])
                                annotations.append({
                                    'class_id': class_id,
                                    'center_x': center_x,
                                    'center_y': center_y,
                                    'width': width,
                                    'height': height
                                })
            except Exception as e:
                print(f"Error loading annotations for {image_name}: {e}")
        
        return annotations
    
    def yolo_to_pixel_coords(self, annotation, img_width, img_height):
        """Convert YOLO normalised coordinates to pixel coordinates"""
        center_x = annotation['center_x'] * img_width
        center_y = annotation['center_y'] * img_height
        width = annotation['width'] * img_width
        height = annotation['height'] * img_height
        
        x1 = int(center_x - width / 2)
        y1 = int(center_y - height / 2)
        x2 = int(center_x + width / 2)
        y2 = int(center_y + height / 2)
        
        return x1, y1, x2, y2
    
    def draw_bounding_boxes(self, image, annotations):
        """Draw bounding boxes and labels on the image"""
        img_height, img_width = image.shape[:2]
        
        for annotation in annotations:
            class_id = annotation['class_id']
            x1, y1, x2, y2 = self.yolo_to_pixel_coords(annotation, img_width, img_height)
            
            # Get color for this class
            color = self.colors[class_id % len(self.colors)]
            
            # Draw bounding box
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # Draw class label
            class_name = self.class_names.get(class_id, f"class_{class_id}")
            label = f"{class_name}"
            
            # Calculate label size and position
            (label_width, label_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            
            # Draw label background
            cv2.rectangle(
                image,
                (x1, y1 - label_height - baseline - 5),
                (x1 + label_width + 5, y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                image,
                label,
                (x1 + 2, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
        
        return image
    
    def draw_help_overlay(self, image):
        """Draw help text overlay"""
        help_text = [
            "Controls:",
            "Right Arrow / Space: Next image",
            "Left Arrow: Previous image", 
            "S: Save current image",
            "H: Toggle this help",
            "Q / Escape: Quit"
        ]
        
        # Semi-transparent overlay
        overlay = image.copy()
        cv2.rectangle(overlay, (10, 10), (400, 180), (0, 0, 0), -1)
        image = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)
        
        # Draw help text
        for i, text in enumerate(help_text):
            cv2.putText(
                image,
                text,
                (20, 40 + i * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
        
        return image
    
    def draw_info_overlay(self, image, image_name, num_annotations):
        """Draw image information overlay"""
        info_text = [
            f"Image: {image_name}",
            f"Annotations: {num_annotations}",
            f"{self.current_index + 1}/{len(self.image_files)}"
        ]
        
        img_height = image.shape[0]
        for i, text in enumerate(info_text):
            cv2.putText(
                image,
                text,
                (10, img_height - 60 + i * 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            cv2.putText(
                image,
                text,
                (10, img_height - 60 + i * 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                1
            )
        
        return image
    
    def save_current_image(self, image, image_name):
        """Save the current image with annotations"""
        output_path = f"{image_name}_with_boxes.png"
        cv2.imwrite(output_path, image)
        print(f"Saved annotated image: {output_path}")
    
    def run(self):
        """Main visualisation loop"""
        cv2.namedWindow('Image Viewer with Annotations', cv2.WINDOW_NORMAL)
        
        while True:
            # Load current image
            current_image_path = self.image_files[self.current_index]
            image_name = Path(current_image_path).name
            
            try:
                image = cv2.imread(current_image_path)
                if image is None:
                    print(f"Could not load image: {current_image_path}")
                    self.current_index = (self.current_index + 1) % len(self.image_files)
                    continue
                
                # Load annotations
                annotations = self.load_annotations(current_image_path)
                
                # Draw bounding boxes
                if annotations:
                    image = self.draw_bounding_boxes(image, annotations)
                
                # Draw info overlay
                image = self.draw_info_overlay(image, image_name, len(annotations))
                
                # Draw help overlay if enabled
                if self.show_help:
                    image = self.draw_help_overlay(image)
                
                # Display image
                cv2.imshow('Image Viewer with Annotations', image)
                
                # Handle keyboard input
                key = cv2.waitKey(0) & 0xFF
                
                if key == ord('q') or key == 27:  # 'q' or Escape
                    break
                elif key == 83 or key == 32:  # Right arrow or Space
                    self.current_index = (self.current_index + 1) % len(self.image_files)
                elif key == 81:  # Left arrow
                    self.current_index = (self.current_index - 1) % len(self.image_files)
                elif key == ord('s'):  # Save
                    self.save_current_image(image, Path(current_image_path).stem)
                elif key == ord('h'):  # Help
                    self.show_help = not self.show_help
                
            except Exception as e:
                print(f"Error processing image {current_image_path}: {e}")
                self.current_index = (self.current_index + 1) % len(self.image_files)
        
        cv2.destroyAllWindows()

parser = argparse.ArgumentParser(description='Visualise images with bounding box annotations')
parser.add_argument('--images', '-i', required=True, help='Path to images folder')
parser.add_argument('--annotations', '-a', required=True, help='Path to annotations folder')
parser.add_argument('--config', '-c', help='Path to YAML config file with class names')

args = parser.parse_args()

# Validate input paths
if not os.path.exists(args.images):
    print(f"Error: Images folder does not exist: {args.images}")
    sys.exit(1)

if not os.path.exists(args.annotations):
    print(f"Error: Annotations folder does not exist: {args.annotations}")
    sys.exit(1)

try:
    visualiser = BBoxVisualiser(args.images, args.annotations, args.config)
    visualiser.run()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
