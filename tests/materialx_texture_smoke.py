"""Cook packed/alpha/normal/SSS MaterialX signals through the USD translator."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from pxr import UsdShade
from bridge.package import make_request
from bridge.houdini import import_package

def png(path):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(b'\x00\x80\x80\xff\x80')) + chunk(b'IEND', b''))

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    png(base / 'map.png')
    (base / 'tree.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n')
    channels = {'Color': 'rgb', 'Opacity': 'a', 'Gloss': 'g', 'Metallic': 'b', 'AO': 'r', 'Normal': 'rgb', 'Specular': 'rgb', 'SubsurfaceColor': 'rgb', 'SubsurfaceAmount': 'r'}
    source = base / 'tree.stmat'
    source.write_text('<Materials Mesh="tree.obj"><Material Name="leaf" TwoSided="1" VertexOpacity="1">' +
                      ''.join('<Map Name="{}" File="map.png" Channel="{}"/>'.format(k, v) for k, v in channels.items()) + '</Material></Materials>')
    path = base / 'request.json'
    engine = 'xpu' if '--xpu' in sys.argv else 'cpu'
    picture = str(base / 'render.exr')
    path.write_text(json.dumps(make_request(source, 'karma', {'normal_flip_y': True, 'scene': {'camera': True, 'dome': True},
                     'solaris': {'engine': engine, 'resolution_x': 64, 'resolution_y': 64, 'samples': 4, 'output_image': picture}})))
    result = import_package(path)
    builder = hou.node(result['materials']['leaf'])
    assert builder.node('Opacity_channel').parm('index').eval() == 3
    assert builder.node('Normal').parm('signature').eval() == 'vector3'
    assert builder.node('normal_flip_y') and builder.node('normal_decode')
    usd = hou.node(result['stage']).stage()
    ids = [str(UsdShade.Shader(p).GetIdAttr().Get()) for p in usd.Traverse() if p.IsA(UsdShade.Shader)]
    assert any('standard_surface' in i for i in ids)
    assert any('extract' in i for i in ids)
    assert any('normalmap' in i for i in ids)
    expected = 'BRAY_HdKarmaXPU' if engine == 'xpu' else 'BRAY_HdKarma'
    assert hou.node(result['render_output']).parm('renderer').eval() == expected
    if '--render' in sys.argv:
        hou.node(result['render_output']).render()
        assert Path(picture).is_file() and Path(picture).stat().st_size > 100
        hou.hipFile.clear(suppress_save_prompt=True)
        hou.hscript('texcache -c')
print(hou.applicationVersionString(), engine, 'MaterialX packed channels, alpha, normal flip, SSS and USD shader graph: PASS')
