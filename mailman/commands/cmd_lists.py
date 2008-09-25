# Copyright (C) 2002-2008 by the Free Software Foundation, Inc.
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

"""
    lists
        See a list of the public mailing lists on this GNU Mailman server.
"""

from mailman.MailList import MailList
from mailman.configuration import config
from mailman.i18n import _


STOP = 1



def gethelp(mlist):
    return _(__doc__)



def process(res, args):
    mlist = res.mlist
    if args:
        res.results.append(_('Usage:'))
        res.results.append(gethelp(mlist))
        return STOP
    hostname = mlist.host_name
    res.results.append(_('Public mailing lists at %(hostname)s:'))
    i = 1
    for listname in sorted(config.list_manager.names):
        if listname == mlist.internal_name():
            xlist = mlist
        else:
            xlist = MailList(listname, lock=0)
        # We can mention this list if you already know about it
        if not xlist.advertised and xlist is not mlist:
            continue
        # Skip the list if it isn't in the same virtual domain.
        if xlist.host_name <> mlist.host_name:
            continue
        realname = xlist.real_name
        description = xlist.description or _('n/a')
        requestaddr = xlist.GetRequestEmail()
        if i > 1:
            res.results.append('')
        res.results.append(_('%(i)3d. List name:   %(realname)s'))
        res.results.append(_('     Description: %(description)s'))
        res.results.append(_('     Requests to: %(requestaddr)s'))
        i += 1
