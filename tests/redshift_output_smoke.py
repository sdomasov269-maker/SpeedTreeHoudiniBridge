"""Check Redshift output, camera selection and rollback in an isolated hython."""
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.package import make_request
from bridge.houdini import import_package

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    (base / "tree.obj").write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    source = base / "tree.stmat"
    source.write_text('<Materials Mesh="tree.obj"><Material Name="bark"/></Materials>')
    filename = base / "tree.bridge.json"
    previous = hou.node("/out").createNode("Redshift_ROP", "user_output")
    previous.parm("RS_objects_candidate").set("user_objects")
    for create_camera in (False, True):
        filename.write_text(json.dumps(make_request(source, "redshift", {"scene": {"camera": create_camera}})))
        result = import_package(filename)
        output = hou.node(result["render_output"])
        assert output.type().name() == "Redshift_ROP"
        assert output.parm("RS_objects_candidate").eval() == result["root"] + "/*"
        assert previous.parm("RS_objects_candidate").eval() == "user_objects"
        if create_camera:
            assert output.parm("RS_renderCamera").eval() == result["camera"]
        else:
            assert any("select a camera" in note for note in result["notes"])
        hou.node(result["root"]).destroy()
        output.destroy()
        if result["camera"]:
            hou.node(result["camera"]).destroy()
        for path in result["materials"].values():
            hou.node(path).destroy()
    before = {p: set(hou.node(p).children()) for p in ("/obj", "/mat", "/out")}
    source.write_text('<Materials Mesh="tree.obj"><Material Name="x"/><Material Name="y"/></Materials>')
    filename.write_text(json.dumps(make_request(source, "redshift", {})))
    try:
        import_package(filename)
    except RuntimeError:
        assert all(set(hou.node(p).children()) == nodes for p, nodes in before.items())
    else:
        raise AssertionError("Expected assignment failure")
print(hou.applicationVersionString(), "Redshift output, camera and rollback: PASS")
