# Checklist status

Implementation status for the supplied SpeedTree Bridge checklist. A code change or CI configuration is not evidence of a successful render or a test on an unavailable platform.

## Priority 1

- [ ] Publish a version tag and GitHub Release after reviewing the release candidate.
- [x] Build an installable ZIP with `python tools/build_release.py`; attaching it to a published release remains pending.
- [x] Add CHANGELOG.md.
- [ ] Record a real SpeedTree export → Houdini import → material and camera demo.
- [x] Add troubleshooting in both README languages.

## Priority 2

- [x] Update a stable live OBJ object on Send / Update, preserving user nodes and shader edits with rollback. Ordinary manual reimport still creates independent objects.
- [x] Support explicit packed texture channels and alpha-only opacity through `Channel="r|g|b|a"` in `.stmat`; no automatic channel inference.
- [x] Create Redshift output in `/out`, with object selection and camera connection.
- [ ] Connect Height as opt-in displacement with explicit scale; define Custom / Custom2 destinations.
- [x] Batch import from the native file picker, with per-tree diagnostics. Failed items roll back; successful items remain and later files are attempted.

## Priority 3

- [ ] Verify Arnold on Houdini 22.0.368: compatible HtoA is unavailable locally.
- [x] Mark Houdini 19/20 as unverified and unsupported for production until end-to-end testing.
- [ ] Validate Linux/macOS in Houdini. POSIX launcher and macOS preferences path are implemented; platform CI covers only pure Python tests.
- [ ] Full UDIM shader/render test; current tests cover file lookup only.
- [ ] Custom OCIO shader/render verification and configurable color-space selection.
- [x] Run unit tests on push and pull request; configure Windows, Linux and macOS jobs.

## Priority 4

- [ ] Alembic, wind and animation.
- [x] Solaris / USD static geometry, MaterialX shaders and Karma CPU/XPU output, including live updates.
- [x] Export saved SpeedTree projects through the Modeler command line. A native toolbar button and unsaved-state access remain pending.
- [ ] Optional HDRI path on the dome light.

## Priority 5

- [x] Structured bug and feature issue templates.
- [x] Roadmap and known limitations linked from README.
- [ ] Real before/after render screenshots. Existing UI screenshot does not satisfy this item.
- [ ] Add GitHub repository topics: houdini, speedtree, arnold, redshift.
- [ ] Community posts. Prepare a demo and obtain explicit authorization to post before sending messages.

## Release candidate verification

Run unit tests and `tests/redshift_output_smoke.py` using an installed, compatible `hython`. The latter checks output selection, explicit camera connection, preservation of existing output and rollback on assignment failure. It does not render images.

Verified locally on 2026-10-14:

- 15 pure Python unit tests passed, including release ZIP contents and reproducibility, platform preferences, explicit channels, relative Windows paths and literal brackets in UDIM filenames.
- Houdini 21.0.596: Arnold and Redshift import, assignments, output creation, rollback and queue error delivery passed; native UI import passed.
- Houdini 21.0.596: Arnold and Redshift packed-channel, alpha/vertex-opacity, AO and gloss-inversion node tests passed.
- Houdini 22.0.368 / Redshift 2026.9: output and camera/rollback tests, packed-channel tests and native batch import with a failed middle item passed.
- Integration checks created nodes without rendering. No new visual-render, Linux/macOS integration, custom OCIO or Houdini 19/20 compatibility claims are made.

Live Bridge 0.3.0: real SpeedTree 10.2 Mushroom export, local queue delivery and repeated update passed on Houdini 22.0.368 / Redshift (20,953 primitives). Synthetic update/rollback and standalone companion tests passed. Interactive two-application testing on the user project remains pending.

Additional live checks: Arnold on Houdini 21.0.596 preserved geometry/node paths and shader edits and rolled back failures. Qt timer delivery, heartbeat, scene identity changes and stale-job rejection passed in an isolated Qt event loop under Houdini 22.0.368. 21 pure Python unit tests passed.

0.3.1 moves live controls into the original Houdini-owned Qt window. A standalone companion is no longer required. Native worker/main-thread, save watcher, scene/close rejection and manual-mode tests passed on Houdini 22.0.368; existing native/manual UI and five-language tests passed on Houdini 21.0.596.

Real native UI export/update verification passed on Houdini 22.0.368 with SpeedTree 10.2 and Redshift. The external exporter no longer inherits Houdini Qt platform/plugin paths. The rendered native live preview was inspected for clipping and overlap.

0.4.0 verification: Solaris USD geometry, subsets/material bindings, camera, dome/sun and Karma output passed on Houdini 21.0.596 and 22.0.368. Karma CPU generated a small EXR on 21; texture-heavy MaterialX CPU and XPU tests generated EXRs on 22. Packed/alpha maps, normal Y flip and subsurface signals cooked into USD. Synthetic Karma live updates preserved SOP/shader edits and node counts; real SpeedTree 10.2 export from the native window imported/updated the same Karma object. Native tab/settings persistence and original Arnold/Redshift import checks passed. There is no full user-project visual-parity, wind/animation or custom OCIO/UDIM verification.

0.5.0: separate OBJ/Solaris workflow; Arnold and Redshift native USD shaders/settings/output and independent UI profiles. Vendor live updates preserve nodes and user edits with rollback. Arnold EXR passed; Redshift image rendering requires further validation. Additional renderer adapters remain future work.
