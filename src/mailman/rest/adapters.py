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

"""Module stuff."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DomainCollection',
    ]


from operator import attrgetter

from zope.component import getUtility
from zope.interface import implements
from zope.publisher.interfaces import NotFound

from mailman.interfaces.domain import IDomainCollection, IDomainManager
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.membership import ISubscriptionService
from mailman.interfaces.rest import IResolvePathNames



class DomainCollection:
    """Sets of known domains."""

    implements(IDomainCollection, IResolvePathNames)

    __name__ = 'domains'

    def get_domains(self):
        """See `IDomainCollection`."""
        # lazr.restful requires the return value to be a concrete list.
        return sorted(getUtility(IDomainManager), key=attrgetter('email_host'))

    def get(self, name):
        """See `IResolvePathNames`."""
        domain = getUtility(IDomainManager).get(name)
        if domain is None:
            raise NotFound(self, name)
        return domain

    def new(self, email_host, description=None, base_url=None,
            contact_address=None):
        """See `IDomainCollection`."""
        value = getUtility(IDomainManager).add(
            email_host, description, base_url, contact_address)
        return value



class SubscriptionService:
    """Subscription services for the REST API."""

    implements(ISubscriptionService, IResolvePathNames)

    __name__ = 'members'

    def get_members(self):
        """See `ISubscriptionService`."""
        # lazr.restful requires the return value to be a concrete list.
        members = []
        address_of_member = attrgetter('address.address')
        list_manager = getUtility(IListManager)
        for fqdn_listname in sorted(list_manager.names):
            mailing_list = list_manager.get(fqdn_listname)
            members.extend(
                sorted((member for member in mailing_list.owners.members),
                       key=address_of_member))
            members.extend(
                sorted((member for member in mailing_list.moderators.members),
                       key=address_of_member))
            members.extend(
                sorted((member for member in mailing_list.members.members),
                       key=address_of_member))
        return members
