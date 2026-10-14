"""Native live controls, asynchronous export, main-thread updates and close safety."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.compat import QtCore, QtWidgets
import bridge.native_ui as ui
import bridge.live as live
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    project = base / 'oak.spm'
    project.touch()
    revision = [0]
    def exporter(executable, source, cache):
        assert QtCore.QThread.currentThread() != app.thread()
        revision[0] += 1
        folder = base / str(revision[0])
        folder.mkdir()
        (folder / 'tree.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 {} 0\nf 1 2 3\n'.format(revision[0]))
        source = folder / 'tree.stmat'
        source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"/></Materials>')
        return source
    original = live.apply_live_request
    def apply_request(filename):
        assert QtCore.QThread.currentThread() == app.thread()
        return original(filename)
    def wait(dialog):
        deadline = time.monotonic() + 20
        while (dialog._live_busy or dialog._worker is not None) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        assert not dialog._live_busy and dialog._worker is None, 'Live worker did not finish'
    parent = QtWidgets.QWidget()
    with patch.object(ui, 'export_project', side_effect=exporter), patch.object(live, 'apply_live_request', side_effect=apply_request):
        dialog = ui.BridgeDialog(parent, config_path=base / 'settings.json')
        assert dialog.parentWidget() == parent
        dialog.tabs.setCurrentIndex(1)
        dialog.source.setText(str(project))
        dialog.profiles['redshift']['scale'].setValue(.01)
        dialog.show()
        app.processEvents()
        assert not dialog.live_group.isHidden()
        assert dialog.import_button.text() == dialog.tr_key('live_update')
        dialog.import_tree()
        wait(dialog)
        assert dialog.status_key == 'done', dialog.log.toPlainText()
        root = hou.node('/obj/tree_bridge')
        assert root is not None
        before = {p: set(hou.node(p).children()) for p in ('/obj', '/mat', '/out')}
        dialog.import_tree()
        wait(dialog)
        assert dialog.status_key == 'live_updated', dialog.log.toPlainText()
        assert root.node('mesh/bridge_assign').geometry().boundingBox().maxvec()[1] == 2
        assert all(set(hou.node(p).children()) == nodes for p, nodes in before.items())
        # Save watcher sends exactly one debounced update.
        dialog.auto_live.setChecked(True)
        dialog._live_signature = dialog.project_signature()
        dialog._live_changed_at = time.monotonic() - 2
        dialog.watch_live_project()
        wait(dialog)
        assert revision[0] == 3
        dialog.auto_live.setChecked(False)
        # A HIP change while exporting rejects the candidate before scene mutation.
        dialog.import_tree()
        dialog.scene_changed(hou.hipFileEventType.AfterClear)
        wait(dialog)
        assert dialog.status_key == 'error'
        assert root.node('mesh/bridge_assign').geometry().boundingBox().maxvec()[1] == 3
        # Closing the owned window also prevents a late result from importing.
        dialog.import_tree()
        dialog.close()
        wait(dialog)
        assert root.node('mesh/bridge_assign').geometry().boundingBox().maxvec()[1] == 3
        assert not dialog._scene_callback_registered
        dialog.show()
        dialog.details.setChecked(False)
        dialog.source.setText('C:/Assets/Oak/oak.spm')
        dialog.modeler.setText('SpeedTree_Modeler.exe')
        dialog.set_status('live_ready')
        app.processEvents()
        preview = Path(__file__).resolve().parents[1] / 'assets' / 'native_live_preview.png'
        assert dialog.grab().save(str(preview))
        dialog.source.setText('C:/Assets/Oak/oak.stmat')
        app.processEvents()
        assert dialog.live_group.isHidden() and dialog.import_button.text() == dialog.tr_key('import')
        dialog.close()
    parent.close()
print('Native Houdini-owned live UI, background export, main-thread updates, watcher and scene/close safety: PASS')
