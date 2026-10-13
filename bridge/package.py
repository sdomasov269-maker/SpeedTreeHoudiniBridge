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
    mesh = (source.parent / root.attrib["Mesh"]).resolve()
    if mesh.suffix.lower() not in {".obj", ".fbx"}:
        raise ValueError("Version 0.1 supports OBJ and FBX exports")
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
                path = (source.parent / tex.attrib["File"]).resolve().as_posix()
                entry["file"] = path
                pattern = path.replace("<UDIM>", "[0-9][0-9][0-9][0-9]")
                if not glob.glob(pattern):
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
    if renderer not in ("arnold", "redshift"):
        raise ValueError("Unknown renderer")
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
    scene = settings.get("scene", {})
    view = scene.get("camera_view", "three_quarter")
    if view not in ("front", "three_quarter", "side"):
        raise ValueError("Unknown camera view")
    request["settings"]["scene"] = {k: bool(scene.get(k, False)) for k in ("camera", "dome", "sun")}
    request["settings"]["scene"]["camera_view"] = view
    return request
