"""Optional scene setup, sized from imported world-space geometry."""
import math


def world_bounds(root):
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
    low = hou.Vector3([min(p[i] for p in points) for i in range(3)])
    high = hou.Vector3([max(p[i] for p in points) for i in range(3)])
    return (low + high) * .5, max((high - low).length() * .5, .001)


def frame_camera(camera, root, view="three_quarter"):
    import hou
    center, radius = world_bounds(root)
    camera.parm("focal").set(50)
    camera.parm("resx").set(1280)
    camera.parm("resy").set(720)
    half_angle = math.atan(camera.parm("aperture").eval() / (2 * 50 * (1280 / 720)))
    distance = 1.15 * radius / math.sin(half_angle)
    direction = {"front": (0, .08, 1), "three_quarter": (1, .15, 1), "side": (1, .08, 0)}[view]
    eye = center + hou.Vector3(direction).normalized() * distance
    rotation = hou.hmath.buildRotateLookAt(eye, center, hou.Vector3(0, 1, 0))
    transform = rotation * hou.hmath.buildTranslate(eye)
    camera.setInput(0, root)
    camera.setParmTransform(transform * root.worldTransform().inverted())
    camera.parm("near").set(max(radius * .001, .00001))
    camera.parm("far").set(distance + radius * 4)
    camera.setUserData("speedtree_bridge_camera_view", view)


def reframe_selected():
    import hou
    selected = hou.selectedNodes()
    cameras = [n for n in selected if n.type().name() == "cam" and n.userData("speedtree_bridge_root")]
    if not cameras:
        hou.ui.displayMessage("Выберите созданную плагином камеру и повторите команду.")
        return
    with hou.undos.group("Reframe SpeedTree camera"):
        for camera in cameras:
            root = hou.node(camera.userData("speedtree_bridge_root"))
            if root is None:
                raise ValueError("Imported tree no longer exists")
            frame_camera(camera, root, camera.userData("speedtree_bridge_camera_view") or "three_quarter")


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
            frame_camera(camera, root, options.get("camera_view", "three_quarter"))
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
            else:
                light = hou.node("/obj").createNode("rslightdome" if key == "dome" else "rslightsun", name + "_" + key)
                nodes.append(light)
            if key == "sun":
                light.parmTuple("r").set((-35, -40, 0))
            lights.append(light.path())
        for node in nodes:
            node.setUserData("speedtree_bridge_root", root.path())
            node.moveToGoodPosition()
        return {"camera": camera.path() if camera else None, "lights": lights, "nodes": nodes}
    except Exception:
        for node in reversed(nodes):
            node.destroy()
        raise
