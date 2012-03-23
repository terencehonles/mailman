# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

"""Incoming runner.

This runner's sole purpose in life is to decide the disposition of the
message.  It can either be accepted for delivery, rejected (i.e. bounced),
held for moderator approval, or discarded.

When accepted, the message is forwarded on to the `prep queue` where it is
prepared for delivery.  Rejections, discards, and holds are processed
immediately.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IncomingRunner',
    ]


from zope.component import getUtility

from mailman.config import config
from mailman.core.chains import process
from mailman.core.runner import Runner
from mailman.interfaces.address import ExistingAddressError
from mailman.interfaces.usermanager import IUserManager



class IncomingRunner(Runner):
    """The incoming runner."""

    def _dispose(self, mlist, msg, msgdata):
        """See `IRunner`."""
        if msgdata.get('envsender') is None:
            msgdata['envsender'] = mlist.no_reply_address
        # Ensure that the email addresses of the message's senders are known
        # to Mailman.  This will be used in nonmember posting dispositions.
        user_manager = getUtility(IUserManager)
        for sender in msg.senders:
            try:
                user_manager.create_address(sender)
            except ExistingAddressError:
                pass
        config.db.commit()
        # Process the message through the mailing list's start chain.
        start_chain = (mlist.owner_chain
                       if msgdata.get('to_owner', False)
                       else mlist.posting_chain)
        process(mlist, msg, msgdata, start_chain)
        # Do not keep this message queued.
        return False
