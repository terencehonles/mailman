# Copyright (C) 1998-2007 by the Free Software Foundation, Inc.
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

import os
import sys
import shutil
import optparse

from Mailman import Errors
from Mailman import Utils
from Mailman import Version
from Mailman.MailList import MailList
from Mailman.app.lifecycle import remove_list
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.initialize import initialize


__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] listname

Remove the components of a mailing list with impunity - beware!

This removes (almost) all traces of a mailing list.  By default, the lists
archives are not removed, which is very handy for retiring old lists.
"""))
    parser.add_option('-a', '--archives',
                      default=False, action='store_true', help=_("""\
Remove the list's archives too, or if the list has already been deleted,
remove any residual archives."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if not args:
        parser.error(_('Missing listname'))
    if len(args) > 1:
        parser.error(_('Unexpected arguments'))
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    fqdn_listname = args[0]
    mlist = config.db.list_manager.get(fqdn_listname)
    if mlist is None:
        if not opts.archives:
            print >> sys.stderr, _(
                'No such list (or list already deleted): $fqdn_listname')
            sys.exit(1)
        else:
            print _("""\
No such list: ${fqdn_listname}.  Removing its residual archives.""")

    if not opts.archives:
        print _('Not removing archives.  Reinvoke with -a to remove them.')

    remove_list(fqdn_listname, mlist, opts.archives)
    config.db.flush()



if __name__ == '__main__':
    main()
