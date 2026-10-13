# SpeedTree Bridge for Houdini

[Русский](README.ru.md) · [Installation](docs/INSTALLATION.md) · [Compatibility](COMPATIBILITY.md)

<img src="houdini/config/Icons/speedtree_bridge.png" width="100" alt="SpeedTree Bridge">

A free Houdini-native plugin for importing SpeedTree exports and building Arnold / Redshift materials, with optional camera and lighting setup.

**Version 0.2.0 — community preview.** Tested on Houdini 21.0.596 and 22.0.368. Adapters target Houdini 19–22; Houdini 19/20 have not been tested end to end. Export mesh, `.stmat` and textures from SpeedTree first. The plugin does not open `.spm` projects directly.

![Plugin interface](assets/ui_preview.png)

## Features

- OBJ / FBX import using `.stmat`, preserving material assignments.
- Arnold Standard Surface, Redshift Standard Material and a legacy Redshift Material adapter.
- Color, opacity, normal, gloss / roughness, specular, metallic, AO and subsurface maps.
- Gloss-to-roughness conversion and vertex opacity through `Alpha`.
- Materials in `/mat`; automatic Arnold output in `/out`.
- Optional camera framing with three views; camera follows the tree's transforms.
- Optional soft environment light and sunlight for the selected renderer.
- Compact Houdini-owned window, separate renderer profiles and expandable diagnostics.
- English, Russian, Japanese, Simplified Chinese and Traditional Chinese UI.
- Free use and modification under the [MIT license](LICENSE).

## Quick start — Windows

1. Download **Code → Download ZIP** and extract to a permanent writable folder.
2. From that folder, run:

   ```powershell
   python install_houdini.py --version 21.0
   ```

   Choose `19.0`, `19.5`, `20.0`, `20.5`, `21.0` or `22.0`. Use `--all` to install for all six preference folders.
3. Restart Houdini. Open **SpeedTree Bridge → Open SpeedTree Bridge** in the main menu or use the shelf button.
4. Select `.stmat`, choose the renderer, scale and scene options, then click **Import tree**.

The native window needs no external Python packages. Installation also works with Houdini's bundled Python or a manually created package JSON. See the [detailed installation guide](docs/INSTALLATION.md).

## Requirements and compatibility

Python 3.7+ and an Arnold / Redshift integration compatible with your exact Houdini build. Windows is the tested platform. Python 2.7 builds are unsupported. Houdini editions that cannot run third-party renderers retain those restrictions.

| Houdini | Status |
|---|---|
| 19.0 / 19.5 | Python 3 / Qt 5 adapters; not tested end to end |
| 20.0 / 20.5 | Python 3 / Qt 5 adapters; not tested end to end |
| 21.0.596 | UI, import and Arnold / Redshift materials tested |
| 22.0.368 | UI and Redshift import tested; Arnold not tested on this build |

Bridge is free; Houdini, SpeedTree, render integrations and their licenses are not included. Read [COMPATIBILITY.md](COMPATIBILITY.md) before treating an untested version as production-ready.

## Workflow

Export OBJ / FBX, `.stmat` and textures together. Missing files block import. Scale is explicit, not inferred from units. Each import creates unique node names and preserves existing scene nodes; reimporting is not an in-place update.

Materials, camera, lights and render output are separate from the tree: deleting the tree manually does not delete them. Imports are grouped for Undo. A newly requested camera is connected to Arnold output. Rendering is not started automatically. Redshift output is not created yet.

Soft lighting is a neutral dome without an HDRI. Assign your own HDRI manually if needed. UI language is independent of Houdini; renderer diagnostics retain their original wording.

## Current limits

- No direct SpeedTree export, batch import or non-destructive tree updates.
- No Alembic, wind, animation, Solaris / USD or displacement.
- Height / Custom / Custom2 are retained as metadata, not connected to shading.
- Opacity expects a separate RGB mask; packed channels and alpha-only textures are unsupported.
- Basic UDIM file validation and path handling; full UDIM workflows need more testing.
- Color textures use sRGB, data maps use Raw; custom OCIO configurations are not analyzed automatically.
- Node tests do not guarantee visual parity across renderer versions.

## Development and support

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Houdini integration tests use `hython`. See [CONTRIBUTING.md](CONTRIBUTING.md). For an Issue, include exact Houdini / renderer versions, reproduction steps and relevant diagnostics. Only share scenes and textures you have permission to distribute.

This is an independent project, not an official SideFX, SpeedTree, Autodesk or Maxon product. The icon was generated with imagegen; its prompt is recorded in [assets/icon_prompt.txt](assets/icon_prompt.txt).
