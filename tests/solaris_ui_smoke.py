"""Tabbed settings persistence and a Karma import through the native window."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.compat import QtWidgets
from bridge.native_ui import BridgeDialog
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    (base / 'tree.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n')
    source = base / 'tree.stmat'
    source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"/></Materials>')
    config = base / 'settings.json'
    dialog = BridgeDialog(config_path=config)
    dialog.renderer_choice.setCurrentIndex(2)
    assert dialog.renderer() == 'karma' and dialog.tabs.currentIndex() == 2
    assert dialog.sections.count() == 4 and dialog.karma_group.isEnabled()
    dialog.solaris_controls['resolution_x'].setValue(640)
    dialog.solaris_controls['resolution_y'].setValue(360)
    dialog.solaris_controls['samples'].setValue(32)
    dialog.karma_engine.setCurrentIndex(1)
    dialog.karma_picture.setText('$HIP/render/tree.$F4.exr')
    dialog.export_cache.setText(str(base / 'cache'))
    dialog.export_timeout.setValue(300)
    dialog.source.setText(str(source))
    dialog.import_tree()
    assert dialog.status_key == 'done', dialog.log.toPlainText()
    assert 'Solaris:' in dialog.log.toPlainText()
    saved = json.loads(config.read_text())
    assert saved['solaris']['samples'] == 32 and saved['solaris']['engine'] == 'xpu'
    assert saved['export']['timeout'] == 300
    root = hou.node('/obj/tree_bridge')
    output = hou.node(root.userData('speedtree_bridge_render_output'))
    assert output.parm('renderer').eval() == 'BRAY_HdKarmaXPU'
    restored = BridgeDialog(config_path=config)
    assert restored.renderer() == 'karma'
    assert restored.solaris_controls['resolution_y'].value() == 360
    assert restored.export_timeout.value() == 300
    restored.close()
    dialog.close()
    for index, renderer in enumerate(('arnold', 'redshift')):
        vendor = BridgeDialog(config_path=config)
        vendor.renderer_choice.setCurrentIndex(index)
        vendor.workflow.setCurrentIndex(1)
        assert vendor.context() == 'solaris' and vendor.render_stack.currentIndex() == index
        assert vendor.render_profiles['arnold']['samples'].value() == 3
        vendor.render_profiles[renderer]['resolution_x'].setValue(320)
        vendor.source.setText(str(source))
        vendor.import_tree()
        assert vendor.status_key == 'done', vendor.log.toPlainText()
        assert 'Solaris:' in vendor.log.toPlainText()
        preferences = json.loads(config.read_text())
        assert preferences['context'] == 'solaris'
        assert preferences['solaris_profiles'][renderer]['resolution_x'] == 320
        assert preferences['solaris_profiles']['karma']['samples'] == 32
        vendor.close()
print('Native tabs, Karma import, renderer synchronization and Solaris/export settings persistence: PASS')
