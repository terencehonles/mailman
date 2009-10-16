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

"""Mailman admin web service configuration."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AdminWebServiceConfiguration',
    ]


from lazr.config import as_boolean
from lazr.restful.interfaces import IWebServiceConfiguration
from lazr.restful.wsgi import BaseWSGIWebServiceConfiguration
from zope.interface import implements

from mailman import version
from mailman.config import config



# pylint: disable-msg=W0232,R0201
class AdminWebServiceConfiguration(BaseWSGIWebServiceConfiguration):
    """A configuration object for the Mailman admin web service."""

    implements(IWebServiceConfiguration)

    @property
    def view_permission(self):
        """See `IWebServiceConfiguration`."""
        if config.webservice.view_permission.lower() == 'none':
            return None
        return config.webservice.view_permission

    path_override = None

    @property
    def use_https(self):
        """See `IWebServiceConfiguration`."""
        return as_boolean(config.webservice.use_https)

    # This should match the major.minor Mailman version.
    service_version_uri_prefix = '{0.MAJOR_REV}.{0.MINOR_REV}'.format(version)
    code_revision = version.VERSION

    @property
    def show_tracebacks(self):
        """See `IWebServiceConfiguration`."""
        return config.webservice.show_tracebacks
        
    default_batch_size = 50
    max_batch_size = 300

    def get_request_user(self):
        """See `IWebServiceConfiguration`."""
        return None
