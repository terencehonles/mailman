# Copyright (C) 2010-2012 by the Free Software Foundation, Inc.
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

"""Interface to bounce detection components."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'BounceContext',
    'IBounceEvent',
    'IBounceProcessor',
    'UnrecognizedBounceDisposition',
    ]


from flufl.enum import Enum
from zope.interface import Attribute, Interface



class BounceContext(Enum):
    """The context in which the bounce was detected."""

    # This is a normal bounce detection.  IOW, Mailman received a bounce in
    # response to a mailing list post.
    normal = 1

    # A probe email bounced.  This can be considered a bit more serious, since
    # it occurred in response to a specific message to a specific user.
    probe = 2



class UnrecognizedBounceDisposition(Enum):
    # Just throw the message away.
    discard = 0
    # Forward the message to the list administrators, which includes both the
    # owners and the moderators.
    administrators = 1
    # Forward the message to the site owner.
    site_owner = 2



class IBounceEvent(Interface):
    """Registration record for a single bounce event."""

    list_name = Attribute(
        """The name of the mailing list that received this bounce.""")

    email = Attribute(
        """The email address that bounced.""")

    timestamp = Attribute(
        """The timestamp for when the bounce was received.""")

    message_id = Attribute(
        """The Message-ID of the bounce message.""")

    context = Attribute(
        """Where was the bounce detected?""")

    processed = Attribute(
        """Has this bounce event been processed?""")



class IBounceProcessor(Interface):
    """Manager/processor of bounce events."""

    def register(mlist, email, msg, context=None):
        """Register a bounce event.

        :param mlist: The mailing list that the bounce occurred on.
        :type mlist: IMailingList
        :param email: The email address that is bouncing.
        :type email: str
        :param msg: The bounce message.
        :type msg: email.message.Message
        :param context: In what context was the bounce detected?  The default
            is 'normal' context (i.e. we received a normal bounce for the
            address).
        :type context: BounceContext
        :return: The registered bounce event.
        :rtype: IBounceEvent
        """

    events = Attribute(
        """An iterator over all events.""")

    unprocessed = Attribute(
        """An iterator over all unprocessed bounce events.""")
