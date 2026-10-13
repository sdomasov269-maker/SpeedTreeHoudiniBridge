"""Run once in Houdini Python Source Editor to connect the standalone window."""
import sys
import importlib
import hou
from pathlib import Path
project = hou.text.expandString("$SPEEDTREE_BRIDGE_ROOT")
if not project or project.startswith("$"):
    project = str(Path(__file__).resolve().parent)
if project not in sys.path:
    sys.path.insert(0, project)
import bridge.package
import bridge.houdini
import bridge.receiver
bridge.receiver.stop()
importlib.reload(bridge.package)
importlib.reload(bridge.houdini)
importlib.reload(bridge.receiver)
hou.ui.displayMessage(bridge.receiver.start())
