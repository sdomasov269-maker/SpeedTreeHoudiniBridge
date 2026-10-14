"""Real Modeler export from the native UI: hython script.py MODELER_EXE SAMPLE_SPM."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.compat import QtWidgets
import bridge.native_ui as ui
from bridge.speedtree import export_project

if len(sys.argv) not in (3, 4, 5):
    raise SystemExit('Provide SpeedTree Modeler executable and sample .spm')
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
renderer = sys.argv[3] if len(sys.argv) >= 4 else 'redshift'
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    def exporter(executable, project, cache):
        return export_project(executable, project, base / 'cache')
    with patch.object(ui, 'export_project', side_effect=exporter):
        dialog = ui.BridgeDialog(config_path=base / 'settings.json')
        dialog.tabs.setCurrentIndex(('arnold', 'redshift', 'karma').index(renderer))
        if len(sys.argv) == 5:
            dialog.workflow.setCurrentIndex(1 if sys.argv[4] == 'solaris' else 0)
        dialog.modeler.setText(sys.argv[1])
        dialog.source.setText(sys.argv[2])
        dialog.profiles[renderer]['scale'].setValue(.01)
        dialog.show()
        previous = None
        for index in range(2):
            dialog.import_tree()
            deadline = time.monotonic() + 200
            while (dialog._live_busy or dialog._worker is not None) and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.02)
            assert not dialog._live_busy and dialog._worker is None
            assert dialog.status_key == ('live_updated' if index else 'done'), dialog.log.toPlainText()
            roots = [n for n in hou.node('/obj').children() if n.userData('speedtree_live_id')]
            assert len(roots) == 1
            root = roots[0]
            assert len(root.node('mesh/bridge_assign').geometry().prims()) > 0
            if previous:
                assert root == previous
                assert {p: set(hou.node(p).children()) for p in before} == before
            previous = root
            before = {p: set(hou.node(p).children()) for p in ('/obj', '/mat', '/out', '/stage')}
        dialog.close()
print(renderer, 'real SpeedTree 10.2 export from native Qt window, first import and stable update: PASS')
