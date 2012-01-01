# Copyright (C) 2000-2012 by the Free Software Foundation, Inc.
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

"""Outgoing runner."""

import socket
import logging

from datetime import datetime
from lazr.config import as_boolean, as_timedelta
from uuid import UUID
from zope.component import getUtility

from mailman.config import config
from mailman.core.runner import Runner
from mailman.interfaces.bounce import BounceContext, IBounceProcessor
from mailman.interfaces.mailinglist import Personalization
from mailman.interfaces.mta import SomeRecipientsFailed
from mailman.interfaces.pending import IPendings
from mailman.interfaces.subscriptions import ISubscriptionService
from mailman.utilities.datetime import now
from mailman.utilities.modules import find_name


# This controls how often _do_periodic() will try to deal with deferred
# permanent failures.  It is a count of calls to _do_periodic()
DEAL_WITH_PERMFAILURES_EVERY = 10

log = logging.getLogger('mailman.error')
smtp_log = logging.getLogger('mailman.smtp')
debug_log = logging.getLogger('mailman.debug')



class OutgoingRunner(Runner):
    """The outgoing runner."""

    def __init__(self, slice=None, numslices=1):
        super(OutgoingRunner, self).__init__(slice, numslices)
        # We look this function up only at startup time.
        self._func = find_name(config.mta.outgoing)
        # This prevents smtp server connection problems from filling up the
        # error log.  It gets reset if the message was successfully sent, and
        # set if there was a socket.error.
        self._logged = False
        self._retryq = config.switchboards['retry']

    def _dispose(self, mlist, msg, msgdata):
        # See if we should retry delivery of this message again.
        deliver_after = msgdata.get('deliver_after', datetime.fromtimestamp(0))
        if now() < deliver_after:
            return True
        # Calculate whether we should VERP this message or not.  The results of
        # this set the 'verp' key in the message metadata.
        interval = int(config.mta.verp_delivery_interval)
        if 'verp' in msgdata:
            # Honor existing settings.
            pass
        # If personalization is enabled for this list and we've configured
        # Mailman to always VERP personalized deliveries, then yes we VERP it.
        # Also, if personalization is /not/ enabled, but
        # verp_delivery_interval is set (and we've hit this interval), then
        # again, this message should be VERP'd. Otherwise, no.
        elif mlist.personalize != Personalization.none:
            if as_boolean(config.mta.verp_personalized_deliveries):
                msgdata['verp'] = True
        elif interval == 0:
            # Never VERP.
            msgdata['verp'] = False
        elif interval == 1:
            # VERP every time.
            msgdata['verp'] = True
        else:
            # VERP every 'interval' number of times.
            msgdata['verp'] = (mlist.post_id % interval == 0)
        try:
            debug_log.debug('[outgoing] {0}: {1}'.format(
                self._func, msg.get('message-id', 'n/a')))
            self._func(mlist, msg, msgdata)
            self._logged = False
        except socket.error:
            # There was a problem connecting to the SMTP server.  Log this
            # once, but crank up our sleep time so we don't fill the error
            # log.
            port = int(config.mta.smtp_port)
            if port == 0:
                port = 'smtp'            # Log this just once.
            if not self._logged:
                log.error('Cannot connect to SMTP server %s on port %s',
                          config.mta.smtp_host, port)
                self._logged = True
            return True
        except SomeRecipientsFailed as error:
            processor = getUtility(IBounceProcessor)
            # BAW: msg is the original message that failed delivery, not a
            # bounce message.  This may be confusing if this is what's sent to
            # the user in the probe message.  Maybe we should craft a
            # bounce-like message containing information about the permanent
            # SMTP failure?
            if 'probe_token' in msgdata:
                # This is a failure of our local MTA to deliver to a probe
                # message recipient.  Register the bounce event for permanent
                # failures.  Start by grabbing and confirming (i.e. removing)
                # the pendable record associated with this bounce token,
                # regardless of what address was actually failing.
                if len(error.permanent_failures) > 0:
                    pended = getUtility(IPendings).confirm(
                        msgdata['probe_token'])
                    # It's possible the token has been confirmed out of the
                    # database.  Just ignore that.
                    if pended is not None:
                        # The UUID had to be pended as a unicode.
                        member = getUtility(ISubscriptionService).get_member(
                            UUID(hex=pended['member_id']))
                        processor.register(
                            mlist, member.address.email, msg,
                            BounceContext.probe)
            else:
                # Delivery failed at SMTP time for some or all of the
                # recipients.  Permanent failures are registered as bounces,
                # but temporary failures are retried for later.
                for email in error.permanent_failures:
                    processor.register(mlist, email, msg, BounceContext.normal)
                # Move temporary failures to the qfiles/retry queue which will
                # occasionally move them back here for another shot at
                # delivery.
                if error.temporary_failures:
                    current_time = now()
                    recipients = error.temporary_failures
                    last_recip_count = msgdata.get('last_recip_count', 0)
                    deliver_until = msgdata.get('deliver_until', current_time)
                    if len(recipients) == last_recip_count:
                        # We didn't make any progress.  If we've exceeded the
                        # configured retry period, log this failure and
                        # discard the message.
                        if current_time > deliver_until:
                            smtp_log.error('Discarding message with '
                                           'persistent temporary failures: '
                                           '{0}'.format(msg['message-id']))
                            return False
                    else:
                        # We made some progress, so keep trying to delivery
                        # this message for a while longer.
                        deliver_until = current_time + as_timedelta(
                            config.mta.delivery_retry_period)
                    msgdata['last_recip_count'] = len(recipients)
                    msgdata['deliver_until'] = deliver_until
                    msgdata['recipients'] = recipients
                    self._retryq.enqueue(msg, msgdata)
        # We've successfully completed handling of this message.
        return False
