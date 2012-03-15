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

"""Personalized delivery."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'PersonalizedDelivery',
    'PersonalizedMixin',
    ]


from email.header import Header
from email.utils import formataddr
from zope.component import getUtility

from mailman.interfaces.mailinglist import Personalization
from mailman.interfaces.usermanager import IUserManager
from mailman.mta.verp import VERPDelivery



class PersonalizedMixin:
    """Personalize the message's To header.

    This is a mixin class, providing the basic functionality for header
    personalization.  The methods it provides are intended to be called from a
    concrete base class.
    """

    def personalize_to(self, mlist, msg, msgdata):
        """Modify the To header to contain the recipient.

        The To header contents is replaced with the recipient's address, and
        if the recipient is a user registered with Mailman, the recipient's
        real name too.
        """
        # Personalize the To header if the list requests it.
        if mlist.personalize != Personalization.full:
            return
        recipient = msgdata['recipient']
        user_manager = getUtility(IUserManager)
        user = user_manager.get_user(recipient)
        if user is None:
            msg.replace_header('To', recipient)
        else:
            # Convert the unicode name to an email-safe representation.
            # Create a Header instance for the name so that it's properly
            # encoded for email transport.
            name = Header(user.display_name).encode()
            msg.replace_header('To', formataddr((name, recipient)))



class PersonalizedDelivery(PersonalizedMixin, VERPDelivery):
    """Personalize the message's To header."""

    def __init__(self):
        """See `IndividualDelivery`."""
        super(PersonalizedDelivery, self).__init__()
        self.callbacks.append(self.personalize_to)
