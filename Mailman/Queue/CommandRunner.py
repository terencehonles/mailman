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



# BAW: get rid of this when we Python 2.2 is a minimum requirement.
from __future__ import nested_scopes

import sys
import re
from types import StringType, UnicodeType

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Message
from Mailman.i18n import _
from Mailman.Queue.Runner import Runner
from Mailman.Logging.Syslog import syslog
from Mailman import LockFile

from email.MIMEText import MIMEText
from email.MIMEMessage import MIMEMessage
from email.Iterators import typed_subpart_iterator

NL = '\n'



class Results:
    def __init__(self, mlist, msg, msgdata):
        self.mlist = mlist
        self.msg = msg
        self.msgdata = msgdata
        # Only set returnaddr if the response is to go to someone other than
        # the address specified in the From: header (e.g. for the password
        # command).
        self.returnaddr = None
        self.commands = []
        self.results = []
        self.ignored = []
        self.lineno = 0
        self.subjcmdretried = 0
        # Always process the Subject: header first
        self.commands.append(msg['subject'])
        # Find the first text/plain part
        part = None
        for part in typed_subpart_iterator(msg, 'text', 'plain'):
            break
        if part is None or part is not msg:
            # Either there was no text/plain part or we ignored some
            # non-text/plain parts.
            self.results.append(_('Ignoring non-text/plain MIME parts'))
        body = part.get_payload()
        # text/plain parts better have string payloads
        assert isinstance(body, StringType) or isinstance(body, UnicodeType)
        lines = body.splitlines()
        # Use no more lines than specified
        self.commands.extend(lines[:mm_cfg.DEFAULT_MAIL_COMMANDS_MAX_LINES])
        self.ignored.extend(lines[mm_cfg.DEFAULT_MAIL_COMMANDS_MAX_LINES:])

    def process(self):
        # Now, process each line until we find an error.  The first
        # non-command line found stops processing.
        stop = 0
        for line in self.commands:
            if line and line.strip():
                args = line.split()
                cmd = args.pop(0).lower()
                stop = self.do_command(cmd, args)
            self.lineno += 1
            if stop:
                break

    def do_command(self, cmd, args=None):
        if args is None:
            args = ()
        # Try to import a command handler module for this command
        modname = 'Mailman.Commands.cmd_' + cmd
        try:
            __import__(modname)
            handler = sys.modules[modname]
        except ImportError:
            # If we're on line zero, it was the Subject: header that didn't
            # contain a command.  It's possible there's a Re: prefix (or
            # localized version thereof) on the Subject: line that's messing
            # things up.  Pop the prefix off and try again... once.
            #
            # If that still didn't work it isn't enough to stop processing.
            # BAW: should we include a message that the Subject: was ignored?
            if not self.subjcmdretried and args:
                self.subjcmdretried += 1
                cmd = args.pop(0)
                return self.do_command(cmd, args)
            return self.lineno <> 0
        return handler.process(self, args)

    def make_response(self):
        def indent(lines):
            return ['    ' + line for line in lines]

        resp = [Utils.wrap(_("""\
The results of your email command are provided below.
Attached is your original message.
"""))]
        if self.results:
            resp.append(_('- Results:'))
            resp.extend(indent(self.results))
        # Ignore empty lines
        unprocessed = [line for line in self.commands[self.lineno:]
                       if line.strip()]
        if unprocessed:
            resp.append(_('\n- Unprocessed:'))
            resp.extend(indent(unprocessed))
        if self.ignored:
            resp.append(_('\n- Ignored:'))
            resp.extend(indent(self.ignored))
        resp.append(_('\n- Done.\n\n'))
        results = MIMEText(
            NL.join(resp),
            _charset=Utils.GetCharSet(self.mlist.preferred_language))
        msg = Message.UserNotification(
            self.returnaddr or self.msg.get_sender(),
            self.mlist.GetBouncesEmail(),
            _('The results of your email commands'))
        msg.set_type('multipart/mixed')
        msg.attach(results)
        orig = MIMEMessage(self.msg)
        msg.attach(orig)
        return msg



class CommandRunner(Runner):
    QDIR = mm_cfg.CMDQUEUE_DIR

    def _dispose(self, mlist, msg, msgdata):
        res = Results(mlist, msg, msgdata)
        # BAW: Not all the functions of this qrunner require the list to be
        # locked.  Still, it's more convenient to lock it here and now and
        # deal with lock failures in one place.
        try:
            mlist.Lock(timeout=mm_cfg.LIST_LOCK_TIMEOUT)
        except LockFile.TimeOutError:
            # Oh well, try again later
            return 1
        # This message will have been delivered to one of mylist-request,
        # mylist-join, or mylist-leave, and the message metadata will contain
        # a key to which one was used.
        try:
            if msgdata.get('torequest'):
                res.process()
            elif msgdata.get('tojoin'):
                res.do_command('join')
            elif msgdata.get('toleave'):
                res.do_command('leave')
            elif msgdata.get('toconfirm'):
                mo = re.match(mm_cfg.VERP_CONFIRM_REGEXP, msg.get('to', ''))
                if mo:
                    res.do_command('confirm', (mo.group('cookie'),))
            msg = res.make_response()
            msg.send(mlist)
            mlist.Save()
        finally:
            mlist.Unlock()
