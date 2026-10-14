# Installation — Houdini 19–22

[Русский](INSTALLATION.ru.md) · [Project overview](../README.md)

## 1. Check your environment

Use a Python 3 build of Houdini, with Python 3.7 or newer. Target preference folders: `houdini19.0`, `houdini19.5`, `houdini20.0`, `houdini20.5`, `houdini21.0`, `houdini22.0`.

Houdini 21.0.596 and 22.0.368 have been tested. The 19/20 adapters have not been tested end to end. Install an Arnold / Redshift plugin compiled for your exact Houdini build; the Bridge installer does not install a renderer. See [compatibility](../COMPATIBILITY.md).

## 2. Download and extract

On GitHub, open **Releases** and download the latest installable release ZIP. Extract the archive, then move the folder containing `install_houdini.py`, `bridge` and `houdini` to a permanent writable location, for example:

```text
C:\Tools\SpeedTreeHoudiniBridge
```

Do not run from inside the ZIP. Avoid a protected folder such as Program Files. The package points to this folder, so moving it later requires rerunning the installer.

## 3. Install on Windows

### Option A: terminal with Python

Open PowerShell in the extracted project folder. Use your existing Python 3 installation:

```powershell
python install_houdini.py --version 21.0
```

If your Python launcher is `py`, use `py -3 install_houdini.py --version 21.0`. Select the matching version:

| Houdini | Command |
|---|---|
| 19.0 | `python install_houdini.py --version 19.0` |
| 19.5 | `python install_houdini.py --version 19.5` |
| 20.0 | `python install_houdini.py --version 20.0` |
| 20.5 | `python install_houdini.py --version 20.5` |
| 21.0 | `python install_houdini.py --version 21.0` |
| 22.0 | `python install_houdini.py --version 22.0` |

Install for all six preference folders:

```powershell
python install_houdini.py --all
```

The installer uses Windows' configured Documents folder, including OneDrive redirection. It writes only `packages/speedtree_bridge.json`, preserving unrelated packages. An existing Bridge package receives a `.bak` copy if one does not already exist.

For a custom Documents location:

```powershell
python install_houdini.py --version 21.0 --documents "D:\Documents"
```

For the exact preference directory, provide it directly:

```powershell
python install_houdini.py "D:\MyHoudiniPreferences\houdini21.0"
```

### Option B: Houdini's own Python

No separate Python installation is needed. Open Houdini, go to **Windows → Python Source Editor**, paste the following and run it. Replace the path with your extracted folder:

```python
import hou, runpy
installer = runpy.run_path(r"C:/Tools/SpeedTreeHoudiniBridge/install_houdini.py")
print(installer["install"](hou.expandString("$HOUDINI_USER_PREF_DIR")))
```

This installs into the preferences of the currently running Houdini version. Save your scene and restart Houdini afterwards.

### Option C: manual package

In Houdini's Python Shell, find the actual preference directory:

```python
print(hou.expandString("$HOUDINI_USER_PREF_DIR"))
```

Create a `packages` subfolder there if needed. Create `speedtree_bridge.json` containing:

```json
{
  "enable": true,
  "env": [
    {"SPEEDTREE_BRIDGE_ROOT": "C:/Tools/SpeedTreeHoudiniBridge"},
    {"PYTHONPATH": {"value": "$SPEEDTREE_BRIDGE_ROOT", "method": "prepend"}}
  ],
  "path": "$SPEEDTREE_BRIDGE_ROOT/houdini"
}
```

Replace only the project path. Use forward slashes in JSON. The extension must be `.json`, not `.json.txt`. No administrator privileges or changes to Houdini's installation folder are needed.

## 4. Launch

Save the current scene and restart Houdini. Open **SpeedTree Bridge → Open SpeedTree Bridge** from the top menu. A shelf named **SpeedTree Bridge** also provides a button. The window opens on demand, not automatically at startup.

Unavailable renderer tabs are disabled. Check the renderer installation if Arnold or Redshift is missing. The native window uses Houdini's Qt; do not install PySide through pip into Houdini for this plugin.

## 5. Prepare a SpeedTree export

Export OBJ or FBX with its `.stmat` file and textures. Preserve material assignments and use separate, unpacked texture maps for the first test. Keep the exported files together and select `.stmat`, not the mesh, in the Bridge window.

Pick the renderer and scale. Units are not inferred automatically. Choose camera and lighting checkboxes, then click **Import tree**. Missing mesh / textures stop the operation. Use **Details** for diagnostics. For Arnold, inspect the new output in `/out` and start rendering yourself.

## 6. Update or move the plugin

Save your scene and close Houdini. Extract the new version into the same project folder, preserving your local `settings.json` if you want to keep profiles. If using a new folder, rerun installation to update the package path. Restart Houdini.

## 7. Uninstall

Close Houdini and remove only `speedtree_bridge.json` from the selected preference folder's `packages` directory. Repeat for other versions if installed with `--all`. Restart Houdini. Removing the package does not delete scenes or nodes previously created in them.

## Troubleshooting

| Problem | Check |
|---|---|
| No menu after restarting | Actual `$HOUDINI_USER_PREF_DIR`, package filename and JSON syntax, extracted folder path |
| Menu is present, shelf is hidden | Use the menu; shelf display depends on the active desktop |
| Import cannot find `bridge` | Package `PYTHONPATH` and project folder containing `bridge/__init__.py` |
| Both renderer tabs disabled | Exact-build Arnold / Redshift installation and supported Houdini edition |
| Missing mesh / textures | File paths referenced by `.stmat`; do not move textures independently |
| Camera needs reframing | Select the Bridge camera, then **SpeedTree Bridge → Reframe Selected Camera** |
| Viewport is correct, Render View looks upside down | Hover over Render View and press `H` to reset its display before changing geometry |
| Access denied when saving profiles | Keep the project folder writable by your user |

macOS / Linux have not been validated. If testing them, use the actual `$HOUDINI_USER_PREF_DIR` and the manual package method rather than assuming Windows-style Documents paths.
