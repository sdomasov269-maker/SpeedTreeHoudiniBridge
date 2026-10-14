"""Integration checks on installed Houdini and actual renderer nodes, without rendering."""
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hou
from bridge.package import make_request
from bridge.houdini import import_package


def png(path):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) +
                     chunk(b"IDAT", zlib.compress(b"\x00\x80\x80\xff")) + chunk(b"IEND", b""))


results = []
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    png(base / "map.png")
    (base / "tree.obj").write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nv 1 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nvt 1 1\nusemtl bark\nf 1/1 2/2 3/3\nusemtl leaf\nf 2/2 4/4 3/3\n")
    channels = ("Color", "Normal", "Gloss", "Opacity", "Metallic", "Specular", "SubsurfaceColor", "SubsurfaceAmount")
    maps = "".join(f'<Map Name="{c}" File="map.png"/>' for c in channels)
    source = base / "tree.stmat"
    source.write_text(f'<Materials Mesh="tree.obj"><Material Name="bark"><Map Name="Color" Value=".4"/><Map Name="AO" Value=".7"/></Material><Material Name="leaf" TwoSided="1" VertexOpacity="1">{maps}</Material></Materials>')
    camera = hou.node("/obj").createNode("cam", "bridge_test_camera")
    existing_output = hou.node("/out").createNode("arnold", "existing_user_render")
    existing_output.parm("ar_AA_samples").set(6)
    for renderer in ("arnold", "redshift"):
        request = make_request(source, renderer, {"scale": .01, "normal_flip_y": True})
        filename = base / "tree.bridge.json"
        filename.write_text(json.dumps(request))
        try:
            outputs_before = set(hou.node("/out").children())
            result = import_package(filename)
            assert result["primitives"] == 2, result
            root = hou.node(result["root"])
            geo = next(n for n in root.children() if n.type().name() == "geo")
            assigned = set(geo.displayNode().geometry().primStringAttribValues("shop_materialpath"))
            assert assigned == set(result["materials"].values()), assigned
            assert all(path.startswith("/mat/tree_" + renderer + "_") for path in result["materials"].values())
            assert existing_output.parm("ar_AA_samples").eval() == 6
            if renderer == "arnold":
                output = hou.node(result["render_output"])
                assert output.parent().path() == "/out" and output.type().name() == "arnold"
                assert output.parm("vobject").eval() == result["root"] + "/*"
                assert output.parm("camera").eval() == camera.path()
                duplicate = import_package(filename)
                assert duplicate["render_output"] != result["render_output"]
                assert set(duplicate["materials"].values()).isdisjoint(result["materials"].values())
                hou.node(duplicate["root"]).destroy()
                hou.node(duplicate["render_output"]).destroy()
                for path in duplicate["materials"].values():
                    hou.node(path).destroy()
            else:
                output = hou.node(result["render_output"])
                assert output.type().name() == "Redshift_ROP"
                assert output.parm("RS_objects_candidate").eval() == result["root"] + "/*"
                assert output.parm("RS_renderCamera").eval() == camera.path()
                assert set(hou.node("/out").children()) == outputs_before | {output}
            assert root.parm("scale").eval() == .01
            leaf = hou.node(result["materials"]["leaf"])
            surface = leaf.node("surface")
            assert surface.parm("thin_walled" if renderer == "arnold" else "refr_thin_walled").eval() == 1
            assert leaf.node("vertex_opacity").parm("attribute").eval() == "Alpha"
            assert leaf.node("opacity_times_vertex") is not None
            assert leaf.node("Normal").parm("color_space" if renderer == "arnold" else "tex0_colorSpace").evalAsString() == "Raw"
            results.append({"renderer": renderer, "passed": True, "primitives": 2, "materials": 2})
            root.destroy()
            if result["render_output"]:
                hou.node(result["render_output"]).destroy()
            for path in result["materials"].values():
                hou.node(path).destroy()
        except Exception as error:
            results.append({"renderer": renderer, "passed": False, "error": str(error)})
    # Unmatched assignments must fail and leave no bridge subnet behind.
    source.write_text('<Materials Mesh="tree.obj"><Material Name="unknown_a"/><Material Name="unknown_b"/></Materials>')
    filename.write_text(json.dumps(make_request(source, "arnold", {})))
    before = set(n.path() for n in hou.node("/obj").children())
    materials_before = set(hou.node("/mat").children())
    outputs_before = set(hou.node("/out").children())
    try:
        import_package(filename)
        raise AssertionError("Unmatched materials were silently accepted")
    except RuntimeError:
        assert set(n.path() for n in hou.node("/obj").children()) == before
        assert set(hou.node("/mat").children()) == materials_before
        assert set(hou.node("/out").children()) == outputs_before
        results.append({"check": "rollback_on_unmatched_material", "passed": True})
    # Exercise standalone-to-Houdini transport and structured error response.
    import bridge.receiver as receiver
    receiver.INBOX = base / "queue"
    receiver.INBOX.mkdir()
    receiver.atomic_json(receiver.INBOX / "test.pending.json", make_request(source, "redshift", {}))
    receiver.process_one()
    response = json.loads((receiver.INBOX / "test.result.json").read_text())
    assert response["ok"] is False and "Unmatched" in response["error"]
    assert not list(receiver.INBOX.glob("*.pending.json"))
    assert not list(receiver.INBOX.glob("*.active.json"))
    results.append({"check": "local_queue_error_delivery", "passed": True})
report = Path(__file__).resolve().parents[1] / "verification.json"
report.write_text(json.dumps({"houdini": hou.applicationVersionString(), "results": results}, indent=2))
print(report.read_text())
if not all(r["passed"] for r in results):
    sys.exit(1)
