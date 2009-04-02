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

"""Traversal rules for the Mailman RESTful admin web service."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Traverse',
    ]


from urllib import unquote

from zope.component import adapts
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse, NotFound
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from mailman.interfaces.rest import IHasGet



class Traverse:
    """An implementation of `IPublishTraverse` that uses the get() method."""

    implements(IPublishTraverse)
    adapts(IHasGet, IDefaultBrowserLayer)

    def __init__(self, context, request):
        self.context = context

    def publishTraverse(self, request, name):
        """See `IPublishTraverse`."""
        name = unquote(name)
        value = self.context.get(name)
        if value is None:
            raise NotFound(self, name)
        return value
