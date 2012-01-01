# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Application level domain support."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'handle_DomainDeletingEvent',
    ]


from zope.component import getUtility

from mailman.interfaces.domain import DomainDeletingEvent
from mailman.interfaces.listmanager import IListManager



def handle_DomainDeletingEvent(event):
    """Delete all mailing lists in a domain when the domain is deleted."""

    if not isinstance(event, DomainDeletingEvent):
        return
    list_manager = getUtility(IListManager)
    for mailing_list in event.domain.mailing_lists:
        list_manager.delete(mailing_list)
