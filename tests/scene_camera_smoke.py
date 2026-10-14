"""Project transformed geometry through OBJ and USD cameras, across scale/aspect/view."""
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from pxr import UsdGeom
from bridge.package import make_request
from bridge.houdini import import_package
from bridge.scene import frame_camera, world_corners

renderer = sys.argv[1] if len(sys.argv) > 1 else 'karma'
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    mesh = base / 'tree.obj'
    mesh.write_text('v -30 0 -20\nv 30 0 -20\nv 30 300 -20\nv -30 300 -20\nv -30 0 20\nv 30 0 20\nv 30 300 20\nv -30 300 20\nusemtl bark\nf 1 2 3 4\nf 5 8 7 6\nf 1 5 6 2\nf 4 3 7 8\n')
    source = base / 'tree.stmat'
    source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"/></Materials>')
    request = base / 'request.json'
    request.write_text(json.dumps(make_request(source, renderer, {'scale': .001, 'context': 'solaris',
        'scene': {'camera': True, 'dome': True, 'sun': True},
        'solaris': {'resolution_x': 640, 'resolution_y': 1280}})))
    result = import_package(request)
    root, camera = hou.node(result['root']), hou.node(result['camera'])
    assert camera.parm('resx').eval() == 640 and camera.parm('resy').eval() == 1280
    for scale in (.001, .01, 1):
        for rotation in ((0, 0, 0), (90, 0, 0), (15, 35, -40)):
            root.parm('scale').set(scale)
            root.parmTuple('r').set(rotation)
            root.parmTuple('t').set((3, -2, 4))
            original = root.worldTransform()
            for resolution in ((1280, 720), (640, 1280)):
                for view in ('front', 'side', 'three_quarter'):
                    frame_camera(camera, root, view, resolution)
                    assert root.worldTransform() == original
                    assert not camera.inputs()
                    assert all(abs(v - 1) < 1e-6 for v in camera.worldTransform().extractScales())
                    tangent_x = camera.parm('aperture').eval() / (2 * camera.parm('focal').eval())
                    tangent_y = tangent_x / (resolution[0] / resolution[1])
                    points = [p * camera.worldTransform().inverted() for p in world_corners(root)]
                    for p in points:
                        depth = -p[2]
                        assert camera.parm('near').eval() < depth < camera.parm('far').eval()
                        assert abs(p[0] / depth / tangent_x) <= .9
                        assert abs(p[1] / depth / tangent_y) <= .9
                    stage = hou.node(result['stage']).stage()
                    usd_camera = UsdGeom.Camera(stage.GetPrimAtPath('/' + camera.name()))
                    assert usd_camera
                    transform = UsdGeom.XformCache().GetLocalToWorldTransform(usd_camera.GetPrim())
                    matrix = hou.Matrix4(tuple(float(transform[i][j]) for i in range(4) for j in range(4)))
                    assert all(abs(a-b) <= 1e-6 * max(1, abs(b)) for a,b in zip(matrix.asTuple(), camera.worldTransform().asTuple())), (scale, rotation, resolution, view, matrix, camera.worldTransform())
                    assert tuple(usd_camera.GetClippingRangeAttr().Get())[0] > 0
    # Repair an old parented camera without touching the mesh or rebuilding the stage/output.
    camera.setInput(0, root)
    camera.setPreTransform(hou.hmath.buildScale((1000, 1000, 1000)))
    subnet = hou.node(result['stage'])
    render = subnet.node(renderer + '_settings')
    render.parm('RS_renderCamera' if renderer == 'redshift' else 'camera').set('/' + root.name() + '/' + camera.name())
    hou.clearAllSelected()
    root.setSelected(True)
    from bridge.scene import reframe_selected
    reframe_selected()
    assert not camera.inputs()
    assert camera.preTransform() == hou.hmath.identityTransform()
    assert all(abs(v - 1) < 1e-6 for v in camera.parmTuple('s').eval())
    assert render.parm('RS_renderCamera' if renderer == 'redshift' else 'camera').eval() == '/' + camera.name()
print(renderer, '54 transformed camera fits, clipping, unit scale, USD transform and existing-camera repair: PASS')
