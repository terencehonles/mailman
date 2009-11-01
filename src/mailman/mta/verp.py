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

"""VERP (i.e. personalized) message delivery."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'VERPDelivery',
    ]


import copy
import logging

from mailman.config import config
from mailman.email.utils import split_email
from mailman.mta.base import BaseDelivery
from mailman.utilities.string import expand


DOT = '.'
log = logging.getLogger('mailman.smtp')



class VERPDelivery(BaseDelivery):
    """Deliver a unique message to the MSA for each recipient."""

    def deliver(self, mlist, msg, msgdata):
        """See `IMailTransportAgentDelivery`.

        Craft a unique message for every recipient.  Encode the recipient's
        delivery address in the return envelope so there can be no ambiguity
        in bounce processing.
        """
        recipients = msgdata.get('recipients')
        if not recipients:
            # Could be None, could be an empty sequence.
            return
        sender = self._get_sender(mlist, msg, msgdata)
        sender_mailbox, sender_domain = split_email(sender)
        for recipient in recipients:
            # Make a copy of the original messages and operator on it, since
            # we're going to munge it repeatedly for each recipient.
            message_copy = copy.deepcopy(msg)
            # Encode the recipient's address for VERP.
            recipient_mailbox, recipient_domain = split_email(recipient)
            if recipient_domain is None:
                # The recipient address is not fully-qualified.  We can't
                # deliver it to this person, nor can we craft a valid verp
                # header.  I don't think there's much we can do except ignore
                # this recipient.
                log.info('Skipping VERP delivery to unqual recip: %s', recip)
                continue
            verp_sender = '{0}@{1}'.format(
                expand(config.mta.verp_format, dict(
                    bounces=sender_mailbox,
                    local=recipient_mailbox,
                    domain=DOT.join(recipient_domain))),
                DOT.join(sender_domain))
            # We can flag the mail as a duplicate for each member, if they've
            # already received this message, as calculated by Message-ID.  See
            # AvoidDuplicates.py for details.
            del message_copy['x-mailman-copy']
            if recipient in msgdata.get('add-dup-header', {}):
                message_copy['X-Mailman-Copy'] = 'yes'
            self._deliver_to_recipients(mlist, msg, msgdata,
                                        verp_sender, [recipient])
