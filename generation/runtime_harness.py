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

import logging
import os
import sys
import tempfile
import traceback


class _StartupProblems(logging.Handler):
    """Collect WARNING+ records emitted while the activity starts.

    The preview runner deliberately degrades — salvaging a partial
    canvas after an __init__ crash, stubbing failed imports — so
    learners always see something.  The gate must not accept degraded
    code, and every degradation is logged as a warning, so warnings
    during startup are failures here.
    """

    def __init__(self):
        logging.Handler.__init__(self)
        self.setFormatter(logging.Formatter('%(message)s'))
        self.problems = []

    def emit(self, record):
        # Theme noise (missing stock icons etc.) also lands on the
        # root logger; every degradation message from the preview
        # runner mentions "preview", so key on that.
        if record.levelno >= logging.WARNING \
                and 'preview' in record.getMessage().lower():
            self.problems.append(self.format(record))


def main(project_dir):
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import GLib
    from gi.repository import Gtk

    from preview.runner import render_activity_preview

    problems = _StartupProblems()
    logging.getLogger().addHandler(problems)
    try:
        instance, canvas, toolbar_ = render_activity_preview(project_dir)
    finally:
        logging.getLogger().removeHandler(problems)
    if instance is None:
        sys.stderr.write('Activity failed to start: %s\n' % canvas)
        return 1
    if problems.problems:
        sys.stderr.write(
            'Activity started only in degraded mode:\n%s\n'
            % '\n\n'.join(problems.problems))
        return 1

    for _ in range(30):
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

    # A non-blocking pump never lets GLib.timeout_add sources become
    # ready, yet the codegen contract drives game loops with exactly
    # those timers -- and PyGObject swallows exceptions raised inside
    # dispatched callbacks (they go through sys.excepthook and the
    # process carries on).  Spin the real main loop for a bounded window
    # with a recording excepthook so a frame callback that crashes on
    # its first ticks fails the gate instead of shipping.
    spin_seconds = _env_float('AOD_RUNTIME_SPIN_SECONDS', 1.5)
    if spin_seconds > 0:
        callback_failures = []
        previous_hook = sys.excepthook

        def _record_failure(exc_type, exc_value, exc_tb):
            callback_failures.append(''.join(
                traceback.format_exception(exc_type, exc_value, exc_tb)))

        sys.excepthook = _record_failure
        try:
            loop = GLib.MainLoop()
            GLib.timeout_add(int(spin_seconds * 1000), loop.quit)
            loop.run()
        finally:
            sys.excepthook = previous_hook
        if callback_failures:
            sys.stderr.write(
                'Activity crashed inside an event callback:\n%s\n'
                % '\n'.join(callback_failures))
            return 1

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


def _env_float(name, default):
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


if __name__ == '__main__':
    try:
        _exit_code = main(sys.argv[1])
    except BaseException:
        # BaseException: a generated sys.exit()/SystemExit must produce a
        # traceback for the repair loop, not a silent exit code.
        traceback.print_exc()
        sys.exit(1)
    sys.exit(_exit_code)
