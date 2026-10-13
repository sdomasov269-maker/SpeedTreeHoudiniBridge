"""Local file queue, consumed on Houdini's UI thread; never executes incoming code."""
import json
import traceback
import os
from pathlib import Path
from .houdini import import_package

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "queue"
_timer = None
_lock = None


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def process_one():
    INBOX.mkdir(exist_ok=True)
    jobs = sorted(INBOX.glob("*.pending.json"))
    if not jobs:
        return
    job = jobs[0]
    active = job.with_name(job.name.replace(".pending.json", ".active.json"))
    try:
        job.rename(active)
    except FileNotFoundError:
        return
    result_path = active.with_name(active.name.replace(".active.json", ".result.json"))
    try:
        result = import_package(active)
        response = {"ok": True, "result": result}
    except Exception as error:
        response = {"ok": False, "error": str(error), "details": traceback.format_exc()}
    atomic_json(result_path, response)
    active.unlink()


def start():
    global _timer, _lock
    import hou
    if not hou.isUIAvailable():
        raise RuntimeError("Start the bridge in interactive Houdini")
    from .compat import QtCore
    if _lock is None:
        INBOX.mkdir(exist_ok=True)
        handle = (INBOX / "receiver.lock").open("a+b")
        try:
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.close()
            raise RuntimeError("Another Houdini session is already connected. Disconnect it first.") from error
        _lock = handle
    if _timer is None:
        _timer = QtCore.QTimer()
        _timer.setInterval(750)
        _timer.timeout.connect(process_one)
    _timer.start()
    return "Bridge connected. Requests will be imported into this Houdini scene."


def stop():
    global _lock
    if _timer is not None:
        _timer.stop()
    if _lock is not None:
        _lock.close()
        _lock = None
