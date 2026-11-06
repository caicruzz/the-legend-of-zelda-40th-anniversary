#!/usr/bin/env python3
"""Opt-in Omarchy idle integration. Run with --uninstall to restore the service."""
import argparse
import getpass
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    home = Path.home()
    state = home / '.local/state/zelda40-screensaver'
    record = state / 'installation.json'
    if args.uninstall:
        if not record.exists():
            print('Screensaver integration is not installed.')
            return
        saved = json.loads(record.read_text())
        service = Path(saved['service'])
        if service.read_text() != saved['installed']:
            sys.exit('Idle plugin changed since setup. Restore the saved original manually: ' + str(state / 'Service.qml.original'))
        service.write_text((state / 'Service.qml.original').read_text())
        record.unlink()
        subprocess.run(['omarchy-shell', 'shell', 'rescanPlugins'], check=True)
        print('Standard screensaver restored; your idle and lock times are unchanged.')
        return

    for command in ('omarchy', 'omarchy-shell', 'hyprctl', 'xdg-terminal-exec', 'socat'):
        if not shutil.which(command):
            sys.exit('Missing requirement: ' + command)
    launcher = Path(__file__).resolve().parent / 'launch'
    if record.exists():
        saved = json.loads(record.read_text())
        if Path(saved['service']).read_text() == saved['installed']:
            print('Screensaver integration is already installed.')
            return
        sys.exit('An earlier installation exists but its idle plugin has changed. See ' + str(state))
    plugin = home / '.config/omarchy/plugins' / (getpass.getuser() + '.idle')
    if not plugin.exists():
        subprocess.run(['omarchy', 'plugin', 'clone', 'omarchy.idle'], check=True)
    service = plugin / 'Service.qml'
    original = service.read_text()
    needle = '|| omarchy-launch-screensaver'
    if original.count(needle) != 1:
        sys.exit('Your idle plugin already has a custom launcher or uses an unsupported format. No files were changed. Preview with: ' + str(launcher) + ' force')
    # Quote for bash, then escape for the enclosing QML string.
    command = shlex.quote(str(launcher)).replace('\\', '\\\\').replace('"', '\\"')
    installed = original.replace(needle, '|| ' + command)
    state.mkdir(parents=True, exist_ok=True)
    (state / 'Service.qml.original').write_text(original)
    record.write_text(json.dumps({'service': str(service), 'installed': installed}, indent=2))
    service.write_text(installed)
    subprocess.run(['omarchy-shell', 'shell', 'rescanPlugins'], check=True)
    subprocess.run(['omarchy', 'plugin', 'enable', plugin.name], check=True)
    print('Triforce + Navi screensaver enabled. Your idle and lock times are unchanged.')


if __name__ == '__main__':
    main()
