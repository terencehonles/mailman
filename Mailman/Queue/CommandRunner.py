# Copyright (C) 1998,1999,2000,2001,2002 by the Free Software Foundation, Inc.
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

"""-request robot command queue runner."""

# See the delivery diagram in IncomingRunner.py.  This module handles all
# email destined for mylist-request, -join, and -leave.  It no longer handles
# bounce messages (i.e. -admin or -bounces), nor does it handle mail to
# -owner.



import re

from Mailman import mm_cfg
from Mailman.Bouncers import BouncerAPI
from Mailman.Handlers import SpamDetect

from Mailman.Queue.Runner import Runner
from Mailman.Queue.sbcache import get_switchboard
from Mailman.Logging.Syslog import syslog
from Mailman import LockFile



class CommandRunner(Runner):
    QDIR = mm_cfg.CMDQUEUE_DIR

    def _dispose(self, mlist, msg, msgdata):
        # BAW: Not all the functions of this qrunner require the list to be
        # locked.  Still, it's more convenient to lock it here and now and
        # deal with lock failures in one place.
        try:
            mlist.Lock(timeout=mm_cfg.LIST_LOCK_TIMEOUT)
        except LockFile.TimeOutError:
            # Oh well, try again later
            return 1
        # runner specific code
        #
        # This message will have been delivered to one of mylist-request,
        # mylist-join, or mylist-leave, and the message metadata will contain
        # a key to which one was used.  BAW: The tojoin and toleave actions
        # are hacks!
        try:
            if msgdata.get('torequest'):
                # Just pass the message off the command handler
                mlist.ParseMailCommands(msg, msgdata)
            elif msgdata.get('tojoin'):
                del msg['subject']
                msg['Subject'] = 'join'
                msg.set_payload('')
                mlist.ParseMailCommands(msg, msgdata)
            elif msgdata.get('toleave'):
                del msg['subject']
                msg['Subject'] = 'leave'
                msg.set_payload('')
                mlist.ParseMailCommands(msg, msgdata)
            elif msgdata.get('toconfirm'):
                mo = re.match(mm_cfg.VERP_CONFIRM_REGEXP, msg.get('to', ''))
                if mo:
                    # BAW: blech, this should not hack the Subject: header,
                    # but this is quick and dirty until we rewrite email
                    # command handling.
                    del msg['subject']
                    msg['Subject'] = 'confirm ' + mo.group('cookie')
                mlist.ParseMailCommands(msg, msgdata)
            mlist.Save()
        finally:
            mlist.Unlock()
