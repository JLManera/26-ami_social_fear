import os
import glob
import platform
import subprocess
import tempfile
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# 1) CONFIGURE YOUR SOURCE TOML FOLDER (this is the location of the TOMLs)
# ──────────────────────────────────────────────────────────────────────────────
toml_dir = r"F:\24-social-cog-sweden\2-data\1-raw_tracks"

# Filter pattern: only process demonstrator TOMLs (set to None to process all)
TOML_FILTER =  None #"*-demonstrator.toml"

# ──────────────────────────────────────────────────────────────────────────────
# 2) BASE-PATH REMAPS for cross-OS portability
#    - Left side is the prefix that appears in TOMLs you authored on your Mac.
#    - Right side is what those paths should become on the CURRENT machine.
#    - Edit WIN_BASE / LINUX_BASE below to match your actual mount points.
# ──────────────────────────────────────────────────────────────────────────────
MAC_BASE   = "/Volumes/Jacks-SSD-1"
WIN_BASE   = r"F:"     
LINUX_BASE = "/mnt/Jacks-SSD-1" 

SYSTEM  = platform.system()  # "Darwin" | "Windows" | "Linux"
IS_MAC  = SYSTEM == "Darwin"
IS_WIN  = SYSTEM == "Windows"
IS_NIX  = SYSTEM == "Linux"

if IS_MAC:
    CURRENT_BASE = MAC_BASE
elif IS_WIN:
    CURRENT_BASE = WIN_BASE
else:
    CURRENT_BASE = LINUX_BASE

# ──────────────────────────────────────────────────────────────────────────────
# 3) TOML loader/dumper
#    - Prefers stdlib tomllib on Python 3.11+ for reading.
#    - Falls back to 'toml' package for reading/writing if available.
# ──────────────────────────────────────────────────────────────────────────────
try:
    import tomllib as _toml_reader  # Python 3.11+
    def load_toml(p: str | Path) -> dict:
        with open(p, "rb") as f:
            return _toml_reader.load(f)
except ModuleNotFoundError:
    _toml_reader = None

try:
    import toml as _toml_rw  # pip install toml
except ModuleNotFoundError:
    _toml_rw = None

if _toml_reader is None and _toml_rw is None:
    raise RuntimeError(
        "No TOML parser available. Install Python 3.11+ (tomllib) or `pip install toml`."
    )

def dump_toml(data: dict, p: str | Path) -> None:
    if _toml_rw is None:
        # Minimal fallback: if no writer is available, we can't remap/write TOML.
        # Ask user to install 'toml' or run on Python with writer available.
        raise RuntimeError("TOML writer not available. Please `pip install toml`.")
    with open(p, "w", encoding="utf-8") as f:
        _toml_rw.dump(data, f)

# ──────────────────────────────────────────────────────────────────────────────
# 4) Helpers: path remapping and normalization
#    - Replaces leading MAC_BASE with CURRENT_BASE when not on macOS.
#    - Ensures slashes/backslashes are appropriate for the OS.
# ──────────────────────────────────────────────────────────────────────────────
def _normalize_sep(p: str) -> str:
    """Normalize path separators for the current OS."""
    if IS_WIN:
        return p.replace("/", "\\")
    else:
        return p.replace("\\", "/")

def remap_path_if_needed(path_str: str) -> str:
    """If TOML path starts with the Mac base, remap to CURRENT_BASE and normalize separators."""
    if not isinstance(path_str, str):
        return path_str
    s = os.path.expanduser(path_str)
    if s.startswith(MAC_BASE + "/") or s == MAC_BASE:
        s = s.replace(MAC_BASE, CURRENT_BASE, 1)
    return _normalize_sep(s)

def remap_paths_in_cfg(cfg: dict, default_output_dir: str = None) -> tuple[dict, bool]:
    """
    Remap known path fields for the current OS. Returns (cfg_copy, changed_flag).
    Also removes deprecated parameters (identity_transfer, knowledge_transfer_folder).
    Known path keys:
      - output_dir (str)
      - video_paths (list[str])
    If output_dir is missing and default_output_dir is provided, it will be added.
    """
    changed = False
    new_cfg = dict(cfg)  # shallow copy

    # Remove deprecated parameters if present
    deprecated_params = ["identity_transfer", "knowledge_transfer_folder"]
    for param in deprecated_params:
        if param in new_cfg:
            del new_cfg[param]
            changed = True

    # output_dir: add if missing, otherwise remap
    if "output_dir" not in new_cfg or not new_cfg["output_dir"]:
        if default_output_dir:
            new_cfg["output_dir"] = _normalize_sep(default_output_dir)
            changed = True
    elif isinstance(new_cfg["output_dir"], str):
        remapped = remap_path_if_needed(new_cfg["output_dir"])
        if remapped != new_cfg["output_dir"]:
            new_cfg["output_dir"] = remapped
            changed = True

    # video_paths
    if "video_paths" in new_cfg and isinstance(new_cfg["video_paths"], list):
        vp_new = []
        vp_changed = False
        for v in new_cfg["video_paths"]:
            nv = remap_path_if_needed(v)
            if nv != v:
                vp_changed = True
            vp_new.append(nv)
        if vp_changed:
            new_cfg["video_paths"] = vp_new
            changed = True

    return new_cfg, changed

# ──────────────────────────────────────────────────────────────────────────────
# 5) Session folder computation from TOML: <output_dir>/session_<name>
# ──────────────────────────────────────────────────────────────────────────────
def session_folder_from_cfg(cfg: dict) -> Path:
    if "output_dir" not in cfg or "name" not in cfg:
        missing = [k for k in ("output_dir", "name") if k not in cfg]
        raise KeyError(f"Missing {', '.join(missing)} in TOML.")
    output_dir = Path(os.path.expanduser(str(cfg["output_dir"])))
    name       = str(cfg["name"])
    return output_dir / f"session_{name}"

# ──────────────────────────────────────────────────────────────────────────────
# 6) Prepare a TOML for this OS:
#    - Load original TOML
#    - Remap paths if needed (on Windows/Linux)
#    - If remapped, write a temp TOML and return its path; else return original
# ──────────────────────────────────────────────────────────────────────────────
def prepare_toml_for_current_os(toml_path: str | Path) -> tuple[str, Path]:
    cfg = load_toml(toml_path)
    cfg_for_os, changed = remap_paths_in_cfg(cfg, default_output_dir=toml_dir)

    # Compute session folder from the *remapped* config (so existence check is valid locally)
    sess_folder = session_folder_from_cfg(cfg_for_os)

    if changed:
        # Create a temporary TOML that idtrackerai can read with correct local paths
        suffix = f".{SYSTEM.lower()}.toml"
        tmp_dir = tempfile.gettempdir()
        tmp_name = Path(toml_path).stem + suffix
        tmp_path = Path(tmp_dir) / tmp_name
        dump_toml(cfg_for_os, tmp_path)
        return str(tmp_path), sess_folder

    # No changes needed; just use the original TOML
    return str(toml_path), sess_folder

# ──────────────────────────────────────────────────────────────────────────────
# 7) Conda environment configuration
# ──────────────────────────────────────────────────────────────────────────────
CONDA_ENV_NAME = "idtrackerai"

# ──────────────────────────────────────────────────────────────────────────────
# 8) Runner that skips existing sessions and streams output to terminal
# ──────────────────────────────────────────────────────────────────────────────
def run_idtrackerai_if_needed(toml_path: str | Path) -> None:
    try:
        toml_for_run, sess_folder = prepare_toml_for_current_os(toml_path)
    except Exception as e:
        print(f"⚠️  Skipping {toml_path}: could not prepare TOML ({e})")
        return

    # Skip if session folder already exists
    if sess_folder.exists():
        print(f"⏭️  Skip (already tracked): {sess_folder}")
        return

    # Ensure parent of session folder exists (idtrackerai usually handles this, but it's safe)
    sess_folder.parent.mkdir(parents=True, exist_ok=True)

    print(f"▶️  Tracking with: {toml_for_run}")
    try:
        full_cmd = [
            "conda", "run", "-n", CONDA_ENV_NAME, "--no-capture-output",
            "idtrackerai", "--load", toml_for_run, "--track"
        ]
        
        # stdout=None/stderr=None -> stream live output in your VS Code terminal
        subprocess.run(
            full_cmd,
            check=True,
            stdout=None,
            stderr=None
        )
        print(f"✅ Done: {toml_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ idtrackerai failed for {toml_path}: {e}")
    except KeyboardInterrupt:
        print("⛔ Interrupted by user.")

# ──────────────────────────────────────────────────────────────────────────────
# 9) Discover TOMLs and run
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # Use filter pattern if specified, otherwise get all TOMLs
    if TOML_FILTER:
        pattern = os.path.join(toml_dir, TOML_FILTER)
    else:
        pattern = os.path.join(toml_dir, "*.toml")
    
    toml_files = sorted(glob.glob(pattern))

    if not toml_files:
        print(f"ℹ️  No TOMLs found matching pattern: {pattern}")
        print("   Check toml_dir and TOML_FILTER settings.")
        return

    print(f"🖥️  OS detected: {SYSTEM} | Using base path: {CURRENT_BASE}")
    print(f"📁 Found {len(toml_files)} TOML files matching '{TOML_FILTER or '*.toml'}'")
    print()

    for p in toml_files:
        run_idtrackerai_if_needed(p)

if __name__ == "__main__":
    main()
