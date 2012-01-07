# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

import os
import sys
import pwd
import grp
import errno
import optparse

from stat import *

from mailman.configuration import config
from mailman.core.i18n import _
from mailman.version import MAILMAN_VERSION


# XXX Need to check the archives/private/*/database/* files



class State:
    FIX = False
    VERBOSE = False
    ERRORS = 0

STATE = State()

DIRPERMS            = S_ISGID | S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH
QFILEPERMS          = S_ISGID | S_IRWXU | S_IRWXG
PYFILEPERMS         = S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH
ARTICLEFILEPERMS    = S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP
MBOXPERMS           = S_IRGRP | S_IWGRP | S_IRUSR | S_IWUSR
PRIVATEPERMS        = QFILEPERMS



def statmode(path):
    return os.stat(path).st_mode


def statgidmode(path):
    stat = os.stat(path)
    return stat.st_mode, stat.st_gid


seen = {}

# libc's getgrgid re-opens /etc/group each time :(
_gidcache = {}

def getgrgid(gid):
    data = _gidcache.get(gid)
    if data is None:
        data = grp.getgrgid(gid)
        _gidcache[gid] = data
    return data



def checkwalk(arg, dirname, names):
    # Short-circuit duplicates
    if seen.has_key(dirname):
        return
    seen[dirname] = True
    for name in names:
        path = os.path.join(dirname, name)
        if arg.VERBOSE:
            print _('    checking gid and mode for $path')
        try:
            mode, gid = statgidmode(path)
        except OSError, e:
            if e.errno != errno.ENOENT: raise
            continue
        if gid != MAILMAN_GID:
            try:
                groupname = getgrgid(gid)[0]
            except KeyError:
                groupname = '<anon gid %d>' % gid
            arg.ERRORS += 1
            print _(
                '$path bad group (has: $groupname, expected $MAILMAN_GROUP)'),
            if STATE.FIX:
                print _('(fixing)')
                os.chown(path, -1, MAILMAN_GID)
            else:
                print
        # Most directories must be at least rwxrwsr-x.
        # The private archive directory  and database directory must be at
        # least rwxrws---.  Their 'other' permissions are checked in
        # checkarchives() and checkarchivedbs() below.  Their 'user' and
        # 'group' permissions are checked here.
        # The directories under qfiles should be rwxrws---.  Their 'user' and
        # 'group' permissions are checked here.  Their 'other' permissions
        # aren't checked.
        private = config.PRIVATE_ARCHIVE_FILE_DIR
        if path == private or (
            os.path.commonprefix((path, private)) == private
            and os.path.split(path)[1] == 'database'):
            # then...
            targetperms = PRIVATEPERMS
        elif (os.path.commonprefix((path, config.QUEUE_DIR))
              == config.QUEUE_DIR):
            targetperms = QFILEPERMS
        else:
            targetperms = DIRPERMS
        octperms = oct(targetperms)
        if S_ISDIR(mode) and (mode & targetperms) != targetperms:
            arg.ERRORS += 1
            print _('directory permissions must be $octperms: $path'),
            if STATE.FIX:
                print _('(fixing)')
                os.chmod(path, mode | targetperms)
            else:
                print
        elif os.path.splitext(path)[1] in ('.py', '.pyc', '.pyo'):
            octperms = oct(PYFILEPERMS)
            if mode & PYFILEPERMS != PYFILEPERMS:
                print _('source perms must be $octperms: $path'),
                arg.ERRORS += 1
                if STATE.FIX:
                    print _('(fixing)')
                    os.chmod(path, mode | PYFILEPERMS)
                else:
                    print
        elif path.endswith('-article'):
            # Article files must be group writeable
            octperms = oct(ARTICLEFILEPERMS)
            if mode & ARTICLEFILEPERMS != ARTICLEFILEPERMS:
                print _('article db files must be $octperms: $path'),
                arg.ERRORS += 1
                if STATE.FIX:
                    print _('(fixing)')
                    os.chmod(path, mode | ARTICLEFILEPERMS)
                else:
                    print



def checkall():
    # first check PREFIX
    if STATE.VERBOSE:
        prefix = config.PREFIX
        print _('checking mode for $prefix')
    dirs = {}
    for d in (config.PREFIX, config.EXEC_PREFIX, config.VAR_PREFIX,
              config.LOG_DIR):
        dirs[d] = True
    for d in dirs.keys():
        try:
            mode = statmode(d)
        except OSError, e:
            if e.errno != errno.ENOENT: raise
            print _('WARNING: directory does not exist: $d')
            continue
        if (mode & DIRPERMS) != DIRPERMS:
            STATE.ERRORS += 1
            print _('directory must be at least 02775: $d'),
            if STATE.FIX:
                print _('(fixing)')
                os.chmod(d, mode | DIRPERMS)
            else:
                print
        # check all subdirs
        os.path.walk(d, checkwalk, STATE)



def checkarchives():
    private = config.PRIVATE_ARCHIVE_FILE_DIR
    if STATE.VERBOSE:
        print _('checking perms on $private')
    # private archives must not be other readable
    mode = statmode(private)
    if mode & S_IROTH:
        STATE.ERRORS += 1
        print _('$private must not be other-readable'),
        if STATE.FIX:
            print _('(fixing)')
            os.chmod(private, mode & ~S_IROTH)
        else:
            print
    # In addition, on a multiuser system you may want to hide the private
    # archives so other users can't read them.
    if mode & S_IXOTH:
        print _("""\
Warning: Private archive directory is other-executable (o+x).
         This could allow other users on your system to read private archives.
         If you're on a shared multiuser system, you should consult the
         installation manual on how to fix this.""")



def checkmboxfile(mboxdir):
    absdir = os.path.join(config.PRIVATE_ARCHIVE_FILE_DIR, mboxdir)
    for f in os.listdir(absdir):
        if not f.endswith('.mbox'):
            continue
        mboxfile = os.path.join(absdir, f)
        mode = statmode(mboxfile)
        if (mode & MBOXPERMS) != MBOXPERMS:
            STATE.ERRORS = STATE.ERRORS + 1
            print _('mbox file must be at least 0660:'), mboxfile
            if STATE.FIX:
                print _('(fixing)')
                os.chmod(mboxfile, mode | MBOXPERMS)
            else:
                print



def checkarchivedbs():
    # The archives/private/listname/database file must not be other readable
    # or executable otherwise those files will be accessible when the archives
    # are public.  That may not be a horrible breach, but let's close this off
    # anyway.
    for dir in os.listdir(config.PRIVATE_ARCHIVE_FILE_DIR):
        if dir.endswith('.mbox'):
            checkmboxfile(dir)
        dbdir = os.path.join(config.PRIVATE_ARCHIVE_FILE_DIR, dir, 'database')
        try:
            mode = statmode(dbdir)
        except OSError, e:
            if e.errno not in (errno.ENOENT, errno.ENOTDIR): raise
            continue
        if mode & S_IRWXO:
            STATE.ERRORS += 1
            print _('$dbdir "other" perms must be 000'),
            if STATE.FIX:
                print _('(fixing)')
                os.chmod(dbdir, mode & ~S_IRWXO)
            else:
                print



def checkcgi():
    cgidir = os.path.join(config.EXEC_PREFIX, 'cgi-bin')
    if STATE.VERBOSE:
        print _('checking cgi-bin permissions')
    exes = os.listdir(cgidir)
    for f in exes:
        path = os.path.join(cgidir, f)
        if STATE.VERBOSE:
            print _('    checking set-gid for $path')
        mode = statmode(path)
        if mode & S_IXGRP and not mode & S_ISGID:
            STATE.ERRORS += 1
            print _('$path must be set-gid'),
            if STATE.FIX:
                print _('(fixing)')
                os.chmod(path, mode | S_ISGID)
            else:
                print



def checkmail():
    wrapper = os.path.join(config.WRAPPER_DIR, 'mailman')
    if STATE.VERBOSE:
        print _('checking set-gid for $wrapper')
    mode = statmode(wrapper)
    if not mode & S_ISGID:
        STATE.ERRORS += 1
        print _('$wrapper must be set-gid'),
        if STATE.FIX:
            print _('(fixing)')
            os.chmod(wrapper, mode | S_ISGID)



def checkadminpw():
    for pwfile in (os.path.join(config.DATA_DIR, 'adm.pw'),
                   os.path.join(config.DATA_DIR, 'creator.pw')):
        targetmode = S_IFREG | S_IRUSR | S_IWUSR | S_IRGRP
        if STATE.VERBOSE:
            print _('checking permissions on $pwfile')
        try:
            mode = statmode(pwfile)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
            return
        if mode != targetmode:
            STATE.ERRORS += 1
            octmode = oct(mode)
            print _('$pwfile permissions must be exactly 0640 (got $octmode)'),
            if STATE.FIX:
                print _('(fixing)')
                os.chmod(pwfile, targetmode)
            else:
                print


def checkmta():
    if config.MTA:
        modname = 'mailman.MTA.' + config.MTA
        __import__(modname)
        try:
            sys.modules[modname].checkperms(STATE)
        except AttributeError:
            pass



def checkdata():
    targetmode = S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP
    checkfiles = ('config.pck', 'config.pck.last',
                  'config.db', 'config.db.last',
                  'next-digest', 'next-digest-topics',
                  'digest.mbox', 'pending.pck',
                  'request.db', 'request.db.tmp')
    if STATE.VERBOSE:
        print _('checking permissions on list data')
    for dir in os.listdir(config.LIST_DATA_DIR):
        for file in checkfiles:
            path = os.path.join(config.LIST_DATA_DIR, dir, file)
            if STATE.VERBOSE:
                print _('    checking permissions on: $path')
            try:
                mode = statmode(path)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
                continue
            if (mode & targetmode) != targetmode:
                STATE.ERRORS += 1
                print _('file permissions must be at least 660: $path'),
                if STATE.FIX:
                    print _('(fixing)')
                    os.chmod(path, mode | targetmode)
                else:
                    print



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Check the permissions of all Mailman files.  With no options, just report the
permission and ownership problems found."""))
    parser.add_option('-f', '--fix',
                      default=False, action='store_true', help=_("""\
Fix all permission and ownership problems found.  With this option, you must
run check_perms as root."""))
    parser.add_option('-v', '--verbose',
                      default=False, action='store_true',
                      help=_('Produce more verbose output'))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    return parser, opts, args



def main():
    global MAILMAN_USER, MAILMAN_GROUP, MAILMAN_UID, MAILMAN_GID

    parser, opts, args = parseargs()
    STATE.FIX = opts.fix
    STATE.VERBOSE = opts.verbose

    config.load(opts.config)

    MAILMAN_USER  = config.MAILMAN_USER
    MAILMAN_GROUP = config.MAILMAN_GROUP
    # Let KeyErrors percolate
    MAILMAN_GID = grp.getgrnam(MAILMAN_GROUP).gr_gid
    MAILMAN_UID = pwd.getpwnam(MAILMAN_USER).pw_uid

    checkall()
    checkarchives()
    checkarchivedbs()
    checkcgi()
    checkmail()
    checkdata()
    checkadminpw()
    checkmta()

    if not STATE.ERRORS:
        print _('No problems found')
    else:
        print _('Problems found:'), STATE.ERRORS
        print _('Re-run as $MAILMAN_USER (or root) with -f flag to fix')


if __name__ == '__main__':
    main()
