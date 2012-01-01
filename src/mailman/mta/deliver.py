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

"""Generic delivery."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'deliver',
    ]


import time
import logging

from mailman.config import config
from mailman.interfaces.mailinglist import Personalization
from mailman.interfaces.mta import SomeRecipientsFailed
from mailman.mta.decorating import DecoratingMixin
from mailman.mta.personalized import PersonalizedMixin
from mailman.mta.verp import VERPMixin
from mailman.mta.base import IndividualDelivery
from mailman.mta.bulk import BulkDelivery
from mailman.utilities.string import expand


COMMA = ','
log = logging.getLogger('mailman.smtp')



class Deliver(VERPMixin, DecoratingMixin, PersonalizedMixin,
              IndividualDelivery):
    """Deliver one message to one recipient.

    All current individualized features are avaialble to this
    `IMailTransportAgentDelivery` instance:

    * VERP
    * Full Personalization
    * Header/Footer decoration
    """

    def __init__(self):
        super(Deliver, self).__init__()
        self.callbacks.extend([
            self.avoid_duplicates,
            self.decorate,
            self.personalize_to,
            ])



def deliver(mlist, msg, msgdata):
    """Deliver a message to the outgoing mail server."""
    # If there are no recipients, there's nothing to do.
    recipients = msgdata.get('recipients')
    if not recipients:
        # Could be None, could be an empty sequence.
        return
    # Which delivery agent should we use?  Several situations can cause us to
    # use individual delivery.  If not specified, use bulk delivery.  See the
    # to-outgoing handler for when the 'verp' key is set in the metadata.
    if msgdata.get('verp', False):
        agent = Deliver()
    elif mlist.personalize != Personalization.none:
        agent = Deliver()
    else:
        agent = BulkDelivery(int(config.mta.max_recipients))
    log.debug('Using agent: %s', agent)
    # Keep track of the original recipients and the original sender for
    # logging purposes.
    original_recipients = msgdata['recipients']
    original_sender = msgdata.get('original-sender', msg.sender)
    # Let the agent attempt to deliver to the recipients.  Record all failures
    # for re-delivery later.
    t0 = time.time()
    refused = agent.deliver(mlist, msg, msgdata)
    t1 = time.time()
    # Log this posting.
    size = getattr(msg, 'original_size', msgdata.get('original_size'))
    if size is None:
        size = len(msg.as_string())
    substitutions = dict(
        msgid       = msg.get('message-id', 'n/a'),
        listname    = mlist.fqdn_listname,
        sender      = original_sender,
        recip       = len(original_recipients),
        size        = size,
        time        = t1 - t0,
        refused     = len(refused),
        smtpcode    = 'n/a',
        smtpmsg     = 'n/a',
        )
    template = config.logging.smtp.every
    if template.lower() != 'no':
        log.info('%s', expand(template, substitutions))
    if refused:
        template = config.logging.smtp.refused
        if template.lower() != 'no':
            log.info('%s', expand(template, substitutions))
    else:
        # Log the successful post, but if it was not destined to the mailing
        # list (e.g. to the owner or admin), print the actual recipients
        # instead of just the number.
        if not msgdata.get('tolist', False):
            recips = msg.get_all('to', [])
            recips.extend(msg.get_all('cc', []))
            substitutions['recips'] = COMMA.join(recips)
        template = config.logging.smtp.success
        if template.lower() != 'no':
            log.info('%s', expand(template, substitutions))
    # Process any failed deliveries.
    temporary_failures = []
    permanent_failures = []
    for recipient, (code, smtp_message) in refused.items():
        # RFC 5321, $4.5.3.1.10 says:
        #
        #   RFC 821 [1] incorrectly listed the error where an SMTP server
        #   exhausts its implementation limit on the number of RCPT commands
        #   ("too many recipients") as having reply code 552.  The correct
        #   reply code for this condition is 452.  Clients SHOULD treat a 552
        #   code in this case as a temporary, rather than permanent, failure
        #   so the logic below works.
        #
        if code >= 500 and code != 552:
            # A permanent failure
            permanent_failures.append(recipient)
        else:
            # Deal with persistent transient failures by queuing them up for
            # future delivery.  TBD: this could generate lots of log entries!
            temporary_failures.append(recipient)
        template = config.logging.smtp.failure
        if template.lower() != 'no':
            substitutions.update(
                recip       = recipient,
                smtpcode    = code,
                smtpmsg     = smtp_message,
                )
            log.info('%s', expand(template, substitutions))
    # Return the results
    if temporary_failures or permanent_failures:
        raise SomeRecipientsFailed(temporary_failures, permanent_failures)
