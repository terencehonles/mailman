# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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
import grp
import pwd
import sys
import errno
import shutil
import optparse
import setuptools

from pkg_resources import resource_string
from string import Template

from mailman import Defaults
from mailman.version import MAILMAN_VERSION
from mailman.i18n import _


SPACE = ' '



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Create a Mailman instance by generating all the necessary basic configuration
support and intervening directories.
"""))
    parser.add_option('-d', '--var-dir',
                      type='string', default=Defaults.DEFAULT_VAR_DIRECTORY,
                      help=_("""\
The top-level runtime data directory.  All supporting runtime data will be
placed in subdirectories of this directory.  It will be created if necessary,
although this might require superuser privileges."""))
    parser.add_option('-f', '--force',
                      default=False, action='store_true', help=_("""\
Force overwriting of mailman.cfg file with new values.  Ordinarily, Mailman
will never overwrite this file because it would cause you to lose your
configuration data."""))
    parser.add_option('-p', '--permchecks',
                      default=False, action='store_true', help=_("""\
Perform permission checks on the runtime directory."""))
    parser.add_option('-u', '--user',
                      type='string', default=None, help=_("""\
The user id or name to use for the runtime environment.  If not specified, the
current user is used."""))
    parser.add_option('-g', '--group',
                      type='string', default=None, help=_("""\
The group id or name to use for the runtime environment.  If not specified, the
current group is used."""))
    parser.add_option('-l', '--languages',
                      default=Defaults.DEFAULT_SERVER_LANGUAGE, type='string',
                      help=_("""\
Space separated list of language codes to enable.  Use -L to print all
available language codes and the name of the associated native language.
Default is to enable just English.  Use the special code 'all' to enable all
available languages."""))
    opts, args = parser.parse_args()
    if args:
        unexpected = SPACE.join(args)
        parser.error(_('Unexpected arguments: $unexpected'))
    return parser, opts, args



def instantiate(var_dir, user, group, languages, force):
    # XXX This needs to be converted to use package resources.
    etc_dir = os.path.join(var_dir, 'etc')
    # Figure out which user name and group name to use.
    if user is None:
        uid = os.getuid()
    else:
        try:
            uid = int(user)
        except ValueError:
            try:
                uid = pwd.getpwnam(user).pw_uid
            except KeyError:
                parser.print_error(_('Unknown user: $user'))
    try:
        user_name = pwd.getpwuid(uid).pw_name
    except KeyError:
        parser.print_error(_('Unknown user: $user'))
    if group is None:
        gid = os.getgid()
    else:
        try:
            gid = int(group)
        except ValueError:
            try:
                gid = grp.getgrnam(group).gr_gid
            except KeyError:
                parser.print_error(_('Unknown group: $group'))
    try:
        group_name = grp.getgrgid(gid).gr_name
    except KeyError:
        parser.print_error(_('Unknown group: $group'))
    # Make the runtime dir if it doesn't yet exist.
    try:
        omask = os.umask(0)
        try:
            os.makedirs(etc_dir, 02775)
        finally:
            os.umask(omask)
    except OSError, e:
        # Ignore the exceptions if the directory already exists
        if e.errno <> errno.EEXIST:
            raise
    os.chown(etc_dir, uid, gid)
    # Create an etc/mailman.cfg file which contains just a few configuration
    # variables about the run-time environment that can't be calculated.
    # Don't overwrite mailman.cfg unless the -f flag was given.
    out_file_path = os.path.join(etc_dir, 'mailman.cfg')
    if os.path.exists(out_file_path) and not force:
        # The logging subsystem isn't up yet, so just print this to stderr.
        print >> sys.stderr, 'File exists:', out_file_path
        print >> sys.stderr, 'Use --force to override.'
    else:
        raw = Template(resource_string('mailman.extras', 'mailman.cfg.in'))
        processed = raw.safe_substitute(var_dir=var_dir,
                                        user_id=uid,
                                        user_name=user_name,
                                        group_name=group_name,
                                        group_id=gid,
                                        languages=SPACE.join(languages),
                                        )
        with open(out_file_path, 'w') as fp:
            fp.write(processed)
    # XXX Do --permchecks
    


def main():
    parser, opts, args = parseargs()
    available_languages = set(Defaults._DEFAULT_LANGUAGE_DATA)
    enable_languages = set(opts.languages.split())
    if 'all' in enable_languages:
        languages = available_languages
    else:
        unknown_language = enable_languages - available_languages
        if unknown_language:
            print >> sys.stderr, 'Ignoring unknown language codes:', \
                  SPACE.join(unknown_language)
        languages = available_languages & enable_languages
    # We need an absolute path for var_dir.
    var_dir = os.path.abspath(opts.var_dir)
    instantiate(var_dir, opts.user, opts.group, languages, opts.force)



if __name__ == '__main__':
    main()

