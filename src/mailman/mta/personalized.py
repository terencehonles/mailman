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

from mailman.interfaces.usermanager import IUserManager
from mailman.mta.verp import VERPDelivery



class PersonalizedMixin:
    """Personalize the message's To header.

    This is a mixin class, providing the basic functionality for header
    personalization.  The methods it provides are intended to be called from a
    concrete base class.
    """

    def personalize_to(self, msg, recipient):
        """Modify the To header to contain the recipient.

        The To header contents is replaced with the recipient's address, and
        if the recipient is a user registered with Mailman, the recipient's
        real name too.

        :param msg: The message to modify.
        :type msg: `email.message.Message`
        :param recipient: The recipient's email address.
        :type recipient: string
        """
        user_manager = getUtility(IUserManager)
        user = user_manager.get_user(recipient)
        if user is None:
            msg.replace_header('To', recipient)
        else:
            # Convert the unicode name to an email-safe representation.
            # Create a Header instance for the name so that it's properly
            # encoded for email transport.
            name = Header(user.real_name).encode()
            msg.replace_header('To', formataddr((name, recipient)))


class PersonalizedDelivery(VERPDelivery, PersonalizedMixin):
    """Personalize the message's To header."""

    def _deliver_to_recipients(self, mlist, msg, msgdata,
                               sender, recipients):
        """See `BaseDelivery`."""
        # This module only works with VERP delivery.
        assert len(recipients) == 1, 'Single recipient is required'
        # Try to find the real name for the recipient email address, if the
        # address is associated with a user registered with Mailman.
        recipient = recipients[0]
        self.personalize_to(msg, recipient)
        return super(PersonalizedDelivery, self)._deliver_to_recipients(
            mlist, msg, msgdata, sender, recipients)
