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

from mailman.app.bounces import StandardVERP
from mailman.config import config
from mailman.interfaces.bounce import Stop
from mailman.queue import Runner


COMMASPACE = ', '

log = logging.getLogger('mailman.bounce')
elog = logging.getLogger('mailman.error')



class BounceRunner(Runner):
    """The bounce runner."""

    def _dispose(self, mlist, msg, msgdata):
        # List isn't doing bounce processing?
        if not mlist.bounce_processing:
            return False
        # Try VERP detection first, since it's quick and easy
        addrs = StandardVERP().get_verp(mlist, msg)
        if addrs:
            # We have an address, but check if the message is non-fatal.
            if scan_messages(mlist, msg) is Stop:
                return
        else:
            # See if this was a probe message.
            token = verp_probe(mlist, msg)
            if token:
                self._probe_bounce(mlist, token)
                return
            # That didn't give us anything useful, so try the old fashion
            # bounce matching modules.
            addrs = scan_messages(mlist, msg)
            if addrs is Stop:
                # This is a recognized, non-fatal notice. Ignore it.
                return
        # If that still didn't return us any useful addresses, then send it on
        # or discard it.
        if not addrs:
            log.info('bounce message w/no discernable addresses: %s',
                     msg.get('message-id'))
            maybe_forward(mlist, msg)
            return
        # BAW: It's possible that there are None's in the list of addresses,
        # although I'm unsure how that could happen.  Possibly scan_messages()
        # can let None's sneak through.  In any event, this will kill them.
        addrs = filter(None, addrs)
        self._queue_bounces(mlist.fqdn_listname, addrs, msg)
