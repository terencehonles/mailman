# Copyright (C) 2000-2009 by the Free Software Foundation, Inc.
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

"""Outgoing queue runner."""

import os
import sys
import socket
import logging

from datetime import datetime
from lazr.config import as_timedelta

from mailman.config import config
from mailman.core import errors
from mailman.queue import Runner
from mailman.queue.bounce import BounceMixin

# This controls how often _do_periodic() will try to deal with deferred
# permanent failures.  It is a count of calls to _do_periodic()
DEAL_WITH_PERMFAILURES_EVERY = 10

log = logging.getLogger('mailman.error')



class OutgoingRunner(Runner, BounceMixin):
    """The outgoing queue runner."""

    def __init__(self, slice=None, numslices=1):
        Runner.__init__(self, slice, numslices)
        BounceMixin.__init__(self)
        # We look this function up only at startup time.
        package, dot, callable_name = config.mta.outgoing.rpartition('.')
        __import__(package)
        self._func = getattr(sys.modules[package], callable_name)
        # This prevents smtp server connection problems from filling up the
        # error log.  It gets reset if the message was successfully sent, and
        # set if there was a socket.error.
        self._logged = False
        self._retryq = config.switchboards['retry']

    def _dispose(self, mlist, msg, msgdata):
        # See if we should retry delivery of this message again.
        deliver_after = msgdata.get('deliver_after', datetime.fromtimestamp(0))
        if datetime.now() < deliver_after:
            return True
        # Make sure we have the most up-to-date state
        try:
            pid = os.getpid()
            self._func(mlist, msg, msgdata)
            # Failsafe -- a child may have leaked through.
            if pid <> os.getpid():
                log.error('child process leaked thru: %s', pid)
                os._exit(1)
            self._logged = False
        except socket.error:
            # There was a problem connecting to the SMTP server.  Log this
            # once, but crank up our sleep time so we don't fill the error
            # log.
            port = int(config.mta.port)
            if port == 0:
                port = 'smtp'
            # Log this just once.
            if not self._logged:
                log.error('Cannot connect to SMTP server %s on port %s',
                          config.mta.host, port)
                self._logged = True
            return True
        except errors.SomeRecipientsFailed, e:
            # Handle local rejects of probe messages differently.
            if msgdata.get('probe_token') and e.permfailures:
                self._probe_bounce(mlist, msgdata['probe_token'])
            else:
                # Delivery failed at SMTP time for some or all of the
                # recipients.  Permanent failures are registered as bounces,
                # but temporary failures are retried for later.
                #
                # BAW: msg is going to be the original message that failed
                # delivery, not a bounce message.  This may be confusing if
                # this is what's sent to the user in the probe message.  Maybe
                # we should craft a bounce-like message containing information
                # about the permanent SMTP failure?
                if e.permfailures:
                    self._queue_bounces(mlist.fqdn_listname, e.permfailures,
                                        msg)
                # Move temporary failures to the qfiles/retry queue which will
                # occasionally move them back here for another shot at
                # delivery.
                if e.tempfailures:
                    now = datetime.now()
                    recips = e.tempfailures
                    last_recip_count = msgdata.get('last_recip_count', 0)
                    deliver_until = msgdata.get('deliver_until', now)
                    if len(recips) == last_recip_count:
                        # We didn't make any progress, so don't attempt
                        # delivery any longer.  BAW: is this the best
                        # disposition?
                        if now > deliver_until:
                            return False
                    else:
                        # Keep trying to delivery this message for a while
                        deliver_until = now + as_timedelta(
                            config.mta.delivery_retry_period)
                    msgdata['last_recip_count'] = len(recips)
                    msgdata['deliver_until'] = deliver_until
                    msgdata['recips'] = recips
                    self._retryq.enqueue(msg, msgdata)
        # We've successfully completed handling of this message
        return False

    _do_periodic = BounceMixin._do_periodic

    def _clean_up(self):
        BounceMixin._clean_up(self)
        Runner._clean_up(self)
