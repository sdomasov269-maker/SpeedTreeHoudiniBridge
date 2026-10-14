"""Z-up SpeedTree OBJ becomes Y-up before camera framing and USD translation."""
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from pxr import UsdGeom
from bridge.package import make_request
from bridge.houdini import import_package

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    (base / 'tree.obj').write_text('v -10 0 0\nv 10 0 0\nv 10 0 300\nv -10 0 300\nusemtl bark\nf 1 2 3 4\n')
    source = base / 'tree.stmat'
    source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"/></Materials>')
    for context in ('obj', 'solaris'):
        renderer = 'arnold' if context == 'obj' else 'karma'
        request = base / 'request.json'
        request.write_text(json.dumps(make_request(source, renderer, {'context': context, 'scale': .001, 'scene': {'camera': True}})))
        result = import_package(request)
        root = hou.node(result['root'])
        assert root.parmTuple('r').eval() == (-90, 0, 0)
        geo = root.node('mesh')
        points = [p.position() * geo.worldTransform() for p in geo.displayNode().geometry().points()]
        assert abs(max(p[1] for p in points) - .3) < 1e-7
        assert all(abs(p[2]) < 1e-7 for p in points)
        camera = hou.node(result['camera'])
        center = hou.Vector3(0, .15, 0) * camera.worldTransform().inverted()
        assert abs(center[0]) < 1e-7 and abs(center[1]) < 1e-7 and center[2] < 0
        if context == 'solaris':
            stage = hou.node(result['stage']).stage()
            cache = UsdGeom.XformCache()
            mesh = next(UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
            matrix = cache.GetLocalToWorldTransform(mesh.GetPrim())
            from pxr import Gf
            world = [matrix.Transform(Gf.Vec3d(*p)) for p in mesh.GetPointsAttr().Get()]
            assert abs(max(p[1] for p in world) - .3) < 1e-6
            assert all(abs(p[2]) < 1e-6 for p in world)
print('Automatic -90 X correction, vertical OBJ/USD geometry and centered camera: PASS')
