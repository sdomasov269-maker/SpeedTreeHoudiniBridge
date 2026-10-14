import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge.compat import QtWidgets
from bridge.native_ui import BridgeDialog
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
config_temp = tempfile.TemporaryDirectory()
dialog = BridgeDialog(config_path=Path(config_temp.name) / 'settings.json')
assert dialog.tabs.count() == 3
assert dialog.sections.count() == 4
dialog.profiles["arnold"]["roughness"].setValue(.25)
dialog.profiles["redshift"]["roughness"].setValue(.75)
assert dialog.settings()["arnold"]["roughness"] == .25
assert dialog.settings()["redshift"]["roughness"] == .75
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    (folder / "native.obj").write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    (folder / "native.stmat").write_text('<Materials Mesh="native.obj"><Material Name="bark"><Map Name="Color" Value="0.4"/></Material></Materials>')
    dialog.config = folder / "settings.json"
    dialog.source.setText(str(folder / "native.stmat"))
    dialog.validate()
    assert "native.obj" in dialog.log.toPlainText()
    chosen = 0 if dialog.available[0] else 1
    dialog.tabs.setCurrentIndex(chosen)
    dialog.scene_options['camera'].setChecked(True)
    dialog.scene_options['dome'].setChecked(True)
    dialog.import_tree()
    assert "Импорт завершён" in dialog.log.toPlainText(), dialog.log.toPlainText()
    assert "/mat/native_" + ('arnold' if chosen == 0 else 'redshift') + "_bark" in dialog.log.toPlainText()
    assert "Камера:" in dialog.log.toPlainText()
    assert "Свет:" in dialog.log.toPlainText()
    import hou
    if chosen == 0:
        assert "/out/native_arnold" in dialog.log.toPlainText()
        assert hou.node('/out/native_arnold').parm('camera').eval().endswith('_camera')
    assert dialog.import_button.isEnabled()
dialog.show()
app.processEvents()
assert dialog.isVisible()
dialog.close()
config_temp.cleanup()
print("Native Qt window, settings, validation, and direct scene import: PASS")
