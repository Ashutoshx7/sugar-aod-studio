# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestStudioDecoupling(unittest.TestCase):

    def test_panel_imports_without_any_jarabe_module(self):
        code = (
            'import sys\n'
            'import aodstudio.ui.panel\n'
            'import aodstudio.ui.window\n'
            'import aodstudio.main\n'
            'bad = [m for m in sys.modules if m.startswith("jarabe")]\n'
            'assert not bad, "jarabe leaked into standalone studio: %s" '
            '% bad\n'
        )
        completed = subprocess.run(
            [sys.executable, '-c', code],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            0, completed.returncode,
            'decoupling check failed:\n%s%s'
            % (completed.stdout, completed.stderr))

    def test_clean_generation_error_text_strips_pipeline_prefixes(self):
        from aodstudio.ui.panel import _clean_generation_error_text

        self.assertEqual(
            'Drawing requests must use a Gtk.DrawingArea draw surface.',
            _clean_generation_error_text(
                'Provider could not generate valid activity code: '
                'Provider generated code did not pass validation: '
                'Drawing requests must use a Gtk.DrawingArea draw '
                'surface.'))
        self.assertEqual('plain message',
                         _clean_generation_error_text('plain message'))
        self.assertEqual('', _clean_generation_error_text(None))


@unittest.skipUnless(
    os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'),
    'needs a display server')
class TestStudioOffscreen(unittest.TestCase):

    def test_panel_starts_on_chooser_and_survives_lifecycle(self):
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk

        from aodstudio.ui.panel import CreateAIActivityPanel

        window = Gtk.OffscreenWindow()
        panel = CreateAIActivityPanel()
        window.add(panel)
        window.show_all()
        panel.reset_view()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

        self.assertEqual('choose', panel._stack.get_visible_child_name())

        panel.append_prompt_text('a fractions quiz for kids')
        panel.cancel_generation()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

        window.destroy()


if __name__ == '__main__':
    unittest.main()
