"""Read SpeedTree material exports without importing Houdini or vendor code."""
from pathlib import Path
import glob
import math
import xml.etree.ElementTree as ET


def read_export(filename):
    source = Path(filename).resolve()
    if source.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Material export is too large")
    raw = source.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("DTD and entities are not supported")
    root = ET.fromstring(raw)
    if root.tag != "Materials" or not root.get("Mesh"):
        raise ValueError("Expected SpeedTree Materials with a Mesh attribute")
    mesh = (source.parent / root.attrib["Mesh"].replace("\\", "/")).resolve()
    if mesh.suffix.lower() not in {".obj", ".fbx"}:
        raise ValueError("Bridge supports OBJ and FBX exports")
    if not mesh.is_file():
        raise ValueError(f"Mesh not found: {mesh}")
    materials, warnings, names = [], [], set()
    for item in root.findall(".//Material"):
        name = item.get("Name", "").strip()
        if not name or name in names:
            raise ValueError(f"Empty or duplicate material name: {name!r}")
        names.add(name)
        maps = {}
        for tex in item.findall(".//Map"):
            channel = tex.get("Name", "")
            if not channel or channel in maps:
                raise ValueError(f"Empty or duplicate map in {name}: {channel}")
            entry = {}
            if tex.get("File"):
                path = (source.parent / tex.attrib["File"].replace("\\", "/")).resolve().as_posix()
                entry["file"] = path
                component = tex.get("Channel", "rgb").lower()
                if component not in ("rgb", "r", "g", "b", "a"):
                    raise ValueError(f"Invalid texture Channel: {name} / {channel}: {component}")
                if channel == "Normal" and component != "rgb":
                    raise ValueError("Normal maps require RGB channels")
                if component != "rgb":
                    entry["channel"] = component
                pattern = glob.escape(path).replace("<UDIM>", "[1-9][0-9][0-9][0-9]")
                if not any(Path(candidate).is_file() for candidate in glob.glob(pattern)):
                    warnings.append(f"Missing texture: {name} / {channel}: {path}")
            else:
                value = float(tex.get("Value", "1"))
                color = [float(tex.get(k, str(value))) for k in ("ColorR", "ColorG", "ColorB")]
                if not all(math.isfinite(v) for v in color):
                    raise ValueError(f"Non-finite map value: {name} / {channel}")
                entry["value"] = color
            maps[channel] = entry
        materials.append({"name": name, "two_sided": item.get("TwoSided") == "1",
                          "vertex_opacity": item.get("VertexOpacity") == "1", "maps": maps})
    if not materials:
        raise ValueError("Export contains no materials")
    return {"schema": 1, "source": source.as_posix(), "mesh": mesh.as_posix(),
            "materials": materials, "warnings": warnings}


def make_request(filename, renderer, settings):
    if renderer not in ("arnold", "redshift", "karma"):
        raise ValueError("Unknown renderer")
    context = settings.get('context', 'solaris' if renderer == 'karma' else 'obj')
    if context not in ('obj', 'solaris') or (renderer == 'karma' and context != 'solaris'):
        raise ValueError('Invalid renderer/workflow combination')
    scale = float(settings.get("scale", 1))
    roughness = float(settings.get("roughness", .5))
    normal = float(settings.get("normal_strength", 1))
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Scale must be positive and finite")
    if not math.isfinite(roughness) or not 0 <= roughness <= 1:
        raise ValueError("Roughness must be between 0 and 1")
    if not math.isfinite(normal) or normal < 0:
        raise ValueError("Normal strength must be positive or zero")
    request = read_export(filename)
    if request["warnings"]:
        raise ValueError("Resolve export issues before importing:\n" + "\n".join(request["warnings"]))
    request.update(renderer=renderer, settings={"scale": scale, "roughness": roughness,
                   "normal_strength": normal, "normal_flip_y": bool(settings.get("normal_flip_y", False))})
    request['settings']['context'] = context
    scene = settings.get("scene", {})
    view = scene.get("camera_view", "three_quarter")
    if view not in ("front", "three_quarter", "side"):
        raise ValueError("Unknown camera view")
    request["settings"]["scene"] = {k: bool(scene.get(k, False)) for k in ("camera", "dome", "sun")}
    request["settings"]["scene"]["camera_view"] = view
    if context == 'solaris':
        options = settings.get('solaris', {})
        engine = options.get('engine', 'cpu')
        if engine not in ('cpu', 'xpu'):
            raise ValueError('Karma engine must be cpu or xpu')
        result = {'engine': engine}
        for key, default, low, high in (('resolution_x', 1280, 16, 32768), ('resolution_y', 720, 16, 32768), ('samples', 3 if renderer == 'arnold' else 128, 1, 16 if renderer == 'arnold' else 65536)):
            value = float(options.get(key, default))
            if not math.isfinite(value) or not value.is_integer() or not low <= value <= high:
                raise ValueError('Invalid Solaris setting: ' + key)
            result[key] = int(value)
        picture = str(options.get('output_image', '$HIP/render/$HIPNAME.$OS.$F4.exr')).strip()
        if not picture or '\x00' in picture or '\n' in picture:
            raise ValueError('Solaris output image path is empty or invalid')
        result['output_image'] = picture
        request['settings']['solaris'] = result
    return request
