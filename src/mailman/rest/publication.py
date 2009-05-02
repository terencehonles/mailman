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

from mailman.interfaces.rest import IResolvePathNames



class Publication:
    """Very simple implementation of `IPublication`."""
    implements(IPublication)

    def __init__(self, application):
        self.application = application

    def beforeTraversal(self, request):
        """See `IPublication`."""
        pass

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
        pass

    def callObject(self, request, ob):
        """Call the object, returning the result."""
        # XXX Bad hack.
        from zope.security.proxy import removeSecurityProxy
        ob = removeSecurityProxy(ob)
        return mapply(ob, request.getPositionalArguments(), request)

    def afterCall(self, request, ob):
        pass

    def handleException(self, object, request, exc_info, retry_allowed=1):
        """Prints the exception."""
        # Reproduce the behavior of ZopePublication by looking up a view
        # for this exception.
        exception = exc_info[1]
        view = queryMultiAdapter((exception, request), name='index.html')
        if view is not None:
            exc_info = None
            request.response.reset()
            request.response.setResult(view())
        else:
            traceback.print_exception(*exc_info)

    def endRequest(self, request, ob):
        """Ends the interaction."""
        endInteraction()



class AdminWebServicePublication(WebServicePublicationMixin, Publication):
    """A publication that mixes in the necessary web service stuff."""
