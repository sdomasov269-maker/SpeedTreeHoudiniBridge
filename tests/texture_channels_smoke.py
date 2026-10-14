"""Verify component selection and combine wiring with actual renderer nodes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.houdini import create_material

renderers = ('arnold', 'redshift') if 'arnold_materialbuilder' in hou.node('/mat').childTypeCategory().nodeTypes() else ('redshift',)
for renderer in renderers:
    for gloss_channel in ('r', 'g', 'b', 'a'):
        material = {'name': 'packed', 'two_sided': True, 'vertex_opacity': True, 'maps': {
            'Color': {'file': '/synthetic/packed.png', 'channel': 'b'},
            'Opacity': {'file': '/synthetic/packed.png', 'channel': 'a'},
            'Gloss': {'file': '/synthetic/packed.png', 'channel': gloss_channel},
            'AO': {'file': '/synthetic/packed.png', 'channel': 'r'}}}
        builder = create_material(hou.node('/mat'), material, renderer, {'roughness': .5, 'normal_strength': 1, 'normal_flip_y': False})
        for name, expected in (('opacity_times_vertex', 'a'), ('color_times_ao', 'b')):
            combine = builder.node(name)
            connection = next(c for c in combine.inputConnections() if c.inputIndex() == combine.inputNames().index('input1'))
            output = connection.inputNode().outputNames()[connection.outputIndex()]
            assert output == (expected if renderer == 'arnold' else 'out' + expected.upper()), (name, output)
        if gloss_channel == 'a':
            assert builder.node('gloss_alpha_to_roughness') is not None
        builder.destroy()
    print(renderer, 'packed channels, alpha, vertex opacity, AO and gloss inversion: PASS')
