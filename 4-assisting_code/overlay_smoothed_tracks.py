
#!/usr/bin/env python3
"""
Overlay Smoothed Tracks on Videos

This script iterates through smoothed track CSVs and overlays the smooth positions
of all four fish (focal + 3 demonstrators) on the corresponding video files.

Uses the same video finding logic as the R wrangling script:
- Video naming: d{day}-t{trial}-c{camera}-{phase}.mp4 or .mkv
- Session naming: d{day}-t{trial}-c{camera}-{phase}-{id}-focal

Usage:
    python overlay_smoothed_tracks.py [--skip-existing] [--session SESSION_NAME]

Arguments:
    --skip-existing     Skip sessions where overlay video already exists
    --session           Process only a specific session (e.g., "d1-t1-c1-b-1l2-d-focal")
    --no-trails         Disable position trails
"""

import os
import re
import argparse
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm


# ── USER CONFIG ─────────────────────────────────────────────────────────────────

# Define paths relative to the project root
PROJECT_ROOT = Path(__file__).parent.parent
SMOOTHED_TRACKS_DIR = PROJECT_ROOT / "2-data" / "2-smoothed_tracks"
VIDEOS_DIR = PROJECT_ROOT / "1-media" / "1-videos"
OUTPUT_DIR = PROJECT_ROOT / "1-media" / "3-overlays"

# Colors for each fish (BGR format for OpenCV)
FISH_COLORS = {
    1: (0, 255, 0),      # Focal fish: Green
    2: (255, 0, 0),      # Demonstrator 1: Blue
    3: (0, 0, 255),      # Demonstrator 2: Red
    4: (255, 255, 0),    # Demonstrator 3: Cyan
}

# Visual settings
POINT_RADIUS = 4
TRAIL_LENGTH = 30  # Number of frames to show in trail


# ── HELPER FUNCTIONS ───────────────────────────────────────────────────────────

def info(msg: str) -> None:
    print(f"[overlay] {msg}", flush=True)


def extract_session_metadata(session_name: str) -> dict:
    """
    Extract day, trial, camera, and phase from session name.
    
    Example: "d1-t1-c1-b-1l2-d-focal" -> day=1, trial=1, camera=1, phase="b"
    """
    match = re.match(r'd(\d+)-t(\d+)-c(\d+)-([bt])-(.+)-focal', session_name)
    if not match:
        raise ValueError(f"Could not parse session name: {session_name}")
    
    return {
        'day': int(match.group(1)),
        'trial': int(match.group(2)),
        'camera': int(match.group(3)),
        'phase': match.group(4),
        'id': match.group(5),
    }


def find_video_file(metadata: dict) -> Optional[Path]:
    """
    Find the corresponding video file for a session.
    
    Video naming convention: d{day}-t{trial}-c{camera}-{phase}.mp4 or .mkv
    (Same logic as R script)
    """
    base_name = f"d{metadata['day']}-t{metadata['trial']}-c{metadata['camera']}-{metadata['phase']}"
    
    for ext in ['.mp4', '.mkv']:
        video_path = VIDEOS_DIR / f"{base_name}{ext}"
        if video_path.exists():
            return video_path
    
    return None


def load_smoothed_tracks(csv_path: Path) -> pd.DataFrame:
    """Load and prepare smoothed track data."""
    df = pd.read_csv(csv_path)
    
    # Get pixels_per_cm for converting back to pixel coordinates
    pixels_per_cm = df['pixels_per_cm'].iloc[0]
    
    if pd.isna(pixels_per_cm):
        raise ValueError(f"No calibration data (pixels_per_cm) in {csv_path}")
    
    # Convert smoothed positions from cm back to pixels
    # Column naming: x_smooth_ind1, y_smooth_ind1, etc.
    for ind in [1, 2, 3, 4]:
        x_col = f'x_smooth_ind{ind}'
        y_col = f'y_smooth_ind{ind}'
        
        if x_col in df.columns and y_col in df.columns:
            df[f'x_px_ind{ind}'] = df[x_col] * pixels_per_cm
            df[f'y_px_ind{ind}'] = df[y_col] * pixels_per_cm
    
    return df


def get_frame_positions(df: pd.DataFrame, frame_time: float, tolerance: float = 0.02) -> dict:
    """
    Get fish positions for a specific frame time.
    
    Returns dict of {individual_number: (x, y)} for fish with valid positions.
    """
    # Find the closest time point
    time_diff = np.abs(df['time'] - frame_time)
    min_idx = time_diff.idxmin()
    
    if time_diff.loc[min_idx] > tolerance:
        return {}
    
    row = df.loc[min_idx]
    positions = {}
    
    for ind in [1, 2, 3, 4]:
        x_col = f'x_px_ind{ind}'
        y_col = f'y_px_ind{ind}'
        
        if x_col in df.columns and y_col in df.columns:
            x, y = row[x_col], row[y_col]
            if not (pd.isna(x) or pd.isna(y)):
                positions[ind] = (int(round(x)), int(round(y)))
    
    return positions


def create_overlay_video(
    video_path: Path,
    tracks_df: pd.DataFrame,
    output_path: Path,
    show_trails: bool = True,
) -> None:
    """
    Create an overlay video with fish positions marked.
    
    Args:
        video_path: Path to the source video
        tracks_df: DataFrame with smoothed track data
        output_path: Path to save the output video
        show_trails: Whether to show position trails
    """
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        raise IOError(f"Could not open video: {video_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Set up video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Track history for trails
    position_history = {ind: [] for ind in [1, 2, 3, 4]}
    
    # Process each frame
    frame_num = 0
    pbar = tqdm(total=total_frames, desc="Processing frames", leave=False)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Calculate current time in seconds
        current_time = frame_num / fps
        
        # Get positions for this frame
        positions = get_frame_positions(tracks_df, current_time)
        
        # Update position history
        for ind in [1, 2, 3, 4]:
            if ind in positions:
                position_history[ind].append(positions[ind])
                # Keep only recent positions for trail
                if len(position_history[ind]) > TRAIL_LENGTH:
                    position_history[ind].pop(0)
            else:
                # Clear history if position is missing (gap in tracking)
                if position_history[ind]:
                    position_history[ind] = []
        
        # Draw trails
        if show_trails:
            for ind, history in position_history.items():
                if len(history) > 1:
                    color = FISH_COLORS[ind]
                    for i in range(len(history) - 1):
                        # Fade alpha based on position in trail
                        alpha = (i + 1) / len(history)
                        faded_color = tuple(int(c * alpha * 0.5) for c in color)
                        cv2.line(frame, history[i], history[i + 1], faded_color, 2)
        
        # Draw current positions
        for ind, (x, y) in positions.items():
            color = FISH_COLORS[ind]
            # Draw filled circle
            cv2.circle(frame, (x, y), POINT_RADIUS, color, -1)
            # Draw outline for visibility
            cv2.circle(frame, (x, y), POINT_RADIUS, (255, 255, 255), 1)
        
        # Add frame info overlay
        info_text = f"Time: {current_time:.2f}s | Frame: {frame_num}"
        cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.7, (0, 0, 0), 1, cv2.LINE_AA)
        
        # Add legend
        legend_y = height - 100
        cv2.putText(frame, "Focal", (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, FISH_COLORS[1], 2, cv2.LINE_AA)
        cv2.putText(frame, "Demo 1", (80, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, FISH_COLORS[2], 2, cv2.LINE_AA)
        cv2.putText(frame, "Demo 2", (160, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, FISH_COLORS[3], 2, cv2.LINE_AA)
        cv2.putText(frame, "Demo 3", (240, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, FISH_COLORS[4], 2, cv2.LINE_AA)
        
        out.write(frame)
        frame_num += 1
        pbar.update(1)
    
    pbar.close()
    cap.release()
    out.release()


def process_session(csv_path: Path, skip_existing: bool = True, show_trails: bool = True) -> dict:
    """
    Process a single session: load tracks, find video, create overlay.
    
    Returns a dict with processing status and any error messages.
    """
    session_name = csv_path.stem
    result = {'session': session_name, 'success': False, 'message': ''}
    
    try:
        # Extract metadata
        metadata = extract_session_metadata(session_name)
        
        # Find corresponding video
        video_path = find_video_file(metadata)
        if video_path is None:
            result['message'] = f"No video file found for session"
            return result
        
        # Check if output already exists
        output_path = OUTPUT_DIR / f"{session_name}-overlay.mp4"
        if skip_existing and output_path.exists():
            result['success'] = True
            result['message'] = "Overlay already exists, skipped"
            return result
        
        # Load tracks
        tracks_df = load_smoothed_tracks(csv_path)
        
        # Create overlay video
        create_overlay_video(video_path, tracks_df, output_path, show_trails=show_trails)
        
        result['success'] = True
        result['message'] = f"Created overlay: {output_path.name}"
        
    except Exception as e:
        result['message'] = f"Error: {str(e)}"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Overlay smoothed tracks on videos")
    parser.add_argument('--skip-existing', action='store_true', 
                        help="Skip sessions where overlay already exists")
    parser.add_argument('--session', type=str, default=None,
                        help="Process only a specific session")
    parser.add_argument('--no-trails', action='store_true',
                        help="Disable position trails")
    args = parser.parse_args()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all smoothed track files
    csv_files = sorted(SMOOTHED_TRACKS_DIR.glob("*.csv"))
    # Filter out macOS hidden files
    csv_files = [f for f in csv_files if not f.name.startswith('._')]
    
    if args.session:
        # Filter to specific session
        session_file = SMOOTHED_TRACKS_DIR / f"{args.session}.csv"
        if not session_file.exists():
            print(f"Error: Session file not found: {session_file}")
            return
        csv_files = [session_file]
    
    info(f"Found {len(csv_files)} smoothed track files")
    info(f"Output directory: {OUTPUT_DIR}")
    print("-" * 60)
    
    # Process each session
    results = []
    for csv_path in tqdm(csv_files, desc="Processing sessions"):
        result = process_session(
            csv_path, 
            skip_existing=args.skip_existing,
            show_trails=not args.no_trails
        )
        results.append(result)
        
        # Print status
        status = "✓" if result['success'] else "✗"
        tqdm.write(f"  {status} {result['session']}: {result['message']}")
    
    # Summary
    print("-" * 60)
    successful = sum(1 for r in results if r['success'])
    info(f"Completed: {successful}/{len(results)} sessions processed successfully")
    
    # List failures
    failures = [r for r in results if not r['success']]
    if failures:
        print(f"\nFailed sessions ({len(failures)}):")
        for r in failures:
            print(f"  - {r['session']}: {r['message']}")


if __name__ == "__main__":
    main()
