import tempfile
import unittest
from pathlib import Path
from bridge.package import read_export, make_request


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.directory / "tree.obj").write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")

    def write(self, body, mesh="tree.obj"):
        path = self.directory / "tree.stmat"
        path.write_text(f'<Materials Mesh="{mesh}">{body}</Materials>')
        return path

    def test_constants_and_relative_paths(self):
        package = read_export(self.write('<Material Name="bark"><Map Name="Color" ColorR=".2" ColorG=".3" ColorB=".4"/></Material>'))
        self.assertEqual(package["materials"][0]["maps"]["Color"]["value"], [.2, .3, .4])
        self.assertEqual(package["mesh"], (self.directory / "tree.obj").as_posix())

    def test_missing_texture_blocks_request(self):
        path = self.write('<Material Name="leaf"><Map Name="Opacity" File="missing.png"/></Material>')
        self.assertTrue(read_export(path)["warnings"])
        with self.assertRaises(ValueError):
            make_request(path, "arnold", {})

    def test_udim(self):
        (self.directory / "leaf.1001.png").touch()
        package = read_export(self.write('<Material Name="leaf"><Map Name="Color" File="leaf.&lt;UDIM&gt;.png"/></Material>'))
        self.assertFalse(package["warnings"])

    def test_duplicate_material(self):
        with self.assertRaises(ValueError):
            read_export(self.write('<Material Name="x"/><Material Name="x"/>'))

    def test_vertex_opacity_can_be_submitted(self):
        request = make_request(self.write('<Material Name="leaf" VertexOpacity="1"/>'), "arnold", {})
        self.assertTrue(request["materials"][0]["vertex_opacity"])
        self.assertFalse(request["warnings"])

    def test_invalid_settings(self):
        path = self.write('<Material Name="x"/>')
        for settings in ({"scale": 0}, {"roughness": 2}, {"normal_strength": -1}, {"scale": "nan"}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                make_request(path, "arnold", settings)

    def test_missing_mesh(self):
        with self.assertRaises(ValueError):
            read_export(self.write('<Material Name="x"/>', "missing.fbx"))


if __name__ == "__main__":
    unittest.main()
