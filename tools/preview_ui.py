import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from bridge.compat import QtWidgets
from bridge.native_ui import BridgeDialog
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
window = BridgeDialog()
window.source.setText("C:/Assets/Oak/oak.stmat")
window.set_status("ready")
window.show()
app.processEvents()
path = Path(__file__).resolve().parents[1] / "assets" / "ui_preview.png"
window.grab().save(str(path))
window.close()
print(path)
