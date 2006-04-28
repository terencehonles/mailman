# Copyright (C) 1998-2006 by the Free Software Foundation, Inc.
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
import getpass
import optparse

from Mailman import Utils
from Mailman import mm_cfg
from Mailman.i18n import _

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=mm_cfg.MAILMAN_VERSION,
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
    opts, args = parser.parse_args()
    if len(args) > 1:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
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
    Utils.set_global_password(password, not opts.listcreator)
    if Utils.check_global_password(password, not opts.listcreator):
        print _('Password changed.')
    else:
        print _('Password change failed.')



if __name__ == '__main__':
    main()
