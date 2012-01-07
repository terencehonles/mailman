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

"""MIME content filtering."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'FilterAction',
    'FilterType',
    'IContentFilter',
    ]


from flufl.enum import Enum
from zope.interface import Interface, Attribute



class FilterAction(Enum):
    # Discard a message that matches the content type filter.
    discard = 0
    # Bounce the message back to the original author.
    bounce = 1
    # Discard and forward the message on to the list owner.
    forward = 2
    # Discard, but preserve it.
    preserve = 3


class FilterType(Enum):
    # Filter MIME type.
    filter_mime = 0
    # Pass MIME type.
    pass_mime = 1
    # Filter file extension.
    filter_extension = 2
    # Pass file extension.
    pass_extension = 3



class IContentFilter(Interface):
    """A single content filter settings for a mailing list."""

    mailing_list = Attribute(
        """The mailing list for this content filter.""")

    filter_pattern = Attribute(
        """The filter/pass content pattern.""")

    filter_type = Attribute(
        """Type of filter.""")
