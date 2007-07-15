# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

from __future__ import with_statement

import os
import grp
import pwd
import sys
import optparse
import setuptools
from string import Template

import Mailman
from Mailman.Version import MAILMAN_VERSION

# Until an instance is actually created, this module won't be importable
# because the Defaults.py module won't have been created yet.
try:
    from Mailman.i18n import _
except ImportError:
    def _(s): return s

__i18n_templates__ = True
SPACE = ' '
DEFAULT_RUNTIME_DIR = '/var/mailman'



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Create a Mailman instance by generating all the necessary basic configuration
support and intervening directories.
"""))
    parser.add_option('-r', '--runtime-dir',
                      type='string', default=DEFAULT_RUNTIME_DIR, help=_("""\
The top-level runtime data directory.  All supporting runtime data will be
placed in subdirectories of this directory.  It will be created if necessary,
although this might require superuser privileges."""))
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
    parser.add_option('-l', '--language',
                      default=[], type='string', action='append', help=_("""\
Enable the given language.  Use 'all' to enable all supported languages."""))
    opts, args = parser.parse_args()
    if args:
        unexpected = SPACE.join(args)
        parser.print_error(_('Unexpected arguments: $unexpected'))
    return parser, opts, args



def instantiate(user=None, group=None, runtime_dir=None):
    # Create the Defaults.py file using substitutions.
    in_file_path = os.path.join(os.path.dirname(Mailman.__file__),
                                'Defaults.py.in')
    out_file_path = os.path.splitext(in_file_path)[0]
    with open(in_file_path) as fp:
        raw = Template(fp.read())
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
    # Process the .in file and write it to Defaults.py.
    processed = raw.safe_substitute(runtime_dir=runtime_dir,
                                    user_name=user_name,
                                    group_name=group_name)
    with open(out_file_path, 'w') as fp:
        fp.write(processed)
    # XXX Do --permchecks
    # XXX Do --language
    


def main():
    parser, opts, args = parseargs()
    instantiate(opts.user, opts.group, opts.runtime_dir)



if __name__ == '__main__':
    main()

