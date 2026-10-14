import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from bridge.speedtree import asset_identity, current_session, export_project, send_project


class SpeedTreeTests(unittest.TestCase):
    def test_identity_is_stable_and_path_specific(self):
        self.assertEqual(asset_identity('tree.spm'), asset_identity(Path('tree.spm').resolve()))
        self.assertNotEqual(asset_identity('first/tree.spm'), asset_identity('second/tree.spm'))

    def test_disconnected_and_expired_session(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory)
            with self.assertRaises(RuntimeError):
                current_session(inbox)
            (inbox / 'session.json').write_text(json.dumps({'session_id': 'a', 'heartbeat': time.time() - 30}))
            with self.assertRaises(RuntimeError):
                current_session(inbox)

    def test_export_checks_outputs_and_uses_argument_list(self):
        with tempfile.TemporaryDirectory(prefix='tree with spaces ') as directory:
            base = Path(directory)
            exe, project = base / 'modeler.exe', base / 'test.spm'
            exe.touch(); project.touch()
            def exporter(command, **kwargs):
                self.assertIsInstance(command, list)
                self.assertEqual(command[3], str(project))
                self.assertNotIn('shell', kwargs)
                for key in ('QT_QPA_PLATFORM', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'):
                    self.assertNotIn(key, kwargs['env'])
                mesh = Path(command[2])
                mesh.write_text('mesh')
                mesh.with_suffix('.stmat').write_text('materials')
                return subprocess.CompletedProcess(command, 0, b'', b'')
            with patch('bridge.speedtree.subprocess.run', side_effect=exporter):
                first = export_project(exe, project, base / 'cache')
                second = export_project(exe, project, base / 'cache')
                self.assertNotEqual(first.parent, second.parent)
            with patch('bridge.speedtree.subprocess.run', return_value=subprocess.CompletedProcess([], 0, b'', b'')):
                with self.assertRaises(RuntimeError):
                    export_project(exe, project, base / 'cache')

    def test_scene_switch_during_export_never_queues(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory)
            with patch('bridge.speedtree.current_session', side_effect=[{'session_id':'one'}, {'session_id':'two'}]), patch('bridge.speedtree.export_project', return_value=inbox / 'tree.stmat'):
                with self.assertRaises(RuntimeError):
                    send_project('exe', 'tree.spm', 'redshift', {}, inbox=inbox)
            self.assertFalse(list(inbox.glob('*.pending.json')))

    def test_queue_includes_scene_and_stable_project_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory)
            source = inbox / 'tree.stmat'
            (inbox / 'tree.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n')
            source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"/></Materials>')
            with patch('bridge.speedtree.current_session', return_value={'session_id': 'scene'}), patch('bridge.speedtree.export_project', return_value=source):
                job = send_project('exe', 'tree.spm', 'redshift', {}, inbox=inbox)
            data = json.loads((inbox / (job + '.pending.json')).read_text())
            self.assertEqual(data['target_session'], 'scene')
            self.assertEqual(data['live']['asset_id'], asset_identity('tree.spm'))
            self.assertFalse(list(inbox.glob('*.tmp')))

    def test_receiver_rejects_old_scene_and_cleans_active_job(self):
        import bridge.receiver as receiver
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory)
            with patch.object(receiver, 'INBOX', inbox), patch.object(receiver, '_session_id', 'new'):
                receiver.atomic_json(inbox / 'old.pending.json', {'target_session': 'old', 'live': {}})
                receiver.process_one()
                result = json.loads((inbox / 'old.result.json').read_text())
                self.assertFalse(result['ok'])
                self.assertIn('another Houdini scene', result['error'])
                self.assertFalse(list(inbox.glob('*.active.json')))
