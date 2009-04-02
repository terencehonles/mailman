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

"""The RESTful service root."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AdminServiceRootResource',
    ]


from lazr.restful import ServiceRootResource
from zope.interface import implements

from mailman.core.system import system
from mailman.interfaces.rest import IHasGet



class AdminServiceRootResource(ServiceRootResource):
    """The root of the Mailman RESTful admin web service."""

    implements(IHasGet)

    def get(self, name):
        """See `IHasGet`."""
        top_level = {
            'sys': system,
            }
        return top_level.get(name)
