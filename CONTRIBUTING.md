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
```

`houdini_smoke.py` and `scene_smoke.py` require both Arnold and Redshift. `native_ui_smoke.py` uses an available renderer; `legacy_redshift_smoke.py` requires the legacy Redshift Material node. Qt tests use an offscreen window and do not replace interactive visual QA. Integration tests run in their own process; do not run scene-mutating tests inside your production scene.

Test files create temporary synthetic meshes. Diagnostic reports are ignored by Git. Test coverage of an adapter does not imply that the corresponding old Houdini installation has been tested.

## Report an issue

Include the exact Houdini build, Python version, renderer / integration version, OS, selected options, reproduction steps and relevant diagnostic text. Remove private paths from logs. Share only assets you are licensed to distribute. A small synthetic export is preferable.

## Scope

The current plugin targets exported SpeedTree OBJ / FBX plus `.stmat`. Planned areas include broader UDIM / texture-channel handling, OCIO configuration awareness and preserving user edits during tree updates. Do not describe a new renderer / version as verified until it has been run and checked.
