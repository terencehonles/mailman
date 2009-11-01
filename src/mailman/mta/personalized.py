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
    ]


from email.header import Header
from email.utils import formataddr
from zope.component import getUtility

from mailman.interfaces.usermanager import IUserManager
from mailman.mta.verp import VERPDelivery



class PersonalizedDelivery(VERPDelivery):
    """Personalize the message's To header."""

    def _deliver_to_recipients(self, mlist, msg, msgdata,
                               sender, recipients):
        """See `BaseDelivery`."""
        # This module only works with VERP delivery.
        assert len(recipients) == 1, 'Single recipient is required'
        # Try to find the real name for the recipient email address, if the
        # address is associated with a user registered with Mailman.
        recipient = recipients[0]
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
        return super(PersonalizedDelivery, self)._deliver_to_recipients(
            mlist, msg, msgdata, sender, recipients)
