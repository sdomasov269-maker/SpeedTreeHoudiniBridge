import json
import tempfile
import unittest
from pathlib import Path
from install_houdini import install, VERSIONS

class InstallationTests(unittest.TestCase):
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
