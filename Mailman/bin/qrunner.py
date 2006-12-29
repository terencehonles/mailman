# Copyright (C) 2001-2006 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

import sys
import signal
import logging
import optparse

from Mailman import Version
from Mailman import loginit
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.initialize import initialize

__i18n_templates__ = True

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
    if runner == 'All':
        for runnername, slices in config.QRUNNERS:
            dest.append((runnername, rslice, rrange))
    elif not runner.endswith('Runner'):
        runner += 'Runner'
    dest.append((runner, rslice, rrange))



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
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
"""))
    parser.add_option('-r', '--runner',
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
    parser.add_option('-o', '--once',
                      default=False, action='store_true', help=_("""\
Run each named qrunner exactly once through its main loop.  Otherwise, each
qrunner runs indefinitely, until the process receives a SIGTERM or SIGINT."""))
    parser.add_option('-l', '--list',
                      default=False, action='store_true',
                      help=_('List the available qrunner names and exit.'))
    parser.add_option('-v', '--verbose',
                      default=0, action='count', help=_("""\
Display more debugging information to the logs/qrunner log file."""))
    parser.add_option('-s', '--subproc',
                      default=False, action='store_true', help=_("""\
This should only be used when running qrunner as a subprocess of the
mailmanctl startup script.  It changes some of the exit-on-error behavior to
work better with that framework."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    if not opts.runners and not opts.list:
        parser.print_help()
        print >> sys.stderr, _('No runner name given.')
        sys.exit(1)
    return parser, opts, args



def make_qrunner(name, slice, range, once=False):
    modulename = 'Mailman.Queue.' + name
    try:
        __import__(modulename)
    except ImportError, e:
        if opts.subproc:
            # Exit with SIGTERM exit code so mailmanctl won't try to restart us
            print >> sys.stderr, _('Cannot import runner module: $modulename')
            print >> sys.stderr, e
            sys.exit(signal.SIGTERM)
        else:
            print >> sys.stderr, e
            sys.exit(1)
    qrclass = getattr(sys.modules[modulename], name)
    if once:
        # Subclass to hack in the setting of the stop flag in _doperiodic()
        class Once(qrclass):
            def _doperiodic(self):
                self.stop()
        qrunner = Once(slice, range)
    else:
        qrunner = qrclass(slice, range)
    return qrunner



def set_signals(loop):
    # Set up the SIGTERM handler for stopping the loop
    def sigterm_handler(signum, frame):
        # Exit the qrunner cleanly
        loop.stop()
        loop.status = signal.SIGTERM
        log.info('%s qrunner caught SIGTERM.  Stopping.', loop.name())
    signal.signal(signal.SIGTERM, sigterm_handler)
    # Set up the SIGINT handler for stopping the loop.  For us, SIGINT is
    # the same as SIGTERM, but our parent treats the exit statuses
    # differently (it restarts a SIGINT but not a SIGTERM).
    def sigint_handler(signum, frame):
        # Exit the qrunner cleanly
        loop.stop()
        loop.status = signal.SIGINT
        log.info('%s qrunner caught SIGINT.  Stopping.', loop.name())
    signal.signal(signal.SIGINT, sigint_handler)
    # SIGHUP just tells us to rotate our log files.
    def sighup_handler(signum, frame):
        loginit.reopen()
        log.info('%s qrunner caught SIGHUP.  Reopening logs.', loop.name())
    signal.signal(signal.SIGHUP, sighup_handler)



def main():
    global log, opts

    parser, opts, args = parseargs()
    # If we're not running as a subprocess of mailmanctl, then we'll log to
    # stderr in addition to logging to the log files.  We do this by passing a
    # value of True to propagate, which allows the 'mailman' root logger to
    # see the log messages.
    initialize(opts.config, propagate_logs=not opts.subproc)
    log = logging.getLogger('mailman.qrunner')

    if opts.list:
        for runnername, slices in config.QRUNNERS:
            if runnername.endswith('Runner'):
                name = runnername[:-len('Runner')]
            else:
                name = runnername
            print _('$name runs the $runnername qrunner')
        print _('All runs all the above qrunners')
        sys.exit(0)

    # Fast track for one infinite runner
    if len(opts.runners) == 1 and not opts.once:
        qrunner = make_qrunner(*opts.runners[0])
        class Loop:
            status = 0
            def __init__(self, qrunner):
                self._qrunner = qrunner
            def name(self):
                return self._qrunner.__class__.__name__
            def stop(self):
                self._qrunner.stop()
        loop = Loop(qrunner)
        set_signals(loop)
        # Now start up the main loop
        log.info('%s qrunner started.', loop.name())
        qrunner.run()
        log.info('%s qrunner exiting.', loop.name())
    else:
        # Anything else we have to handle a bit more specially
        qrunners = []
        for runner, rslice, rrange in opts.runners:
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
        set_signals(loop)
        log.info('Main qrunner loop started.')
        while not loop.isdone():
            for qrunner in qrunners:
                # In case the SIGTERM came in the middle of this iteration
                if loop.isdone():
                    break
                if opts.verbose:
                    log.info('Now doing a %s qrunner iteration',
                             qrunner.__class__.__bases__[0].__name__)
                qrunner.run()
            if opts.once:
                break
        log.info('Main qrunner loop exiting.')
    # All done
    sys.exit(loop.status)



if __name__ == '__main__':
    main()
