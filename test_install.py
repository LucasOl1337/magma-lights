"""Exercise a real install in a temporary home, never on the live desktop."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from install import install


class Installation(unittest.TestCase):
    def test_install_preserves_settings_and_quotes_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'test home $literal'
            state = home / '.config/magma-lights/state.json'
            state.parent.mkdir(parents=True)
            state.write_text('{"preset":"oceano"}')
            with patch('install.shutil.which', return_value=None):
                target = install(home)
                install(home)
            self.assertEqual(state.read_text(), '{"preset":"oceano"}')
            self.assertTrue((target / 'app.py').is_file())
            launcher = home / '.local/bin/magma-lights'
            self.assertTrue(launcher.stat().st_mode & 0o111)
            subprocess.run(['sh', '-n', str(launcher)], check=True)
            with patch('install.sys.executable', '/usr/bin/true'), patch('install.shutil.which', return_value=None):
                install(home)
            subprocess.run([str(launcher), '--demo'], check=True)
            desktop = home / '.local/share/applications/local.omarchy.MagmaLights.desktop'
            self.assertIn('\\$literal', desktop.read_text())


if __name__ == '__main__':
    unittest.main()
