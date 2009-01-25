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

from mailman.app.lifecycle import remove_list
from mailman.config import config
from mailman.i18n import _
from mailman.options import MultipleMailingListOptions



class ScriptOptions(MultipleMailingListOptions):
    usage = _("""\
%prog [options]

Remove the components of a mailing list with impunity - beware!

This removes (almost) all traces of a mailing list.  By default, the lists
archives are not removed, which is very handy for retiring old lists.
""")

    def add_options(self):
        super(ScriptOptions, self).add_options()
        self.parser.add_option(
            '-a', '--archives',
            default=False, action='store_true',
            help=_("""\
Remove the list's archives too, or if the list has already been deleted,
remove any residual archives."""))
        self.parser.add_option(
            '-q', '--quiet',
            default=False, action='store_true',
            help=_('Suppress status messages'))

    def sanity_check(self):
        if len(self.options.listnames) == 0:
            self.parser.error(_('Nothing to do'))
        if len(self.arguments) > 0:
            self.parser.error(_('Unexpected arguments'))



def main():
    options = ScriptOptions()
    options.initialize()

    for fqdn_listname in options.options.listnames:
        if not options.options.quiet:
            print _('Removing list: $fqdn_listname')
        mlist = config.db.list_manager.get(fqdn_listname)
        if mlist is None:
            if options.options.archives:
                print _("""\
No such list: ${fqdn_listname}.  Removing its residual archives.""")
            else:
                print >> sys.stderr, _(
                    'No such list (or list already deleted): $fqdn_listname')

        if not options.options.archives:
            print _('Not removing archives.  Reinvoke with -a to remove them.')

        remove_list(fqdn_listname, mlist, options.options.archives)
        config.db.commit()



if __name__ == '__main__':
    main()
