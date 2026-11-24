#!/usr/bin/env python3
"""Read selected vehicle sources into an archive without changing the workspaces."""

import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


SELECTIONS = (
    ("agilex_ws/src/limo_ros", "ros1/src/limo_ros",
     ("limo_base", "limo_bringup", "learning_limo", "LICENSE", "README.md")),
    ("agilex_ws/src/agilex_pure_pursuit", "ros1/src/agilex_pure_pursuit", (".",)),
    ("agilex_ws/src/set_nav_point", "ros1/src/set_nav_point", (".",)),
    ("agilex_ws/src/fixed_point_navigation", "ros1/src/fixed_point_navigation", (".",)),
    ("limo_ros2_ws/src/limo_ros2", "ros2/src/limo_ros2",
     ("limo_base", "limo_bringup", "limo_msgs", "LICENSE", "README.md")),
)
EXCLUDED_PARTS = {".git", "build", "devel", "install", "log", "logs", "Log", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip", ".bag", ".db3", ".mcap"}


def git_output(directory, *args):
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    return result.stdout.decode("utf-8", errors="replace").strip() if result.returncode == 0 else None


def add_json(archive, name, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    archive.addfile(info, io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vehicle-home", type=Path, default=Path.home())
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new archive path.")

    manifest = {
        "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "vehicle_home": str(args.vehicle_home),
        "scope": "Selected chassis, bringup, navigation configuration and task sources; not a full workspace backup.",
        "repositories": [],
        "files": [],
    }
    with tarfile.open(str(args.output), "w:gz") as archive:
        for relative_root, destination, members in SELECTIONS:
            root = args.vehicle_home / relative_root
            if not root.is_dir():
                raise FileNotFoundError(str(root))
            manifest["repositories"].append({
                "source": str(root),
                "destination": destination,
                "head": git_output(root, "rev-parse", "HEAD"),
                "status": git_output(root, "status", "--short"),
                "selected_members": list(members),
            })
            for member in members:
                selected = root / member
                if not selected.exists():
                    continue
                candidates = sorted(selected.rglob("*")) if selected.is_dir() else [selected]
                for path in candidates:
                    relative = path.relative_to(root)
                    if set(relative.parts) & EXCLUDED_PARTS or path.suffix.lower() in EXCLUDED_SUFFIXES:
                        continue
                    if path.is_symlink():
                        raise ValueError("Review symlink before exporting: " + str(path))
                    if not path.is_file():
                        continue
                    name = destination + "/" + relative.as_posix()
                    data = path.read_bytes()
                    mode = path.stat().st_mode & 0o777
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = mode
                    archive.addfile(info, io.BytesIO(data))
                    manifest["files"].append({
                        "path": name,
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "executable": bool(mode & 0o111),
                    })
        add_json(archive, "docs/source-baseline.json", manifest)
    print(json.dumps({"archive": str(args.output), "files": len(manifest["files"])}))


if __name__ == "__main__":
    main()
