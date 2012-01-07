# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
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

"""Creation/deletion hooks for the MTAs that do things automatically.

Exim one example of an MTA that Just Works.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'NullMTA',
    ]


from zope.interface import implements
from mailman.interfaces.mta import IMailTransportAgentLifecycle



class NullMTA:
    """Null MTA that just satisfies the interface."""

    implements(IMailTransportAgentLifecycle)

    def create(self, mlist):
        """See `IMailTransportAgentLifecycle`."""
        pass

    def delete(self, mlist):
        """See `IMailTransportAgentLifecycle`."""
        pass

    def regenerate(self, output=None):
        """See `IMailTransportAgentLifecycle`."""
        pass
