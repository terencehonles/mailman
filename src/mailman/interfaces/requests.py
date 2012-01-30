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

"""Interfaces for the request database.

The request database handles events that must be approved by the list
moderators, such as subscription requests and held messages.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IListRequests',
    'RequestType',
    ]


from flufl.enum import Enum
from zope.interface import Interface, Attribute



class RequestType(Enum):
    held_message = 1
    subscription = 2
    unsubscription = 3



class IListRequests(Interface):
    """Held requests for a specific mailing list."""

    mailing_list = Attribute(
        """The IMailingList for these requests.""")

    count = Attribute(
        """The total number of requests held for the mailing list.""")

    def count_of(request_type):
        """The total number of requests held of the given request type.

        :param request_type: A `RequestType` enum value.
        :return: An integer.
        """

    def hold_request(request_type, key, data=None):
        """Hold some data for moderator approval.

        :param request_type: A `RequestType` enum value.
        :param key: The key piece of request data being held.
        :param data: Additional optional data in the form of a dictionary that
            is associated with the held request.
        :return: A unique id for this held request.
        """

    held_requests = Attribute(
        """An iterator over the held requests.

        Returned items have two attributes:
         * `id` is the held request's unique id;
         * `type` is a `RequestType` enum value.
        """)

    def of_type(request_type):
        """An iterator over the held requests of the given type.

        Returned items have two  attributes:
         * `id` is the held request's unique id;
         * `type` is a `RequestType` enum value.

         Only items with a matching `type' are returned.
         """

    def get_request(request_id, request_type):
        """Get the data associated with the request id, or None.

        :param request_id: The unique id for the request.
        :type request_id: int
        :param request_type: Optional request type that the requested id must
            match, otherwise no match is returned.
        :type request_type: `RequestType`
        :return: A 2-tuple of the key and data originally held, or None if the
            `request_id` is not in the database.
        """

    def delete_request(request_id):
        """Delete the request associated with the id.

        :param request_id: The unique id for the request.
        :raises KeyError: If `request_id` is not in the database.
        """
