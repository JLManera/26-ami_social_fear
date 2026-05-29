#!/usr/bin/env python3
"""
GUI pixel-distance annotator for idtracker.ai sessions.

Controls:
  - Click TWO points on the image to create a segment.
  - Enter/Return: save/update distance for this session, jump to next.
  - Left/Right arrows: move to previous/next image (loads existing measurement if present).
  - Backspace/Delete: clear current selection for this image (without saving).
  - Q or Esc: quit (progress is saved continuously).

CSV columns:
  timestamp,id,distance_px,x1,y1,x2,y2,background_path,session_root

Dependencies:
  pip install PyQt5 matplotlib
"""

from __future__ import annotations
import sys
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PyQt5 import QtWidgets, QtCore, QtGui

# ── USER SETTINGS ─────────────────────────────────────────────────────────────
# Point this to your raw idtracker.ai output root:
BASE_DIR = Path("/Volumes/Jacks-SSD-1/24-social-cog-sweden/2-data/1-raw_tracks")
# You can also use a relative path like Path("./2-data/1-raw_tracks")

OUTPUT_CSV = Path("/Volumes/Jacks-SSD-1/24-social-cog-sweden/2-data/pixel_distances.csv")
CSV_SUFFIX = Path("trajectories/trajectories_csv/trajectories.csv")

# background candidates relative to session root (checked in order)
BACKGROUND_RELATIVE_CANDIDATES = [
    Path("preprocessing/background.png"),  # your layout
    Path("background/background.png"),
    Path("background.png"),
]

# ── IMPORTS AFTER SETTINGS ────────────────────────────────────────────────────
from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.image as mpimg


@dataclass
class SessionItem:
    id: str
    session_root: Path
    background_path: Path


def find_trajectories_csvs(base_dir: Path) -> List[Path]:
    """
    Find all .../trajectories/trajectories_csv/trajectories.csv under base_dir,
    excluding any paths containing 'pretrained'.
    """
    all_csvs = list(base_dir.rglob("trajectories.csv"))
    keep = [p for p in all_csvs if str(p).endswith(str(CSV_SUFFIX))]
    keep = [p for p in keep if "pretrained" not in str(p).lower()]
    keep.sort()
    return keep


def session_root_from_csv(csv_path: Path) -> Path:
    # .../session_<ID>/trajectories/trajectories_csv/trajectories.csv
    return csv_path.parent.parent.parent


def session_id_from_root(session_root: Path) -> str:
    name = session_root.name  # e.g., "session_d6-t1-c9-b-6l1-d"
    return name[len("session_") :] if name.startswith("session_") else name


def find_background_for_session(session_root: Path) -> Optional[Path]:
    # Try common locations
    for rel in BACKGROUND_RELATIVE_CANDIDATES:
        p = session_root / rel
        if p.exists():
            return p
    # Fallback: first background.png anywhere under the session
    hits = list(session_root.rglob("background.png"))
    return hits[0] if hits else None


def build_sessions(base_dir: Path) -> List[SessionItem]:
    csvs = find_trajectories_csvs(base_dir)
    roots_seen = set()
    items: List[SessionItem] = []
    for c in csvs:
        root = session_root_from_csv(c)
        if root in roots_seen:
            continue
        roots_seen.add(root)
        
        # Only include sessions ending with "focal"
        session_id = session_id_from_root(root)
        if not session_id.endswith("-focal"):
            continue
        
        bg = find_background_for_session(root)
        if bg:
            items.append(SessionItem(
                id=session_id,
                session_root=root,
                background_path=bg
            ))
        else:
            print(f"Warning: no background.png found under {root}")
    return items


def load_measurements(csv_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Return dict: id -> row dict with keys:
    timestamp,id,distance_px,x1,y1,x2,y2,background_path,session_root
    """
    data: Dict[str, Dict[str, str]] = {}
    if not csv_path.exists():
        return data
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row.get("id")
            if sid:
                data[sid] = row
    return data


def save_measurements(csv_path: Path, rows: Dict[str, Dict[str, str]]) -> None:
    fields = ["timestamp", "id", "distance_px", "x1", "y1", "x2", "y2", "background_path", "session_root"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid in sorted(rows.keys()):
            row = rows[sid]
            w.writerow({k: row.get(k, "") for k in fields})


class MplImageWidget(FigureCanvas):
    """
    Matplotlib canvas that shows an image and collects two clicks (points).
    """
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)
        self.fig.tight_layout()
        self.cid_click = self.fig.canvas.mpl_connect("button_press_event", self.on_click)
        self.img = None
        self.points: List[Tuple[float, float]] = []
        self.seg_artist = None
        self.scatter_artist = None

    def load_image(self, path: Path, title: str):
        self.ax.clear()
        try:
            self.img = mpimg.imread(str(path))
        except Exception:
            self.img = None
        if self.img is None:
            self.ax.text(0.5, 0.5, f"Failed to load:\n{path.name}", ha="center", va="center", transform=self.ax.transAxes)
            self.draw()
            return
        h, w = self.img.shape[0], self.img.shape[1]
        self.ax.imshow(self.img, origin="upper")
        self.ax.set_title(title)
        self.ax.set_xlim([0, w])
        self.ax.set_ylim([h, 0])  # y-down to match pixel coords
        self.ax.set_xticks([]); self.ax.set_yticks([])
        self.points.clear()
        self.seg_artist = None
        self.scatter_artist = None
        self.draw()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        if len(self.points) >= 2:
            return
        self.points.append((event.xdata, event.ydata))
        self._redraw_overlay()

    def _redraw_overlay(self):
        if self.seg_artist is not None:
            self.seg_artist.remove()
            self.seg_artist = None
        if self.scatter_artist is not None:
            self.scatter_artist.remove()
            self.scatter_artist = None

        if len(self.points) == 1:
            x, y = self.points[0]
            self.scatter_artist = self.ax.scatter([x], [y])
        elif len(self.points) == 2:
            (x1, y1), (x2, y2) = self.points
            self.seg_artist = self.ax.plot([x1, x2], [y1, y2])[0]
            self.scatter_artist = self.ax.scatter([x1, x2], [y1, y2])

        self.draw()

    def clear_points(self):
        self.points.clear()
        self._redraw_overlay()

    def set_points(self, p1: Tuple[float, float], p2: Tuple[float, float]):
        self.points = [p1, p2]
        self._redraw_overlay()

    @staticmethod
    def pixel_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return (dx * dx + dy * dy) ** 0.5


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, sessions: List[SessionItem], measurements: Dict[str, Dict[str, str]]):
        super().__init__()
        self.sessions = sessions
        self.measurements = measurements  # mutable dict (id -> row)
        self.index = 0

        self.setWindowTitle("idtracker.ai Pixel Calibration")

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)

        self.lbl_info = QtWidgets.QLabel("", self)
        vbox.addWidget(self.lbl_info)

        self.canvas = MplImageWidget(self)
        vbox.addWidget(self.canvas, stretch=1)

        self.lbl_help = QtWidgets.QLabel(
            "Click TWO points → Enter to save | ←/→ navigate | Backspace clear | Q/Esc quit",
            self
        )
        vbox.addWidget(self.lbl_help)

        # Hotkeys
        QtWidgets.QShortcut(QtGui.QKeySequence("Return"), self, activated=self.save_current)
        QtWidgets.QShortcut(QtGui.QKeySequence("Enter"),  self, activated=self.save_current)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left),  self, activated=self.prev_image)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self, activated=self.next_image)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Backspace), self, activated=self.clear_selection)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Delete),    self, activated=self.clear_selection)
        QtWidgets.QShortcut(QtGui.QKeySequence("Q"), self, activated=self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Escape"), self, activated=self.close)

        if not self.sessions:
            self.lbl_info.setText("No sessions with background.png found.")
        else:
            unfinished = [i for i, s in enumerate(self.sessions) if s.id not in self.measurements]
            self.index = unfinished[0] if unfinished else 0
            self.load_current()

    def current(self) -> Optional[SessionItem]:
        if 0 <= self.index < len(self.sessions):
            return self.sessions[self.index]
        return None

    def load_current(self):
        s = self.current()
        if s is None:
            self.lbl_info.setText("No session selected.")
            return
        title = f"[{self.index+1}/{len(self.sessions)}] Session: {s.id}"
        self.lbl_info.setText(title)
        self.canvas.load_image(s.background_path, title)

        # If we already have saved points, restore and show exact line
        if s.id in self.measurements:
            row = self.measurements[s.id]
            try:
                x1 = float(row.get("x1", "nan"))
                y1 = float(row.get("y1", "nan"))
                x2 = float(row.get("x2", "nan"))
                y2 = float(row.get("y2", "nan"))
                if all(map(lambda v: v == v, [x1, y1, x2, y2])):  # not NaN
                    self.canvas.set_points((x1, y1), (x2, y2))
                    dist = float(row.get("distance_px", "nan"))
                    if dist == dist:
                        self.canvas.ax.set_title(f"{title}  |  saved: {dist:.3f} px")
                        self.canvas.draw()
            except Exception:
                pass  # if parse fails, just ignore

    def next_image(self):
        if not self.sessions:
            return
        self.index = (self.index + 1) % len(self.sessions)
        self.load_current()

    def prev_image(self):
        if not self.sessions:
            return
        self.index = (self.index - 1) % len(self.sessions)
        self.load_current()

    def clear_selection(self):
        self.canvas.clear_points()

    def save_current(self):
        s = self.current()
        if s is None:
            return
        if len(self.canvas.points) != 2:
            QtWidgets.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(0, 0)), "Select TWO points first.")
            return
        p1, p2 = self.canvas.points
        dpx = self.canvas.pixel_distance(p1, p2)

        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "id": s.id,
            "distance_px": f"{dpx:.6f}",
            "x1": f"{p1[0]:.6f}",
            "y1": f"{p1[1]:.6f}",
            "x2": f"{p2[0]:.6f}",
            "y2": f"{p2[1]:.6f}",
            "background_path": str(s.background_path.resolve()),
            "session_root": str(s.session_root.resolve()),
        }
        self.measurements[s.id] = row
        save_measurements(OUTPUT_CSV, self.measurements)
        self.next_image()


def main():
    base_dir = BASE_DIR.resolve()
    print(f"Base directory: {base_dir}")
    sessions = build_sessions(base_dir)
    print(f"Sessions discovered (with background.png): {len(sessions)}")
    measurements = load_measurements(OUTPUT_CSV)
    print(f"Existing measurements loaded: {len(measurements)}")
    print(f"Output CSV: {OUTPUT_CSV.resolve()}")

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(sessions, measurements)
    win.resize(1200, 800)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
