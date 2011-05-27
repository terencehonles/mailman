# Copyright (C) 2001-2011 by the Free Software Foundation, Inc.
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

"""Bounce queue runner."""

import logging

from zope.component import getUtility

from mailman.app.bounces import (
    ProbeVERP, StandardVERP, maybe_forward, scan_message)
from mailman.interfaces.bounce import BounceContext, IBounceProcessor, Stop
from mailman.queue import Runner


COMMASPACE = ', '

log = logging.getLogger('mailman.bounce')
elog = logging.getLogger('mailman.error')



class BounceRunner(Runner):
    """The bounce runner."""

    def __init__(self, name, slice=None):
        super(BounceRunner, self).__init__(name, slice)
        self._processor = getUtility(IBounceProcessor)

    def _dispose(self, mlist, msg, msgdata):
        # List isn't doing bounce processing?
        if not mlist.bounce_processing:
            return False
        # Try VERP detection first, since it's quick and easy
        context = BounceContext.normal
        addresses = StandardVERP().get_verp(mlist, msg)
        if addresses:
            # We have an address, but check if the message is non-fatal.  It
            # will be non-fatal if the bounce scanner returns Stop.  It will
            # return a set of addresses when the bounce is fatal, but we don't
            # care about those addresses, since we got it out of the VERP.
            if scan_message(mlist, msg) is Stop:
                return False
        else:
            # See if this was a probe message.
            addresses = ProbeVERP().get_verp(mlist, msg)
            if addresses:
                context = BounceContext.probe
            else:
                # That didn't give us anything useful, so try the old fashion
                # bounce matching modules.
                addresses = scan_message(mlist, msg)
                if addresses is Stop:
                    # This is a recognized, non-fatal notice. Ignore it.
                    return False
        # If that still didn't return us any useful addresses, then send it on
        # or discard it.
        if len(addresses) > 0:
            for address in addresses:
                self._processor.register(mlist, address, msg, context)
        else:
            log.info('Bounce message w/no discernable addresses: %s',
                     msg.get('message-id', 'n/a'))
            maybe_forward(mlist, msg)
        # Dequeue this message.
        return False
