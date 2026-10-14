# Live transfer inside Houdini

Live transfer is integrated into the original Houdini-owned Qt plugin window, with the same renderer profiles, scene options, styling and localization. No companion application or Connect Live Bridge step is required.

1. Restart Houdini after updating Bridge, then open **SpeedTree Bridge → Open SpeedTree Bridge** or its shelf button.
2. Browse for one saved `.spm`; the Live transfer controls are available on the Export tab. Select the Modeler executable if discovery did not find it.
3. Choose your renderer and initial scale/scene options. Export uses centimeters; `.01` usually converts them to Houdini units. Verify the scale in your project.
4. Click **Import / Update tree**, or enable **Update after saving in SpeedTree**. Subsequent Ctrl+S saves in Modeler trigger export and update. Enabling automatic mode also sends the current saved file.

Only the external export runs in a worker thread; changes to the current scene run on Houdini's UI thread. Closing the window or loading/clearing a HIP turns off automatic updates and prevents a late export from modifying another scene. Errors disable automatic mode and appear in Details.

Tree transforms, existing source/assignment nodes, downstream user nodes, shader edits, camera, lights and render output are retained. Unchanged managed texture paths refresh; new material names get new shaders. Existing shader topology and constants are not rebuilt. Initial scale and scene controls do not overwrite subsequent user edits. Ordinary `.stmat` selection retains the manual and batch import workflow.

This exports the saved `.spm`, not unsaved Modeler state, and requires Pro/Enterprise command-line export in the installed Modeler. It adds no native SpeedTree toolbar button. Static OBJ geometry is supported; wind, animation and live FBX are not implemented. Solaris / Karma supports live updates of the linked USD stage. Keep the same renderer for a linked tree. The full project path identifies the tree; renamed/moved projects start another link and duplicated links are rejected.

Immutable revisions live in `live_cache` under the permanent plugin directory. Preserve revisions referenced by saved HIP files or Undo and keep that cache with the scene. Automatic cache cleanup and dependency packaging are not provided.

Tests cover the native Qt controls, background export, main-thread scene changes, repeated updates, save watcher, scene/close safety and a real Modeler sample export. They do not replace testing your working project and visual output in the interactive applications.

[Detailed Russian guide](LIVE_BRIDGE.ru.md)
