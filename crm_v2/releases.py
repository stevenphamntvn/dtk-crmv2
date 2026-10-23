"""Code-only release packaging and transactional local updates."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import shutil
import tempfile
import zipfile

ROOT_FILES = {'streamlit_app.py', 'requirements.txt', 'run.bat', 'update.bat',
              '.streamlit/config.toml'}
DATA_CODE = {'Data/crm_app.py', 'Data/customer_data.py', 'Data/sync_report.py'}


def allowed(name):
    path = PurePosixPath(name)
    if '\\' in name or path.is_absolute() or '..' in path.parts or ':' in name:
        return False
    if name in ROOT_FILES | DATA_CODE:
        return True
    return (len(path.parts) > 1 and (
        (path.parts[0] == 'crm_v2' and path.suffix in {'.py', '.js', '.css'}) or
        (path.parts[0] == 'tools' and path.name in {'release.py', 'update.py'}) or
        (path.parts[:2] == ('assets', 'icons') and path.suffix in {'.png', '.ico', '.svg'})
    ) and '__pycache__' not in path.parts)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(root, destination, version):
    root, destination = Path(root), Path(destination)
    payload = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
               if p.is_file() and allowed(p.relative_to(root).as_posix())}
    manifest = {'version': version, 'files': {name: digest(data) for name, data in payload.items()}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in payload.items():
            archive.writestr(name, data)
        archive.writestr('release.json', json.dumps(manifest, indent=2))
    return digest(destination.read_bytes())


def inspect_package(package, expected_sha256=None):
    package = Path(package)
    if expected_sha256 and digest(package.read_bytes()) != expected_sha256.lower():
        raise ValueError('SHA256 của gói cập nhật không đúng.')
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or 'release.json' not in names:
            raise ValueError('Gói cập nhật thiếu manifest hoặc có file trùng.')
        if sum(i.file_size for i in archive.infolist()) > 50_000_000:
            raise ValueError('Gói cập nhật quá lớn.')
        manifest = json.loads(archive.read('release.json'))
        files = manifest['files']
        if not files or set(files) != set(names) - {'release.json'}:
            raise ValueError('Danh sách file không đúng manifest.')
        for name, sha in files.items():
            if not allowed(name) or digest(archive.read(name)) != sha:
                raise ValueError(f'File không hợp lệ: {name}')
        if 'streamlit_app.py' not in files or 'crm_v2/__init__.py' not in files:
            raise ValueError('Gói thiếu mã nguồn chính.')
        return manifest


def apply(root, package, expected_sha256=None):
    root = Path(root).resolve()
    manifest = inspect_package(package, expected_sha256)
    staging = root / '.updates'
    staging.mkdir(exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='rollback-', dir=staging))
    changed = []
    with zipfile.ZipFile(package) as archive:
        try:
            for name in manifest['files']:
                target = root / name
                # Resolve symlinks before any write, even though package paths are allowlisted.
                if not target.resolve().is_relative_to(root):
                    raise ValueError('Đường dẫn nằm ngoài thư mục CRM V2.')
                saved = backup / name
                existed = target.exists()
                if existed:
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, saved)
                target.parent.mkdir(parents=True, exist_ok=True)
                changed.append((target, saved, existed))
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as f:
                    temp = Path(f.name)
                    f.write(archive.read(name))
                try:
                    temp.replace(target)
                finally:
                    temp.unlink(missing_ok=True)
        except Exception:
            for target, saved, existed in reversed(changed):
                if existed:
                    shutil.copy2(saved, target)
                else:
                    target.unlink(missing_ok=True)
            raise
    (backup / 'installed.json').write_text(json.dumps(manifest), encoding='utf-8')
    return manifest['version'], backup
