"""Official saved-SPM command-line export and local Send/Update transport."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
from .package import make_request

ROOT = Path(__file__).resolve().parents[1]


def discover_modeler():
    candidates = []
    if os.environ.get('SPEEDTREE_MODELER'):
        candidates.append(Path(os.environ['SPEEDTREE_MODELER']))
    bases = [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'SpeedTree']
    if os.name == 'nt':
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        bases += [Path(chr(65 + i) + ':/') for i in range(26) if mask & (1 << i)]
    for base in bases:
        if base.is_dir():
            candidates += sorted(base.glob('SpeedTree Modeler*/win64/SpeedTree_Modeler.exe'), reverse=True)
    return next((str(p) for p in candidates if p.is_file()), '')


def asset_identity(project):
    return hashlib.sha256(os.path.normcase(str(Path(project).resolve())).encode('utf-8')).hexdigest()


def export_project(executable, project, cache, preset=None, timeout=180):
    executable, project = Path(executable), Path(project).resolve()
    if not executable.is_file():
        raise ValueError('Select the SpeedTree Modeler executable')
    if project.suffix.lower() != '.spm' or not project.is_file():
        raise ValueError('Save the tree as .spm in SpeedTree first')
    directory = Path(cache) / asset_identity(project) / uuid.uuid4().hex
    directory.mkdir(parents=True)
    mesh = directory / 'tree.obj'
    options = directory / 'export.ini'
    if preset:
        text = Path(preset).read_text(encoding='utf-8-sig')
        lines = text.splitlines()
        lines = ['Filetype=Wavefront OBJ (*.obj)' if line.startswith('Filetype=') else line for line in lines]
        options.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    else:
        options.write_text('[General]\nType=VFX\nFiletype=Wavefront OBJ (*.obj)\nGrouping=Material\nInclude3dGeometry=true\nIncludeBones=false\nAnimationWind=false\nShowSummary=false\nTextureSaveFormat=PNG\nTextureSkipWriting=false\nTransformScale=1\nTransformConvertUnit=Centimeter\nTransformSwapYZ=true\n', encoding='utf-8')
    startup = None
    if os.name == 'nt':
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    command = [str(executable), '-export', str(mesh), str(project), '-export_options', str(options)]
    environment = dict(os.environ)
    # Houdini's Qt paths/platform must not be inherited by the standalone Modeler.
    for key in ('QT_QPA_PLATFORM', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
                'QML_IMPORT_PATH', 'QML2_IMPORT_PATH'):
        environment.pop(key, None)
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=timeout, startupinfo=startup, env=environment)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('SpeedTree export timed out; no update was sent to Houdini') from error
    output = (process.stdout + process.stderr).decode('utf-8', errors='replace')
    (directory / 'export.log').write_text(output, encoding='utf-8')
    if process.returncode or not mesh.is_file() or not mesh.with_suffix('.stmat').is_file():
        raise RuntimeError('SpeedTree export failed (exit code {}). Log: {}\nCommand-line export requires a Pro or Enterprise license.\n'.format(process.returncode, directory / 'export.log') + output[-3000:])
    return mesh.with_suffix('.stmat')


def current_session(inbox, max_age=5):
    try:
        session = json.loads((Path(inbox) / 'session.json').read_text(encoding='utf-8'))
        age = time.time() - session['heartbeat']
        if not 0 <= age <= max_age or not session.get('session_id'):
            raise ValueError('Expired session')
        return session
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError('Connect Live Bridge in the intended Houdini session first') from error


def send_project(executable, project, renderer, settings, inbox=None, cache=None, preset=None):
    inbox = Path(inbox) if inbox else ROOT / 'queue'
    session = current_session(inbox)
    source = export_project(executable, project, cache or ROOT / 'live_cache', preset)
    # Never send an export to a different scene if the user switched HIPs while exporting.
    if current_session(inbox)['session_id'] != session['session_id']:
        raise RuntimeError('Houdini scene changed during export; resend to the intended scene')
    request = make_request(source, renderer, settings)
    request['target_session'] = session['session_id']
    request['live'] = {'asset_id': asset_identity(project), 'project': str(Path(project).resolve()),
                       'revision': source.parent.name}
    job_id = str(time.time_ns()) + '_' + uuid.uuid4().hex
    job = inbox / (job_id + '.pending.json')
    temporary = job.with_suffix('.tmp')
    temporary.write_text(json.dumps(request), encoding='utf-8')
    temporary.replace(job)
    return job_id
