#!/usr/bin/env python3
"""
Image Curator Tool for NUpbr Dataset

This tool allows you to review generated images with their annotations,
visualize bounding boxes, and accept/reject images for your final dataset.

Usage:
    python image_curator.py --input /path/to/run_X --output /path/to/curated_dataset

Controls:
    - Left/Right Arrow Keys: Navigate between images
    - 'a' or Space: Accept current image
    - 'r' or Delete: Reject current image
    - 's': Skip current image (no decision)
    - 'q' or Escape: Quit
    - 't': Toggle bounding box visibility
    - 'f': Toggle fullscreen
"""

import argparse
import os
import shutil
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np


class ImageCurator:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.current_index = 0
        self.show_boxes = True
        
        # Class names for YOLO format
        self.class_names = {
            0: "Ball",
            1: "Goal_post", 
            2: "Robot",
            3: "L_intersection",
            4: "T_intersection", 
            5: "X_intersection"
        }
        
        # Colors for bounding boxes (BGR format for OpenCV)
        self.class_colors = {
            0: (0, 255, 0),      # Ball - Green
            1: (0, 255, 255),    # Goal_post - Yellow
            2: (255, 0, 0),      # Robot - Blue
            3: (255, 0, 255),    # L_intersection - Magenta
            4: (255, 255, 0),    # T_intersection - Cyan
            5: (0, 165, 255)     # X_intersection - Orange
        }
        
        # Initialize paths
        self.raw_dir = self.input_dir / "raw"
        self.seg_dir = self.input_dir / "seg" 
        self.meta_dir = self.input_dir / "meta"
        self.annotations_dir = self.input_dir / "annotations"
        
        # Output paths
        self.output_raw_dir = self.output_dir / "raw"
        self.output_seg_dir = self.output_dir / "seg"
        self.output_meta_dir = self.output_dir / "meta"
        self.output_annotations_dir = self.output_dir / "annotations"
        
        # Create output directories
        for dir_path in [self.output_raw_dir, self.output_seg_dir, self.output_meta_dir, self.output_annotations_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Load image list
        self.load_images()
        
        # Statistics
        self.stats = {
            'total': len(self.images),
            'accepted': 0,
            'rejected': 0,
            'reviewed': 0
        }
        
        # Load existing decisions
        self.decisions_file = self.output_dir / "curation_decisions.json"
        self.decisions = self.load_decisions()
        
        # Setup GUI
        self.setup_gui()
        
    def load_images(self):
        """Load list of available images"""
        if not self.raw_dir.exists():
            raise ValueError(f"Raw images directory not found: {self.raw_dir}")
            
        self.images = []
        for img_file in sorted(self.raw_dir.glob("*.png")):
            # Check if annotation file exists
            ann_file = self.annotations_dir / f"{img_file.stem}.txt"
            if ann_file.exists():
                self.images.append(img_file.stem)
        
        print(f"Found {len(self.images)} images with annotations")
        
    def load_decisions(self):
        """Load previous curation decisions"""
        if self.decisions_file.exists():
            with open(self.decisions_file, 'r') as f:
                decisions = json.load(f)
                # Count existing decisions
                for decision in decisions.values():
                    if decision == 'accepted':
                        self.stats['accepted'] += 1
                    elif decision == 'rejected':
                        self.stats['rejected'] += 1
                self.stats['reviewed'] = self.stats['accepted'] + self.stats['rejected']
                return decisions
        return {}
        
    def save_decisions(self):
        """Save curation decisions"""
        with open(self.decisions_file, 'w') as f:
            json.dump(self.decisions, f, indent=2)
            
    def setup_gui(self):
        """Setup the GUI"""
        self.root = tk.Tk()
        self.root.title("NUpbr Image Curator")
        self.root.geometry("1200x900")
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Image info
        self.info_label = ttk.Label(control_frame, text="", font=("Arial", 12))
        self.info_label.pack(side=tk.LEFT)
        
        # Statistics
        self.stats_label = ttk.Label(control_frame, text="", font=("Arial", 10))
        self.stats_label.pack(side=tk.RIGHT)
        
        # Navigation frame
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(nav_frame, text="← Previous", command=self.prev_image).pack(side=tk.LEFT)
        ttk.Button(nav_frame, text="Next →", command=self.next_image).pack(side=tk.LEFT, padx=(5, 0))
        
        # Decision buttons
        decision_frame = ttk.Frame(nav_frame)
        decision_frame.pack(side=tk.RIGHT)
        
        ttk.Button(decision_frame, text="✓ Accept (A)", command=self.accept_image, 
                  style="Accept.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(decision_frame, text="✗ Reject (R)", command=self.reject_image,
                  style="Reject.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(decision_frame, text="Skip (S)", command=self.skip_image).pack(side=tk.LEFT)
        
        # Toggle controls
        toggle_frame = ttk.Frame(nav_frame)
        toggle_frame.pack()
        
        ttk.Button(toggle_frame, text="Toggle Boxes (T)", command=self.toggle_boxes).pack(side=tk.LEFT, padx=(0, 5))
        
        # Image display frame
        self.image_frame = ttk.Frame(main_frame)
        self.image_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for image display
        self.canvas = tk.Canvas(self.image_frame, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Setup key bindings
        self.root.bind('<Key>', self.on_key_press)
        self.root.focus_set()
        
        # Configure styles
        style = ttk.Style()
        style.configure("Accept.TButton", foreground="green")
        style.configure("Reject.TButton", foreground="red")
        
        # Load first image
        if self.images:
            self.show_current_image()
            
    def load_annotations(self, image_name):
        """Load YOLO format annotations for an image"""
        ann_file = self.annotations_dir / f"{image_name}.txt"
        annotations = []
        
        if ann_file.exists():
            with open(ann_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        annotations.append((class_id, x_center, y_center, width, height))
        
        return annotations
    
    def draw_bounding_boxes(self, image, annotations, img_width, img_height):
        """Draw bounding boxes on image"""
        if not self.show_boxes or not annotations:
            return image
            
        # Convert PIL image to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        for class_id, x_center, y_center, width, height in annotations:
            # Convert YOLO format to pixel coordinates
            x1 = int((x_center - width/2) * img_width)
            y1 = int((y_center - height/2) * img_height)
            x2 = int((x_center + width/2) * img_width)
            y2 = int((y_center + height/2) * img_height)
            
            # Get color and class name
            color = self.class_colors.get(class_id, (255, 255, 255))
            class_name = self.class_names.get(class_id, f"Class_{class_id}")
            
            # Draw bounding box
            cv2.rectangle(cv_image, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            label = f"{class_name}"
            (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(cv_image, (x1, y1 - label_height - 10), (x1 + label_width, y1), color, -1)
            
            # Draw label text
            cv2.putText(cv_image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Convert back to PIL format
        return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
    
    def show_current_image(self):
        """Display the current image with annotations"""
        if not self.images:
            return
            
        image_name = self.images[self.current_index]
        
        # Load image
        img_path = self.raw_dir / f"{image_name}.png"
        if not img_path.exists():
            self.info_label.config(text=f"Image not found: {img_path}")
            return
            
        image = Image.open(img_path)
        original_width, original_height = image.size
        
        # Load annotations
        annotations = self.load_annotations(image_name)
        
        # Draw bounding boxes
        image_with_boxes = self.draw_bounding_boxes(image, annotations, original_width, original_height)
        
        # Resize image to fit canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:  # Avoid division by zero
            # Calculate scaling factor to fit image in canvas while maintaining aspect ratio
            scale_x = canvas_width / original_width
            scale_y = canvas_height / original_height
            scale = min(scale_x, scale_y, 1.0)  # Don't upscale
            
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            image_with_boxes = image_with_boxes.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Display image
        self.photo = ImageTk.PhotoImage(image_with_boxes)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width//2, canvas_height//2, image=self.photo)
        
        # Update info
        decision = self.decisions.get(image_name, "pending")
        decision_text = f" [{decision.upper()}]" if decision != "pending" else ""
        self.info_label.config(text=f"Image {self.current_index + 1}/{len(self.images)}: {image_name}{decision_text} | "
                                   f"Annotations: {len(annotations)}")
        
        # Update statistics
        self.update_stats_display()
        
    def update_stats_display(self):
        """Update the statistics display"""
        progress = (self.stats['reviewed'] / self.stats['total']) * 100 if self.stats['total'] > 0 else 0
        self.stats_label.config(text=f"Progress: {progress:.1f}% | "
                                    f"Accepted: {self.stats['accepted']} | "
                                    f"Rejected: {self.stats['rejected']} | "
                                    f"Reviewed: {self.stats['reviewed']}/{self.stats['total']}")
    
    def accept_image(self):
        """Accept the current image and copy files"""
        if not self.images:
            return
            
        image_name = self.images[self.current_index]
        
        # Update decision
        if image_name not in self.decisions or self.decisions[image_name] != 'accepted':
            if image_name in self.decisions and self.decisions[image_name] == 'rejected':
                self.stats['rejected'] -= 1
            elif image_name not in self.decisions:
                self.stats['reviewed'] += 1
            
            self.decisions[image_name] = 'accepted'
            self.stats['accepted'] += 1
            
            # Copy files
            self.copy_image_files(image_name)
        
        self.save_decisions()
        self.next_image()
        
    def reject_image(self):
        """Reject the current image"""
        if not self.images:
            return
            
        image_name = self.images[self.current_index]
        
        # Update decision
        if image_name not in self.decisions or self.decisions[image_name] != 'rejected':
            if image_name in self.decisions and self.decisions[image_name] == 'accepted':
                self.stats['accepted'] -= 1
                # Remove files from output if they exist
                self.remove_image_files(image_name)
            elif image_name not in self.decisions:
                self.stats['reviewed'] += 1
            
            self.decisions[image_name] = 'rejected'
            self.stats['rejected'] += 1
        
        self.save_decisions()
        self.next_image()
        
    def skip_image(self):
        """Skip the current image without decision"""
        self.next_image()
        
    def copy_image_files(self, image_name):
        """Copy image files to output directory"""
        files_to_copy = [
            (self.raw_dir / f"{image_name}.png", self.output_raw_dir / f"{image_name}.png"),
            (self.annotations_dir / f"{image_name}.txt", self.output_annotations_dir / f"{image_name}.txt"),
        ]
        
        # Optional files
        seg_file = self.seg_dir / f"{image_name}.png"
        if seg_file.exists():
            files_to_copy.append((seg_file, self.output_seg_dir / f"{image_name}.png"))
            
        meta_file = self.meta_dir / f"{image_name}.yaml"
        if meta_file.exists():
            files_to_copy.append((meta_file, self.output_meta_dir / f"{image_name}.yaml"))
        
        for src, dst in files_to_copy:
            if src.exists():
                shutil.copy2(src, dst)
                
    def remove_image_files(self, image_name):
        """Remove image files from output directory"""
        files_to_remove = [
            self.output_raw_dir / f"{image_name}.png",
            self.output_annotations_dir / f"{image_name}.txt",
            self.output_seg_dir / f"{image_name}.png",
            self.output_meta_dir / f"{image_name}.yaml"
        ]
        
        for file_path in files_to_remove:
            if file_path.exists():
                file_path.unlink()
    
    def toggle_boxes(self):
        """Toggle bounding box visibility"""
        self.show_boxes = not self.show_boxes
        self.show_current_image()
    
    def prev_image(self):
        """Go to previous image"""
        if self.images and self.current_index > 0:
            self.current_index -= 1
            self.show_current_image()
    
    def next_image(self):
        """Go to next image"""
        if self.images and self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.show_current_image()
    
    def on_key_press(self, event):
        """Handle key press events"""
        key = event.keysym.lower()
        
        if key in ['left', 'up']:
            self.prev_image()
        elif key in ['right', 'down']:
            self.next_image()
        elif key in ['a', 'space']:
            self.accept_image()
        elif key in ['r', 'delete']:
            self.reject_image()
        elif key == 's':
            self.skip_image()
        elif key == 't':
            self.toggle_boxes()
        elif key in ['q', 'escape']:
            self.quit()
    
    def quit(self):
        """Quit the application"""
        self.save_decisions()
        self.root.quit()
    
    def run(self):
        """Run the curator"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit()


def main():
    parser = argparse.ArgumentParser(description="Image Curator for NUpbr Dataset")
    parser.add_argument("--input", "-i", required=True, help="Input directory (e.g., outputs/run_6)")
    parser.add_argument("--output", "-o", required=True, help="Output directory for curated dataset")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return
    
    if not (input_dir / "raw").exists():
        print(f"Error: Raw images directory not found: {input_dir / 'raw'}")
        return
        
    if not (input_dir / "annotations").exists():
        print(f"Error: Annotations directory not found: {input_dir / 'annotations'}")
        return
    
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    curator = ImageCurator(input_dir, output_dir)
    curator.run()


if __name__ == "__main__":
    main()
