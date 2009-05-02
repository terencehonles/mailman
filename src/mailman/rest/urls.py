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
    'AbsoluteURLMapper',
    ]


from zope.component import adapts
from zope.interface import implements, Interface
from zope.traversing.browser.interfaces import IAbsoluteURL



class AbsoluteURLMapper:
    """Generic absolute url mapper."""

    implements(IAbsoluteURL)
    adapts(Interface, IAbsoluteURL)

    def __init__(self, context, request):
        """Initialize with respect to a context and request."""
        # Avoid circular imports.
        from mailman.rest.configuration import AdminWebServiceConfiguration
        self.webservice_config = AdminWebServiceConfiguration()
        self.version = webservice_config.service_version_uri_prefix
        self.schema = ('https' if self.webservice_config.use_https else 'http')
        self.hostname = config.webservice.hostname

    def __str__(self):
        """Return the semi-hard-coded URL to the service root."""
        return '{0.schema}://{0.hostname}/{0.version}'.format(self)

    __call__ = __str__
