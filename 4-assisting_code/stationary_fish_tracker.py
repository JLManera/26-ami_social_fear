#!/usr/bin/env python3
"""
Stationary Fish Tracker
-----------------------
Generates trajectory.csv files for fish that never moved during tracking.
Allows user to click on a video frame to specify the stationary position.

Usage:
    python stationary_fish_tracker.py
"""

import os
import cv2
import toml
import numpy as np
from pathlib import Path

# Define the stationary fish sessions (without .toml extension)
STATIONARY_FISH = [
    "d2-t2-c3-b-2h1-d-focal",
    "d2-t2-c3-t-2h1-d-focal", 
    "d3-t2-c2-b-3h3-d-focal",
    "d4-t1-c1-b-4h2-d-focal",
    "d6-t1-c1-b-6h2-i-focal",
]

# Base paths
TOML_DIR = Path("/Volumes/Jacks-SSD-1/24-social-cog-sweden/2-data/1-raw_tracks")
OUTPUT_BASE = Path("/Volumes/Jacks-SSD-1/24-social-cog-sweden/2-data/1-raw_tracks")

# Frame rate (based on example CSV: 0.033s per frame ≈ 30 fps)
FRAME_RATE = 30.0


class ClickHandler:
    """Handle mouse clicks on the video frame."""
    
    def __init__(self):
        self.x = None
        self.y = None
        self.clicked = False
    
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.x = x
            self.y = y
            self.clicked = True
            print(f"  Clicked at: ({x}, {y})")


def load_toml_config(toml_path: Path) -> dict:
    """Load and parse the TOML configuration file."""
    with open(toml_path, 'r') as f:
        return toml.load(f)


def get_frame_from_video(video_path: str, frame_number: int) -> np.ndarray:
    """Extract a specific frame from the video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise ValueError(f"Could not read frame {frame_number} from video")
    
    return frame


def get_click_position(frame: np.ndarray, session_name: str) -> tuple:
    """Display frame and get click position from user."""
    click_handler = ClickHandler()
    window_name = f"Click on stationary fish - {session_name}"
    
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, click_handler.mouse_callback)
    
    # Add instructions to the frame
    display_frame = frame.copy()
    cv2.putText(display_frame, "Click on the stationary fish, then press any key", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(display_frame, "Press 'q' to quit without saving", 
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    print(f"\n  Window opened. Click on the fish location...")
    
    while True:
        # Show frame with click marker if clicked
        show_frame = display_frame.copy()
        if click_handler.clicked:
            cv2.circle(show_frame, (click_handler.x, click_handler.y), 10, (0, 255, 0), 2)
            cv2.putText(show_frame, f"({click_handler.x}, {click_handler.y})", 
                       (click_handler.x + 15, click_handler.y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.imshow(window_name, show_frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            cv2.destroyAllWindows()
            return None, None
        elif key != 255 and click_handler.clicked:
            cv2.destroyAllWindows()
            return click_handler.x, click_handler.y
    

def generate_trajectory_csv(output_path: Path, x: float, y: float, 
                           start_frame: int, end_frame: int, fps: float = 30.0):
    """Generate trajectory.csv with constant position for all frames."""
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    num_frames = end_frame - start_frame
    
    with open(output_path, 'w') as f:
        # Write header
        f.write("time,trajectories1,trajectories2\n")
        
        # Write each frame with the same position
        for i in range(num_frames):
            time = i / fps
            f.write(f"{time:.3f},{x:.3f},{y:.3f}\n")
    
    print(f"  Created: {output_path}")
    print(f"  Frames: {num_frames}, Position: ({x:.3f}, {y:.3f})")


def process_fish(session_name: str):
    """Process a single stationary fish session."""
    print(f"\n{'='*60}")
    print(f"Processing: {session_name}")
    print(f"{'='*60}")
    
    # Load TOML config
    toml_path = TOML_DIR / f"{session_name}.toml"
    if not toml_path.exists():
        print(f"  ERROR: TOML file not found: {toml_path}")
        return False
    
    config = load_toml_config(toml_path)
    
    # Extract video path and tracking interval
    video_path = config['video_paths'][0]
    tracking_interval = config['tracking_intervals'][0]
    start_frame, end_frame = tracking_interval
    
    print(f"  Video: {video_path}")
    print(f"  Tracking interval: frames {start_frame} to {end_frame}")
    
    # Check if video exists
    if not os.path.exists(video_path):
        print(f"  ERROR: Video file not found: {video_path}")
        return False
    
    # Get middle frame
    middle_frame = (start_frame + end_frame) // 2
    print(f"  Loading frame {middle_frame}...")
    
    try:
        frame = get_frame_from_video(video_path, middle_frame)
    except ValueError as e:
        print(f"  ERROR: {e}")
        return False
    
    # Get click position from user
    x, y = get_click_position(frame, session_name)
    
    if x is None:
        print("  Skipped by user")
        return False
    
    # Create output directory structure
    session_dir = OUTPUT_BASE / f"session_{session_name}"
    trajectories_dir = session_dir / "trajectories" / "trajectories_csv"
    output_csv = trajectories_dir / "trajectories.csv"
    
    # Generate the CSV
    generate_trajectory_csv(output_csv, x, y, start_frame, end_frame, FRAME_RATE)
    
    return True


def main():
    print("\n" + "="*60)
    print("STATIONARY FISH TRAJECTORY GENERATOR")
    print("="*60)
    print(f"\nThis script will generate trajectory.csv files for {len(STATIONARY_FISH)} stationary fish.")
    print("For each fish, a video frame will be displayed.")
    print("Click on the fish location and press any key to confirm.")
    print("Press 'q' to skip a fish.\n")
    
    input("Press Enter to continue...")
    
    successful = 0
    for session_name in STATIONARY_FISH:
        if process_fish(session_name):
            successful += 1
    
    print("\n" + "="*60)
    print(f"COMPLETE: Successfully processed {successful}/{len(STATIONARY_FISH)} fish")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
