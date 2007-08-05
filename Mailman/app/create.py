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

"""Application level list creation."""

from Mailman import Errors
from Mailman import Utils
from Mailman.Utils import ValidateEmail
from Mailman.app.plugins import get_plugin
from Mailman.app.styles import style_manager
from Mailman.configuration import config



def create_list(fqdn_listname):
    """Create the named list and apply styles."""
    ValidateEmail(fqdn_listname)
    listname, domain = Utils.split_listname(fqdn_listname)
    if domain not in config.domains:
        raise Errors.BadDomainSpecificationError(domain)
    mlist = config.db.list_manager.create(fqdn_listname)
    for style in style_manager.lookup(mlist):
        # XXX FIXME.  When we get rid of the wrapper object, this hack won't
        # be necessary.  Until then, setattr on the MailList instance won't
        # set the database column values, so pass the underlying database
        # object to .apply() instead.
        style.apply(mlist._data)
    # Coordinate with the MTA, which should be defined by plugins.
    # XXX FIXME
##     mta_plugin = get_plugin('mailman.mta')
##     mta_plugin().create(mlist)
    return mlist
