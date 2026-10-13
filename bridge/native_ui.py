"""Compact Houdini-native window with live localization."""
import json
import tempfile
from pathlib import Path
from .compat import QtCore, QtGui, QtWidgets, main_window, check_host
from .i18n import LANGUAGES, translate
from .package import read_export, make_request
from .houdini import import_package
ROOT = Path(__file__).resolve().parents[1]
_window = None

class BridgeDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, config_path=None):
        super().__init__(parent)
        self.setObjectName("SpeedTreeBridge")
        self.setFont(parent.font() if parent else QtWidgets.QApplication.font())
        self.setWindowTitle("SpeedTree Bridge")
        path = str(ROOT / "houdini/config/Icons/speedtree_bridge.png")
        self.setWindowIcon(QtGui.QIcon(path))
        self.setWindowFlag(QtCore.Qt.Window, True)
        self.resize(560, 430)
        self.setMinimumSize(500, 410)
        self.setStyleSheet((ROOT / "assets/theme.qss").read_text(encoding="utf-8"))
        self.config = Path(config_path) if config_path else ROOT / "settings.json"
        try: saved = json.loads(self.config.read_text(encoding="utf-8"))
        except (OSError, ValueError): saved = {}
        self.language_code = saved.get("language", "ru")
        if self.language_code not in dict(LANGUAGES): self.language_code = "en"
        self.text_widgets = []
        self.status_key, self.status_suffix = "ready", ""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        header = QtWidgets.QHBoxLayout()
        icon = QtWidgets.QLabel()
        icon.setPixmap(QtGui.QPixmap(path).scaledToHeight(40, QtCore.Qt.SmoothTransformation))
        header.addWidget(icon)
        title = QtWidgets.QLabel("SpeedTree Bridge")
        title.setObjectName("bridgeTitle")
        header.addWidget(title, 1)
        self.language = QtWidgets.QComboBox()
        for code, name in LANGUAGES: self.language.addItem(name, code)
        self.language.setCurrentIndex(self.language.findData(self.language_code))
        self.language.setMaximumWidth(122)
        header.addWidget(self.language)
        layout.addLayout(header)
        row = QtWidgets.QHBoxLayout()
        self.source = QtWidgets.QLineEdit(saved.get("source", ""))
        self.source.setPlaceholderText("SpeedTree (.stmat)")
        row.addWidget(self.source, 1)
        browse = self.text(QtWidgets.QPushButton(), "browse")
        browse.clicked.connect(self.browse)
        row.addWidget(browse)
        layout.addLayout(row)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.profiles = {}
        for renderer in ("arnold", "redshift"):
            tab = QtWidgets.QWidget()
            form = self.form(tab)
            values = {}
            for key, label, default, minimum, maximum in (("scale", "scale", 1, .000001, 1000000), ("roughness", "roughness", .5, 0, 1), ("normal_strength", "normal", 1, 0, 1000)):
                spin = QtWidgets.QDoubleSpinBox()
                spin.setDecimals(6 if key == "scale" else 3)
                spin.setMinimumHeight(26)
                spin.setRange(minimum, maximum)
                spin.setValue(float(saved.get(renderer, {}).get(key, default)))
                form.addRow(self.text(QtWidgets.QLabel(), label), spin)
                values[key] = spin
            flip = self.text(QtWidgets.QCheckBox(), "flip")
            flip.setChecked(bool(saved.get(renderer, {}).get("normal_flip_y", False)))
            form.addRow(flip)
            values["normal_flip_y"] = flip
            self.profiles[renderer] = values
            self.tabs.addTab(tab, renderer.title())
        self.tabs.setCurrentIndex(1 if saved.get("renderer") == "redshift" else 0)
        import hou
        types = hou.node("/mat").childTypeCategory().nodeTypes()
        self.available = ["arnold_materialbuilder" in types, "redshift_vopnet" in types]
        for index, available in enumerate(self.available): self.tabs.setTabEnabled(index, available)
        if any(self.available) and not self.available[self.tabs.currentIndex()]: self.tabs.setCurrentIndex(self.available.index(True))
        layout.addWidget(self.tabs)
        group = self.text(QtWidgets.QGroupBox(), "scene")
        group.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        scene_form = self.form(group)
        options = QtWidgets.QWidget()
        checks = QtWidgets.QHBoxLayout(options)
        checks.setContentsMargins(0, 0, 0, 0)
        self.scene_options = {}
        for key, label, default in (("camera", "camera", True), ("dome", "dome", True), ("sun", "sun", False)):
            checkbox = self.text(QtWidgets.QCheckBox(), label)
            checkbox.setChecked(bool(saved.get("scene", {}).get(key, default)))
            checks.addWidget(checkbox)
            self.scene_options[key] = checkbox
        checks.addStretch()
        scene_form.addRow(options)
        self.camera_view = QtWidgets.QComboBox()
        for token in ("three_quarter", "front", "side"): self.camera_view.addItem("", token)
        self.camera_view.setCurrentIndex(max(0, self.camera_view.findData(saved.get("scene", {}).get("camera_view", "three_quarter"))))
        scene_form.addRow(self.text(QtWidgets.QLabel(), "view"), self.camera_view)
        self.scene_options["camera"].toggled.connect(self.camera_view.setEnabled)
        self.camera_view.setEnabled(self.scene_options["camera"].isChecked())
        layout.addWidget(group)
        self.import_button = self.text(QtWidgets.QPushButton(), "import")
        self.import_button.setObjectName("primaryAction")
        self.import_button.setMinimumHeight(34)
        self.import_button.setEnabled(any(self.available))
        self.import_button.clicked.connect(self.import_tree)
        layout.addWidget(self.import_button)
        footer = QtWidgets.QHBoxLayout()
        self.status = QtWidgets.QLabel()
        self.status.setObjectName("bridgeStatus")
        footer.addWidget(self.status, 1)
        self.details = self.text(QtWidgets.QPushButton(), "details")
        self.details.setObjectName("detailsAction")
        self.details.setCheckable(True)
        self.details.toggled.connect(self.toggle_details)
        footer.addWidget(self.details)
        layout.addLayout(footer)
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(108)
        self.log.hide()
        layout.addWidget(self.log)
        self.apply_language()
        self.language.currentIndexChanged.connect(self.change_language)

    def form(self, widget):
        form = QtWidgets.QFormLayout(widget)
        form.setContentsMargins(12, 10, 12, 10)
        form.setVerticalSpacing(5)
        form.setHorizontalSpacing(12)
        form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        return form

    def tr_key(self, key): return translate(self.language_code, key)

    def text(self, widget, key):
        if isinstance(widget, QtWidgets.QLabel):
            widget.setMinimumWidth(110)
        self.text_widgets.append((widget, key))
        return widget

    def apply_language(self):
        for widget, key in self.text_widgets:
            if isinstance(widget, QtWidgets.QGroupBox): widget.setTitle(self.tr_key(key))
            else: widget.setText(self.tr_key(key))
        for index, key in enumerate(("quarter", "front", "side")): self.camera_view.setItemText(index, self.tr_key(key))
        for index, available in enumerate(self.available): self.tabs.setTabToolTip(index, "" if available else self.tr_key("unavailable"))
        self.status.setText(self.tr_key(self.status_key) + self.status_suffix)

    def change_language(self, index):
        self.language_code = self.language.itemData(index)
        self.apply_language()
        try:
            saved = json.loads(self.config.read_text(encoding="utf-8")) if self.config.exists() else {}
            saved["language"] = self.language_code
            self.config.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, ValueError) as error: self.log.setPlainText(str(error))

    def toggle_details(self, visible):
        self.log.setVisible(visible)
        self.resize(self.width(), self.height() + (116 if visible else -116))

    def set_status(self, key, suffix=""):
        self.status_key, self.status_suffix = key, suffix
        self.status.setText(self.tr_key(key) + suffix)

    def renderer(self): return ("arnold", "redshift")[self.tabs.currentIndex()]

    def settings(self):
        return {r: {k: w.isChecked() if k == "normal_flip_y" else w.value() for k, w in values.items()} for r, values in self.profiles.items()}

    def browse(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "SpeedTree", self.source.text(), "SpeedTree (*.stmat)")
        if path:
            self.source.setText(path)
            self.validate()

    def validate(self):
        try:
            data = read_export(self.source.text())
            lines = [data["mesh"], self.tr_key("materials") + ": " + str(len(data["materials"]))]
            lines += [m["name"] + ": " + ", ".join(m["maps"]) for m in data["materials"]]
            lines += data["warnings"]
            self.log.setPlainText("\n".join(lines))
            self.set_status("materials", ": " + str(len(data["materials"])))
        except Exception as error:
            self.log.setPlainText(str(error))
            self.set_status("error")
            self.details.setChecked(True)

    def import_tree(self):
        self.import_button.setEnabled(False)
        self.set_status("busy")
        QtWidgets.QApplication.processEvents()
        try:
            settings = self.settings()
            scene = {key: widget.isChecked() for key, widget in self.scene_options.items()}
            scene["camera_view"] = self.camera_view.currentData()
            request = make_request(self.source.text(), self.renderer(), dict(settings[self.renderer()], scene=scene))
            with tempfile.TemporaryDirectory(prefix="speedtree_bridge_") as directory:
                path = Path(directory) / "tree.bridge.json"
                path.write_text(json.dumps(request), encoding="utf-8")
                result = import_package(path)
            settings.update(source=self.source.text(), renderer=self.renderer(), scene=scene, language=self.language_code)
            self.config.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
            lines = [self.tr_key("done") + ": " + result["root"], self.tr_key("polygons") + ": " + str(result["primitives"])]
            lines += list(result["materials"].values())
            if result.get("render_output"): lines.append("Arnold: " + result["render_output"])
            if result.get("camera"): lines.append(self.tr_key("camera") + ": " + result["camera"])
            lines += [self.tr_key("light") + ": " + p for p in result.get("lights", [])]
            lines += result.get("notes", [])
            self.log.setPlainText("\n".join(lines))
            self.set_status("done")
        except Exception as error:
            self.log.setPlainText(self.tr_key("error") + ":\n" + str(error))
            self.set_status("error")
            self.details.setChecked(True)
        finally: self.import_button.setEnabled(any(self.available))

def show():
    global _window
    import hou
    if not hou.isUIAvailable(): raise RuntimeError("Open SpeedTree Bridge in interactive Houdini")
    if _window is None:
        check_host()
        _window = BridgeDialog(main_window())
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window
