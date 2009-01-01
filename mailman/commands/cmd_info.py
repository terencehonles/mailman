# Copyright (C) 2002-2009 by the Free Software Foundation, Inc.
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
    info
        Get information about this mailing list.
"""

from mailman.i18n import _

STOP = 1



def gethelp(mlist):
    return _(__doc__)



def process(res, args):
    mlist = res.mlist
    if args:
        res.results.append(gethelp(mlist))
        return STOP
    listname = mlist.real_name
    description = mlist.description or _('n/a')
    postaddr = mlist.posting_address
    requestaddr = mlist.request_address
    owneraddr = mlist.owner_address
    listurl = mlist.script_url('listinfo')
    res.results.append(_('List name:    %(listname)s'))
    res.results.append(_('Description:  %(description)s'))
    res.results.append(_('Postings to:  %(postaddr)s'))
    res.results.append(_('List Helpbot: %(requestaddr)s'))
    res.results.append(_('List Owners:  %(owneraddr)s'))
    res.results.append(_('More information: %(listurl)s'))
