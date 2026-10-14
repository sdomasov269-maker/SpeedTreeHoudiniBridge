"""Run with hython: live_export_smoke.py MODELER_EXE SAMPLE_SPM."""
import json
from pathlib import Path
import sys
import tempfile
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.package import make_request
from bridge.speedtree import asset_identity, export_project
import bridge.receiver as receiver

if len(sys.argv) != 3:
    raise SystemExit('Provide SpeedTree Modeler executable and an authorized sample .spm')
executable, project = map(Path, sys.argv[1:])
with tempfile.TemporaryDirectory(prefix='speedtree_live_verify_') as directory:
    base = Path(directory)
    receiver.INBOX = base / 'queue'
    receiver.INBOX.mkdir()
    receiver._session_id = uuid.uuid4().hex
    old = None
    for index in range(2):
        source = export_project(executable, project, base / 'cache')
        data = make_request(source, 'redshift', {'scale': .01, 'scene': {'camera': True}})
        data['target_session'] = receiver._session_id
        data['live'] = {'asset_id': asset_identity(project), 'project': str(project.resolve()), 'revision': source.parent.name}
        receiver.atomic_json(receiver.INBOX / ('test{}.pending.json'.format(index)), data)
        receiver.process_one()
        response = json.loads((receiver.INBOX / ('test{}.result.json'.format(index))).read_text())
        assert response['ok'], response
        result = response['result']
        assert result['primitives'] > 0
        if old:
            assert result['updated'] and result['root'] == old['root']
            assert result['materials'] == old['materials']
            assert {p: set(hou.node(p).children()) for p in before} == before
            for name, path in old['materials'].items():
                color = hou.node(path).node('Color')
                assert color.parm('tex0').eval() == str(source.parent / (Path(previous_paths[name]).name)).replace('\\', '/')
        else:
            assert not result['updated']
            old = result
            previous_paths = {name: hou.node(path).node('Color').parm('tex0').eval() for name, path in result['materials'].items()}
            before = {p: set(hou.node(p).children()) for p in ('/obj', '/mat', '/out')}
        print('PASS:', 'update' if index else 'initial import', result['root'], result['primitives'], 'primitives')
print('Real SpeedTree saved-project export -> local queue -> stable Houdini update: PASS')
