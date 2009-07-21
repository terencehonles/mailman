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

from zope.interface import implements
from zope.publisher.interfaces import NotFound

from mailman.interfaces.domain import IDomainCollection
from mailman.interfaces.rest import IResolvePathNames



class DomainCollection:
    """Sets of known domains."""

    implements(IDomainCollection, IResolvePathNames)

    __name__ = 'domains'

    def __init__(self, manager):
        """Initialize the adapter from an `IDomainManager`.

        :param manager: The domain manager.
        :type manager: `IDomainManager`.
        """
        self._manager = manager

    def get_domains(self):
        """See `IDomainCollection`."""
        # lazr.restful requires the return value to be a concrete list.
        return sorted(self._manager, key=attrgetter('email_host'))

    def get(self, name):
        """See `IResolvePathNames`."""
        domain = self._manager.get(name)
        if domain is None:
            raise NotFound(self, name)
        return domain

    def new(self, email_host, description=None, base_url=None,
            contact_address=None):
        """See `IDomainCollection`."""
        value = self._manager.add(
            email_host, description, base_url, contact_address)
        return value
