# Copyright (C) 1998-2009 by the Free Software Foundation, Inc.
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

import sys
import getpass
import optparse

from mailman import Utils
from mailman import passwords
from mailman.configuration import config
from mailman.core.i18n import _
from mailman.initialize import initialize
from mailman.version import MAILMAN_VERSION



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] [password]

Set the site or list creator password.

The site password can be used in most if not all places that the list
administrator's password can be used, which in turn can be used in most places
that a list user's password can be used.  The list creator password is a
separate password that can be given to non-site administrators to delegate the
ability to create new mailing lists.

If password is not given on the command line, it will be prompted for.
"""))
    parser.add_option('-c', '--listcreator',
                      default=False, action='store_true',
                      help=_("""\
Set the list creator password instead of the site password.  The list
creator is authorized to create and remove lists, but does not have
the total power of the site administrator."""))
    parser.add_option('-p', '--password-scheme',
                      default='', type='string',
                      help=_("""\
Specify the RFC 2307 style hashing scheme for passwords included in the
output.  Use -P to get a list of supported schemes, which are
case-insensitive."""))
    parser.add_option('-P', '--list-hash-schemes',
                      default=False, action='store_true', help=_("""\
List the supported password hashing schemes and exit.  The scheme labels are
case-insensitive."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if len(args) > 1:
        parser.error(_('Unexpected arguments'))
    if opts.list_hash_schemes:
        for label in passwords.Schemes:
            print str(label).upper()
        sys.exit(0)
    return parser, opts, args


def check_password_scheme(parser, password_scheme):
    # shoule be checked after config is loaded.
    if password_scheme == '':
        password_scheme = config.PASSWORD_SCHEME
    scheme = passwords.lookup_scheme(password_scheme.lower())
    if not scheme:
        parser.error(_('Invalid password scheme'))
    return scheme



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)
    opts.password_scheme = check_password_scheme(parser, opts.password_scheme)
    if args:
        password = args[0]
    else:
        # Prompt for the password
        if opts.listcreator:
            prompt_1 = _('New list creator password: ')
        else:
            prompt_1 = _('New site administrator password: ')
        pw1 = getpass.getpass(prompt_1)
        pw2 = getpass.getpass(_('Enter password again to confirm: '))
        if pw1 <> pw2:
            print _('Passwords do not match; no changes made.')
            sys.exit(1)
        password = pw1
    Utils.set_global_password(password,
                              not opts.listcreator, opts.password_scheme)
    if Utils.check_global_password(password, not opts.listcreator):
        print _('Password changed.')
    else:
        print _('Password change failed.')



if __name__ == '__main__':
    main()
