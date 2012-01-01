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

"""VERP delivery."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'VERPDelivery',
    'VERPMixin',
    ]


import logging

from mailman.config import config
from mailman.mta.base import IndividualDelivery
from mailman.utilities.email import split_email
from mailman.utilities.string import expand


DOT = '.'
log = logging.getLogger('mailman.smtp')



class VERPMixin:
    """Mixin for VERP functionality.

    This works by overriding the base class's _get_sender() method to return
    the VERP'd envelope sender.  It expects the individual recipient's address
    to be squirreled away in the message metadata.
    """
    def _get_sender(self, mlist, msg, msgdata):
        """Return the recipient's address VERP encoded in the sender.

        :param mlist: The mailing list being delivered to.
        :type mlist: `IMailingList`
        :param msg: The original message being delivered.
        :type msg: `Message`
        :param msgdata: Additional message metadata for this delivery.
        :type msgdata: dictionary
        """
        sender = super(VERPMixin, self)._get_sender(mlist, msg, msgdata)
        if msgdata.get('verp', False):
            log.debug('VERPing %s', msg.get('message-id'))
            recipient = msgdata['recipient']
            sender_mailbox, sender_domain = split_email(sender)
            # Encode the recipient's address for VERP.
            recipient_mailbox, recipient_domain = split_email(recipient)
            if recipient_domain is None:
                # The recipient address is not fully-qualified.  We can't
                # deliver it to this person, nor can we craft a valid verp
                # header.  I don't think there's much we can do except ignore
                # this recipient.
                log.info('Skipping VERP delivery to unqual recip: %s',
                         recipient)
                return sender
            return '{0}@{1}'.format(
                expand(config.mta.verp_format, dict(
                    bounces=sender_mailbox,
                    local=recipient_mailbox,
                    domain=DOT.join(recipient_domain))),
                DOT.join(sender_domain))
        else:
            return sender

    def avoid_duplicates(self, mlist, msg, msgdata):
        """Flag the message for duplicate avoidance.

        We can flag the mail as a duplicate for each member, if they've
        already received this message, as calculated by Message-ID.  See
        `AvoidDuplicates.py`_ for details.
        """
        recipient = msgdata['recipient']
        del msg['x-mailman-copy']
        if recipient in msgdata.get('add-dup-header', {}):
            msg['X-Mailman-Copy'] = 'yes'



class VERPDelivery(VERPMixin, IndividualDelivery):
    """Deliver a unique message to the MSA for each recipient."""

    def __init__(self):
        """See `IndividualDelivery`."""
        super(VERPDelivery, self).__init__()
        self.callbacks.append(self.avoid_duplicates)
