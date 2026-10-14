"""Check renderer-specific USD shaders/settings and delegated outputs."""
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from pxr import UsdGeom, UsdShade, UsdRender
from bridge.package import make_request
from bridge.houdini import import_package
from bridge.solaris import renderer_delegate

renderer = sys.argv[1]
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    (base / 'tree.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nv 1 1 0\nusemtl bark\nf 1 2 3\nusemtl leaf\nf 2 4 3\n')
    source = base / 'tree.stmat'
    source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"><Map Name="Color" Value=".4"/></Material><Material Name="leaf" TwoSided="1" VertexOpacity="1"><Map Name="Opacity" Value=".8"/><Map Name="Color" Value=".2"/></Material></Materials>')
    path = base / 'request.json'
    picture = str(base / 'render.exr')
    options = {'context': 'solaris', 'scene': {'camera': True, 'dome': True, 'sun': True},
               'solaris': {'resolution_x': 64, 'resolution_y': 64, 'samples': 3 if renderer == 'arnold' else 16, 'output_image': picture}}
    path.write_text(json.dumps(make_request(source, renderer, options)))
    result = import_package(path)
    stage = hou.node(result['stage']).stage()
    materials = [UsdShade.Material(p) for p in stage.Traverse() if p.IsA(UsdShade.Material)]
    print('MATERIALS', [(str(m.GetPath()), [str(o.GetFullName()) for o in m.GetOutputs()]) for m in materials])
    ids = [str(UsdShade.Shader(p).GetIdAttr().Get()) for p in stage.Traverse() if p.IsA(UsdShade.Shader)]
    print('SHADERS', ids)
    assert len(materials) == 2
    context = 'arnold' if renderer == 'arnold' else 'Redshift'
    assert all(m.ComputeSurfaceSource(context)[0] for m in materials)
    assert any(renderer in identifier.lower() for identifier in ids), ids
    subsets = [p for p in stage.Traverse() if p.IsA(UsdGeom.Subset)]
    assert len(subsets) == 2
    assert all(UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0] for p in subsets)
    settings = UsdRender.Settings(stage.GetPrimAtPath(hou.node(result['render_output']).parm('rendersettings').eval()))
    assert tuple(settings.GetResolutionAttr().Get()) == (64, 64)
    assert stage.GetPrimAtPath(settings.GetCameraRel().GetTargets()[0]).IsA(UsdGeom.Camera)
    assert settings.GetProductsRel().GetTargets()
    assert hou.node(result['render_output']).parm('renderer').eval() == renderer_delegate(renderer)
    if '--render' in sys.argv:
        hou.node(result['render_output']).render()
        assert Path(picture).is_file() and Path(picture).stat().st_size > 100
        hou.hipFile.clear(suppress_save_prompt=True)
        hou.hscript('texcache -c')
    else:
        from bridge.solaris import update_settings
        root = hou.node(result['root'])
        options = json.loads(root.userData('speedtree_solaris_options'))
        subnet = hou.node(result['stage'])
        render = subnet.node(renderer + '_settings')
        resolution = (subnet.node('render_settings') if renderer == 'redshift' else render).parm('resolution1')
        resolution.set(96)
        changes = []
        update_settings(root, options, changes)
        assert resolution.eval() == 96 and not changes
        update_settings(root, dict(options, resolution_x=128, samples=2), changes)
        assert resolution.eval() == 128
        if renderer == 'redshift':
            assert render.parm('redshiftglobalUnifiedMinSamples').eval() <= 2
print(hou.applicationVersionString(), renderer, 'Solaris shaders, bindings, render settings and output: PASS')
