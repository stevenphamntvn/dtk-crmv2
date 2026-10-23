from pathlib import Path
import json
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from crm_v2.releases import allowed, apply, build, inspect_package


class ReleaseTests(unittest.TestCase):
    def test_failed_update_restores_files_already_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'app'
            (root / 'crm_v2').mkdir(parents=True)
            (root / 'streamlit_app.py').write_text('new app')
            (root / 'crm_v2/__init__.py').write_text('new version')
            package = Path(folder) / 'release.zip'
            build(root, package, '2')
            (root / 'streamlit_app.py').write_text('old app')
            (root / 'crm_v2/__init__.py').write_text('old version')
            original = Path.replace
            def fail_second(source, destination):
                if Path(destination).name == '__init__.py':
                    raise OSError('simulated failed file replacement')
                return original(source, destination)
            with patch.object(Path, 'replace', fail_second):
                with self.assertRaises(OSError):
                    apply(root, package)
            self.assertEqual((root / 'streamlit_app.py').read_text(), 'old app')
            self.assertEqual((root / 'crm_v2/__init__.py').read_text(), 'old version')

    def test_release_keeps_private_device_data_and_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'app'
            root.mkdir()
            for name, data in {'streamlit_app.py':'new', 'crm_v2/__init__.py':'VERSION="2"',
                               'Data/cache/people.csv':'private', 'Data/credentials.json':'secret',
                               '.streamlit/secrets.toml':'secret', 'settings.local.json':'device'}.items():
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(data)
            package = Path(folder) / 'release.zip'
            sha = build(root, package, '2')
            self.assertEqual(set(inspect_package(package, sha)['files']), {'streamlit_app.py', 'crm_v2/__init__.py'})
            (root / 'streamlit_app.py').write_text('old')
            version, backup = apply(root, package, sha)
            self.assertEqual(version, '2')
            self.assertEqual((root / 'streamlit_app.py').read_text(), 'new')
            self.assertEqual((backup / 'streamlit_app.py').read_text(), 'old')
            self.assertEqual((root / 'Data/cache/people.csv').read_text(), 'private')
            self.assertEqual((root / 'Data/credentials.json').read_text(), 'secret')
            with self.assertRaises(ValueError):
                inspect_package(package, '0'*64)

    def test_rejects_path_traversal_and_data_overwrite(self):
        for name in ['../outside.py', '/outside.py', 'crm_v2/../../outside.py',
                     'Data/credentials.json', 'Data/cache/a.csv', '.streamlit/secrets.toml',
                     'crm_v2/evil\\x.py', 'crm_v2/C:evil.py']:
            self.assertFalse(allowed(name), name)
