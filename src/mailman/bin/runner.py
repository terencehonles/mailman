# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""The runner process."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'main',
    ]


import os
import sys
import signal
import logging
import traceback

from mailman.config import config
from mailman.core.i18n import _
from mailman.core.logging import reopen
from mailman.options import Options
from mailman.utilities.modules import find_name


log = None



def r_callback(option, opt, value, parser):
    """Callback for -r/--runner option."""
    dest = getattr(parser.values, option.dest)
    parts = value.split(':')
    if len(parts) == 1:
        runner = parts[0]
        rslice = rrange = 1
    elif len(parts) == 3:
        runner = parts[0]
        try:
            rslice = int(parts[1])
            rrange = int(parts[2])
        except ValueError:
            parser.print_help()
            print >> sys.stderr, _('Bad runner specification: $value')
            sys.exit(1)
    else:
        parser.print_help()
        print >> sys.stderr, _('Bad runner specification: $value')
        sys.exit(1)
    dest.append((runner, rslice, rrange))



class ScriptOptions(Options):
    """Options for bin/runner."""
    usage = _("""\
Start one or more runners.

The runner named on the command line is started, and it can either run through
its main loop once (for those runners that support this) or continuously.  The
latter is how the master runner starts all its subprocesses.

When more than one runner is specified on the command line, they are each run
in round-robin fashion.  All runners must support running its main loop once.
In other words, the first named runner is run once.  When that runner is done,
the next one is run to consume all the files in *its* directory, and so on.
The number of total iterations can be given on the command line.  This mode of
operation is primarily for debugging purposes.

Usage: %prog [options]

-r is required unless -l or -h is given, and its argument must be one of the
names displayed by the -l switch.

Normally, this script should be started from 'bin/mailman start'.  Running it
separately or with -o is generally useful only for debugging.  When run this
way, the environment variable $MAILMAN_UNDER_MASTER_CONTROL will be set which
subtly changes some error handling behavior.
""")

    def add_options(self):
        """See `Options`."""
        self.parser.add_option(
            '-r', '--runner',
            metavar='runner[:slice:range]', dest='runners',
            type='string', default=[],
            action='callback', callback=r_callback,
            help=_("""\
Start the named runner, which must be one of the strings returned by the -l
option.

For runners that manage a queue directory, optional slice:range if given, is
used to assign multiple runner processes to that queue.  range is the total
number of runners for the queue while slice is the number of this runner from
[0..range).  For runners that do not manage a queue, slice and range are
ignored.

When using the slice:range form, you must ensure that each runner for the
queue is given the same range value.  If slice:runner is not given, then 1:1
is used.

Multiple -r options may be given, in which case each runner will run once in
round-robin fashion.  The special runner 'All' is shorthand for running all
named runners listed by the -l option."""))
        self.parser.add_option(
            '-o', '--once',
            default=False, action='store_true', help=_("""\
Run each named runner exactly once through its main loop.  Otherwise, each
runner runs indefinitely, until the process receives signal.  This is not
compatible with runners that cannot be run once."""))
        self.parser.add_option(
            '-l', '--list',
            default=False, action='store_true',
            help=_('List the available runner names and exit.'))
        self.parser.add_option(
            '-v', '--verbose',
            default=0, action='count', help=_("""\
Display more debugging information to the log file."""))

    def sanity_check(self):
        """See `Options`."""
        if self.arguments:
            self.parser.error(_('Unexpected arguments'))
        if not self.options.runners and not self.options.list:
            self.parser.error(_('No runner name given.'))



def make_runner(name, slice, range, once=False):
    # Several conventions for specifying the runner name are supported.  It
    # could be one of the shortcut names.  If the name is a full module path,
    # use it explicitly.  If the name starts with a dot, it's a class name
    # relative to the Mailman.runner package.
    runner_config = getattr(config, 'runner.' + name, None)
    if runner_config is not None:
        # It was a shortcut name.
        class_path = runner_config['class']
    elif name.startswith('.'):
        class_path = 'mailman.runners' + name
    else:
        class_path = name
    try:
        runner_class = find_name(class_path)
    except ImportError:
        if os.environ.get('MAILMAN_UNDER_MASTER_CONTROL') is not None:
            # Exit with SIGTERM exit code so the master watcher won't try to
            # restart us.
            print >> sys.stderr, _('Cannot import runner module: $class_path')
            traceback.print_exc()
            sys.exit(signal.SIGTERM)
        else:
            raise
    if once:
        # Subclass to hack in the setting of the stop flag in _do_periodic()
        class Once(runner_class):
            def _do_periodic(self):
                self.stop()
        return Once(name, slice)
    return runner_class(name, slice)



def set_signals(loop):
    """Set up the signal handlers.

    Signals caught are: SIGTERM, SIGINT, SIGUSR1 and SIGHUP.  The latter is
    used to re-open the log files.  SIGTERM and SIGINT are treated exactly the
    same -- they cause the runner to exit with no restart from the master.
    SIGUSR1 also causes the runner to exit, but the master watcher will
    restart it in that case.

    :param loop: A runner instance.
    :type loop: `IRunner`
    """
    def sigterm_handler(signum, frame):
        # Exit the runner cleanly
        loop.stop()
        loop.status = signal.SIGTERM
        log.info('%s runner caught SIGTERM.  Stopping.', loop.name())
    signal.signal(signal.SIGTERM, sigterm_handler)
    def sigint_handler(signum, frame):
        # Exit the runner cleanly
        loop.stop()
        loop.status = signal.SIGINT
        log.info('%s runner caught SIGINT.  Stopping.', loop.name())
    signal.signal(signal.SIGINT, sigint_handler)
    def sigusr1_handler(signum, frame):
        # Exit the runner cleanly
        loop.stop()
        loop.status = signal.SIGUSR1
        log.info('%s runner caught SIGUSR1.  Stopping.', loop.name())
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    # SIGHUP just tells us to rotate our log files.
    def sighup_handler(signum, frame):
        reopen()
        log.info('%s runner caught SIGHUP.  Reopening logs.', loop.name())
    signal.signal(signal.SIGHUP, sighup_handler)



def main():
    global log

    options = ScriptOptions()
    options.initialize()

    log = logging.getLogger('mailman.runner')

    if options.options.list:
        descriptions = {}
        for section in config.runner_configs:
            ignore, dot, shortname = section.name.rpartition('.')
            ignore, dot, classname = getattr(section, 'class').rpartition('.')
            descriptions[shortname] = classname
        longest = max(len(name) for name in descriptions)
        for shortname in sorted(descriptions):
            classname = descriptions[shortname]
            name = (' ' * (longest - len(shortname))) + shortname
            print _('$name runs $classname')
        sys.exit(0)

    # Fast track for one infinite runner.
    if len(options.options.runners) == 1 and not options.options.once:
        runner = make_runner(*options.options.runners[0])
        class Loop:
            status = 0
            def __init__(self, runner):
                self._runner = runner
            def name(self):
                return self._runner.__class__.__name__
            def stop(self):
                self._runner.stop()
        loop = Loop(runner)
        if runner.intercept_signals:
            set_signals(loop)
        # Now start up the main loop
        log.info('%s runner started.', loop.name())
        runner.run()
        log.info('%s runner exiting.', loop.name())
    else:
        # Anything else we have to handle a bit more specially.
        runners = []
        for runner, rslice, rrange in options.options.runners:
            runner = make_runner(runner, rslice, rrange, once=True)
            runners.append(runner)
        # This class is used to manage the main loop.
        class Loop:
            status = 0
            def __init__(self):
                self._isdone = False
            def name(self):
                return 'Main loop'
            def stop(self):
                self._isdone = True
            def isdone(self):
                return self._isdone
        loop = Loop()
        if runner.intercept_signals:
            set_signals(loop)
        log.info('Main runner loop started.')
        while not loop.isdone():
            for runner in runners:
                # In case the SIGTERM came in the middle of this iteration.
                if loop.isdone():
                    break
                if options.options.verbose:
                    log.info('Now doing a %s runner iteration',
                             runner.__class__.__bases__[0].__name__)
                runner.run()
            if options.options.once:
                break
        log.info('Main runner loop exiting.')
    # All done
    sys.exit(loop.status)
