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
    'DomainSet',
    ]


from zope.interface import implements
from zope.publisher.interfaces import NotFound

from mailman.interfaces.domain import IDomainSet
from mailman.interfaces.rest import IResolvePathNames



class DomainSet:
    """Sets of known domains."""

    implements(IDomainSet, IResolvePathNames)

    __name__ = 'domains'

    def __init__(self, config):
        self._config = config

    def get_domains(self):
        """See `IDomainSet`."""
        # lazr.restful will not allow this to be a generator.
        domains = self._config.domains
        return [domains[domain] for domain in sorted(domains)]

    def get(self, name):
        """See `IResolvePathNames`."""
        domain = self._config.domains.get(name)
        if domain is None:
            raise NotFound(self, name)
        return domain
