import tempfile
import unittest
from pathlib import Path
from bridge.package import read_export, make_request


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
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

    def test_literal_brackets_and_udim_files(self):
        (self.directory / 'leaf[oak].1001.png').touch()
        data = read_export(self.write('<Material Name="leaf"><Map Name="Color" File="leaf[oak].&lt;UDIM&gt;.png"/></Material>'))
        self.assertFalse(data['warnings'])
        (self.directory / 'directory.png').mkdir()
        data = read_export(self.write('<Material Name="leaf"><Map Name="Color" File="directory.png"/></Material>'))
        self.assertTrue(data['warnings'])

    def test_packed_channels_and_alpha(self):
        (self.directory / 'packed.png').touch()
        path = self.write('<Material Name="leaf"><Map Name="Opacity" File="packed.png" Channel="a"/><Map Name="Roughness" File="packed.png" Channel="g"/></Material>')
        maps = make_request(path, 'redshift', {})['materials'][0]['maps']
        self.assertEqual(maps['Opacity']['channel'], 'a')
        self.assertEqual(maps['Roughness']['channel'], 'g')
        for name, component in (('Opacity', 'z'), ('Normal', 'r')):
            with self.subTest(name=name), self.assertRaises(ValueError):
                read_export(self.write('<Material Name="leaf"><Map Name="{}" File="packed.png" Channel="{}"/></Material>'.format(name, component)))

    def test_duplicate_material(self):
        with self.assertRaises(ValueError):
            read_export(self.write('<Material Name="x"/><Material Name="x"/>'))

    def test_windows_relative_paths(self):
        (self.directory / 'textures').mkdir()
        (self.directory / 'textures' / 'leaf.png').touch()
        data = read_export(self.write('<Material Name="leaf"><Map Name="Color" File="textures\\leaf.png"/></Material>'))
        self.assertFalse(data['warnings'])
        self.assertEqual(data['materials'][0]['maps']['Color']['file'], (self.directory / 'textures' / 'leaf.png').as_posix())

    def test_vertex_opacity_can_be_submitted(self):
        request = make_request(self.write('<Material Name="leaf" VertexOpacity="1"/>'), "arnold", {})
        self.assertTrue(request["materials"][0]["vertex_opacity"])
        self.assertFalse(request["warnings"])

    def test_invalid_settings(self):
        path = self.write('<Material Name="x"/>')
        for settings in ({"scale": 0}, {"roughness": 2}, {"normal_strength": -1}, {"scale": "nan"}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                make_request(path, "arnold", settings)

    def test_karma_settings(self):
        path = self.write('<Material Name="bark"/>')
        settings = make_request(path, 'karma', {'solaris': {'engine': 'xpu', 'resolution_x': 1920, 'samples': 64}})['settings']['solaris']
        self.assertEqual(settings['engine'], 'xpu')
        self.assertEqual(settings['resolution_x'], 1920)
        self.assertEqual(settings['samples'], 64)
        for options in ({'engine': 'invalid'}, {'resolution_y': 0}, {'samples': 'nan'}, {'samples': 1.5}, {'output_image': ''}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                make_request(path, 'karma', {'solaris': options})

    def test_missing_mesh(self):
        with self.assertRaises(ValueError):
            read_export(self.write('<Material Name="x"/>', "missing.fbx"))

    def test_solaris_renderer_context(self):
        path = self.write('<Material Name="bark"/>')
        for renderer in ('arnold', 'redshift'):
            self.assertEqual(make_request(path, renderer, {})['settings']['context'], 'obj')
            data = make_request(path, renderer, {'context': 'solaris'})['settings']
            self.assertEqual(data['context'], 'solaris')
            self.assertEqual(data['solaris']['samples'], 3 if renderer == 'arnold' else 128)
        for renderer, options in (('karma', {'context': 'obj'}), ('arnold', {'context': 'unknown'}),
                                  ('arnold', {'context': 'solaris', 'solaris': {'samples': 128}})):
            with self.subTest(renderer=renderer, options=options), self.assertRaises(ValueError):
                make_request(path, renderer, options)


if __name__ == "__main__":
    unittest.main()
