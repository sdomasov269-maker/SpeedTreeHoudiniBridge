"""Small Send/Update companion; auto mode follows saved SpeedTree projects."""
import json
import os
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog
from .speedtree import ROOT, current_session, send_project


def discover_modeler():
    candidates = []
    if os.environ.get('SPEEDTREE_MODELER'):
        candidates.append(Path(os.environ['SPEEDTREE_MODELER']))
    bases = [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'SpeedTree']
    if os.name == 'nt':
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        bases += [Path(chr(65 + i) + ':/') for i in range(26) if mask & (1 << i)]
    for base in bases:
        if base.is_dir():
            candidates += sorted(base.glob('SpeedTree Modeler*/win64/SpeedTree_Modeler.exe'), reverse=True)
    return next((str(p) for p in candidates if p.is_file()), '')


class LiveWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('SpeedTree → Houdini — Live Bridge')
        self.geometry('610x340')
        self.minsize(540, 320)
        self.config = ROOT / 'live_settings.json'
        try:
            saved = json.loads(self.config.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            saved = {}
        self.executable = tk.StringVar(value=saved.get('executable') or discover_modeler())
        self.project = tk.StringVar(value=saved.get('project', ''))
        self.renderer = tk.StringVar(value=saved.get('renderer', 'redshift'))
        self.scale = tk.StringVar(value=str(saved.get('scale', .01)))
        self.camera = tk.BooleanVar(value=saved.get('camera', True))
        self.auto = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='В Houdini: SpeedTree Bridge → Connect Live Bridge')
        self.busy = False
        self.pending = None
        self.messages = queue.Queue()
        self.signature = None
        self.changed_at = None
        self.auto.set(False)
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='SpeedTree → Houdini', font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Сохраняйте дерево в SpeedTree. Геометрия обновляется в том же объекте.').pack(anchor='w', pady=(2, 10))
        self.controls = []
        for label, variable, pattern in (('SpeedTree', self.executable, [('SpeedTree Modeler', '*.exe')]),
                                         ('Дерево', self.project, [('SpeedTree project', '*.spm')])):
            row = ttk.Frame(frame)
            row.pack(fill='x', pady=3)
            ttk.Label(row, text=label, width=10).pack(side='left')
            entry = ttk.Entry(row, textvariable=variable)
            entry.pack(side='left', fill='x', expand=True)
            button = ttk.Button(row, text='Выбрать…', command=lambda v=variable, p=pattern: self.browse(v, p))
            button.pack(side='left', padx=(6, 0))
            self.controls.extend((entry, button))
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=8)
        for renderer in ('redshift', 'arnold'):
            control = ttk.Radiobutton(row, text=renderer.title(), value=renderer, variable=self.renderer)
            control.pack(side='left', padx=(0, 8))
            self.controls.append(control)
        ttk.Label(row, text='Масштаб').pack(side='left', padx=(14, 4))
        scale = ttk.Entry(row, textvariable=self.scale, width=9)
        scale.pack(side='left')
        self.controls.append(scale)
        camera = ttk.Checkbutton(row, text='Камера при первом импорте', variable=self.camera)
        camera.pack(side='left', padx=8)
        self.controls.append(camera)
        ttk.Checkbutton(frame, text='Автообновление после сохранения .spm (Ctrl+S)', variable=self.auto, command=self.toggle_auto).pack(anchor='w')
        self.send_button = ttk.Button(frame, text='Send / Update → Houdini', command=self.send)
        self.send_button.pack(fill='x', pady=10)
        ttk.Label(frame, textvariable=self.status, wraplength=565).pack(anchor='w')
        ttk.Label(frame, text='Передаются сохранённые изменения. Окно можно держать рядом со SpeedTree.').pack(anchor='w', side='bottom')
        self.after(500, self.poll)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def close(self):
        if self.busy:
            self.auto.set(False)
            self.status.set('Дождитесь завершения отправки, затем закройте окно.')
            return
        self.destroy()

    def browse(self, variable, pattern):
        path = filedialog.askopenfilename(filetypes=pattern)
        if path:
            variable.set(path)
            self.signature = None

    def file_signature(self):
        stat = Path(self.project.get()).stat()
        return (self.project.get(), stat.st_mtime_ns, stat.st_size)

    def toggle_auto(self):
        self.signature = None
        self.changed_at = time.monotonic() if self.auto.get() else None
        self.status.set('Автообновление включено: сохраните дерево в SpeedTree.' if self.auto.get() else 'Автообновление выключено.')

    def set_busy(self, busy):
        self.busy = busy
        state = 'disabled' if busy else 'normal'
        self.send_button.configure(state=state)
        for control in self.controls:
            control.configure(state=state)

    def send(self):
        if self.busy:
            return
        try:
            current_session(ROOT / 'queue')
            scale = float(self.scale.get())
            if not 0 < scale < float('inf'):
                raise ValueError('Масштаб должен быть положительным числом')
            self.signature = self.file_signature()
            values = dict(executable=self.executable.get(), project=self.project.get(), renderer=self.renderer.get(),
                          scale=scale, camera=self.camera.get())
            self.config.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as error:
            self.status.set(str(error))
            self.auto.set(False)
            return
        self.changed_at = None
        self.set_busy(True)
        self.status.set('Экспорт из SpeedTree…')
        def worker():
            try:
                settings = {'scale': values['scale'], 'scene': {'camera': values['camera']}}
                job = send_project(values['executable'], values['project'], values['renderer'], settings)
                self.messages.put(('job', job))
            except Exception as error:
                self.messages.put(('error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == 'job':
                    self.pending = (value, time.monotonic())
                    self.status.set('Houdini принимает геометрию…')
                else:
                    self.status.set(value)
                    self.auto.set(False)
                    self.set_busy(False)
        except queue.Empty:
            pass
        if self.pending:
            job, started = self.pending
            result = ROOT / 'queue' / (job + '.result.json')
            if result.exists():
                response = json.loads(result.read_text(encoding='utf-8'))
                if response.get('ok'):
                    info = response['result']
                    self.status.set(('Обновлено: ' if info.get('updated') else 'Импортировано: ') + info['root'] + ' · ' + str(info['primitives']) + ' полигонов')
                else:
                    self.status.set(response.get('error', 'Ошибка Houdini'))
                    self.auto.set(False)
                self.pending = None
                self.set_busy(False)
            elif time.monotonic() - started > 180:
                pending = ROOT / 'queue' / (job + '.pending.json')
                try:
                    pending.unlink()
                    self.status.set('Houdini не принял запрос; отправка отменена. Подключите Live Bridge.')
                    self.pending = None
                    self.set_busy(False)
                    self.auto.set(False)
                except FileNotFoundError:
                    self.status.set('Houdini обрабатывает запрос. Дождитесь результата; не отправляйте повторно.')
        if self.auto.get() and not self.busy:
            try:
                signature = self.file_signature()
                if signature != self.signature:
                    self.signature = signature
                    self.changed_at = time.monotonic()
                if self.changed_at and time.monotonic() - self.changed_at >= 1:
                    self.send()
            except OSError:
                self.status.set('Сохранённый .spm недоступен')
                self.auto.set(False)
        self.after(500, self.poll)


def main():
    LiveWindow().mainloop()
