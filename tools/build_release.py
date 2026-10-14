"""Build an installable ZIP using an explicit public-file allowlist."""
import argparse
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bridge import __version__

FILES = ("README.md", "README.ru.md", "LICENSE", "COMPATIBILITY.md",
         "CHANGELOG.md", "ROADMAP.md", "CONTRIBUTING.md", "install_houdini.py",
         "launch.py", "Start Bridge.cmd", "Start Bridge.sh", "Import Bridge.py",
         "Connect Houdini.py", "Fix Camera.py")
DIRECTORIES = {"bridge": {".py"}, "houdini": {".py", ".xml", ".shelf", ".png"},
               "docs": {".md"}, "assets": {".qss", ".png", ".txt"}}


def release_files():
    files = [ROOT / name for name in FILES]
    for directory, suffixes in DIRECTORIES.items():
        files.extend(p for p in (ROOT / directory).rglob("*")
                     if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts
                     and p.name != "live_ui.py")
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
    return sorted(files)


def build_release(output=None):
    output = Path(output) if output else ROOT / "dist" / ("SpeedTreeBridge-" + __version__ + ".zip")
    files = release_files()
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = "SpeedTreeBridge-" + __version__
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = prefix + "/" + path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(name, (2026, 10, 14, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    print(build_release(parser.parse_args().output))
