"""Standalone Tk UI test; requires a display and Tkinter, but not a renderer."""
import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bridge.live_ui as ui

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    (base / 'queue').mkdir()
    project = base / 'tree.spm'
    project.touch()
    with patch.object(ui, 'ROOT', base), patch.object(ui, 'discover_modeler', return_value='modeler.exe'), patch.object(ui, 'current_session', return_value={'session_id': 'test'}), patch.object(ui, 'send_project', return_value='job'):
        window = ui.LiveWindow()
        window.withdraw()
        window.project.set(str(project))
        window.send()
        deadline = time.monotonic() + 5
        while window.pending is None and time.monotonic() < deadline:
            window.update()
            window.poll()
            time.sleep(.01)
        assert window.pending and window.busy
        assert str(window.send_button['state']) == 'disabled'
        (base / 'queue' / 'job.result.json').write_text(json.dumps({'ok': True, 'result': {'root': '/obj/tree', 'primitives': 123, 'updated': True}}))
        window.poll()
        assert not window.busy and '123' in window.status.get()
        assert str(window.send_button['state']) == 'normal'
        window.auto.set(True)
        window.toggle_auto()
        assert window.changed_at is not None
        window.destroy()
print('Companion Send/Update, background job, result display and auto-mode controls: PASS')
