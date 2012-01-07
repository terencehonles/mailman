# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""Interface for a web request accessing a mailing list."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IMailingListRequest',
    ]


from zope.interface import Interface, Attribute



class IMailingListRequest(Interface):
    """The web request accessing a mailing list."""

    location = Attribute(
        """The url location of the request, used to calculate relative urls by
        other components.""")
