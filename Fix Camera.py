"""Run in Houdini with the bridge camera selected; no reimport needed."""
import importlib
import bridge.scene
importlib.reload(bridge.scene)
bridge.scene.reframe_selected()
