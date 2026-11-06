"""Regression coverage for Omarchy's keepLoaded idle service integration."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('screensaver_setup', Path(__file__).resolve().parents[1] / 'screensaver/setup.py')
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)
ORIGINAL = 'runProcess(screensaverProcess, "screensaver", "check || omarchy-launch-screensaver")\n'


class ScreensaverSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='zelda setup ')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.plugin = self.home / '.config/omarchy/plugins/test-user.idle'
        self.service = self.plugin / 'Service.qml'
        self.record = self.home / '.local/state/zelda40-screensaver/installation.json'
        self.calls = []
        self.restart_fails = False

    def fake_run(self, command, **kwargs):
        self.calls.append(command)
        if command == ['omarchy', 'plugin', 'clone', 'omarchy.idle']:
            self.plugin.mkdir(parents=True)
            self.service.write_text(ORIGINAL)
        if command == ['omarchy', 'restart', 'shell']:
            return subprocess.CompletedProcess(command, 1 if self.restart_fails else 0)
        return subprocess.CompletedProcess(command, 0)

    def run_setup(self, *args):
        with patch.object(setup.Path, 'home', return_value=self.home), \
             patch.object(setup.getpass, 'getuser', return_value='test-user'), \
             patch.object(setup.shutil, 'which', return_value='/fake/command'), \
             patch.object(setup.subprocess, 'run', side_effect=self.fake_run), \
             patch.object(sys, 'argv', ['setup.py', *args]):
            setup.main()

    def test_fresh_clone_restarts_after_enabling(self):
        self.run_setup()
        self.assertNotEqual(self.service.read_text(), ORIGINAL)
        self.assertEqual(self.calls[-2:], [
            ['omarchy', 'plugin', 'enable', 'test-user.idle'],
            ['omarchy', 'restart', 'shell'],
        ])
        self.assertTrue(self.record.exists())

    def test_repeat_setup_reloads_the_running_service(self):
        self.run_setup()
        original_backup = (self.record.parent / 'Service.qml.original').read_text()
        self.calls.clear()
        self.run_setup()
        self.assertEqual(self.calls[-1], ['omarchy', 'restart', 'shell'])
        self.assertEqual((self.record.parent / 'Service.qml.original').read_text(), original_backup)

    def test_uninstall_restores_then_restarts(self):
        self.run_setup()
        self.calls.clear()
        self.run_setup('--uninstall')
        self.assertEqual(self.service.read_text(), ORIGINAL)
        self.assertEqual(self.calls, [['omarchy', 'restart', 'shell']])
        self.assertFalse(self.record.exists())

    def test_failed_restart_can_be_retried(self):
        self.restart_fails = True
        with self.assertRaisesRegex(SystemExit, 'could not restart'):
            self.run_setup()
        self.assertTrue(self.record.exists())
        self.restart_fails = False
        self.run_setup()
        self.assertEqual(self.calls[-1], ['omarchy', 'restart', 'shell'])

    def test_failed_uninstall_restart_can_be_retried(self):
        self.run_setup()
        self.restart_fails = True
        with self.assertRaisesRegex(SystemExit, 'could not restart'):
            self.run_setup('--uninstall')
        self.assertTrue(self.record.exists())
        self.restart_fails = False
        self.run_setup('--uninstall')
        self.assertEqual(self.service.read_text(), ORIGINAL)
        self.assertFalse(self.record.exists())

    def test_uninstall_preserves_later_user_edits(self):
        self.run_setup()
        edited = self.service.read_text() + '// user edit\n'
        self.service.write_text(edited)
        self.calls.clear()
        with self.assertRaisesRegex(SystemExit, 'changed since setup'):
            self.run_setup('--uninstall')
        self.assertEqual(self.service.read_text(), edited)
        self.assertEqual(self.calls, [])

    def test_existing_custom_launcher_is_preserved(self):
        self.plugin.mkdir(parents=True)
        self.service.write_text('custom launcher\n')
        with self.assertRaisesRegex(SystemExit, 'custom launcher'):
            self.run_setup()
        self.assertEqual(self.service.read_text(), 'custom launcher\n')
        self.assertEqual(self.calls, [])
        self.assertFalse(self.record.exists())


if __name__ == '__main__':
    unittest.main()
