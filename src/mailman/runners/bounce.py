# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
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

"""Bounce runner."""

import logging

from flufl.bounce import all_failures, scan_message
from zope.component import getUtility

from mailman.app.bounces import ProbeVERP, StandardVERP, maybe_forward
from mailman.core.runner import Runner
from mailman.interfaces.bounce import BounceContext, IBounceProcessor


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
        if not mlist.process_bounces:
            return False
        # Try VERP detection first, since it's quick and easy
        context = BounceContext.normal
        addresses = StandardVERP().get_verp(mlist, msg)
        if len(addresses) > 0:
            # Scan the message to see if it contained permanent or temporary
            # failures.  We'll ignore temporary failures, but even if there
            # are no permanent failures, we'll assume VERP bounces are
            # permanent.
            temporary, permanent = all_failures(msg)
            if len(temporary) > 0:
                # This was a temporary failure, so just ignore it.
                return False
        else:
            # See if this was a probe message.
            addresses = ProbeVERP().get_verp(mlist, msg)
            if len(addresses) > 0:
                context = BounceContext.probe
            else:
                # That didn't give us anything useful, so try the old fashion
                # bounce matching modules.  This returns only the permanently
                # failing addresses.  Since Mailman currently doesn't score
                # temporary failures, if we get no permanent failures, we're
                # done.s
                addresses = scan_message(msg)
        # If that still didn't return us any useful addresses, then send it on
        # or discard it.  The addresses will come back from flufl.bounce as
        # bytes/8-bit strings, but we must store them as unicodes in the
        # database.  Assume utf-8 encoding, but be cautious.
        if len(addresses) > 0:
            for address in addresses:
                if isinstance(address, bytes):
                    try:
                        address = address.decode('utf-8')
                    except UnicodeError:
                        log.exception('Ignoring non-UTF-8 encoded '
                                      'address: {0}'.format(address))
                        continue
                self._processor.register(mlist, address, msg, context)
        else:
            log.info('Bounce message w/no discernable addresses: %s',
                     msg.get('message-id', 'n/a'))
            maybe_forward(mlist, msg)
        # Dequeue this message.
        return False
