"""Optional scene setup, sized from imported world-space geometry."""
import math


def world_corners(root):
    import hou
    points = []
    for geo in root.allSubChildren():
        if geo.type().name() != "geo" or geo.displayNode() is None:
            continue
        geometry = geo.displayNode().geometry()
        if geometry.intrinsicValue("pointcount") == 0:
            continue
        box = geometry.boundingBox()
        low, high = box.minvec(), box.maxvec()
        transform = geo.worldTransform()
        for x in (low[0], high[0]):
            for y in (low[1], high[1]):
                for z in (low[2], high[2]):
                    points.append(hou.Vector3(x, y, z) * transform)
    if not points:
        raise ValueError("Cannot frame an empty tree")
    return points


def world_bounds(root):
    import hou
    points = world_corners(root)
    low = hou.Vector3([min(p[i] for p in points) for i in range(3)])
    high = hou.Vector3([max(p[i] for p in points) for i in range(3)])
    return (low + high) * .5, max((high - low).length() * .5, .001)


def frame_camera(camera, root, view="three_quarter", resolution=None):
    import hou
    center, radius = world_bounds(root)
    if resolution:
        camera.parm('resx').set(resolution[0])
        camera.parm('resy').set(resolution[1])
    aspect = camera.parm('resx').eval() * camera.parm('aspect').eval() / camera.parm('resy').eval()
    tangent_x = camera.parm('aperture').eval() / (2 * camera.parm('focal').eval())
    tangent_y = tangent_x / aspect
    direction = {"front": (0, .08, 1), "three_quarter": (1, .15, 1), "side": (1, .08, 0)}[view]
    direction = hou.Vector3(direction).normalized()
    rotation = hou.hmath.buildRotateLookAt(center + direction, center, hou.Vector3(0, 1, 0))
    corners = [(p - center) * hou.Matrix3(rotation).inverted() for p in world_corners(root)]
    distance = max(p[2] + 1.12 * max(abs(p[0]) / tangent_x, abs(p[1]) / tangent_y) for p in corners)
    distance = max(distance, radius * .1)
    eye = center + direction * distance
    rotation = hou.hmath.buildRotateLookAt(eye, center, hou.Vector3(0, 1, 0))
    transform = rotation * hou.hmath.buildTranslate(eye)
    # A camera must not inherit the tree's scale, rotation or FBX axis conversion.
    camera.setInput(0, None)
    camera.setPreTransform(hou.hmath.identityTransform())
    camera.parm('scale').set(1)
    camera.setWorldTransform(transform)
    depths = [distance - p[2] for p in corners]
    camera.parm("near").set(max(min(depths) * .1, .000001))
    camera.parm("far").set(max(depths) + radius)
    camera.parm('focus').set(distance)
    camera.parm('iconscale').set(max(radius * .15, .000001))
    camera.setUserData("speedtree_bridge_camera_view", view)


def reframe_selected():
    import hou
    selected = hou.selectedNodes()
    cameras = [n for n in selected if n.type().name() == "cam" and n.userData("speedtree_bridge_root")]
    selected_roots = {n.path() for n in selected}
    cameras += [n for n in hou.node('/obj').allSubChildren() if n.type().name() == 'cam'
                and n.userData('speedtree_bridge_root') in selected_roots and n not in cameras]
    if not cameras:
        hou.ui.displayMessage("Выберите дерево или камеру SpeedTree Bridge и повторите команду.")
        return
    with hou.undos.group("Reframe SpeedTree camera"):
        for camera in cameras:
            root = hou.node(camera.userData("speedtree_bridge_root"))
            if root is None:
                raise ValueError("Imported tree no longer exists")
            from . import solaris
            if not hasattr(solaris, 'sync_camera'):
                import importlib
                importlib.reload(solaris)
            frame_camera(camera, root, camera.userData("speedtree_bridge_camera_view") or "three_quarter", solaris.camera_resolution(root))
            solaris.sync_camera(root, camera)
            center, radius = world_bounds(root)
            for node in hou.node('/obj').allSubChildren():
                if node.userData('speedtree_bridge_root') == root.path() and node.type().name() != 'cam':
                    size_guides(node, radius)


def size_guides(node, radius):
    for name in ('iconscale',):
        parm = node.parm(name)
        if parm is not None:
            parm.set(max(radius * .15, .000001))


def setup_scene(root, renderer, settings):
    import hou
    nodes = []
    camera = None
    try:
        options = settings.get("scene", {})
        if not any(options.get(k) for k in ("camera", "dome", "sun")):
            return {"camera": None, "lights": [], "nodes": []}
        center, radius = world_bounds(root)
        name = root.name()
        if options.get("camera"):
            camera = hou.node("/obj").createNode("cam", name + "_camera")
            nodes.append(camera)
            render = settings.get('solaris', {}) if settings.get('context') == 'solaris' else {}
            resolution = (render.get('resolution_x', 1280), render.get('resolution_y', 720))
            frame_camera(camera, root, options.get("camera_view", "three_quarter"), resolution)
        lights = []
        for key in ("dome", "sun"):
            if not options.get(key):
                continue
            if renderer == "arnold":
                light = hou.node("/obj").createNode("arnold_light", name + "_" + key)
                nodes.append(light)
                parm = light.parm("ar_light_type")
                parm.set(parm.menuItems().index("skydome" if key == "dome" else "distant"))
                light.parm("ar_intensity").set(1)
                light.parm("ar_exposure").set(0 if key == "dome" else 1)
            elif renderer == 'redshift':
                light = hou.node("/obj").createNode("rslightdome" if key == "dome" else "rslightsun", name + "_" + key)
                nodes.append(light)
            else:
                light = hou.node('/obj').createNode('envlight' if key == 'dome' else 'hlight', name + '_' + key)
                nodes.append(light)
                if key == 'sun':
                    light.parm('light_type').set('distant')
            if key == "sun":
                light.parmTuple("r").set((-35, -40, 0))
            lights.append(light.path())
        for node in nodes:
            if node != camera:
                size_guides(node, radius)
            node.setUserData("speedtree_bridge_root", root.path())
            node.moveToGoodPosition()
        return {"camera": camera.path() if camera else None, "lights": lights, "nodes": nodes}
    except Exception:
        for node in reversed(nodes):
            node.destroy()
        raise
