"""Standalone window; no Houdini license is needed for export validation."""
import json
import os
import time
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .package import read_export, make_request

ROOT = Path(__file__).resolve().parents[1]


class Window(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SpeedTree → Houdini | Arnold / Redshift")
        self.geometry("880x660")
        self.minsize(720, 540)
        self.source = tk.StringVar()
        self.profiles = {}
        self.pending = None
        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="SpeedTree → Houdini", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Экспортируйте OBJ или FBX вместе с .stmat и текстурами из SpeedTree 10.").pack(anchor="w", pady=8)
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=10)
        ttk.Entry(row, textvariable=self.source).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Выбрать .stmat", command=self.browse).pack(side="left", padx=8)
        self.tabs = ttk.Notebook(frame)
        self.tabs.pack(fill="x", pady=8)
        saved = {}
        self.config = ROOT / "settings.json"
        if self.config.exists():
            try:
                saved = json.loads(self.config.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
        for renderer in ("arnold", "redshift"):
            tab = ttk.Frame(self.tabs, padding=12)
            self.tabs.add(tab, text=renderer.title())
            variables = {}
            for index, (key, label, default) in enumerate([
                ("scale", "Масштаб геометрии", 1),
                ("roughness", "Roughness без карты", .5),
                ("normal_strength", "Сила normal map", 1),
            ]):
                ttk.Label(tab, text=label).grid(row=index, column=0, sticky="w", pady=4)
                variable = tk.StringVar(value=str(saved.get(renderer, {}).get(key, default)))
                ttk.Entry(tab, textvariable=variable, width=16).grid(row=index, column=1, padx=20)
                variables[key] = variable
            variables["normal_flip_y"] = tk.BooleanVar(value=saved.get(renderer, {}).get("normal_flip_y", False))
            ttk.Checkbutton(tab, text="Инвертировать Y normal map", variable=variables["normal_flip_y"]).grid(row=3, column=0, columnspan=2, sticky="w")
            self.profiles[renderer] = variables
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=10)
        ttk.Button(buttons, text="Проверить экспорт", command=lambda: self.action(False)).pack(side="left")
        ttk.Button(buttons, text="Создать пакет для Houdini", command=lambda: self.action(True)).pack(side="left", padx=10)
        self.send_button = ttk.Button(buttons, text="Отправить в Houdini", command=self.send)
        self.send_button.pack(side="left")
        ttk.Button(buttons, text="Открыть папку проекта", command=lambda: os.startfile(ROOT)).pack(side="right")
        self.log = tk.Text(frame, wrap="word", height=12, font=("Consolas", 10))
        self.log.pack(fill="both", expand=True)
        self.write("Выберите .stmat. В Houdini выполните Connect Houdini.py, затем нажмите «Отправить в Houdini».\n"
                   "Подключайте только одну сцену Houdini одновременно.\n"
                   "Версия 0.1: проверены узлы и тестовый OBJ; проверка реального дерева и рендера ещё впереди.")

    def send(self):
        try:
            renderer = ("arnold", "redshift")[self.tabs.index("current")]
            profiles = {key: {k: v.get() for k, v in values.items()} for key, values in self.profiles.items()}
            request = make_request(self.source.get(), renderer, profiles[renderer])
            queue = ROOT / "queue"
            queue.mkdir(exist_ok=True)
            token = uuid.uuid4().hex
            temporary = queue / (token + ".tmp")
            job = queue / (token + ".pending.json")
            temporary.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(job)
            self.config.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
            self.pending = (queue / (token + ".result.json"), job, time.monotonic())
            self.send_button.configure(state="disabled")
            self.write("Ожидание Houdini. Если сцена не подключена, выполните Connect Houdini.py в Houdini.")
            self.after(500, self.poll)
        except Exception as error:
            messagebox.showerror("SpeedTree Bridge", str(error))

    def poll(self):
        result, job, started = self.pending
        if result.exists():
            try:
                response = json.loads(result.read_text(encoding="utf-8"))
                if response["ok"]:
                    imported = response["result"]
                    self.write(f"Импорт завершён: {imported['root']}\nМатериалы в /mat: {len(imported['materials'])}\nПолигонов: {imported['primitives']}\nArnold output: {imported.get('render_output') or '—'}\n{imported['messages']}\n" + "\n".join(imported.get('notes', [])))
                else:
                    self.write("Ошибка импорта:\n" + response["error"])
            except (OSError, ValueError, KeyError) as error:
                self.write(str(error))
            self.pending = None
            self.send_button.configure(state="normal")
        elif time.monotonic() - started > 30 and job.exists():
            try:
                job.unlink()
                self.write("Houdini не принял запрос за 30 секунд. Запрос отменён. Выполните Connect Houdini.py и повторите отправку.")
                self.pending = None
                self.send_button.configure(state="normal")
            except FileNotFoundError:
                self.after(500, self.poll)
        else:
            self.after(500, self.poll)

    def write(self, text):
        self.log.delete("1.0", "end")
        self.log.insert("end", text)

    def browse(self):
        path = filedialog.askopenfilename(filetypes=[("SpeedTree materials", "*.stmat")])
        if path:
            self.source.set(path)
            self.action(False)

    def action(self, export):
        try:
            renderer = ("arnold", "redshift")[self.tabs.index("current")]
            profiles = {key: {k: v.get() for k, v in values.items()} for key, values in self.profiles.items()}
            package = make_request(self.source.get(), renderer, profiles[renderer]) if export else read_export(self.source.get())
            text = [f"Mesh: {package['mesh']}", f"Материалов: {len(package['materials'])}"]
            for material in package["materials"]:
                text.append(f"  {material['name']}: {', '.join(material['maps'])}")
            text.extend(package["warnings"])
            if export:
                target = filedialog.asksaveasfilename(defaultextension=".json", initialfile="tree.bridge.json", filetypes=[("Bridge package", "*.json")])
                if not target:
                    return
                Path(target).write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
                self.config.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
                text.append(f"\nПакет: {target}\nВ Houdini выполните Import Bridge.py и выберите этот пакет.")
            self.write("\n".join(text))
        except Exception as error:
            self.write(str(error))
            messagebox.showerror("SpeedTree Bridge", str(error))


def main():
    Window().mainloop()
