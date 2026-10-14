# Contributing

Small, reproducible changes and bug reports are welcome. Keep the plugin usable with Python 3.7 syntax and both Qt 5 / Qt 6 adapters. Do not add vendor binaries, trees, textures, credentials or machine-specific configuration.

## Tests without Houdini

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Houdini integration tests

Run from the repository root with a supported `hython` and the appropriate renderer integrations installed:

```powershell
hython tests/houdini_smoke.py
hython tests/native_ui_smoke.py
hython tests/localized_ui_smoke.py
hython tests/scene_smoke.py
hython tests/legacy_redshift_smoke.py
hython tests/redshift_output_smoke.py
hython tests/texture_channels_smoke.py
hython tests/batch_ui_smoke.py
```

`houdini_smoke.py` and `scene_smoke.py` require both Arnold and Redshift. `native_ui_smoke.py` uses an available renderer; `legacy_redshift_smoke.py` requires the legacy Redshift Material node. Qt tests use an offscreen window and do not replace interactive visual QA. Integration tests run in their own process; do not run scene-mutating tests inside your production scene.

Test files create temporary synthetic meshes. Diagnostic reports are ignored by Git. Test coverage of an adapter does not imply that the corresponding old Houdini installation has been tested.

## Report an issue

Include the exact Houdini build, Python version, renderer / integration version, OS, selected options, reproduction steps and relevant diagnostic text. Remove private paths from logs. Share only assets you are licensed to distribute. A small synthetic export is preferable.

## Scope

The current plugin targets exported SpeedTree OBJ / FBX plus `.stmat`. Planned areas include broader UDIM / texture-channel handling, OCIO configuration awareness and preserving user edits during tree updates. Do not describe a new renderer / version as verified until it has been run and checked.

Build the distributable ZIP with `python tools/build_release.py`. Its allowlist excludes settings, queues, scenes, tests and local diagnostic results. Review [ROADMAP.md](ROADMAP.md) before publishing a release; platform CI does not run Houdini.

Live update checks: `hython tests/live_update_smoke.py redshift` or `hython tests/live_update_smoke.py arnold`. Real export: `hython tests/live_export_smoke.py MODELER_EXE SAMPLE_SPM`. Companion: `python tests/live_companion_smoke.py` requires a display and Tkinter.

Native live UI: `hython tests/native_live_ui_smoke.py`. Real native export: `hython tests/native_live_export_smoke.py MODELER_EXE SAMPLE_SPM`.

Solaris checks: `hython tests/solaris_smoke.py`, `hython tests/solaris_smoke.py --render`, `hython tests/materialx_texture_smoke.py --render`, `hython tests/materialx_texture_smoke.py --xpu --render`, `hython tests/solaris_ui_smoke.py` and `hython tests/live_update_smoke.py karma`. Render tests use tiny synthetic images and clear their isolated test HIP before releasing texture-cache files; never run them in a production scene.
