import os, tempfile
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from bridge.compat import QtWidgets
from bridge.native_ui import BridgeDialog
from bridge.i18n import LANGUAGES, translate
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
with tempfile.TemporaryDirectory() as directory:
    config = Path(directory) / 'settings.json'
    dialog = BridgeDialog(config_path=config)
    dialog.profiles['arnold']['roughness'].setValue(.321)
    dialog.camera_view.setCurrentIndex(2)
    dialog.show()
    app.processEvents()
    assert dialog.width() <= 560 and dialog.height() <= 500, dialog.size()
    assert not dialog.log.isVisible()
    for code, _ in LANGUAGES:
        dialog.language.setCurrentIndex(dialog.language.findData(code))
        app.processEvents()
        assert dialog.import_button.text() == translate(code,'import')
        assert dialog.profiles['arnold']['roughness'].value() == .321
        assert dialog.camera_view.currentData() == 'side'
        assert all(w.title() == translate(code,k) if isinstance(w,QtWidgets.QGroupBox) else w.text() == translate(code,k) for w,k in dialog.text_widgets)
        print(code, 'live translation and values retained: PASS')
    restored = BridgeDialog(config_path=config)
    assert restored.language_code == 'zh_TW'
    restored.close()
    dialog.details.setChecked(True)
    app.processEvents()
    assert dialog.log.isVisible()
    dialog.details.setChecked(False)
    app.processEvents()
    assert not dialog.log.isVisible()
    dialog.close()
