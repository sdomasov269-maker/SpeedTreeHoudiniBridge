import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from install_houdini import install, VERSIONS, preferences_folder

class InstallationTests(unittest.TestCase):
    def test_platform_preferences(self):
        with patch('install_houdini.sys.platform', 'darwin'):
            self.assertEqual(preferences_folder('21.0'), Path.home() / 'Library' / 'Preferences' / 'houdini' / '21.0')
            self.assertEqual(preferences_folder('21.0', '/custom'), Path('/custom') / 'houdini21.0')
        with patch('install_houdini.sys.platform', 'linux'), patch('install_houdini.documents_folder', return_value=Path('/home/test')):
            self.assertEqual(preferences_folder('22.0'), Path('/home/test/houdini22.0'))

    def test_package_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            for version in VERSIONS:
                preferences = Path(directory) / ('houdini' + version)
                target = install(preferences)
                data = json.loads(target.read_text())
                self.assertTrue(data['enable'])
                self.assertEqual(data['path'], '$SPEEDTREE_BRIDGE_ROOT/houdini')
                self.assertTrue((Path(data['env'][0]['SPEEDTREE_BRIDGE_ROOT']) / 'bridge').is_dir())
                unrelated = target.parent / 'other_plugin.json'
                unrelated.write_text('{"enable":true}')
                target.write_text('{"enable":false}')
                install(preferences)
                self.assertEqual(target.with_suffix('.json.bak').read_text(), '{"enable":false}')
                self.assertEqual(unrelated.read_text(), '{"enable":true}')
