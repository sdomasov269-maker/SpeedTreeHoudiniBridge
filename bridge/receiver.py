"""Local file queue, consumed on Houdini's UI thread; never executes incoming code."""
import json
import traceback
import os
import time
import uuid
import logging
from pathlib import Path
from .houdini import import_package

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "queue"
_timer = None
_lock = None
_session_id = None
_callback_registered = False


def scene_changed(event):
    global _session_id
    import hou
    if event in (hou.hipFileEventType.AfterLoad, hou.hipFileEventType.AfterClear):
        _session_id = uuid.uuid4().hex
        publish_session()


def publish_session():
    import hou
    atomic_json(INBOX / 'session.json', {'session_id': _session_id, 'heartbeat': time.time(),
                'pid': os.getpid(), 'hip': hou.hipFile.name(), 'houdini': hou.applicationVersionString()})


def tick():
    try:
        publish_session()
        process_one()
    except Exception:
        logging.getLogger(__name__).exception('Live Bridge receiver failed')


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
        raw = json.loads(active.read_text(encoding='utf-8'))
        if raw.get('target_session') and raw['target_session'] != _session_id:
            raise RuntimeError('Request belongs to another Houdini scene or connection; resend it')
        if 'live' in raw:
            if not raw.get('target_session'):
                raise ValueError('Live requests must target a connected Houdini scene')
            from .live import apply_live_request
            result = apply_live_request(active)
        else:
            result = import_package(active)
        response = {"ok": True, "result": result}
    except Exception as error:
        response = {"ok": False, "error": str(error), "details": traceback.format_exc()}
    atomic_json(result_path, response)
    active.unlink()


def start():
    global _timer, _lock, _session_id, _callback_registered
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
        _timer.timeout.connect(tick)
    if not _timer.isActive():
        _session_id = uuid.uuid4().hex
    if not _callback_registered:
        hou.hipFile.addEventCallback(scene_changed)
        _callback_registered = True
    publish_session()
    _timer.start()
    return "Bridge connected. Requests will be imported into this Houdini scene."


def stop():
    global _lock, _callback_registered, _session_id
    if _timer is not None:
        _timer.stop()
    if _lock is not None:
        try:
            (INBOX / 'session.json').unlink()
        except FileNotFoundError:
            pass
        _lock.close()
        _lock = None
    if _callback_registered:
        import hou
        hou.hipFile.removeEventCallback(scene_changed)
        _callback_registered = False
    _session_id = None
