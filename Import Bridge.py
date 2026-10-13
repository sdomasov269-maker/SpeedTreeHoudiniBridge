"""Run this file in Houdini's Python Source Editor, or paste it into a shelf tool."""
import sys
from pathlib import Path
import hou

project = Path(hou.text.expandString("$SPEEDTREE_BRIDGE_ROOT"))
if str(project).startswith("$"):
    project = Path(__file__).resolve().parent
if str(project) not in sys.path:
    sys.path.insert(0, str(project))
from bridge.houdini import import_package

filename = hou.ui.selectFile(title="Import SpeedTree Bridge", pattern="*.bridge.json")
if filename:
    try:
        result = import_package(hou.expandString(filename))
        hou.ui.displayMessage(f"Imported: {result['root']}\nPrimitives: {result['primitives']}\nMaterials in /mat: {len(result['materials'])}\nArnold output: {result.get('render_output') or '—'}\n" + "\n".join(result.get('notes', [])))
    except Exception as error:
        hou.ui.displayMessage(str(error), severity=hou.severityType.Error)
