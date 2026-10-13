"""Install the Bridge package into Houdini 19–22 user preferences."""
import argparse
import json
import shutil
import os
from pathlib import Path
VERSIONS = ("19.0", "19.5", "20.0", "20.5", "21.0", "22.0")


def documents_folder():
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            return Path(os.path.expandvars(winreg.QueryValueEx(key, "Personal")[0]))
    return Path.home()


def install(preferences):
    project = Path(__file__).resolve().parent
    target = Path(preferences) / "packages" / "speedtree_bridge.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    package = {"enable": True, "env": [
        {"SPEEDTREE_BRIDGE_ROOT": project.as_posix()},
        {"PYTHONPATH": {"value": "$SPEEDTREE_BRIDGE_ROOT", "method": "prepend"}},
    ], "path": "$SPEEDTREE_BRIDGE_ROOT/houdini"}
    if target.exists():
        backup = target.with_suffix(".json.bak")
        if not backup.exists():
            shutil.copy2(target, backup)
    target.write_text(json.dumps(package, indent=2), encoding="utf-8")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preferences", type=Path, nargs="?")
    parser.add_argument("--all", action="store_true", help="Install for Houdini 19.0 through 22.0")
    parser.add_argument("--documents", type=Path)
    parser.add_argument("--version", choices=VERSIONS, help="Install for one Houdini version")
    args = parser.parse_args()
    if args.all and (args.version or args.preferences):
        parser.error("--all cannot be combined with --version or a preferences path")
    if args.version and args.preferences:
        parser.error("Choose --version or an explicit preferences path")
    if args.all or args.version:
        base = args.documents or documents_folder()
        for version in VERSIONS if args.all else (args.version,):
            print(install(base / ("houdini" + version)))
    elif args.preferences:
        print(install(args.preferences))
    else:
        parser.error("Provide the Houdini preferences path, or --all")
