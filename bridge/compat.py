"""Python 3 / Qt 5 and Qt 6 adapters for Houdini 19+."""
import importlib
import sys


def load_qt():
    errors = []
    for name in ("hutil.PySide", "hutil.Qt", "PySide6", "PySide2"):
        try:
            module = importlib.import_module(name)
            return module.QtCore, module.QtGui, module.QtWidgets
        except (ImportError, AttributeError) as error:
            errors.append(str(error))
    raise ImportError("Houdini Qt binding is unavailable: " + "; ".join(errors))


QtCore, QtGui, QtWidgets = load_qt()


def main_window():
    import hou
    if hasattr(hou, "qt") and hasattr(hou.qt, "mainWindow"):
        return hou.qt.mainWindow()
    return hou.ui.mainQtWindow()


def check_host():
    import hou
    if hou.applicationVersion()[0] < 19 or sys.version_info < (3, 7):
        raise RuntimeError("SpeedTree Bridge requires Houdini 19+ with Python 3.7 or newer.")
    return hou.applicationVersionString()
