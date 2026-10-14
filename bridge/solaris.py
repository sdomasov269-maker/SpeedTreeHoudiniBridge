"""Build isolated Solaris stages and renderer-specific USD Render outputs."""
import json
from .houdini import safe_name


def renderer_delegate(renderer, engine='cpu'):
    return {'arnold': 'HdArnoldRendererPlugin', 'redshift': 'HdRedshiftRendererPlugin',
            'karma': 'BRAY_HdKarmaXPU' if engine == 'xpu' else 'BRAY_HdKarma'}[renderer]


def available_delegates():
    from pxr import UsdImagingGL
    return set(UsdImagingGL.Engine.GetRendererPlugins())


def require_renderer(renderer, engine='cpu'):
    delegate = renderer_delegate(renderer, engine)
    if delegate not in available_delegates():
        raise RuntimeError(renderer.title() + ' Solaris/Hydra integration is not loaded for this Houdini build')


def arnold_sample_parms(node):
    prefix = 'xn__arnoldglobalAA_samples_'
    value = next((p for p in node.parms() if p.name().startswith(prefix) and not p.name().startswith(prefix + 'max') and '_control_' not in p.name()), None)
    control = next((p for p in node.parms() if p.name().startswith(prefix + 'control_')), None)
    if value is None or control is None:
        raise RuntimeError('Unsupported Arnold USD AA sample interface')
    return control, value


def output_picture(root, template, renderer='karma'):
    # Each tree's automatic output must have its own filename, including in batch imports.
    return template.replace('$OS', safe_name(root.name()) + '_' + renderer)


def sync_camera(root, camera):
    """Repair the USD camera target when detaching an older parented OBJ camera."""
    import hou
    subnet = hou.node(root.userData('speedtree_bridge_solaris') or '')
    if subnet is None:
        return
    renderer = root.userData('speedtree_solaris_renderer') or 'karma'
    render = subnet.node(renderer + '_settings')
    if render is None:
        raise ValueError('Linked Solaris render settings were removed or renamed')
    if renderer == 'redshift':
        render.parm('f_render_camera').set(True)
    render.parm('RS_renderCamera' if renderer == 'redshift' else 'camera').set('/' + camera.name())


def camera_resolution(root):
    """Use the current LOP resolution when explicitly reframing a linked camera."""
    import hou
    subnet = hou.node(root.userData('speedtree_bridge_solaris') or '')
    if subnet is None:
        return None
    renderer = root.userData('speedtree_solaris_renderer') or 'karma'
    render = subnet.node('render_settings' if renderer == 'redshift' else renderer + '_settings')
    if render is None:
        return None
    names = ('resolutionx', 'resolutiony') if renderer == 'karma' else ('resolution1', 'resolution2')
    return tuple(render.parm(name).eval() for name in names)


def setup_solaris(root, scene, settings, renderer='karma'):
    import hou
    require_renderer(renderer, settings['solaris'].get('engine', 'cpu'))
    subnet = hou.node('/stage').createNode('subnet', safe_name(root.name()) + '_solaris')
    output = None
    try:
        imported = subnet.createNode('sceneimport', 'import_tree')
        objects = [root.path() + '/*'] + ([scene['camera']] if scene['camera'] else []) + scene['lights']
        imported.parm('objects').set(' '.join(objects))
        imported.parm('importbundles').set(False)
        imported.parm('matdestpath').set('/Looks')
        # Follow the live SOP chain and translate only assigned renderer materials.
        imported.parm('importmats').set(True)
        imported.parm('enable_attribs').set(True)
        imported.parm('attribs').set('* ^__* ^usd*')
        kind = {'karma': 'karmarendersettings', 'arnold': 'arnold_rendersettings', 'redshift': 'redshift'}[renderer]
        render = subnet.createNode(kind, renderer + '_settings')
        render.setInput(0, imported)
        options = settings['solaris']
        primpath = '/Render/' + safe_name(root.name()) + '/Settings'
        camera = '/' + hou.node(scene['camera']).name() if scene['camera'] else '/cameras/camera1'
        picture = output_picture(root, options['output_image'], renderer)
        if renderer == 'karma':
            render.parm('engine').set(options['engine'])
            render.parm('res_mode').set('manual')
            render.parm('res_mode').pressButton()
            render.parm('resolutionx').set(options['resolution_x'])
            render.parm('resolutiony').set(options['resolution_y'])
            render.parm('samplesperpixel').set(options['samples'])
            render.parm('pathtracedsamples').set(options['samples'])
            render.parm('picture').set(picture)
            render.parm('primpath').set(primpath)
            render.parm('camera').set(camera)
        elif renderer == 'arnold':
            render.parm('primpath').set(primpath)
            render.parm('productName').set(picture)
            render.parm('camera').set(camera)
            render.parm('res_mode').set('manual')
            render.parm('res_mode').pressButton()
            render.parmTuple('resolution').set((options['resolution_x'], options['resolution_y']))
            control, samples = arnold_sample_parms(render)
            control.set('set')
            samples.set(options['samples'])
        else:
            render.parm('rs_rendersettings_primpath').set(primpath)
            render.parm('f_render_camera').set(True)
            render.parm('RS_renderCamera').set(camera)
            render.parm('RS_outputFileNamePrefix').set(picture)
            render.parm('redshiftglobalUnifiedMaxSamples').set(options['samples'])
            render.parm('redshiftglobalUnifiedMinSamples').set(min(4, options['samples']))
        for name, child in (('renderproductsparentprimpath', 'Products'), ('rendervarsparentprimpath', 'Vars')):
            if render.parm(name):
                render.parm(name).set('/Render/' + safe_name(root.name()) + '/' + child)
        final = render
        if renderer == 'redshift':
            final = subnet.createNode('rendersettings', 'render_settings')
            final.setInput(0, render)
            final.parm('primpath').set(primpath)
            final.parm('products_control').set('none')
            final.parm('camera_control').set('none')
            final.parm('res_mode').set('manual')
            final.parm('res_mode').pressButton()
            final.parmTuple('resolution').set((options['resolution_x'], options['resolution_y']))
        terminal = subnet.node('output0')
        terminal.setInput(0, final)
        final.setDisplayFlag(True)
        subnet.layoutChildren()
        subnet.moveToGoodPosition()
        output = hou.node('/out').createNode('usdrender', safe_name(root.name()) + '_' + renderer)
        output.parm('loppath').set(subnet.path())
        output.parm('renderer').set(renderer_delegate(renderer, options['engine']))
        output.parm('rendersettings').set(primpath)
        output.moveToGoodPosition()
        for node in (subnet, output):
            node.setUserData('speedtree_bridge_root', root.path())
        subnet.stage()
        errors = imported.errors() + render.errors() + (final.errors() if final != render else ())
        if errors:
            raise RuntimeError('\n'.join(errors))
        root.setUserData('speedtree_bridge_solaris', subnet.path())
        root.setUserData('speedtree_solaris_options', json.dumps(options))
        root.setUserData('speedtree_solaris_renderer', renderer)
        return {'stage': subnet.path(), 'render_output': output, 'settings_node': render.path()}
    except Exception:
        if output:
            output.destroy()
        subnet.destroy()
        raise


def update_settings(root, options, changes):
    """Apply explicit UI setting changes while retaining edits made directly on LOPs."""
    import hou
    previous = json.loads(root.userData('speedtree_solaris_options') or '{}')
    subnet = hou.node(root.userData('speedtree_bridge_solaris') or '')
    renderer = root.userData('speedtree_solaris_renderer') or 'karma'
    render = subnet.node(renderer + '_settings') if subnet else None
    output = hou.node(root.userData('speedtree_bridge_render_output') or '')
    if render is None or output is None:
        raise ValueError('Linked Solaris render settings or output were removed or renamed')
    if renderer == 'karma':
        destinations = {'engine': ('engine',), 'resolution_x': ('resolutionx',), 'resolution_y': ('resolutiony',),
                        'samples': ('samplesperpixel', 'pathtracedsamples'), 'output_image': ('picture',)}
    elif renderer == 'arnold':
        destinations = {'resolution_x': ('resolution1',), 'resolution_y': ('resolution2',),
                        'samples': (arnold_sample_parms(render)[1].name(),), 'output_image': ('productName',)}
    else:
        destinations = {'resolution_x': ('resolution1',), 'resolution_y': ('resolution2',),
                        'samples': ('redshiftglobalUnifiedMaxSamples',), 'output_image': ('RS_outputFileNamePrefix',)}
    planned = []
    for key, names in destinations.items():
        if options[key] != previous.get(key):
            value = output_picture(root, options[key], renderer) if key == 'output_image' else options[key]
            node = subnet.node('render_settings') if renderer == 'redshift' and key.startswith('resolution_') else render
            planned += [(node.parm(name), value) for name in names]
            if key == 'samples' and renderer == 'redshift':
                minimum = render.parm('redshiftglobalUnifiedMinSamples')
                if minimum.eval() > value:
                    planned.append((minimum, value))
            elif key == 'samples' and renderer == 'arnold':
                planned.append((arnold_sample_parms(render)[0], 'set'))
            if key == 'engine':
                require_renderer(renderer, options[key])
                planned.append((output.parm('renderer'), renderer_delegate(renderer, options[key])))
    if any(parm is None or parm.isLocked() or parm.keyframes() for parm, _ in planned):
        raise ValueError('A changed Solaris setting is locked or driven by an expression; edit it on the render node')
    for parm, value in planned:
        old = parm.unexpandedString() if parm.parmTemplate().type() == hou.parmTemplateType.String else parm.eval()
        parm.set(value)
        changes.append((parm, old))
    root.setUserData('speedtree_solaris_options', json.dumps(options))
