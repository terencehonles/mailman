#! /usr/bin/env python
#
# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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

"""Incoming queue runner."""

# A typical Mailman list exposes four aliases which point to three different
# wrapped scripts.  E.g. for a list named `mylist', you'd have:
#
# mylist         -> post
# mylist-admin   -> mailowner
# mylist-request -> mailcmd
# mylist-owner   -> mailowner (through an alias to mylist-admin)
#
# Only 3 scripts are used for historical purposes, and this is unlikely to
# change to due backwards compatibility.  That's immaterial though since the
# mailowner script can determine which alias it received the message on.
#
# mylist-request is a robot address; it's sole purpose is to process emailed
# commands in a Majordomo-like fashion.  mylist-admin is supposed to reach the
# list owners, but it performs one vital step before list owner delivery - it
# examines the message for bounce content.  mylist-owner is the fallback for
# delivery to the list owners; it performs no bounce detection, but it /does/
# look for bounce loops, which can occur if a list owner address is bouncing.
#
# So delivery flow of messages look like this:
#
# joerandom ---> mylist ---> list members
#    |                           |
#    |                           |[bounces]
#    +-------> mylist-admin <----+ <-------------------------------+
#    |              |                                              |
#    |              +--->[internal bounce processing]              |
#    |                               |                             |
#    |                               |    [bounce found]           |
#    |                               +--->[register and discard]   |
#    |                               |                             |
#    |                               |     [no bounce found]       |
#    |                               +---> list owners <------+    |
#    |                                          |             |    |
#    |                                          |[bounces]    |    |
#    +-------> mylist-owner <-------------------+             |    |
#    |              |                                         |    |
#    |              |     [bounce loop detected]              |    |
#    |              +---> [log and discard]                   |    |
#    |              |                                         |    |
#    |              +-----------------------------------------+    |
#    |               [no bounce loop detected]                     |
#    |                                                             |
#    |                                                             |
#    +-------> mylist-request                                      |
#                   |                                              |
#                   +---> [command processor]                      |
#                                 |                                |
#                                 +---> joerandom                  |
#                                           |                      |
#                                           |[bounces]             |
#                                           +----------------------+



import mimetools

from Mailman import mm_cfg
from Mailman.Queue import Runner
from Mailman.Handlers import HandlerAPI
from Mailman.Bouncers import BouncerAPI
from Mailman.Logging.Syslog import syslog
from Mailman.pythonlib.StringIO import StringIO



class IncomingRunner(Runner.Runner):
    def __init__(self, cachelists=1):
        Runner.Runner.__init__(self, mm_cfg.INQUEUE_DIR)

    def _dispose_message(self, msg, msgdata):
        # TBD: refactor this stanza.
        # Find out which mailing list this message is destined for
        listname = msgdata.get('listname')
        if not listname:
            syslog('qrunner', 'qfile metadata specifies no list: %s' % root)
            return 1
        mlist = self._open_list(listname)
        if not mlist:
            syslog('qrunner',
                   'Dequeuing message destined for missing list: %s' % root)
            self._dequeue(root)
            return 1
        # Now try to get the list lock
        try:
            mlist.Lock(timeout=mm_cfg.LIST_LOCK_TIMEOUT)
        except LockFile.TimeOutError:
            # oh well, try again later
            return 1
        #
        # runner specific code
        try:
            # The message may be destined for one of three subsystems: the
            # list delivery subsystem (i.e. the message gets delivered to
            # every member of the list), the bounce detector (i.e. this was a
            # message to the -owner address), or the mail command handler
            # (i.e. this was a message to the -request address).  The flags
            # controlling this path are found in the message metadata.
            #
            # post      - no `toadmin' or `torequest' key
            # mailowner - `toadmin' == true
            # mailcmd   - `torequest' == true
            #
            if msgdata.get('toadmin'):
                s = StringIO(str(msg))
                mimemsg = mimetools.Message(s)
                if mlist.bounce_processing:
                    if BouncerAPI.ScanMessages(mlist, mimemsg):
                        return 0
                # Either bounce processing isn't turned on or the bounce
                # detector found no recognized bounce format in the message.
                # In either case, forward the dang thing off to the list
                # owners.  Be sure to munge the headers so that any bounces
                # from the list owners goes to the -owner address instead of
                # the -admin address.  This will avoid bounce loops.
                msgdata.update({'recips'  : mlist.owner[:],
                                'errorsto': mlist.GetOwnerEmail(),
                                'noack'   : 0,            # enable Replybot
                                })
                return HandlerAPI.DeliverToUser(mlist, msg, msgdata)
            elif msgdata.get('toowner'):
                # The message could have been a bounce from a broken list
                # admin address.  About the only other test we can do is to
                # see if the message is appearing to come from a well-known
                # MTA generated address.
                sender = msg.GetSender()
                i = sender.find('@')
                if i >= 0:
                    senderlhs = sender[:i].lower()
                else:
                    senderlhs = sender
                if senderlhs in mm_cfg.LIKELY_BOUNCE_SENDERS:
                    syslog('error', 'bounce loop detected from: %s' % sender)
                    return 0
                # Any messages to the owner address must have Errors-To: set
                # back to the owners address so bounce loops can be broken, as
                # per the code above.
                msgdata.update({'recips'  : mlist.owner[:],
                                'errorsto': mlist.GetOwnerEmail(),
                                'noack'   : 0,            # enable Replybot
                                })
                return HandlerAPI.DeliverToUser(mlist, msg, msgdata)
            elif msgdata.get('torequest'):
                mlist.ParseMailCommands(msg)
                return 0
            else:
                # Pre 2.0beta3 qfiles have no schema version number
                if msgdata.get('version', 0) < 1:
                    msg.Requeue(mlist, newdata=msgdata,
                                pipeline = [mm_cfg.DELIVERY_MODULE])
                    return
                return HandlerAPI.DeliverToList(mlist, msg, msgdata)
        finally:
            mlist.Save()
            mlist.Unlock()
