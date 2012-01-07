# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""One last digest."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IOneLastDigest'
    ]


from flufl.enum import Enum
from zope.interface import Interface, Attribute



class DigestFrequency(Enum):
    yearly = 0
    monthly = 1
    quarterly = 2
    weekly = 3
    daily = 4



class IOneLastDigest(Interface):
    """Users who should receive one last digest."""

    mailing_list = Attribute(
        """The mailing list for the one last digest.""")

    address = Attribute(
        """The address to receive the one last digest.""")

    delivery_mode = Attribute(
        """The digest delivery mode to send.""")
