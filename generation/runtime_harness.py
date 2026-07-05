# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Subprocess body for the generation runtime check.

Runs a generated activity the same way the studio preview does:
instantiate it against the PreviewActivity stubs, pump the GTK loop,
and exercise the generated class's own Journal round-trip.  Exits 0
and prints RUNTIME-OK on success; any crash prints the traceback and
exits nonzero so the parent can feed it back to the model.
"""

import os
import sys
import tempfile
import traceback


def main(project_dir):
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk

    from preview.runner import render_activity_preview

    instance, canvas, toolbar_ = render_activity_preview(project_dir)
    if instance is None:
        sys.stderr.write('Activity failed to start: %s\n' % canvas)
        return 1

    for _ in range(30):
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

    # The generated class overrides read_file/write_file; run them for
    # real so broken Journal persistence fails the gate.
    handle, journal_path = tempfile.mkstemp(prefix='aod-runtime-journal-')
    os.close(handle)
    try:
        instance.write_file(journal_path)
        instance.read_file(journal_path)
    finally:
        try:
            os.remove(journal_path)
        except OSError:
            pass

    try:
        instance.cleanup()
    except Exception:
        pass

    print('RUNTIME-OK')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1]))
    except Exception:
        traceback.print_exc()
        sys.exit(1)
