"""Transactional OBJ updates for a stable live-linked Houdini object."""
import json
from pathlib import Path
import re
from .package import make_request
from .houdini import import_package, assignment_code, safe_name


def apply_live_request(filename):
    import hou
    raw = json.loads(Path(filename).read_text(encoding="utf-8"))
    live = raw.get("live", {})
    asset_id = live.get("asset_id", "")
    if not re.fullmatch(r"[a-f0-9]{64}", asset_id):
        raise ValueError("Invalid live asset identity")
    package = make_request(raw["source"], raw["renderer"], raw["settings"])
    if Path(package["mesh"]).suffix.lower() != ".obj":
        raise ValueError("Live updates require OBJ exports")
    matches = [n for n in hou.node('/obj').children() if n.userData('speedtree_live_id') == asset_id]
    if len(matches) > 1:
        raise ValueError("Multiple live targets for this tree; remove the duplicated link first")
    root = matches[0] if matches else None
    if root is None:
        result = import_package(filename)
        root = hou.node(result['root'])
        root.setUserData('speedtree_live_id', asset_id)
        root.setUserData('speedtree_live_renderer', package['renderer'])
        root.setUserData('speedtree_live_context', package['settings']['context'])
        root.setUserData('speedtree_live_project', str(live.get('project', '')))
        root.setUserData('speedtree_live_maps', json.dumps({m['name']: m['maps'] for m in package['materials']}))
        root.setUserData('speedtree_live_revision', str(live.get('revision', '')))
        root.setUserData('speedtree_live_file', root.node('mesh/speedtree_mesh').path())
        root.setUserData('speedtree_live_assign', root.node('mesh/bridge_assign').path())
        root.node('mesh/speedtree_mesh').setUserData('speedtree_live_role', 'file')
        root.node('mesh/bridge_assign').setUserData('speedtree_live_role', 'assign')
        for name, path in result['materials'].items():
            node = hou.node(path)
            node.setUserData('speedtree_live_id', asset_id)
            node.setUserData('speedtree_live_material', name)
        result['updated'] = False
        return result
    if root.userData('speedtree_live_renderer') != package['renderer']:
        raise ValueError("Keep the same renderer for this live tree, or unlink it before switching")
    previous_context = root.userData('speedtree_live_context') or ('solaris' if package['renderer'] == 'karma' else 'obj')
    if previous_context != package['settings']['context']:
        raise ValueError('Keep the same OBJ/Solaris workflow for this live link; import a new link to switch')
    roles = {role: [n for n in root.allSubChildren() if n.userData('speedtree_live_role') == role] for role in ('file', 'assign')}
    if any(len(nodes) != 1 for nodes in roles.values()):
        raise ValueError('Live source nodes are missing or duplicated')
    source, assign = roles['file'][0], roles['assign'][0]
    if source is None or assign is None or assign.inputs()[0] != source:
        raise ValueError("Live source nodes were removed or rewired; reconnect the source before updating")
    previous = json.loads(root.userData('speedtree_bridge_materials') or '{}')
    previous_maps = json.loads(root.userData('speedtree_live_maps') or '{}')
    staged = None
    transferred = set()
    changes = []
    metadata = {key: root.userData(key) for key in ('speedtree_bridge_source', 'speedtree_bridge_materials', 'speedtree_live_maps', 'speedtree_live_revision', 'speedtree_solaris_options')}
    # Validate a complete candidate without touching the user's tree or scene setup.
    candidate = dict(raw)
    candidate['settings'] = dict(raw['settings'], scene={})
    temporary = Path(filename).with_name(Path(filename).name + '.candidate.json')
    temporary.write_text(json.dumps(candidate), encoding='utf-8')
    with hou.undos.group('Update live SpeedTree'):
        try:
            staged = import_package(temporary)
            mapping = {}
            for material in package['materials']:
                name = material['name']
                shaders = [n for n in hou.node('/mat').children() if n.userData('speedtree_live_id') == asset_id and n.userData('speedtree_live_material') == name]
                if len(shaders) > 1:
                    raise ValueError('Duplicated live material: ' + name)
                current = shaders[0] if shaders else None
                if current is None:
                    path = staged['materials'][name]
                    mapping[name] = path
                    transferred.add(path)
                    hou.node(path).setUserData('speedtree_bridge_root', root.path())
                    hou.node(path).setUserData('speedtree_live_id', asset_id)
                    hou.node(path).setUserData('speedtree_live_material', name)
                    continue
                mapping[name] = current.path()
                # Refresh only texture paths that still have their last bridge value.
                for channel, data in material['maps'].items():
                    old = previous_maps.get(name, {}).get(channel, {}).get('file')
                    if old and 'file' in data:
                        texture = current.node(safe_name(channel))
                        parm = texture.parm({'arnold': 'filename', 'redshift': 'tex0', 'karma': 'file'}[package['renderer']]) if texture else None
                        if parm and not parm.isLocked() and not parm.keyframes() and parm.unexpandedString() == old:
                            changes.append((parm, parm.unexpandedString()))
                            parm.set(data['file'])
            for parm, value in ((source.parm('file'), package['mesh']), (assign.parm('python'), assignment_code(mapping))):
                if parm.isLocked() or parm.keyframes():
                    raise ValueError('Live source parameters must not contain expressions or animation')
                old = parm.unexpandedString()
                parm.set(value)
                changes.append((parm, old))
            # Reload even when an exporter has overwritten a file at the same path.
            source.parm('reload').pressButton()
            assign.cook(force=True)
            if assign.errors() or not assign.geometry().prims():
                raise RuntimeError('\n'.join(assign.errors()) or 'Updated mesh is empty')
            all_materials = dict(previous, **mapping)
            root.setUserData('speedtree_bridge_materials', json.dumps(all_materials))
            root.setUserData('speedtree_bridge_source', package['source'])
            new_maps = dict(previous_maps)
            new_maps.update({m['name']: m['maps'] for m in package['materials']})
            root.setUserData('speedtree_live_maps', json.dumps(new_maps))
            root.setUserData('speedtree_live_revision', str(live.get('revision', '')))
            if package['settings']['context'] == 'solaris':
                from .solaris import update_settings
                update_settings(root, package['settings']['solaris'], changes)
                stage = hou.node(root.userData('speedtree_bridge_solaris') or '')
                if stage is None:
                    raise ValueError('The linked Solaris stage was removed')
                stage.stage()
                if stage.errors():
                    raise RuntimeError('\n'.join(stage.errors()))
            return {'root': root.path(), 'materials': mapping, 'primitives': len(assign.geometry().prims()),
                    'updated': True, 'render_output': root.userData('speedtree_bridge_render_output'),
                    'stage': root.userData('speedtree_bridge_solaris'),
                    'notes': ['Existing shaders, tree transforms, camera, lights and downstream nodes preserved. New material names get new shaders; existing shader topology and values are not rebuilt.']}
        except Exception:
            for parm, value in reversed(changes):
                parm.set(value)
            for key, value in metadata.items():
                if value is None:
                    if key in root.userDataDict():
                        root.destroyUserData(key)
                else:
                    root.setUserData(key, value)
            source.parm('reload').pressButton()
            transferred.clear()
            raise
        finally:
            temporary.unlink()
            if staged:
                if staged.get('stage'):
                    hou.node(staged['stage']).destroy()
                hou.node(staged['root']).destroy()
                if staged.get('render_output'):
                    hou.node(staged['render_output']).destroy()
                for path in staged['materials'].values():
                    if path not in transferred and hou.node(path):
                        hou.node(path).destroy()
