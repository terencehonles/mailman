# Copyright (C) 2009 by the Free Software Foundation, Inc.
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

"""Membership interface for REST."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'SubscriptionService',
    ]


from lazr.restful.declarations import (
    collection_default_content, export_as_webservice_collection,
    export_factory_operation)
from zope.interface import Interface

from mailman.core.i18n import _
from mailman.interfaces.member import IMember



class ISubscriptionService(Interface):
    """Subscription services for the REST API."""

    export_as_webservice_collection(IMember)

    @collection_default_content()
    def get_members():
        """Return a sequence of all members of all mailing lists.

        The members are sorted first by fully-qualified mailing list name,
        then by subscribed email address, then by role.  Because the user may
        be a member of the list under multiple roles (e.g. as an owner and as
        a digest member), the member can appear multiple times in this list.
        Roles are sorted by: owner, moderator, member.

        :return: The list of all members.
        :rtype: list of `IMember`
        """
