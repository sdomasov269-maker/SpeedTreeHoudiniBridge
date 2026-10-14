"""MaterialX shaders for Karma CPU/XPU, preserving exported channel semantics."""
import json
from .houdini import safe_name, set_value, connect_existing


def image(builder, name, data, color=False, scalar=False, vector=False):
    node = builder.createNode('mtlximage', safe_name(name))
    component = data.get('channel', 'rgb')
    signature = 'color4' if component == 'a' else ('vector3' if vector else 'color3')
    if scalar and component == 'rgb':
        signature = 'float'
    node.parm('signature').set(signature)
    node.parm('file').set(data['file'])
    node.parm('filecolorspace').set('srgb_texture' if color else 'raw')
    if component != 'rgb':
        extract = builder.createNode('mtlxextract', safe_name(name) + '_channel')
        extract.parm('signature').set('color4' if component == 'a' else 'default')
        extract.parm('index').set('rgba'.index(component))
        extract.setNamedInput('in', node, 'out')
        return extract
    return node


def create_material(parent, material, settings, name):
    builder = parent.createNode('subnet', name)
    try:
        builder.setShaderLanguageName('MaterialX')
        builder.setMaterialFlag(True)
        for child in builder.children():
            child.destroy()
        surface = builder.createNode('mtlxstandard_surface', 'surface')
        terminal = builder.createNode('subnetconnector', 'surface_output')
        terminal.setParms({'parmname': 'surface', 'parmlabel': 'Surface', 'parmtype': 24,
                           'connectorkind': 1, 'useasparmdefiner': 0})
        terminal.setInput(0, surface)
        set_value(surface, 'specular_roughness', settings['roughness'])
        set_value(surface, 'thin_walled', int(material['two_sided']))
        destinations = {'Color': 'base_color', 'Opacity': 'opacity', 'Roughness': 'specular_roughness',
                        'Gloss': 'specular_roughness', 'Metallic': 'metalness', 'Specular': 'specular_color',
                        'SubsurfaceColor': 'subsurface_color', 'SubsurfaceAmount': 'subsurface'}
        auxiliary = {'Height', 'Custom', 'Custom2', 'AO'}
        unknown = set(material['maps']) - set(destinations) - auxiliary - {'Normal'}
        if unknown:
            raise ValueError('Unsupported maps: ' + ', '.join(sorted(unknown)))
        if 'Gloss' in material['maps'] and 'Roughness' in material['maps']:
            raise ValueError('Export contains both Gloss and Roughness; choose one')
        for channel, data in material['maps'].items():
            if channel in auxiliary:
                builder.setUserData('speedtree_map_' + channel, json.dumps(data))
                continue
            scalar = channel in ('Gloss', 'Roughness', 'Metallic', 'SubsurfaceAmount')
            if 'file' not in data:
                if channel == 'Normal':
                    continue
                value = data['value']
                if channel == 'Gloss':
                    value = [1 - v for v in value]
                set_value(surface, destinations[channel], value[0] if scalar else value)
                continue
            signal = image(builder, channel, data, color=channel in ('Color', 'Specular', 'SubsurfaceColor'),
                           scalar=scalar, vector=channel == 'Normal')
            if not scalar and channel != 'Normal' and data.get('channel', 'rgb') != 'rgb':
                combine = builder.createNode('mtlxcombine3', safe_name(channel) + '_rgb')
                combine.parm('signature').set('color3')
                for input_name in ('in1', 'in2', 'in3'):
                    combine.setNamedInput(input_name, signal, 'out')
                signal = combine
            if channel == 'Gloss':
                invert = builder.createNode('mtlxsubtract', 'gloss_to_roughness')
                invert.parm('in1').set(1)
                invert.setNamedInput('in2', signal, 'out')
                signal = invert
            if channel == 'Normal':
                if settings['normal_flip_y']:
                    multiply = builder.createNode('mtlxmultiply', 'normal_flip_y')
                    multiply.parm('signature').set('vector3')
                    multiply.setNamedInput('in1', signal, 'out')
                    set_value(multiply, 'in2_vector3', [1, -1, 1])
                    offset = builder.createNode('mtlxadd', 'normal_offset_y')
                    offset.parm('signature').set('vector3')
                    offset.setNamedInput('in1', multiply, 'out')
                    set_value(offset, 'in2_vector3', [0, 1, 0])
                    signal = offset
                normal = builder.createNode('mtlxnormalmap', 'normal_decode')
                normal.setNamedInput('in', signal, 'out')
                normal.parm('scale').set(settings['normal_strength'])
                surface.setNamedInput('normal', normal, 'out')
            else:
                surface.setNamedInput(destinations[channel], signal, 'out')
        if material['vertex_opacity']:
            vertex = builder.createNode('mtlxgeompropvalue', 'vertex_opacity')
            vertex.parm('geomprop').set('Alpha')
            vertex.parm('default').set(1)
            combine = builder.createNode('mtlxmultiply', 'opacity_times_vertex')
            combine.parm('signature').set('color3FA')
            if not connect_existing(combine, 'in1', surface, 'opacity'):
                set_value(combine, 'in1_color3FA', surface.parmTuple('opacity').eval())
            combine.setNamedInput('in2', vertex, 'out')
            surface.setNamedInput('opacity', combine, 'out')
        if 'AO' in material['maps']:
            ao = material['maps']['AO']
            combine = builder.createNode('mtlxmultiply', 'color_times_ao')
            combine.parm('signature').set('color3')
            if not connect_existing(combine, 'in1', surface, 'base_color'):
                set_value(combine, 'in1_color3', surface.parmTuple('base_color').eval())
            if 'file' in ao:
                signal = image(builder, 'AO', ao)
                if ao.get('channel', 'rgb') != 'rgb':
                    rgb = builder.createNode('mtlxcombine3', 'AO_rgb')
                    rgb.parm('signature').set('color3')
                    for input_name in ('in1', 'in2', 'in3'):
                        rgb.setNamedInput(input_name, signal, 'out')
                    signal = rgb
                combine.setNamedInput('in2', signal, 'out')
            else:
                set_value(combine, 'in2_color3', ao['value'])
            surface.setNamedInput('base_color', combine, 'out')
        builder.setUserData('speedtree_bridge_renderer', 'karma')
        builder.setUserData('speedtree_bridge_material', material['name'])
        builder.layoutChildren()
        return builder
    except Exception:
        builder.destroy()
        raise
