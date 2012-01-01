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

"""Autoresponder."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ALWAYS_REPLY',
    'IAutoResponseRecord',
    'IAutoResponseSet',
    'Response',
    'ResponseAction',
    ]


from datetime import timedelta
from flufl.enum import Enum
from zope.interface import Interface, Attribute

ALWAYS_REPLY = timedelta()



class Response(Enum):
    # Your message was held for approval.
    hold = 1
    # Email commands, i.e. -request messages.
    command = 2
    # Messages to the list owner/administrator.
    owner = 3
    # Messages to the list's posting address.
    postings = 4



class ResponseAction(Enum):
    # No automatic response.
    none = 0
    # Respond, but discard the original message.
    respond_and_discard = 1
    # Respond and continue processing the message.
    respond_and_continue = 2



class IAutoResponseRecord(Interface):
    """An auto-response record.

    Every time Mailman sends an automatic response to an address, on a
    specific mailing list for a specific purpose, it records the response.  To
    limit the effects of blow back and other third party spam, Mailman will
    only send a certain number of such automatic response per day.  After the
    maximum is reached, it will not send another such response to the same
    address until the next day.
    """
    address = Attribute("""The email address being sent the auto-response.""")

    mailing_list = Attribute(
        """The mailing list sending the auto-response.""")

    response_type = Attribute("""The type of response sent.""")



class IAutoResponseSet(Interface):
    """Matching and setting auto-responses.

    The `IAutoResponseSet` is contexted to a particular mailing list.
    """

    def todays_count(address, response_type):
        """The number of responses sent to an address today.

        :param address: The address who is the recipient of the auto-response.
        :type address: `IAddress`
        :param response_type: The response type being sent.
        :type response_type: `Response`
        :return: The number of auto-responses already received by the user
            today, of this type, from this mailing list.
        :rtype: int
        """

    def response_sent(address, response_type):
        """Record the fact that another response is being sent to the address.

        :param address: The address who is the recipient of the auto-response.
        :type address: `IAddress`
        :param response_type: The response type being sent.
        :type response_type: `Response`
        """

    def last_response(address, response_type):
        """Record the fact that another response is being sent to the address.

        :param address: The address who is the recipient of the auto-response.
        :type address: `IAddress`
        :param response_type: The response type being sent.
        :type response_type: `Response`
        :return: the last response recorded.
        :rtype: `IAutoResponseRecord`
        """
