# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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

"""Bounce and command queue runner."""

# See the delivery diagram in IncomingRunner.py.  This module handles all
# email destined for mylist-owner, mylist-admin, and mylist-request.



from Mailman import mm_cfg
from Mailman.Bouncers import BouncerAPI

from Mailman.Queue.Runner import Runner
from Mailman.Queue.sbcache import get_switchboard
from Mailman.Logging.Syslog import syslog



class CommandRunner(Runner):
    def __init__(self, slice=None, numslices=1, cachelists=1):
        Runner.__init__(self, mm_cfg.CMDQUEUE_DIR,
                        slice, numslices, cachelists)

    def _dispose(self, mlist, msg, msgdata):
        # BAW: Not all the functions of this qrunner require the list to be
        # locked.  Still, it's more convenient to lock it here and now and
        # deal with lock failures in one place.
        try:
            mlist.Lock(timeout=mm_cfg.LIST_LOCK_TIMEOUT)
        except LockFile.TimeOutError:
            # Oh well, try again later
            return 1
        #
        # runner specific code
        try:
            # The message may be destined to one of three list related
            # recipients (note that posts to the list membership are handled
            # by the IncomingRunner via the qfiles/in queue):
            #
            # <list>-admin -- all errors are directed to this address, which
            # performs bounce processing.  If the bounce processor fails to
            # detect a bounce, the message is forwarded on to the <list>-owner
            # address.
            #
            # <list>-owner -- this message is directed to the human operators
            # of the list.  No bounce processing is performed, and the message
            # is forwarded to the list owners.  However, it is possible that
            # there are bogus addresses in the list owners, so if <list>-owner
            # appears to get a message from a "likely bounce sender" then it
            # simply discards the message.  BAW: should it save it some place?
            #
            # <list>-request -- this message is an emailed command, sent to
            # the command robot.  Pass it on to the command handler.
            #
            # Note that which of these subsystems the message is destined for
            # is determined by message metadata, as assigned by the front-end
            # mail filter scripts.  I've thought about adding additional
            # subsystems such as <list>-subscribe and <list>-unsubscribe as
            # shorthands for getting on and off the list.
            #
            # See the diagram in IncomingRunner.py for more information.
            if msgdata.get('toadmin'):
                if mlist.bounce_processing:
                    if BouncerAPI.ScanMessages(mlist, msg):
                        return
                # Either bounce processing isn't turned on or the bounce
                # detector found no recognizable bounce format in the message.
                # In either case, forward the dang thing off to the list
                # owners.  Be sure to munge the headers so that any bounces
                # from the list owners goes to the -owner address instead of
                # the -admin address.  This will avoid bounce loops.
                virginq = get_switchboard(mm_cfg.VIRGINQUEUE_DIR)
                virginq.enqueue(msg, msgdata,
                                recips = mlist.owner[:],
                                errorsto = mlist.GetOwnerEmail(),
                                noack = 0         # enable Replybot
                                )
                return
            elif msgdata.get('toowner'):
                # The message could have been a bounce from a broken list
                # owner address.  About the only other test we can do is to
                # see if the message is appearing to come from a well-known
                # MTA generated address.
                sender = msg.get_sender()
                i = sender.find('@')
                if i >= 0:
                    senderlhs = sender[:i].lower()
                else:
                    senderlhs = sender
                if senderlhs in mm_cfg.LIKELY_BOUNCE_SENDERS:
                    syslog('error', 'bounce loop detected from: %s' % sender)
                    return
                # Any messages to the owner address must have Errors-To: set
                # back to the owners address so bounce loops can be broken, as
                # per the code above.
                virginq = get_switchboard(mm_cfg.VIRGINQUEUE_DIR)
                virginq.enqueue(msg, msgdata,
                                recips = mlist.owner,
                                errorsto = mlist.GetOwnerEmail(),
                                noack = 0         # enable Replybot
                                )
                return
            elif msgdata.get('torequest'):
                # Just pass the message off the command handler
                mlist.ParseMailCommands(msg)
                return
        finally:
            mlist.Save()
            mlist.Unlock()
