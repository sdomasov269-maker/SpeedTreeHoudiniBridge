"""Compact Houdini-native window with live localization."""
import json
import tempfile
import time
from pathlib import Path
from .compat import QtCore, QtGui, QtWidgets, main_window, check_host
from .i18n import LANGUAGES, translate
from .package import read_export, make_request
from .houdini import import_package
from .speedtree import discover_modeler, export_project, asset_identity
ROOT = Path(__file__).resolve().parents[1]
_window = None

class LiveExportWorker(QtCore.QThread):
    succeeded = QtCore.Signal(str)
    failed = QtCore.Signal(str)

    def __init__(self, executable, project, renderer, settings, parent=None):
        super().__init__(parent)
        self.executable, self.project = executable, project
        self.renderer, self.export_settings = renderer, settings

    def run(self):
        try:
            options = self.export_settings.get('export', {})
            kwargs = {}
            if options.get('preset'):
                kwargs['preset'] = options['preset']
            if options.get('timeout', 180) != 180:
                kwargs['timeout'] = options['timeout']
            source = export_project(self.executable, self.project, options.get('cache') or ROOT / 'live_cache', **kwargs)
            request = make_request(source, self.renderer, self.export_settings)
            request['live'] = {'asset_id': asset_identity(self.project), 'project': str(Path(self.project).resolve()),
                               'revision': source.parent.name}
            filename = source.parent / 'native.bridge.json'
            filename.write_text(json.dumps(request), encoding='utf-8')
            self.succeeded.emit(str(filename))
        except Exception as error:
            self.failed.emit(str(error))


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
        layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
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
        self.sections = QtWidgets.QTabWidget()
        self.section_keys = ('general_tab', 'materials_tab', 'render_tab', 'export_tab')
        self.pages = []
        for key in self.section_keys:
            page = QtWidgets.QWidget()
            page_layout = QtWidgets.QVBoxLayout(page)
            page_layout.setContentsMargins(10, 12, 10, 12)
            page_layout.setSpacing(10)
            self.sections.addTab(page, '')
            self.pages.append(page_layout)
        layout.addWidget(self.sections)
        general, materials_page, render_page, export_page = self.pages
        row = QtWidgets.QHBoxLayout()
        self.source = QtWidgets.QLineEdit(saved.get("source", ""))
        self.selected_sources = []
        self.source.textEdited.connect(self.clear_batch)
        self.source.setPlaceholderText("SpeedTree (.stmat)")
        row.addWidget(self.source, 1)
        browse = self.text(QtWidgets.QPushButton(), "browse")
        browse.clicked.connect(self.browse)
        row.addWidget(browse)
        general.addLayout(row)
        renderer_row = QtWidgets.QHBoxLayout()
        renderer_row.addWidget(self.text(QtWidgets.QLabel(), 'renderer_label'))
        self.renderer_choice = QtWidgets.QComboBox()
        self.renderer_choice.addItems(['Arnold', 'Redshift', 'Karma'])
        renderer_row.addWidget(self.renderer_choice, 1)
        general.addLayout(renderer_row)
        context_row = QtWidgets.QHBoxLayout()
        context_row.addWidget(self.text(QtWidgets.QLabel(), 'context_label'))
        self.workflow = QtWidgets.QComboBox()
        self.workflow.addItem('OBJ', 'obj')
        self.workflow.addItem('Solaris / USD', 'solaris')
        self.workflow.setCurrentIndex(1 if saved.get('context') == 'solaris' else 0)
        context_row.addWidget(self.workflow, 1)
        general.addLayout(context_row)
        scale_row = QtWidgets.QHBoxLayout()
        scale_row.addWidget(self.text(QtWidgets.QLabel(), 'scale'))
        self.scale_stack = QtWidgets.QStackedWidget()
        self.scale_stack.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        scale_row.addWidget(self.scale_stack, 1)
        general.addLayout(scale_row)
        self.live_group = self.text(QtWidgets.QGroupBox(), 'live')
        live_form = self.form(self.live_group)
        executable_row = QtWidgets.QWidget()
        executable_layout = QtWidgets.QHBoxLayout(executable_row)
        executable_layout.setContentsMargins(0, 0, 0, 0)
        self.modeler = QtWidgets.QLineEdit(saved.get('live', {}).get('executable') or discover_modeler())
        executable_layout.addWidget(self.modeler, 1)
        executable_browse = self.text(QtWidgets.QPushButton(), 'browse')
        executable_browse.clicked.connect(self.browse_modeler)
        executable_layout.addWidget(executable_browse)
        live_form.addRow(QtWidgets.QLabel('SpeedTree'), executable_row)
        self.auto_live = self.text(QtWidgets.QCheckBox(), 'auto_live')
        live_form.addRow(self.auto_live)
        self.live_hint = self.text(QtWidgets.QLabel(), 'live_hint')
        self.live_hint.setWordWrap(True)
        live_form.addRow(self.live_hint)
        self.live_group.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.live_group.hide()
        export_page.addWidget(self.live_group)
        export_options = QtWidgets.QWidget()
        export_form = self.form(export_options)
        self.export_cache = QtWidgets.QLineEdit(saved.get('export', {}).get('cache', str(ROOT / 'live_cache')))
        export_form.addRow(self.text(QtWidgets.QLabel(), 'export_cache'), self.export_cache)
        preset_row = QtWidgets.QWidget()
        preset_layout = QtWidgets.QHBoxLayout(preset_row)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        self.export_preset = QtWidgets.QLineEdit(saved.get('export', {}).get('preset', ''))
        preset_layout.addWidget(self.export_preset, 1)
        preset_browse = self.text(QtWidgets.QPushButton(), 'browse')
        preset_browse.clicked.connect(self.browse_export_preset)
        preset_layout.addWidget(preset_browse)
        export_form.addRow(self.text(QtWidgets.QLabel(), 'export_preset'), preset_row)
        self.export_timeout = QtWidgets.QSpinBox()
        self.export_timeout.setRange(30, 1800)
        self.export_timeout.setValue(int(saved.get('export', {}).get('timeout', 180)))
        export_form.addRow(self.text(QtWidgets.QLabel(), 'export_timeout'), self.export_timeout)
        export_page.addWidget(export_options)
        export_page.addStretch()
        self._worker = None
        self._live_busy = False
        self._live_signature = None
        self._live_changed_at = None
        self._scene_generation = 0
        self._export_generation = None
        self._scene_callback_registered = False
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.profiles = {}
        for renderer in ("arnold", "redshift", "karma"):
            tab = QtWidgets.QWidget()
            form = self.form(tab)
            values = {}
            for key, label, default, minimum, maximum in (("scale", "scale", 1, .000001, 1000000), ("roughness", "roughness", .5, 0, 1), ("normal_strength", "normal", 1, 0, 1000)):
                spin = QtWidgets.QDoubleSpinBox()
                spin.setDecimals(6 if key == "scale" else 3)
                spin.setMinimumHeight(26)
                spin.setRange(minimum, maximum)
                spin.setValue(float(saved.get(renderer, {}).get(key, default)))
                if key == 'scale':
                    self.scale_stack.addWidget(spin)
                else:
                    form.addRow(self.text(QtWidgets.QLabel(), label), spin)
                values[key] = spin
            flip = self.text(QtWidgets.QCheckBox(), "flip")
            flip.setChecked(bool(saved.get(renderer, {}).get("normal_flip_y", False)))
            form.addRow(flip)
            values["normal_flip_y"] = flip
            self.profiles[renderer] = values
            self.tabs.addTab(tab, 'Karma / MaterialX' if renderer == 'karma' else renderer.title())
        self.tabs.setCurrentIndex(('arnold', 'redshift', 'karma').index(saved.get('renderer', 'arnold')) if saved.get('renderer', 'arnold') in ('arnold', 'redshift', 'karma') else 0)
        import hou
        types = hou.node("/mat").childTypeCategory().nodeTypes()
        stage_network = hou.node('/stage')
        karma_available = stage_network is not None and 'karmarendersettings' in stage_network.childTypeCategory().nodeTypes()
        from .solaris import available_delegates
        self.solaris_delegates = available_delegates()
        self.available = ["arnold_materialbuilder" in types, "redshift_vopnet" in types, karma_available]
        for index, available in enumerate(self.available): self.tabs.setTabEnabled(index, available)
        if any(self.available) and not self.available[self.tabs.currentIndex()]: self.tabs.setCurrentIndex(self.available.index(True))
        materials_page.addWidget(self.tabs)
        materials_page.addStretch()
        self.renderer_choice.setCurrentIndex(self.tabs.currentIndex())
        self.scale_stack.setCurrentIndex(self.tabs.currentIndex())
        for index, available in enumerate(self.available):
            self.renderer_choice.model().item(index).setEnabled(available)
        self.renderer_choice.currentIndexChanged.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.renderer_choice.setCurrentIndex)
        self.tabs.currentChanged.connect(self.scale_stack.setCurrentIndex)
        self.karma_group = self.text(QtWidgets.QGroupBox(), 'karma_render')
        karma_form = self.form(self.karma_group)
        self.karma_engine = QtWidgets.QComboBox()
        self.karma_engine.addItem('Karma CPU', 'cpu')
        self.karma_engine.addItem('Karma XPU', 'xpu')
        solaris_saved = saved.get('solaris_profiles', {}).get('karma', saved.get('solaris', {}))
        self.karma_engine.setCurrentIndex(1 if solaris_saved.get('engine') == 'xpu' else 0)
        karma_form.addRow(self.text(QtWidgets.QLabel(), 'karma_engine'), self.karma_engine)
        self.solaris_controls = {}
        for key, label, default, low, high in (('resolution_x', 'resolution_x', 1280, 16, 32768), ('resolution_y', 'resolution_y', 720, 16, 32768), ('samples', 'karma_samples', 128, 1, 65536)):
            widget = QtWidgets.QSpinBox()
            widget.setRange(low, high)
            widget.setValue(int(solaris_saved.get(key, default)))
            karma_form.addRow(self.text(QtWidgets.QLabel(), label), widget)
            self.solaris_controls[key] = widget
        self.karma_picture = QtWidgets.QLineEdit(solaris_saved.get('output_image', '$HIP/render/$HIPNAME.$OS.$F4.exr'))
        karma_form.addRow(self.text(QtWidgets.QLabel(), 'output_image'), self.karma_picture)
        self.render_stack = QtWidgets.QStackedWidget()
        self.render_profiles = {}
        for renderer in ('arnold', 'redshift'):
            vendor_group = QtWidgets.QGroupBox('Solaris / ' + renderer.title())
            vendor_form = self.form(vendor_group)
            values = {}
            prior = saved.get('solaris_profiles', {}).get(renderer, {})
            for key, label, default, high in (('resolution_x', 'resolution_x', 1280, 32768),
                                             ('resolution_y', 'resolution_y', 720, 32768),
                                             ('samples', 'arnold_samples' if renderer == 'arnold' else 'redshift_samples', 3 if renderer == 'arnold' else 128, 16 if renderer == 'arnold' else 65536)):
                spin = QtWidgets.QSpinBox()
                spin.setRange(16 if key.startswith('resolution_') else 1, high)
                spin.setValue(int(prior.get(key, default)))
                vendor_form.addRow(self.text(QtWidgets.QLabel(), label), spin)
                values[key] = spin
            picture = QtWidgets.QLineEdit(prior.get('output_image', '$HIP/render/$HIPNAME.$OS.$F4.exr'))
            vendor_form.addRow(self.text(QtWidgets.QLabel(), 'output_image'), picture)
            values['output_image'] = picture
            self.render_profiles[renderer] = values
            self.render_stack.addWidget(vendor_group)
        self.render_profiles['karma'] = dict(self.solaris_controls, output_image=self.karma_picture)
        self.render_stack.addWidget(self.karma_group)
        self.render_stack.setCurrentIndex(self.tabs.currentIndex())
        render_page.addWidget(self.render_stack)
        render_hint = self.text(QtWidgets.QLabel(), 'solaris_hint')
        render_hint.setWordWrap(True)
        render_page.addWidget(render_hint)
        render_page.addStretch()
        self.tabs.currentChanged.connect(self.render_stack.setCurrentIndex)
        self.tabs.currentChanged.connect(self.update_context)
        self.workflow.currentIndexChanged.connect(self.update_context)
        self.update_context()
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
        general.addWidget(group)
        general.addStretch()
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
        self.tabs.setMinimumHeight(self.tabs.sizeHint().height() + 18)
        self.language.currentIndexChanged.connect(self.change_language)
        self.source.textChanged.connect(self.update_live_mode)
        self.auto_live.toggled.connect(self.toggle_auto_live)
        self._watcher = QtCore.QTimer(self)
        self._watcher.setInterval(500)
        self._watcher.timeout.connect(self.watch_live_project)
        self.update_live_mode()

    def is_live(self):
        return Path(self.source.text()).suffix.lower() == '.spm'

    def update_live_mode(self):
        live = self.is_live()
        self.live_group.setVisible(live)
        for index, (widget, key) in enumerate(self.text_widgets):
            if widget is self.import_button:
                self.text_widgets[index] = (widget, 'live_update' if live else 'import')
                widget.setText(self.tr_key('live_update' if live else 'import'))
                break
        self._live_signature = None
        self._live_changed_at = None
        if not live:
            self.auto_live.setChecked(False)
        self.source.setPlaceholderText('SpeedTree (.stmat / .spm)')
        self.live_group.setMinimumHeight(self.live_group.sizeHint().height())
        self.adjustSize()
        self.resize(max(560, self.width()), self.height())

    def browse_modeler(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'SpeedTree Modeler', self.modeler.text(), 'SpeedTree Modeler (*)')
        if path:
            self.modeler.setText(path)

    def browse_export_preset(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'SpeedTree export preset', self.export_preset.text(), 'SpeedTree (*.ini)')
        if path:
            self.export_preset.setText(path)

    def solaris_options(self):
        return self.solaris_profiles()[self.renderer()]

    def solaris_profiles(self):
        return {renderer: dict({key: widget.text() if key == 'output_image' else widget.value()
                               for key, widget in values.items()},
                              engine=self.karma_engine.currentData() if renderer == 'karma' else 'cpu')
                for renderer, values in self.render_profiles.items()}

    def context(self):
        return 'solaris' if self.renderer() == 'karma' else self.workflow.currentData()

    def update_context(self, *args):
        from .solaris import renderer_delegate
        karma = self.renderer() == 'karma'
        supported = renderer_delegate(self.renderer()) in self.solaris_delegates
        self.workflow.model().item(1).setEnabled(supported)
        self.workflow.setToolTip('' if supported else self.tr_key('unavailable'))
        self.workflow.setEnabled(not karma)
        if karma:
            self.workflow.setCurrentIndex(1)
        self.render_stack.setEnabled(self.context() == 'solaris')

    def export_options(self):
        import hou
        return {'cache': hou.text.expandString(self.export_cache.text()),
                'preset': hou.text.expandString(self.export_preset.text()), 'timeout': self.export_timeout.value()}

    def toggle_auto_live(self, enabled):
        self._live_signature = None
        self._live_changed_at = time.monotonic() if enabled else None
        if enabled:
            self._watcher.start()

    def project_signature(self):
        stat = Path(self.source.text()).stat()
        return (self.source.text(), stat.st_mtime_ns, stat.st_size)

    def watch_live_project(self):
        if not self.is_live() or not self.auto_live.isChecked() or self._live_busy:
            return
        try:
            signature = self.project_signature()
            if signature != self._live_signature:
                self._live_signature = signature
                self._live_changed_at = time.monotonic()
            if self._live_changed_at and time.monotonic() - self._live_changed_at >= 1:
                self.start_live_export()
        except OSError as error:
            self.live_failed(str(error))

    def scene_changed(self, event):
        import hou
        if event in (hou.hipFileEventType.AfterLoad, hou.hipFileEventType.AfterClear):
            self._scene_generation += 1
            self.auto_live.setChecked(False)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._scene_callback_registered:
            import hou
            hou.hipFile.addEventCallback(self.scene_changed)
            self._scene_callback_registered = True
        self._watcher.start()

    def closeEvent(self, event):
        self.auto_live.setChecked(False)
        self._watcher.stop()
        self._scene_generation += 1
        if self._scene_callback_registered:
            import hou
            hou.hipFile.removeEventCallback(self.scene_changed)
            self._scene_callback_registered = False
        super().closeEvent(event)

    def start_live_export(self):
        if self._live_busy or (self._worker and self._worker.isRunning()):
            return
        try:
            if self.context() == 'solaris':
                from .solaris import require_renderer
                require_renderer(self.renderer(), self.solaris_options()['engine'])
            if not self._scene_callback_registered:
                import hou
                hou.hipFile.addEventCallback(self.scene_changed)
                self._scene_callback_registered = True
            self._live_signature = self.project_signature()
            self._live_changed_at = None
            scene = {key: widget.isChecked() for key, widget in self.scene_options.items()}
            scene['camera_view'] = self.camera_view.currentData()
            profiles = self.settings()
            export = self.export_options()
            if export['preset'] and not Path(export['preset']).is_file():
                raise ValueError(self.tr_key('export_preset_missing'))
            settings = dict(profiles[self.renderer()], scene=scene, context=self.context(), solaris=self.solaris_options(), export=export)
            profiles.update(source=self.source.text(), renderer=self.renderer(), scene=scene,
                            language=self.language_code, live={'executable': self.modeler.text()},
                            context=self.context(), solaris=self.solaris_profiles()['karma'], solaris_profiles=self.solaris_profiles(), export=export)
            self.config.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding='utf-8')
            self._export_generation = self._scene_generation
            self._worker = LiveExportWorker(self.modeler.text(), self.source.text(), self.renderer(), settings, self)
            self._worker.succeeded.connect(self.live_exported)
            self._worker.failed.connect(self.live_failed)
            self._worker.finished.connect(self.worker_finished)
            self._live_busy = True
            self.setEnabled(False)
            self.set_status('live_busy')
            self._worker.start()
        except Exception as error:
            self.live_failed(str(error))

    def finish_live_export(self):
        self._live_busy = False
        self.setEnabled(True)
        self.import_button.setEnabled(any(self.available))

    def worker_finished(self):
        worker = self.sender()
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    def live_failed(self, error):
        self.auto_live.setChecked(False)
        self.log.setPlainText(str(error))
        self.set_status('error')
        self.details.setChecked(True)
        self.finish_live_export()

    def live_exported(self, filename):
        try:
            if self._export_generation != self._scene_generation:
                raise RuntimeError(self.tr_key('live_scene_changed'))
            from .live import apply_live_request
            result = apply_live_request(filename)
            lines = [self.tr_key('live_updated' if result['updated'] else 'done') + ': ' + result['root'],
                     self.tr_key('polygons') + ': ' + str(result['primitives'])]
            lines += list(result['materials'].values()) + result.get('notes', [])
            if result.get('stage'):
                lines.append('Solaris: ' + result['stage'])
            if result.get('render_output'):
                lines.append(self.renderer().title() + ': ' + result['render_output'])
            self.log.setPlainText('\n'.join(lines))
            self.set_status('live_updated' if result['updated'] else 'done')
        except Exception as error:
            self.live_failed(str(error))
        finally:
            self.finish_live_export()

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
        for index, key in enumerate(self.section_keys): self.sections.setTabText(index, self.tr_key(key))
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
        self.adjustSize()
        self.resize(max(560, self.width()), self.height())

    def set_status(self, key, suffix=""):
        self.status_key, self.status_suffix = key, suffix
        self.status.setText(self.tr_key(key) + suffix)

    def renderer(self): return ("arnold", "redshift", "karma")[self.tabs.currentIndex()]

    def settings(self):
        return {r: {k: w.isChecked() if k == "normal_flip_y" else w.value() for k, w in values.items()} for r, values in self.profiles.items()}

    def browse(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "SpeedTree", self.source.text(), "SpeedTree (*.stmat *.spm)")
        if paths:
            if any(Path(path).suffix.lower() == '.spm' for path in paths) and len(paths) != 1:
                self.live_failed(self.tr_key('live_one_project'))
                return
            self.selected_sources = list(dict.fromkeys(paths))
            self.source.setText(self.selected_sources[0])
            self.source.setToolTip("\n".join(self.selected_sources))
            self.validate()

    def clear_batch(self):
        self.selected_sources = []
        self.source.setToolTip("")

    def sources(self):
        return self.selected_sources or [self.source.text()]

    def validate(self):
        try:
            if self.is_live():
                self.project_signature()
                self.log.setPlainText(self.source.text() + '\n' + self.tr_key('live_hint'))
                self.set_status('live_ready')
                return
            lines, count = [], 0
            for filename in self.sources():
                data = read_export(filename)
                count += len(data["materials"])
                lines += [data["mesh"], self.tr_key("materials") + ": " + str(len(data["materials"]))]
                lines += [m["name"] + ": " + ", ".join(m["maps"]) for m in data["materials"]]
                lines += data["warnings"]
            self.log.setPlainText("\n".join(lines))
            self.set_status("materials", ": " + str(count) + " / " + str(len(self.sources())) + " .stmat")
        except Exception as error:
            self.log.setPlainText(str(error))
            self.set_status("error")
            self.details.setChecked(True)

    def import_tree(self):
        if self.is_live():
            self.start_live_export()
            return
        self.setEnabled(False)
        self.import_button.setEnabled(False)
        self.set_status("busy")
        QtWidgets.QApplication.processEvents()
        try:
            settings = self.settings()
            scene = {key: widget.isChecked() for key, widget in self.scene_options.items()}
            scene["camera_view"] = self.camera_view.currentData()
            lines, failures = [], 0
            with tempfile.TemporaryDirectory(prefix="speedtree_bridge_") as directory:
                path = Path(directory) / "tree.bridge.json"
                for filename in self.sources():
                    try:
                        request = make_request(filename, self.renderer(), dict(settings[self.renderer()], scene=scene, context=self.context(), solaris=self.solaris_options()))
                        path.write_text(json.dumps(request), encoding="utf-8")
                        result = import_package(path)
                        lines += [self.tr_key("done") + ": " + result["root"], self.tr_key("polygons") + ": " + str(result["primitives"])]
                        lines += list(result["materials"].values())
                        if result.get("render_output"): lines.append(self.renderer().title() + ": " + result["render_output"])
                        if result.get('stage'): lines.append('Solaris: ' + result['stage'])
                        if result.get("camera"): lines.append(self.tr_key("camera") + ": " + result["camera"])
                        lines += [self.tr_key("light") + ": " + p for p in result.get("lights", [])]
                        lines += result.get("notes", [])
                    except Exception as error:
                        failures += 1
                        lines.append(self.tr_key("error") + ": " + filename + "\n" + str(error))
                    QtWidgets.QApplication.processEvents()
            settings.update(source=self.source.text(), renderer=self.renderer(), scene=scene, language=self.language_code,
                            context=self.context(), solaris=self.solaris_profiles()['karma'], solaris_profiles=self.solaris_profiles(), export=self.export_options())
            self.config.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
            self.log.setPlainText("\n".join(lines))
            self.set_status("error" if failures else "done", ": " + str(len(self.sources()) - failures) + "/" + str(len(self.sources())))
            if failures: self.details.setChecked(True)
        except Exception as error:
            self.log.setPlainText(self.tr_key("error") + ":\n" + str(error))
            self.set_status("error")
            self.details.setChecked(True)
        finally:
            self.setEnabled(True)
            self.import_button.setEnabled(any(self.available))

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
