# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

"""Mailman start/stop script."""

from __future__ import with_statement

import os
import grp
import pwd
import sys
import errno
import signal
import logging

from optparse import OptionParser

from Mailman import Version
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.initialize import initialize


COMMASPACE = ', '

log = None
parser = None



def parseargs():
    parser = OptionParser(version=Version.MAILMAN_VERSION,
                          usage=_("""\
Primary start-up and shutdown script for Mailman's qrunner daemon.

This script starts, stops, and restarts the main Mailman queue runners, making
sure that the various long-running qrunners are still alive and kicking.  It
does this by forking and exec'ing the qrunners and waiting on their pids.
When it detects a subprocess has exited, it may restart it.

The qrunners respond to SIGINT, SIGTERM, SIGUSR1 and SIGHUP.  SIGINT, SIGTERM
and SIGUSR1 all cause the qrunners to exit cleanly, but the master will only
restart qrunners that have exited due to a SIGUSR1.  SIGHUP causes the master
and the qrunners to close their log files, and reopen then upon the next
printed message.

The master also responds to SIGINT, SIGTERM, SIGUSR1 and SIGHUP, which it
simply passes on to the qrunners (note that the master will close and reopen
its own log files on receipt of a SIGHUP).  The master also leaves its own
process id in the file data/master-qrunner.pid but you normally don't need to
use this pid directly.  The `start', `stop', `restart', and `reopen' commands
handle everything for you.

Commands:

    start   - Start the master daemon and all qrunners.  Prints a message and
              exits if the master daemon is already running.

    stop    - Stops the master daemon and all qrunners.  After stopping, no
              more messages will be processed.

    restart - Restarts the qrunners, but not the master process.  Use this
              whenever you upgrade or update Mailman so that the qrunners will
              use the newly installed code.

    reopen  - This will close all log files, causing them to be re-opened the
              next time a message is written to them

Usage: %prog [options] [ start | stop | restart | reopen ]"""))
    parser.add_option('-u', '--run-as-user',
                      default=True, action='store_false',
                      help=_("""\
Normally, this script will refuse to run if the user id and group id are not
set to the `mailman' user and group (as defined when you configured Mailman).
If run as root, this script will change to this user and group before the
check is made.

This can be inconvenient for testing and debugging purposes, so the -u flag
means that the step that sets and checks the uid/gid is skipped, and the
program is run as the current user and group.  This flag is not recommended
for normal production environments.

Note though, that if you run with -u and are not in the mailman group, you may
have permission problems, such as begin unable to delete a list's archives
through the web.  Tough luck!"""))
    parser.add_option('-f', '--force',
                      default=False, action='store_true',
                      help=_("""\
If the master watcher finds an existing master lock, it will normally exit
with an error message.  With this option,the master will perform an extra
level of checking.  If a process matching the host/pid described in the lock
file is running, the master will still exit, requiring you to manually clean
up the lock.  But if no matching process is found, the master will remove the
apparently stale lock and make another attempt to claim the master lock."""))
    parser.add_option('-q', '--quiet',
                      default=False, action='store_true',
                      help=_("""\
Don't print status messages.  Error messages are still printed to standard
error."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    options, arguments = parser.parse_args()
    if not arguments:
        parser.error(_('No command given.'))
    if len(arguments) > 1:
        commands = COMMASPACE.join(arguments)
        parser.error(_('Bad command: $commands'))
    parser.options = options
    parser.arguments = arguments
    return parser



def kill_watcher(sig):
    try:
        with open(config.PIDFILE) as f:
            pid = int(f.read().strip())
    except (IOError, ValueError), e:
        # For i18n convenience
        print >> sys.stderr, _('PID unreadable in: $config.PIDFILE')
        print >> sys.stderr, e
        print >> sys.stderr, _('Is qrunner even running?')
        return
    try:
        os.kill(pid, sig)
    except OSError, error:
        if e.errno <> errno.ESRCH:
            raise
        print >> sys.stderr, _('No child with pid: $pid')
        print >> sys.stderr, e
        print >> sys.stderr, _('Stale pid file removed.')
        os.unlink(config.PIDFILE)



def check_privileges():
    # If we're running as root (uid == 0), coerce the uid and gid to that
    # which Mailman was configured for, and refuse to run if we didn't coerce
    # the uid/gid.
    gid = grp.getgrnam(config.MAILMAN_GROUP).gr_gid
    uid = pwd.getpwnam(config.MAILMAN_USER).pw_uid
    myuid = os.getuid()
    if myuid == 0:
        # Set the process's supplimental groups.
        groups = [group.gr_gid for group in grp.getgrall()
                  if config.MAILMAN_USER in group.gr_mem]
        groups.append(gid)
        os.setgroups(groups)
        os.setgid(gid)
        os.setuid(uid)
    elif myuid <> uid:
        name = config.MAILMAN_USER
        parser.error(
            _('Run this program as root or as the $name user, or use -u.'))



def main():
    global log, parser

    parser = parseargs()
    initialize(parser.options.config)

    log = logging.getLogger('mailman.qrunner')

    if not parser.options.run_as_user:
        check_privileges()
    else:
        if not parser.options.quiet:
            print _('Warning!  You may encounter permission problems.')

    # Handle the commands
    command = parser.arguments[0].lower()
    if command == 'stop':
        if not parser.options.quiet:
            print _("Shutting down Mailman's master qrunner")
        kill_watcher(signal.SIGTERM)
    elif command == 'restart':
        if not parser.options.quiet:
            print _("Restarting Mailman's master qrunner")
        kill_watcher(signal.SIGUSR1)
    elif command == 'reopen':
        if not parser.options.quiet:
            print _('Re-opening all log files')
        kill_watcher(signal.SIGHUP)
    elif command == 'start':
        # Start the master qrunner watcher process.
        #
        # Daemon process startup according to Stevens, Advanced Programming in
        # the UNIX Environment, Chapter 13.
        pid = os.fork()
        if pid:
            # parent
            if not parser.options.quiet:
                print _("Starting Mailman's master qrunner.")
            return
        # child
        #
        # Create a new session and become the session leader, but since we
        # won't be opening any terminal devices, don't do the ultra-paranoid
        # suggestion of doing a second fork after the setsid() call.
        os.setsid()
        # Instead of cd'ing to root, cd to the Mailman runtime directory.
        os.chdir(config.VAR_DIR)
        # Exec the master watcher.
        args = [sys.executable, sys.executable,
                os.path.join(config.BIN_DIR, 'master')]
        if parser.options.force:
            args.append('--force')
        if parser.options.config:
            args.extend(['-C', parser.options.config])
        log.debug('starting: %s', args)
        os.execl(*args)
        # We should never get here.
        raise RuntimeError('os.execl() failed')



if __name__ == '__main__':
    main()
