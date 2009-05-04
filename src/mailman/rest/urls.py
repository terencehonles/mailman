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

from mailman.config import config
from mailman.core.system import system
from mailman.rest.configuration import AdminWebServiceConfiguration
from mailman.rest.webservice import AdminWebServiceApplication



class AbsoluteURLMapper:
    """Generic absolute url mapper."""

    implements(IAbsoluteURL)

    def __init__(self, context, request):
        """Initialize with respect to a context and request."""
        self.context = context
        self.request = request
        self.webservice_config = AdminWebServiceConfiguration()
        self.version = self.webservice_config.service_version_uri_prefix
        self.schema = ('https' if self.webservice_config.use_https else 'http')
        self.hostname = config.webservice.hostname
        self.port = int(config.webservice.port)

    def __str__(self):
        """Return the semi-hard-coded URL to the service root."""
        path = self[self.context]
        return '{0.schema}://{0.hostname}:{0.port}/{0.version}/{1}'.format(
            self, path)

    __call__ = __str__

    def __getitem__(self, ob):
        """Return the path component for the object.

        :param ob: The object we're looking for.
        :type ob: anything
        :return: The path component.
        :rtype: string
        :raises KeyError: if no path component can be found.
        """
        # Special cases.
        if isinstance(ob, AdminWebServiceApplication):
            return ''
        urls = {
            system: 'system',
            }
        return urls[ob]
