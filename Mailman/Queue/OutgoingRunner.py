# Copyright (C) 2000,2001,2002 by the Free Software Foundation, Inc.
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
import time
import socket

import email

from Mailman import mm_cfg
from Mailman import Message
from Mailman import Errors
from Mailman import LockFile
from Mailman.Queue.Runner import Runner
from Mailman.Logging.Syslog import syslog

# This controls how often _doperiodic() will try to deal with deferred
# permanent failures.
DEAL_WITH_PERMFAILURES_EVERY = 1



class OutgoingRunner(Runner):
    QDIR = mm_cfg.OUTQUEUE_DIR

    def __init__(self, slice=None, numslices=1):
        Runner.__init__(self, slice, numslices)
        # Maps mailing lists to (recip, msg) tuples
        self._permfailures = {}
        self._permfail_counter = 0
        # We look this function up only at startup time
        modname = 'Mailman.Handlers.' + mm_cfg.DELIVERY_MODULE
        mod = __import__(modname)
        self._func = getattr(sys.modules[modname], 'process')
        # This prevents smtp server connection problems from filling up the
        # error log.  It gets reset if the message was successfully sent, and
        # set if there was a socket.error.
        self.__logged = 0

    def _dispose(self, mlist, msg, msgdata):
        # Make sure we have the most up-to-date state
        mlist.Load()
        try:
            pid = os.getpid()
            self._func(mlist, msg, msgdata)
            # Failsafe -- a child may have leaked through.
            if pid <> os.getpid():
                syslog('error', 'child process leaked thru: %s', modname)
                os._exit(1)
            self.__logged = 0
        except socket.error:
            # There was a problem connecting to the SMTP server.  Log this
            # once, but crank up our sleep time so we don't fill the error
            # log.
            port = mm_cfg.SMTPPORT
            if port == 0:
                port = 'smtp'
            # Log this just once.
            if not self.__logged:
                syslog('error', 'Cannot connect to SMTP server %s on port %s',
                       mm_cfg.SMTPHOST, port)
                self.__logged = 1
            return 1
        except Errors.SomeRecipientsFailed, e:
            # The delivery module being used (SMTPDirect or Sendmail) failed
            # to deliver the message to one or all of the recipients.
            # Permanent failures should be registered (but registration
            # requires the list lock), and temporary failures should be
            # retried later.
            #
            # For permanent failures, make a copy of the message for bounce
            # handling.  I'm not sure this is necessary, or the right thing to
            # do.
            pcnt = len(e.permfailures)
            copy = email.message_from_string(str(msg))
            self._permfailures.setdefault(mlist, []).extend(
                zip(e.permfailures, [copy] * pcnt))
            # Temporary failures
            if not e.tempfailures:
                # Don't need to keep the message queued if there were only
                # permanent failures.
                return 0
            now = time.time()
            recips = e.tempfailures
            last_recip_count = msgdata.get('last_recip_count', 0)
            deliver_until = msgdata.get('deliver_until', now)
            if len(recips) == last_recip_count:
                # We didn't make any progress, so don't attempt delivery any
                # longer.  BAW: is this the best disposition?
                if now > deliver_until:
                    return 0
            else:
                # Keep trying to delivery this for 3 days
                deliver_until = now + mm_cfg.DELIVERY_RETRY_PERIOD
            msgdata['last_recip_count'] = len(recips)
            msgdata['deliver_until'] = deliver_until
            msgdata['recips'] = recips
            # Requeue
            return 1
        # We've successfully completed handling of this message
        return 0

    def _doperiodic(self):
        # Periodically try to acquire the list lock and clear out the
        # permanent failures.
        self._permfail_counter += 1
        if self._permfail_counter < DEAL_WITH_PERMFAILURES_EVERY:
            return
        # Reset the counter
        self._permfail_counter = 0
        # And deal with the deferred permanent failures.
        for mlist in self._permfailures.keys():
            try:
                mlist.Lock(timeout=mm_cfg.LIST_LOCK_TIMEOUT)
            except LockFile.TimeOutError:
                return
            try:
                for recip, msg in self._permfailures[mlist]:
                    mlist.registerBounce(recip, msg)
                del self._permfailures[mlist]
                mlist.Save()
            finally:
                mlist.Unlock()
