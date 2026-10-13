from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
import bridge.houdini as adapter
original = adapter.redshift_surface_type
adapter.redshift_surface_type = lambda builder: "redshift::Material"
try:
    material = {"name":"legacy_test", "two_sided":True, "vertex_opacity":True,
        "maps": {"Color":{"value":[.2,.3,.4]},"Metallic":{"value":[.1,.1,.1]},
                 "AO":{"value":[.8,.8,.8]}, "SubsurfaceColor":{"value":[.1,.2,.3]},
                 "SubsurfaceAmount":{"value":[.15,.15,.15]}}}
    node = adapter.create_material(hou.node('/mat'),material,'redshift',
        {"roughness":.5,"normal_strength":1,"normal_flip_y":False})
    surface = node.node('surface')
    assert surface.type().name() == 'redshift::Material'
    assert surface.parm('refl_metalness').eval() == .1
    assert node.node('color_times_ao') is not None
    assert node.node('vertex_opacity') is not None
    print('Legacy Redshift material adapter: PASS')
finally:
    adapter.redshift_surface_type = original
