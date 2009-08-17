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
    'AdminWebServicePublication',
    ]


import traceback

from lazr.restful.publisher import WebServicePublicationMixin
from lazr.restful.simple import Publication
from zope.component import queryMultiAdapter
from zope.publisher.interfaces import NotFound

from mailman.config import config
from mailman.interfaces.rest import IResolvePathNames



class AdminWebServicePublication(Publication):
    """Very simple implementation of `IPublication`."""

    def traverseName(self, request, ob, name):
        """See `IPublication`."""
        missing = object()
        resolver = IResolvePathNames(ob, missing)
        if resolver is missing:
            raise NotFound(ob, name, request)
        next_step = resolver.get(name)
        if next_step is None:
            raise NotFound(ob, name, request)
        return next_step

    def handleException(self, application, request, exc_info,
                        retry_allowed=True):
        """See `IPublication`."""
        # Any in-progress transaction must be aborted.
        config.db.abort()
        # XXX BAW 2009-08-06 This should not be necessary.  I need to register
        # a view so that 404 will be returned for a NotFound.
        exception = exc_info[1]
        if isinstance(exception, NotFound):
            request.response.reset()
            request.response.setStatus(404)
            request.response.setResult('')
        else:
            super(AdminWebServicePublication, self).handleException(
                application, request, exc_info, retry_allowed)

    def endRequest(self, request, ob):
        """Ends the interaction."""
        config.db.commit()
        super(AdminWebServicePublication, self).endRequest(request, ob)
