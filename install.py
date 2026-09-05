#!/usr/bin/env python3
"""Install Magma for the current user without changing hardware or packages."""
import argparse
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent
FILES = ('app.py', 'controller.py', 'style.css', 'icon.svg', 'README.md', 'LICENSE')


def desktop_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def install(home):
    home = Path(home).resolve()
    target = home / '.local/share/magma-lights'
    binary = home / '.local/bin/magma-lights'
    desktop = home / '.local/share/applications/local.omarchy.MagmaLights.desktop'
    for path in (target, binary.parent, desktop.parent):
        path.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        shutil.copy2(SOURCE / filename, target / filename)
    binary.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(target / 'app.py')) + ' "$@"\n')
    binary.chmod(0o755)
    cli = desktop_quote(sys.executable) + ' ' + desktop_quote(target / 'controller.py')
    desktop.write_text(f'''[Desktop Entry]
Version=1.0
Type=Application
Name=Magma — Luzes do PC
Comment=Cores, presets e modo dormir para o seu PC
Exec={desktop_quote(binary)}
Icon={target / 'icon.svg'}
Terminal=false
Categories=Utility;
Keywords=RGB;Luzes;Lava;Fans;Cooler;Dormir;Magma;
StartupNotify=true
StartupWMClass=local.omarchy.MagmaLights
Actions=Lava;Dormir;Restaurar;

[Desktop Action Lava]
Name=Lava
Exec={cli} preset lava

[Desktop Action Dormir]
Name=Modo dormir
Exec={cli} sleep

[Desktop Action Restaurar]
Name=Restaurar luzes
Exec={cli} restore
''')
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(desktop.parent)], check=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home(), help='Alternative home directory, useful for packaging tests')
    args = parser.parse_args()
    print(f'Magma instalado em {install(args.home)}')
    print('Abra Magma — Luzes do PC no menu. Nenhum comando de iluminação foi enviado.')
