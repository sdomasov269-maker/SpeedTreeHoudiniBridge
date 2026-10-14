"""Exercise receiver timer, heartbeat and scene identity in an isolated Qt loop."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.compat import QtWidgets
import bridge.receiver as receiver
from bridge.package import make_request
from bridge.speedtree import asset_identity, current_session

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    receiver.INBOX = base / 'queue'
    (base / 'tree.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n')
    source = base / 'tree.stmat'
    source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"/></Materials>')
    with patch.object(hou, 'isUIAvailable', return_value=True):
        receiver.start()
        first = current_session(receiver.INBOX)['session_id']
        receiver.start()
        assert current_session(receiver.INBOX)['session_id'] == first
        data = make_request(source, 'redshift', {})
        data['target_session'] = first
        data['live'] = {'asset_id': asset_identity(base / 'tree.spm'), 'revision': 'one'}
        receiver.atomic_json(receiver.INBOX / 'one.pending.json', data)
        deadline = time.monotonic() + 15
        while not (receiver.INBOX / 'one.result.json').exists() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.02)
        response = json.loads((receiver.INBOX / 'one.result.json').read_text())
        assert response['ok'], response
        receiver.scene_changed(hou.hipFileEventType.AfterSave)
        assert receiver._session_id == first
        receiver.scene_changed(hou.hipFileEventType.AfterClear)
        assert receiver._session_id != first
        receiver.atomic_json(receiver.INBOX / 'old.pending.json', data)
        receiver.tick()
        assert not json.loads((receiver.INBOX / 'old.result.json').read_text())['ok']
        receiver.stop()
        assert not (receiver.INBOX / 'session.json').exists() and receiver._lock is None
        receiver.start()
        assert receiver._session_id != first
        receiver.stop()
print('Qt receiver timer, session heartbeat, HIP identity, stale job and disconnect: PASS')
