"""Verify cooked USD geometry, MaterialX bindings and Karma render settings."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from pxr import UsdGeom, UsdShade, UsdRender
from bridge.package import make_request
from bridge.houdini import import_package

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    (base / 'tree.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nv 1 1 0\nusemtl bark\nf 1 2 3\nusemtl leaf\nf 2 4 3\n')
    source = base / 'tree.stmat'
    source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"><Map Name="Color" Value=".4"/></Material><Material Name="leaf" TwoSided="1" VertexOpacity="1"><Map Name="Color" Value=".2"/><Map Name="Opacity" Value=".8"/><Map Name="AO" Value=".7"/></Material></Materials>')
    path = base / 'request.json'
    path.write_text(json.dumps(make_request(source, 'karma', {'scene': {'camera': True, 'dome': True, 'sun': True}, 'solaris': {'resolution_x': 320, 'resolution_y': 180, 'samples': 8, 'output_image': str(base / 'test.exr')}})))
    result = import_package(path)
    stage = hou.node(result['stage']).stage()
    print(result)
    print([(str(p.GetPath()), p.GetTypeName()) for p in stage.Traverse()])
    assert result['primitives'] == 2
    meshes = [p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)]
    assert meshes
    materials = [p for p in stage.Traverse() if p.IsA(UsdShade.Material)]
    assert len(materials) == 2
    subsets = [p for p in stage.Traverse() if p.IsA(UsdGeom.Subset)]
    assert len(subsets) == 2
    assert all(UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0] for p in subsets)
    shaders = [p for p in stage.Traverse() if p.IsA(UsdShade.Shader)]
    assert any('standard_surface' in str(UsdShade.Shader(p).GetIdAttr().Get()) for p in shaders)
    settings = [UsdRender.Settings(p) for p in stage.Traverse() if p.IsA(UsdRender.Settings)]
    assert len(settings) == 1
    assert tuple(settings[0].GetResolutionAttr().Get()) == (320, 180)
    cameras = settings[0].GetCameraRel().GetTargets()
    assert len(cameras) == 1 and stage.GetPrimAtPath(cameras[0]).IsA(UsdGeom.Camera)
    assert hou.node(result['render_output']).parm('loppath').eval() == result['stage']
    assert hou.node(result['render_output']).parm('renderer').eval() == 'BRAY_HdKarma'
    assert len([p for p in stage.Traverse() if p.GetTypeName() in ('DomeLight', 'DistantLight')]) == 2
    # Different UI values update the linked Karma settings; unchanged UI values retain LOP edits.
    from bridge.solaris import update_settings
    root = hou.node(result['root'])
    render = hou.node(result['stage']).node('karma_settings')
    render.parm('pathtracedsamples').set(17)
    original_options = json.loads(root.userData('speedtree_solaris_options'))
    update_settings(root, original_options, [])
    assert render.parm('pathtracedsamples').eval() == 17
    changes = []
    updated_options = dict(original_options, samples=16, engine='xpu')
    update_settings(root, updated_options, changes)
    assert render.parm('pathtracedsamples').eval() == 16
    assert hou.node(result['render_output']).parm('renderer').eval() == 'BRAY_HdKarmaXPU'
    update_settings(root, original_options, [])
    # Failed imports must remove stage, output, object and shaders, preserving existing nodes.
    before = {p: set(hou.node(p).children()) for p in ('/obj', '/mat', '/out', '/stage')}
    bad = base / 'bad.stmat'
    bad.write_text('<Materials Mesh="tree.obj"><Material Name="missing_a"/><Material Name="missing_b"/></Materials>')
    bad_request = base / 'bad.json'
    bad_request.write_text(json.dumps(make_request(bad, 'karma', {})))
    try:
        import_package(bad_request)
    except RuntimeError:
        assert all(set(hou.node(p).children()) == nodes for p, nodes in before.items())
    else:
        raise AssertionError('Expected unmatched material failure')
    if '--render' in sys.argv:
        node = hou.node(result['stage']).node('karma_settings')
        node.parm('resolutionx').set(64)
        node.parm('resolutiony').set(64)
        node.parm('pathtracedsamples').set(4)
        node.parm('samplesperpixel').set(4)
        hou.node(result['render_output']).render()
        image = base / 'test.exr'
        assert image.is_file() and image.stat().st_size > 100
        print('Karma CPU rendered EXR:', image.stat().st_size, 'bytes')
print(hou.applicationVersionString(), 'Solaris geometry, MaterialX bindings, camera, lights and Karma output: PASS')
