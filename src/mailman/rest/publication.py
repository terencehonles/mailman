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
from zope.component import queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces import IPublication, NotFound
from zope.publisher.publish import mapply
from zope.security.management import endInteraction, newInteraction

from mailman.config import config
from mailman.interfaces.rest import IResolvePathNames



class Publication:
    """Very simple implementation of `IPublication`."""

    implements(IPublication)

    def __init__(self, application):
        self.application = application

    def beforeTraversal(self, request):
        """See `IPublication`."""
        endInteraction()
        newInteraction(request)

    def getApplication(self, request):
        """See `IPublication`."""
        return self.application

    def callTraversalHooks(self, request, ob):
        """See `IPublication`."""
        pass

    def traverseName(self, request, ob, name):
        """See `IPublication`."""
        missing = object()
        resolver = IResolvePathNames(ob, missing)
        if resolver is missing:
            raise NotFound(ob, name, request)
        return ob.get(name)

    def afterTraversal(self, request, ob):
        """See `IPublication`."""
        pass

    def callObject(self, request, ob):
        """See `IPublication`."""
        return ob()

    def afterCall(self, request, ob):
        """See `IPublication`."""
        pass

    def handleException(self, application, request, exc_info,
                        retry_allowed=True):
        """See `IPublication`."""
        # Any in-progress transaction must be aborted.
        config.db.abort()
        exception = exc_info[1]
        if isinstance(exception, NotFound):
            request.response.reset()
            request.response.setStatus(404)
            request.response.setResult('')
        else:
            traceback.print_exception(*exc_info)

    def endRequest(self, request, ob):
        """Ends the interaction."""
        config.db.commit()
        endInteraction()



class AdminWebServicePublication(WebServicePublicationMixin, Publication):
    """A publication that mixes in the necessary web service stuff."""
