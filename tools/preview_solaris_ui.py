"""Render the authored Qt tabs offscreen, with temporary preview preferences."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge.compat import QtWidgets
from bridge.native_ui import BridgeDialog
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
with tempfile.TemporaryDirectory() as directory:
    dialog = BridgeDialog(config_path=Path(directory) / 'settings.json')
    dialog.renderer_choice.setCurrentIndex(2)
    dialog.source.setText('D:/Trees/Oak/oak.spm')
    dialog.modeler.setText('SpeedTree_Modeler.exe')
    dialog.export_cache.setText('$HIP/speedtree_cache')
    dialog.profiles['karma']['scale'].setValue(.01)
    dialog.set_status('live_ready')
    dialog.show()
    for index, name in enumerate(('general', 'materials', 'render', 'export')):
        dialog.sections.setCurrentIndex(index)
        app.processEvents()
        target = Path(__file__).resolve().parents[1] / 'assets' / ('solaris_' + name + '_preview.png')
        assert dialog.grab().save(str(target))
        print(target)
    for index, renderer in enumerate(('arnold', 'redshift')):
        dialog.renderer_choice.setCurrentIndex(index)
        dialog.workflow.setCurrentIndex(1)
        dialog.sections.setCurrentIndex(2)
        app.processEvents()
        target = Path(__file__).resolve().parents[1] / 'assets' / ('solaris_' + renderer + '_preview.png')
        assert dialog.grab().save(str(target))
    dialog.close()
