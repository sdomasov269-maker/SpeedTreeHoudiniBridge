"""Inspect installed renderer interfaces. Run using hython."""
import json
from pathlib import Path
import hou

result = {"houdini": hou.applicationVersionString(), "nodes": {}}
for kind in ("arnold_materialbuilder", "redshift_vopnet"):
    try:
        builder = hou.node("/mat").createNode(kind)
        result["nodes"][kind] = {"children": [(n.type().name(), n.inputNames(), n.outputNames()) for n in builder.children()]}
        types = ("arnold::standard_surface", "arnold::image", "arnold::normal_map", "arnold::subtract") if kind.startswith("arnold") else ("redshift::StandardMaterial", "redshift::TextureSampler", "redshift::BumpMap", "redshift::RSColorCorrection")
        for node_type in types:
            try:
                node = builder.createNode(node_type)
                result["nodes"][node_type] = {"inputs": node.inputNames(), "outputs": node.outputNames(),
                    "parms": {p.name(): p.eval() for p in node.parms()}}
            except Exception as error:
                result["nodes"][node_type] = {"error": str(error)}
        builder.destroy()
    except Exception as error:
        result["nodes"][kind] = {"error": str(error)}
target = Path(__file__).resolve().with_name("renderer_interfaces.json")
target.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
print("Interfaces saved:", target)
