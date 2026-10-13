"""Houdini 21 / HtoA 6 / Redshift material adapter. Import only inside Houdini."""
import json
import re
import logging
from pathlib import Path
from .package import make_request
log = logging.getLogger(__name__)


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name) or "material"


def set_value(node, name, value):
    parm = node.parmTuple(name) if isinstance(value, (tuple, list)) else node.parm(name)
    if parm is None:
        raise RuntimeError(f"Unsupported renderer interface: {node.type().name()}.{name}")
    parm.set(value)


def connected_input(node, name):
    index = node.inputNames().index(name)
    inputs = node.inputs()
    return inputs[index] if index < len(inputs) else None


def redshift_surface_type(builder):
    types = builder.childTypeCategory().nodeTypes()
    for kind in ("redshift::StandardMaterial", "redshift::Material"):
        if kind in types:
            return kind
    raise RuntimeError("No supported Redshift surface shader is installed")


def create_material(parent, material, renderer, settings, node_name=None):
    before = set(parent.children())
    try:
        return _create_material(parent, material, renderer, settings, node_name)
    except Exception:
        for node in set(parent.children()) - before:
            node.destroy()
        raise


def _create_material(parent, material, renderer, settings, node_name):
    arnold = renderer == "arnold"
    builder = parent.createNode("arnold_materialbuilder" if arnold else "redshift_vopnet", node_name or safe_name(material["name"]))
    builder.setUserData("speedtree_bridge_renderer", renderer)
    builder.setUserData("speedtree_bridge_material", material["name"])
    output = next(n for n in builder.children() if n.type().name() in ("arnold_material", "redshift_material"))
    for child in builder.children():
        if child != output:
            child.destroy()
    kind = "arnold::standard_surface" if arnold else redshift_surface_type(builder)
    legacy_rs = kind == "redshift::Material"
    base_color = "diffuse_color" if legacy_rs else "base_color"
    metalness = "refl_metalness" if legacy_rs else "metalness"
    surface = builder.createNode(kind, "surface")
    output.setNamedInput("surface" if arnold else "Surface", surface, "shader" if arnold else "outColor")
    set_value(surface, "specular_roughness" if arnold else "refl_roughness", settings["roughness"])
    if material["two_sided"]:
        set_value(surface, "thin_walled" if arnold else "refr_thin_walled", 1)
    destinations = {
        "Color": base_color, "Opacity": "opacity" if arnold else "opacity_color",
        "Roughness": "specular_roughness" if arnold else "refl_roughness",
        "Gloss": "specular_roughness" if arnold else "refl_roughness",
        "Metallic": metalness, "Specular": "specular_color" if arnold else "refl_color",
        "SubsurfaceColor": "subsurface_color" if arnold else ("ms_color0" if legacy_rs else "ms_color"),
        "SubsurfaceAmount": "subsurface" if arnold else "ms_amount",
    }
    auxiliary = {"Height", "Custom", "Custom2", "AO"}
    unknown = set(material["maps"]) - set(destinations) - {"Normal"} - auxiliary
    if unknown:
        raise ValueError(f"Unsupported maps in {material['name']}: {sorted(unknown)}")
    if "Gloss" in material["maps"] and "Roughness" in material["maps"]:
        raise ValueError("Export contains both Gloss and Roughness; choose one")
    for channel, data in material["maps"].items():
        if channel in auxiliary:
            # Retain auxiliary export data without guessing displacement units or custom channel semantics.
            builder.setUserData("speedtree_map_" + channel, json.dumps(data))
            continue
        dest = destinations.get(channel)
        if "file" not in data:
            if channel == "Normal":
                continue
            value = data["value"]
            if channel == "Gloss":
                value = [1 - v for v in value]
            if dest in {"metalness", "refl_metalness", "specular_roughness", "refl_roughness", "subsurface", "ms_amount"}:
                value = value[0]
            set_value(surface, dest, value)
            continue
        texture = builder.createNode("arnold::image" if arnold else "redshift::TextureSampler", safe_name(channel))
        set_value(texture, "filename" if arnold else "tex0", data["file"])
        color = channel in {"Color", "Specular", "SubsurfaceColor"}
        set_value(texture, "color_space" if arnold else "tex0_colorSpace", "sRGB" if color else "Raw")
        out = "rgba" if arnold else "outColor"
        if channel == "Gloss":
            set_value(texture, "multiply" if arnold else "color_multiplier", [-1, -1, -1])
            set_value(texture, "offset" if arnold else "color_offset", [1, 1, 1])
        if channel == "Normal":
            normal = builder.createNode("arnold::normal_map" if arnold else "redshift::BumpMap", "normal_decode")
            normal.setNamedInput("input", texture, out)
            set_value(normal, "strength" if arnold else "scale", settings["normal_strength"])
            set_value(normal, "invert_y" if arnold else "flipY", int(settings["normal_flip_y"]))
            if not arnold:
                set_value(normal, "inputType", "1")
            surface.setNamedInput("normal" if arnold else "bump_input", normal, "vector" if arnold else "out")
        else:
            if arnold and dest in {"metalness", "specular_roughness", "subsurface"}:
                out = "r"
            surface.setNamedInput(dest, texture, out)
    if material["vertex_opacity"]:
        opacity_input = "opacity" if arnold else "opacity_color"
        existing = connected_input(surface, opacity_input)
        vertex = builder.createNode("arnold::user_data_float" if arnold else "redshift::RSUserDataScalar", "vertex_opacity")
        set_value(vertex, "attribute", "Alpha")
        set_value(vertex, "default", 1.0)
        combine = builder.createNode("arnold::multiply" if arnold else "redshift::RSMathMulVector", "opacity_times_vertex")
        if existing is not None:
            combine.setNamedInput("input1", existing, "rgba" if arnold else "outColor")
        else:
            set_value(combine, "input1", surface.parmTuple(opacity_input).eval())
        combine.setNamedInput("input2", vertex, "float" if arnold else "out")
        surface.setNamedInput(opacity_input, combine, "rgb" if arnold else "out")
    if "AO" in material["maps"]:
        ao = material["maps"]["AO"]
        combine = builder.createNode("arnold::multiply" if arnold else "redshift::RSMathMulVector", "color_times_ao")
        existing = connected_input(surface, base_color)
        if existing:
            combine.setNamedInput("input1", existing, "rgba" if arnold else "outColor")
        else:
            set_value(combine, "input1", surface.parmTuple(base_color).eval())
        if "file" in ao:
            tex = builder.createNode("arnold::image" if arnold else "redshift::TextureSampler", "AO")
            set_value(tex, "filename" if arnold else "tex0", ao["file"])
            set_value(tex, "color_space" if arnold else "tex0_colorSpace", "Raw")
            combine.setNamedInput("input2", tex, "rgba" if arnold else "outColor")
        else:
            set_value(combine, "input2", ao["value"])
        surface.setNamedInput(base_color, combine, "rgb" if arnold else "out")
    builder.layoutChildren()
    return builder


def create_arnold_output(root, name):
    import hou
    node = hou.node("/out").createNode("arnold", safe_name(name) + "_arnold")
    try:
        node.setUserData("speedtree_bridge_root", root.path())
        set_value(node, "vobject", root.path() + "/*")
        cameras = [n for n in hou.node("/obj").allSubChildren() if n.type().name() == "cam"]
        if len(cameras) == 1:
            set_value(node, "camera", cameras[0].path())
        # Use Arnold's image viewer output. The user can choose a file or camera on the ROP.
        set_value(node, "ar_picture", "ip")
        node.moveToGoodPosition()
        return node
    except Exception:
        node.destroy()
        raise


def assignment_code(mapping):
    # Map imported material names, never guess from bark/leaf filenames.
    return '''import hou, re
geo = hou.pwd().geometry()
mapping = ''' + repr(mapping) + '''
def norm(value):
    return re.sub(r"[^A-Za-z0-9_]", "_", value)
aliases = {norm(k): v for k, v in mapping.items()}
if len(aliases) != len(mapping):
    raise hou.NodeError("Material names collide after normalization")
attr = geo.findPrimAttrib("shop_materialpath")
if attr is None:
    attr = geo.addAttrib(hou.attribType.Prim, "shop_materialpath", "")
unmatched = set()
cache = {}
values = []
for index, original in enumerate(geo.primStringAttribValues("shop_materialpath")):
    if original in cache:
        values.append(cache[original])
        continue
    name = original.replace(chr(92), "/").rsplit("/", 1)[-1]
    path = mapping.get(name) or aliases.get(norm(name))
    cacheable = bool(path)
    if not path:
        prim = geo.prim(index)
        candidates = {mapping[g.name()] for g in geo.primGroups() if g.name() in mapping and g.contains(prim)}
        if len(candidates) == 1:
            path = candidates.pop()
    if not path and len(mapping) == 1:
        path = next(iter(mapping.values()))
    if path:
        if cacheable:
            cache[original] = path
        values.append(path)
    else:
        unmatched.add(name or "<no material>")
if unmatched:
    raise hou.NodeError("Unmatched exported materials: " + ", ".join(sorted(unmatched)))
geo.setPrimStringAttribValues("shop_materialpath", values)
'''


def import_package(filename):
    import hou
    raw = json.loads(Path(filename).read_text(encoding="utf-8"))
    if raw.get("schema") != 1:
        raise ValueError("Unsupported bridge schema")
    # Re-read source and validate all files/settings instead of trusting edited JSON.
    package = make_request(raw["source"], raw["renderer"], raw["settings"])
    names = [safe_name(m["name"]) for m in package["materials"]]
    if len(names) != len(set(names)):
        raise ValueError("Material names collide after normalization")
    renderer = package["renderer"]
    kind = "arnold_materialbuilder" if renderer == "arnold" else "redshift_vopnet"
    if hou.node("/mat").childTypeCategory().nodeTypes().get(kind) is None:
        raise RuntimeError(f"{renderer} is not loaded in this Houdini session")
    root = None
    created_materials = []
    render_output = None
    scene_setup = {"nodes": [], "camera": None, "lights": []}
    with hou.undos.group("Import SpeedTree Bridge"):
        try:
            mesh = Path(package["mesh"])
            if mesh.suffix.lower() == ".fbx":
                log.info("Importing FBX %s", mesh)
                root, messages = hou.hipFile.importFBX(str(mesh), suppress_save_prompt=True,
                    merge_into_scene=True, import_cameras=False, import_lights=False,
                    import_materials=True, import_into_object_subnet=True,
                    override_scene_frame_range=False, convert_units=False)
                geos = [n for n in root.allSubChildren() if n.type().name() == "geo"]
                log.info("FBX loaded; %s geometry objects", len(geos))
            else:
                root = hou.node("/obj").createNode("subnet", safe_name(mesh.stem) + "_bridge")
                geo = root.createNode("geo", "mesh")
                for child in geo.children():
                    child.destroy()
                file_node = geo.createNode("file", "speedtree_mesh")
                file_node.parm("file").set(mesh.as_posix())
                geos = [geo]
                messages = ""
            root.setUserData("speedtree_bridge_source", package["source"])
            set_value(root, "scale", package["settings"]["scale"])
            network = hou.node("/mat")
            mapping = {}
            for m in package["materials"]:
                node = create_material(network, m, renderer, package["settings"],
                    safe_name(mesh.stem) + "_" + renderer + "_" + safe_name(m["name"]))
                created_materials.append(node)
                mapping[m["name"]] = node.path()
                node.setUserData("speedtree_bridge_root", root.path())
                node.moveToGoodPosition()
            root.setUserData("speedtree_bridge_materials", json.dumps(mapping))
            log.info("Created %s materials", len(mapping))
            if not geos:
                raise ValueError("Export contains no geometry objects")
            count = 0
            for geo in geos:
                log.info("Assigning %s", geo.path())
                source = geo.displayNode()
                if source is None:
                    continue
                assign = geo.createNode("python", "bridge_assign")
                assign.setInput(0, source)
                assign.parm("python").set(assignment_code(mapping))
                try:
                    assign.cook(force=True)
                    log.info("Assignment cooked: %s", geo.path())
                except hou.OperationFailed as error:
                    raise RuntimeError("\n".join(assign.errors()) or str(error)) from error
                if assign.errors():
                    raise RuntimeError("\n".join(assign.errors()))
                count += len(assign.geometry().prims())
                log.info("Primitive count: %s", count)
                assign.setDisplayFlag(True)
                assign.setRenderFlag(True)
                # Arnold requires non-opaque geometry for leaf cutouts.
                if renderer == "arnold" and any("Opacity" in m["maps"] or m["vertex_opacity"] for m in package["materials"]):
                    parm = geo.parm("ar_opaque")
                    if parm is None:
                        from htoa.properties import addArnoldProperties
                        addArnoldProperties(geo)
                        parm = geo.parm("ar_opaque")
                    if parm is None:
                        raise RuntimeError("Arnold ar_opaque parameter is missing on geometry")
                    parm.set(False)
                geo.layoutChildren()
                log.info("Geometry complete: %s", geo.path())
            if not count:
                raise ValueError("Mesh import produced zero primitives")
            from .scene import setup_scene
            scene_setup = setup_scene(root, renderer, package["settings"])
            if renderer == "arnold":
                render_output = create_arnold_output(root, mesh.stem)
                if scene_setup["camera"]:
                    set_value(render_output, "camera", scene_setup["camera"])
                root.setUserData("speedtree_bridge_render_output", render_output.path())
            root.layoutChildren()
            root.moveToGoodPosition()
            notes = []
            if render_output is not None and hou.node(render_output.parm("camera").eval()) is None:
                notes.append("Arnold output created; select a camera in its Camera parameter before rendering.")
            for m in package["materials"]:
                if "file" in m["maps"].get("Height", {}):
                    notes.append(f"{m['name']}: Height retained as metadata; displacement is not enabled.")
                for channel in ("Custom", "Custom2"):
                    if channel in m["maps"]:
                        notes.append(f"{m['name']}: {channel} retained as metadata, not connected to shading.")
            return {"root": root.path(), "materials": mapping, "primitives": count, "messages": messages,
                    "notes": notes, "render_output": render_output.path() if render_output else None,
                    "camera": scene_setup["camera"], "lights": scene_setup["lights"]}
        except Exception:
            if render_output is not None:
                render_output.destroy()
            for node in reversed(scene_setup["nodes"]):
                node.destroy()
            if root is not None:
                root.destroy()
            for node in created_materials:
                node.destroy()
            raise
