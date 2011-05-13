# Copyright (C) 2010-2011 by the Free Software Foundation, Inc.
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
    'IBounceDetector',
    'IBounceEvent',
    'IBounceProcessor',
    'Stop',
    ]


from flufl.enum import Enum
from zope.interface import Attribute, Interface



# If a bounce detector returns Stop, that means to just discard the
# message.  An example is warning messages for temporary delivery
# problems.  These shouldn't trigger a bounce notification, but we also
# don't want to send them on to the list administrator.
Stop = object()



class BounceContext(Enum):
    """The context in which the bounce was detected."""

    # This is a normal bounce detection.  IOW, Mailman received a bounce in
    # response to a mailing list post.
    normal = 1

    # A probe email bounced.  This can be considered a bit more serious, since
    # it occurred in response to a specific message to a specific user.
    probe = 2



class IBounceDetector(Interface):
    """Detect a bounce in an email message."""

    def process(self, msg):
        """Scan an email message looking for bounce addresses.

        :param msg: An email message.
        :type msg: `Message`
        :return: The detected bouncing addresses.  When bouncing addresses are
            found but are determined to be non-fatal, the value `Stop` is
            returned to halt any bounce processing pipeline.
        :rtype: A set strings, or `Stop`
        """



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
