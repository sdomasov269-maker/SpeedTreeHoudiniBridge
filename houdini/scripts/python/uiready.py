"""Expose our shelf at UI startup without opening a window or changing the scene."""
import hou
if hou.isUIAvailable():
    import logging
    try:
        shelf = hou.shelves.shelves().get("speedtree_bridge")
        if shelf is None:
            from pathlib import Path
            hou.shelves.loadFile(str(Path(__file__).resolve().parents[2] / "toolbar" / "speedtree_bridge.shelf"))
            shelf = hou.shelves.shelves().get("speedtree_bridge")
        dock = hou.ui.curDesktop().shelfDock()
        sets = dock.shelfSets()
        if shelf is not None and sets:
            target = sets[0]
            if shelf not in target.shelves():
                target.setShelves(target.shelves() + (shelf,))
    except Exception:
        logging.getLogger("speedtree_bridge").exception("Could not attach SpeedTree Bridge shelf; use the top menu")
