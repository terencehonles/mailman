# Copyright (C) 2000,2001 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Outgoing queue runner."""

import sys
import os

from Mailman import mm_cfg
from Mailman import Errors
from Mailman.Queue.Runner import Runner



class OutgoingRunner(Runner):
    def __init__(self, slice=None, numslices=1, cachelists=1):
        Runner.__init__(self, mm_cfg.OUTQUEUE_DIR,
                        slice, numslices, cachelists)

    def _dispose(self, mlist, msg, msgdata):
        # Fortunately, we do not need the list lock to do deliveries.
        handler = mm_cfg.DELIVERY_MODULE
        modname = 'Mailman.Handlers.' + handler
        mod = __import__(modname)
        func = getattr(sys.modules[modname], 'process')
        try:
            pid = os.getpid()
            func(mlist, msg, msgdata)
            # Failsafe -- a child may have leaked through.
            if pid <> os.getpid():
                syslog('error', 'child process leaked through: %s' % modname)
                os._exit(1)
        except Errors.SomeRecipientsFailed:
            # The delivery module being used (SMTPDirect or Sendmail) failed
            # to deliver the message to one or all of the recipients.  Requeue
            # the message so that delivery to those temporary failures are
            # retried later.
            #
            # Consult and adjust some meager metrics that try to decide
            # whether it's worth continuing to attempt delivery of this
            # message.
            now = time.time()
            recips = msgdata['recips']
            last_recip_count = msgdata.get('last_recip_count', 0)
            deliver_until = msgdata.get('deliver_until', now)
            if len(recips) == last_recip_count:
                # We didn't make any progress.
                if now > deliver_until:
                    # We won't attempt delivery any longer.
                    return 0
            else:
                # Keep trying to delivery this for 3 days
                deliver_until = now + mm_cfg.DELIVERY_RETRY_PERIOD
            msgdata['last_recip_count'] = len(recips)
            msgdata['deliver_until'] = deliver_until
            # Requeue
            return 1
        except Exception, e:
            # Some other exception occurred, which we definitely did not
            # expect, so set this message up for requeuing.
            self._log(e)
            return 1
        # We've successfully completed handling of this message
        return 0
