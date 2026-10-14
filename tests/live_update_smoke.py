"""Stable paths, preserved user nodes/material edits, new materials and rollback."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.package import make_request
from bridge.live import apply_live_request
from bridge.speedtree import asset_identity
renderer = sys.argv[1] if len(sys.argv) > 1 else 'redshift'
context = sys.argv[2] if len(sys.argv) > 2 else ('solaris' if renderer == 'karma' else 'obj')

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    identity = asset_identity(base / 'working.spm')
    def request(revision, height, names=('bark',)):
        folder = base / str(revision)
        folder.mkdir()
        (folder / 'tree.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 {} 0\nusemtl {}\nf 1 2 3\n'.format(height, names[0]))
        source = folder / 'tree.stmat'
        source.write_text('<Materials Mesh="tree.obj">' + ''.join('<Material Name="{}"><Map Name="Color" Value=".4"/></Material>'.format(n) for n in names) + '</Materials>')
        data = make_request(source, renderer, {'context': context, 'scale': .01, 'scene': {'camera': True, 'dome': True}})
        data['live'] = {'asset_id': identity, 'revision': revision, 'project': str(base / 'working.spm')}
        path = folder / 'request.json'
        path.write_text(json.dumps(data))
        return path
    first = apply_live_request(request(1, 1))
    root = hou.node(first['root'])
    assert root.parm('rx').eval() == -90
    geo = root.node('mesh')
    file_node, assign = root.node('mesh/speedtree_mesh'), root.node('mesh/bridge_assign')
    downstream = geo.createNode('null', 'USER_OUT')
    downstream.setInput(0, assign)
    downstream.setDisplayFlag(True)
    downstream.setRenderFlag(True)
    root.parmTuple('t').set((7, 2, -4))
    root.parm('scale').set(.03)
    surface = hou.node(first['materials']['bark']).node('surface')
    roughness = 'specular_roughness' if renderer in ('arnold', 'karma') else 'refl_roughness'
    surface.parm(roughness).set(.123)
    extra = hou.node(first['materials']['bark']).createNode({'arnold': 'arnold::image', 'redshift': 'redshift::TextureSampler', 'karma': 'mtlximage'}[renderer], 'user_texture')
    contexts = ('/obj', '/mat', '/out', '/stage')
    before = {p: set(hou.node(p).children()) for p in contexts}
    camera_matrix = hou.node(first['camera']).worldTransform()
    second = apply_live_request(request(2, 5))
    assert second['updated'] and second['root'] == first['root']
    assert second['materials'] == first['materials']
    assert root.parmTuple('t').eval() == (7, 2, -4) and root.parm('scale').eval() == .03
    assert surface.parm(roughness).eval() == .123 and hou.node(extra.path()) == extra
    assert downstream.inputs()[0] == assign and geo.displayNode() == downstream
    assert downstream.geometry().boundingBox().maxvec()[1] == 5
    assert all(set(hou.node(p).children()) == nodes for p, nodes in before.items())
    assert hou.node(first['camera']).worldTransform() == camera_matrix
    if context == 'solaris':
        from pxr import UsdGeom
        usd = hou.node(first['stage']).stage()
        meshes = [UsdGeom.Mesh(p) for p in usd.Traverse() if p.IsA(UsdGeom.Mesh)]
        assert max(p[1] for mesh in meshes for p in mesh.GetPointsAttr().Get()) == 5
    third = apply_live_request(request(3, 8, ('leaf', 'bark')))
    assert third['materials']['bark'] == first['materials']['bark']
    assert 'leaf' in third['materials']
    stable_file = file_node.parm('file').eval()
    stable_code = assign.parm('python').eval()
    before = {p: set(hou.node(p).children()) for p in contexts}
    bad = request(4, 10, ('missing_a', 'missing_b'))
    mesh = bad.parent / 'tree.obj'
    mesh.write_text(mesh.read_text().replace('usemtl missing_a', 'usemtl no_match'))
    try:
        apply_live_request(bad)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Expected invalid assignment')
    assert file_node.parm('file').eval() == stable_file
    assert assign.parm('python').eval() == stable_code
    assert downstream.geometry().boundingBox().maxvec()[1] == 8
    assert all(set(hou.node(p).children()) == nodes for p, nodes in before.items())
    # Force failure after validation to exercise rollback of already changed live parms.
    import bridge.live as live
    original = live.assignment_code
    live.assignment_code = lambda mapping: 'raise hou.NodeError("forced commit failure")'
    try:
        try:
            apply_live_request(request(5, 12, ('leaf', 'bark', 'added')))
        except hou.OperationFailed:
            pass
        else:
            raise AssertionError('Expected failure in live assignment')
    finally:
        live.assignment_code = original
    assert file_node.parm('file').eval() == stable_file and assign.parm('python').eval() == stable_code
    assert downstream.geometry().boundingBox().maxvec()[1] == 8
    assert all(set(hou.node(p).children()) == nodes for p, nodes in before.items())
print(hou.applicationVersionString(), renderer, 'live update, stable paths, preserved user edits, new materials and rollback: PASS')
