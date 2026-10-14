"""Exercise multiple exports and a failed item through the native UI."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.compat import QtWidgets
from bridge.native_ui import BridgeDialog

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    dialog = BridgeDialog(config_path=base / 'settings.json')
    dialog.tabs.setCurrentIndex(1)
    paths = []
    for name in ('first', 'broken', 'last'):
        (base / (name + '.obj')).write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n')
        source = base / (name + '.stmat')
        source.write_text('<Materials Mesh="{}.obj"><Material Name="bark"/></Materials>'.format(name))
        paths.append(str(source))
    (base / 'broken.obj').unlink()
    dialog.selected_sources = paths
    dialog.source.setText(paths[0])
    dialog.import_tree()
    assert hou.node('/obj/first_bridge') is not None
    assert hou.node('/obj/last_bridge') is not None
    assert hou.node('/obj/broken_bridge') is None
    assert 'broken.stmat' in dialog.log.toPlainText()
    assert dialog.status_key == 'error' and dialog.status_suffix == ': 2/3'
    assert dialog.isEnabled() and dialog.import_button.isEnabled()
    dialog.clear_batch()
    assert dialog.sources() == [paths[0]]
    dialog.close()
print(hou.applicationVersionString(), 'batch UI, per-item failure and restored controls: PASS')
