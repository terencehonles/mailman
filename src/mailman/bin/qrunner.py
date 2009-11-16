# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

"""The queue runner."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'main',
    ]


import sys
import signal
import logging

from mailman.config import config
from mailman.core.i18n import _
from mailman.core.logging import reopen
from mailman.options import Options
from mailman.utilities.modules import find_name


COMMASPACE = ', '
log = None



def r_callback(option, opt, value, parser):
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

    usage = _("""\
Run one or more qrunners, once or repeatedly.

Each named runner class is run in round-robin fashion.  In other words, the
first named runner is run to consume all the files currently in its
directory.  When that qrunner is done, the next one is run to consume all the
files in /its/ directory, and so on.  The number of total iterations can be
given on the command line.

Usage: %prog [options]

-r is required unless -l or -h is given, and its argument must be one of the
names displayed by the -l switch.

Normally, this script should be started from mailmanctl.  Running it
separately or with -o is generally useful only for debugging.
""")

    def add_options(self):
        self.parser.add_option(
            '-r', '--runner',
            metavar='runner[:slice:range]', dest='runners',
            type='string', default=[],
            action='callback', callback=r_callback,
            help=_("""\
Run the named qrunner, which must be one of the strings returned by the -l
option.  Optional slice:range if given, is used to assign multiple qrunner
processes to a queue.  range is the total number of qrunners for this queue
while slice is the number of this qrunner from [0..range).

When using the slice:range form, you must ensure that each qrunner for the
queue is given the same range value.  If slice:runner is not given, then 1:1
is used.

Multiple -r options may be given, in which case each qrunner will run once in
round-robin fashion.  The special runner `All' is shorthand for a qrunner for
each listed by the -l option."""))
        self.parser.add_option(
            '-o', '--once',
            default=False, action='store_true', help=_("""\
Run each named qrunner exactly once through its main loop.  Otherwise, each
qrunner runs indefinitely, until the process receives signal."""))
        self.parser.add_option(
            '-l', '--list',
            default=False, action='store_true',
            help=_('List the available qrunner names and exit.'))
        self.parser.add_option(
            '-v', '--verbose',
            default=0, action='count', help=_("""\
Display more debugging information to the logs/qrunner log file."""))
        self.parser.add_option(
            '-s', '--subproc',
            default=False, action='store_true', help=_("""\
This should only be used when running qrunner as a subprocess of the
mailmanctl startup script.  It changes some of the exit-on-error behavior to
work better with that framework."""))

    def sanity_check(self):
        if self.arguments:
            self.parser.error(_('Unexpected arguments'))
        if not self.options.runners and not self.options.list:
            self.parser.error(_('No runner name given.'))



def make_qrunner(name, slice, range, once=False):
    # Several conventions for specifying the runner name are supported.  It
    # could be one of the shortcut names.  If the name is a full module path,
    # use it explicitly.  If the name starts with a dot, it's a class name
    # relative to the Mailman.queue package.
    qrunner_config = getattr(config, 'qrunner.' + name, None)
    if qrunner_config is not None:
        # It was a shortcut name.
        class_path = qrunner_config['class']
    elif name.startswith('.'):
        class_path = 'mailman.queue' + name
    else:
        class_path = name
    try:
        qrclass = find_name(class_path)
    except ImportError as error:
        if config.options.options.subproc:
            # Exit with SIGTERM exit code so the master watcher won't try to
            # restart us.
            print >> sys.stderr, _('Cannot import runner module: $module_name')
            print >> sys.stderr, error
            sys.exit(signal.SIGTERM)
        else:
            raise
    if once:
        # Subclass to hack in the setting of the stop flag in _do_periodic()
        class Once(qrclass):
            def _do_periodic(self):
                self.stop()
        qrunner = Once(name, slice)
    else:
        qrunner = qrclass(name, slice)
    return qrunner



def set_signals(loop):
    """Set up the signal handlers.

    Signals caught are: SIGTERM, SIGINT, SIGUSR1 and SIGHUP.  The latter is
    used to re-open the log files.  SIGTERM and SIGINT are treated exactly the
    same -- they cause qrunner to exit with no restart from the master.
    SIGUSR1 also causes qrunner to exit, but the master watcher will restart
    it in that case.

    :param loop: A loop queue runner instance.
    """
    def sigterm_handler(signum, frame):
        # Exit the qrunner cleanly
        loop.stop()
        loop.status = signal.SIGTERM
        log.info('%s qrunner caught SIGTERM.  Stopping.', loop.name())
    signal.signal(signal.SIGTERM, sigterm_handler)
    def sigint_handler(signum, frame):
        # Exit the qrunner cleanly
        loop.stop()
        loop.status = signal.SIGINT
        log.info('%s qrunner caught SIGINT.  Stopping.', loop.name())
    signal.signal(signal.SIGINT, sigint_handler)
    def sigusr1_handler(signum, frame):
        # Exit the qrunner cleanly
        loop.stop()
        loop.status = signal.SIGUSR1
        log.info('%s qrunner caught SIGUSR1.  Stopping.', loop.name())
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    # SIGHUP just tells us to rotate our log files.
    def sighup_handler(signum, frame):
        reopen()
        log.info('%s qrunner caught SIGHUP.  Reopening logs.', loop.name())
    signal.signal(signal.SIGHUP, sighup_handler)



def main():
    global log

    options = ScriptOptions()
    options.initialize()

    if options.options.list:
        descriptions = {}
        for section in config.qrunner_configs:
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
        qrunner = make_qrunner(*options.options.runners[0])
        class Loop:
            status = 0
            def __init__(self, qrunner):
                self._qrunner = qrunner
            def name(self):
                return self._qrunner.__class__.__name__
            def stop(self):
                self._qrunner.stop()
        loop = Loop(qrunner)
        if qrunner.intercept_signals:
            set_signals(loop)
        # Now start up the main loop
        log = logging.getLogger('mailman.qrunner')
        log.info('%s qrunner started.', loop.name())
        qrunner.run()
        log.info('%s qrunner exiting.', loop.name())
    else:
        # Anything else we have to handle a bit more specially.
        qrunners = []
        for runner, rslice, rrange in options.options.runners:
            qrunner = make_qrunner(runner, rslice, rrange, once=True)
            qrunners.append(qrunner)
        # This class is used to manage the main loop
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
        if qrunner.intercept_signals:
            set_signals(loop)
        log.info('Main qrunner loop started.')
        while not loop.isdone():
            for qrunner in qrunners:
                # In case the SIGTERM came in the middle of this iteration
                if loop.isdone():
                    break
                if options.options.verbose:
                    log.info('Now doing a %s qrunner iteration',
                             qrunner.__class__.__bases__[0].__name__)
                qrunner.run()
            if options.options.once:
                break
        log.info('Main qrunner loop exiting.')
    # All done
    sys.exit(loop.status)
