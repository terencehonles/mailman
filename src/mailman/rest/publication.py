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
from zope.component import getUtility, queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces import IPublication, IPublishTraverse, NotFound
from zope.publisher.publish import mapply
from zope.security.checker import ProxyFactory
from zope.security.management import endInteraction, newInteraction



class Publication:
    """Very simple implementation of `IPublication`.

    The object pass to the constructor is returned by getApplication().
    """
    implements(IPublication)

    def __init__(self, application):
        """Create the test publication.

        The object at which traversal should start is passed as parameter.
        """
        self.application = application

    def beforeTraversal(self, request):
        """Sets the request as the current interaction.

        (It also ends any previous interaction, that's convenient when
        tests don't go through the whole request.)
        """
        endInteraction()
        newInteraction(request)

    def getApplication(self, request):
        """Returns the application passed to the constructor."""
        return self.application

    def callTraversalHooks(self, request, ob):
        """Does nothing."""

    def traverseName(self, request, ob, name):
        """Traverse by looking at an `IPublishTraverse` adapter.

        The object is security wrapped.
        """
        # XXX flacoste 2009/03/06 bug=338831. This is copied from
        # zope.app.publication.publicationtraverse.PublicationTraverse.
        # This should really live in zope.publisher, we are copying because
        # we don't want to depend on zope.app stuff.
        # Namespace support was dropped.
        if name == '.':
            return ob

        if IPublishTraverse.providedBy(ob):
            ob2 = ob.publishTraverse(request, name)
        else:
            # self is marker.
            adapter = queryMultiAdapter(
                (ob, request), IPublishTraverse, default=self)
            if adapter is not self:
                ob2 = adapter.publishTraverse(request, name)
            else:
                raise NotFound(ob, name, request)

        return ProxyFactory(ob2)

    def afterTraversal(self, request, ob):
        """Does nothing."""

    def callObject(self, request, ob):
        """Call the object, returning the result."""
        return mapply(ob, request.getPositionalArguments(), request)

    def afterCall(self, request, ob):
        """Does nothing."""

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
