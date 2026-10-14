# Changelog

## 0.5.2 — 2026-10-14

- Apply the SpeedTree OBJ Z-up to Houdini Y-up correction (-90 degrees around X) once at initial import, before camera framing and Solaris translation. FBX retains Houdini's importer axis conversion.
- Preserve existing tree transforms on live updates; do not accumulate the rotation or overwrite manually corrected scenes.

## 0.5.1 — 2026-10-14 (unreleased)

- Frame cameras against transformed world-space geometry with the actual image aspect ratio, fitting all bounding corners and computing matching clipping/focus distances.
- Detach cameras from scaled/rotated tree objects to prevent inherited camera roll/scale after mesh orientation changes; size camera/light icons relative to the tree.
- Use independent camera paths in Solaris and repair older USD render camera targets when reframing.
- Allow the reframe command to operate on a selected tree or camera, preserving mesh transforms, materials and node paths. Camera edits remain unchanged during live updates; explicitly reframe after tree transform/shape changes.

## 0.5.0 — 2026-10-14 (unreleased)

- Separate OBJ/Solaris workflow from the Arnold, Redshift and Karma renderer selection in the native window.
- Add Arnold USD shaders and Arnold Render Settings, plus Redshift USD material builders and renderer settings. Automatically create the matching USD Render ROP in `/out`.
- Persist independent Solaris resolution, samples and image paths for each renderer; use Camera AA for Arnold and unified maximum samples for Redshift. Retain Karma CPU/XPU settings.
- Detect installed Hydra delegates and reject unsupported renderer/workflow combinations before creating scene nodes.
- Preserve linked stage/output nodes and user shader/SOP edits during Arnold/Redshift Solaris live updates, including rollback on failure.
- Validate Arnold EXR rendering, both vendor USD bindings/settings and native UI/live updates. Redshift image rendering still requires additional validation; only the listed renderer adapters are included.

## 0.4.0 — 2026-10-14 (unreleased)

- Add Solaris / Karma as a third renderer mode, with MaterialX standard-surface shaders, packed/alpha texture channels, normal strength/Y flip, vertex opacity, AO and subsurface maps.
- Create an isolated `/stage` subnet importing the linked geometry, assigned materials, camera and lights, followed by Karma Render Settings. Create a Karma-configured USD Render ROP in `/out`.
- Configure Karma CPU/XPU, image resolution, samples and output path. Repeated live sends keep the same stage and output; explicit UI render-setting changes are applied while unchanged settings retain edits made directly on LOPs.
- Reorganize the native window into General, Materials, Render and Export tabs. Keep independent renderer profiles and five-language controls.
- Add cache directory, optional SpeedTree INI preset and export timeout controls for saved-project exports.
- Verify cooked USD material bindings and live geometry updates on Houdini 21/22, plus small Karma CPU renders. XPU test status is recorded in the Solaris guide.

## 0.3.1 — 2026-10-14 (unreleased)

- Integrate live `.spm` export and geometry updates into the original Houdini-owned Qt window, using the same renderer profiles, scene options, styling and localization.
- Keep manual `.stmat` import and batch workflows; selecting `.spm` shows live controls and changes the primary action to Import / Update.
- Run only the external export in a worker thread; apply scene changes on Houdini's UI thread. The native workflow needs no standalone window or queue connection.
- Stop automatic updates on close or HIP load/clear and reject late export results after the target scene changes.
- Isolate the external Modeler from Houdini's Qt plugin paths and platform settings when launching the exporter.
- Keep the old companion implementation in development sources, but exclude its launchers and UI from the installation ZIP.

## 0.3.0 — 2026-10-14 (unreleased)

- Add a Send / Update companion for saved SpeedTree projects using the Modeler's command-line exporter.
- Add automatic updates after `.spm` saves, with a debounce and one in-flight request.
- Keep a stable Houdini OBJ object, source and material assignment nodes on repeated sends; preserve user transforms, downstream nodes, existing shader edits and scene setup.
- Refresh unchanged managed texture paths, create shaders for new material names and roll back a failed update.
- Target a connected Houdini scene with a heartbeat and connection identity; reject requests after a HIP load/clear or reconnection.
- Add Connect / Disconnect Live Bridge menu actions and expose connection shelf buttons.
- Export to immutable cache revisions, validate before submission and retain previous revisions for Undo and saved HIP references.

The companion exports the saved `.spm` file. A native SpeedTree toolbar integration and access to unsaved Modeler state are not implemented. Live geometry uses static OBJ; wind/animation, automatic rebuild of existing shaders and switching the renderer of a linked tree are outside this release.

## 0.2.1 — 2026-10-14 (unreleased)

- Create a Redshift ROP in `/out`, restrict its object selection to the imported tree and connect the requested camera.
- Show the selected renderer in import diagnostics.
- Select explicit RGB / R / G / B / A components in texture maps, including alpha opacity combined with vertex opacity, packed AO and gloss inversion.
- Select multiple `.stmat` files in the native file picker; report each import separately and continue after a failed item.
- Normalize relative Windows export paths for portable file lookup.
- Use the native macOS Houdini preferences location; add a POSIX standalone launcher.
- Provide a reproducible installable ZIP builder that excludes local settings, scenes and test results.
- Add troubleshooting, an implementation roadmap and structured issue templates.
- Extend unit-test CI to Windows and macOS, retaining Python 3.7 syntax coverage on Linux.

## 0.2.0 — community preview

- Houdini-native UI with English, Russian, Japanese and Chinese localization.
- Python 3 and Qt 5 / Qt 6 adapters targeting Houdini 19–22.
- Arnold, Redshift Standard Material and legacy Redshift Material adapters.
- Optional camera framing, dome and sunlight; Arnold render output.
- OBJ / FBX material assignment, scalar and texture maps, AO and vertex opacity.

Historical publication dates and GitHub release tags are not recorded here until verified.
