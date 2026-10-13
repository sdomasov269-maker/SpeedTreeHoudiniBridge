import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.scene import setup_scene
root = hou.node('/obj').createNode('subnet', 'scene_test_tree')
root.parmTuple('t').set((4, 2, -3))
root.parm('scale').set(.01)
geo = root.createNode('geo')
box = geo.createNode('box')
box.parmTuple('size').set((100, 1000, 300))
box.setDisplayFlag(True)
existing = hou.node('/obj').createNode('cam', 'existing_camera')
before = existing.worldTransform()
for renderer in ('arnold','redshift'):
    for view in ('front','three_quarter','side'):
        result = setup_scene(root, renderer, {'scene':{'camera':True,'dome':True,'sun':True,'camera_view':view}})
        camera = hou.node(result['camera'])
        inverse = camera.worldTransform().inverted()
        tan_h = camera.parm('aperture').eval() / (2 * camera.parm('focal').eval())
        tan_v = tan_h / (camera.parm('resx').eval()/camera.parm('resy').eval())
        for point in box.geometry().points():
            p = point.position() * geo.worldTransform() * inverse
            assert p[2] < 0, p
            assert abs(p[0]) < -p[2] * tan_h, p
            assert abs(p[1]) < -p[2] * tan_v, p
        assert len(result['lights']) == 2
        assert existing.worldTransform() == before
        assert camera.inputs()[0] == root
        for scale in (.001, 1, .01):
            root.parm('scale').set(scale)
            inverse = camera.worldTransform().inverted()
            for point in box.geometry().points():
                p = point.position() * geo.worldTransform() * inverse
                assert p[2] < 0 and abs(p[0]) < -p[2]*tan_h and abs(p[1]) < -p[2]*tan_v, p
        for node in reversed(result['nodes']): node.destroy()
        print(renderer, view, 'camera framing and lights: PASS')
assert setup_scene(root,'arnold',{})['nodes'] == []
