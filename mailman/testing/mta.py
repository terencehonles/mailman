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

"""Fake MTA for testing purposes."""

__metaclass__ = type
__all__ = [
    'FakeMTA',
    ]


from zope.interface import implements

from mailman.interfaces.mta import IMailTransportAgent



class FakeMTA:
    """Fake MTA for testing purposes."""

    implements(IMailTransportAgent)

    def create(self, mlist):
        pass

    def delete(self, mlist):
        pass

    def regenerate(self):
        pass
