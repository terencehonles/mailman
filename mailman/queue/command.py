# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""-request robot command queue runner."""

__metaclass__ = type
__all__ = [
    'CommandRunner',
    'Results',
    ]

# See the delivery diagram in IncomingRunner.py.  This module handles all
# email destined for mylist-request, -join, and -leave.  It no longer handles
# bounce messages (i.e. -admin or -bounces), nor does it handle mail to
# -owner.

import re
import sys
import logging

from StringIO import StringIO
from email.Errors import HeaderParseError
from email.Header import decode_header, make_header, Header
from email.Iterators import typed_subpart_iterator
from email.MIMEMessage import MIMEMessage
from email.MIMEText import MIMEText
from zope.interface import implements

from mailman import Message
from mailman import Utils
from mailman.app.replybot import autorespond_to_sender
from mailman.configuration import config
from mailman.i18n import _
from mailman.interfaces import IEmailResults
from mailman.queue import Runner

NL = '\n'

log = logging.getLogger('mailman.vette')



class CommandFinder:
    """Generate commands from the content of a message."""

    def __init__(self, msg, results):
        self.command_lines = []
        self.ignored_lines = []
        self.processed_lines = []
        # Depending on where the message was destined to, add some implicit
        # commands.  For example, if this was sent to the -join or -leave
        # addresses, it's the same as if 'join' or 'leave' commands were sent
        # to the -request address.
        if msgdata.get('tojoin'):
            self.command_lines.append('join')
        elif msgdata.get('toleave'):
            self.command_lines.append('leave')
        elif msgdata.get('toconfirm'):
            mo = re.match(config.VERP_CONFIRM_REGEXP, msg.get('to', ''))
            if mo:
                self.command_lines.append('confirm ' + mo.group('cookie'))
        # Extract the subject header and do RFC 2047 decoding.
        subject = msg.get('subject', '')
        try:
            subject = unicode(make_header(decode_header(raw_subject)))
            # Mail commands must be ASCII.
            self.command_lines.append(subject.encode('us-ascii'))
        except (HeaderParseError, UnicodeError, LookupError):
            # The Subject header was unparseable or not ASCII, so just ignore
            # it.
            pass
        # Find the first text/plain part of the message.
        part = None
        for part in typed_subpart_iterator(msg, 'text', 'plain'):
            break
        if part is None or part is not msg:
            # Either there was no text/plain part or we ignored some
            # non-text/plain parts.
            print >> results, _('Ignoring non-text/plain MIME parts')
        if part is None:
            # There was no text/plain part to be found.
            return
        body = part.get_payload(decode=True)
        # text/plain parts better have string payloads.
        assert isinstance(body, basestring), 'Non-string decoded payload'
        lines = body.splitlines()
        # Use no more lines than specified
        self.command_lines.extend(lines[:config.EMAIL_COMMANDS_MAX_LINES])
        self.ignored_lines.extend(lines[config.EMAIL_COMMANDS_MAX_LINES:])

    def __iter__(self):
        """Return each command line, split into commands and arguments.

        :return: 2-tuples where the first element is the command and the
            second element is a tuple of the arguments.
        """
        while self.command_lines:
            line = self.command_lines.pop(0)
            self.processed_lines.append(line)
            parts = line.strip().split()
            yield parts[0], tuple(parts[1:])



class Results:
    """The email command results."""

    implements(IResults)

    def __init__(self):
        self._output = StringIO()
        print >> self._output, _("""\
The results of your email command are provided below.

""")
        print >> self._output, _('- Results:')

    def write(self, text):
        self._output.write(text)

    def __str__(self):
        return self._output.getvalue()



class CommandRunner(Runner):
    QDIR = config.CMDQUEUE_DIR

    def _dispose(self, mlist, msg, msgdata):
        message_id = msg.get('message-id', 'n/a')
        # The policy here is similar to the Replybot policy.  If a message has
        # "Precedence: bulk|junk|list" and no "X-Ack: yes" header, we discard
        # the command message.
        precedence = msg.get('precedence', '').lower()
        ack = msg.get('x-ack', '').lower()
        if ack <> 'yes' and precedence in ('bulk', 'junk', 'list'):
            log.info('%s Precedence: %s message discarded by: %s',
                     message_id, precedence, mlist.request_address)
            return False
        # Do replybot for commands.
        replybot = config.handlers['replybot']
        replybot.process(mlist, msg, msgdata)
        if mlist.autorespond_requests == 1:
            # Respond and discard.
            log.info('%s -request message replied and discard', message_id)
            return False
        # Now craft the response and process the command lines.
        results = Results()
        finder = CommandFinder(msg, results)
        for command_name, arguments in finder:
            command = config.commands.get(command_name)
            if command is None:
                print >> results, _('No such command: $command_name')
            else:
                command.process(msg, msgdata, arguments, results)
        # All done, send the response.
        print >> results, _('\n- Unprocessed:')
        # XXX


        # Ignore empty lines
        unprocessed = [line for line in self.commands[self.lineno:]
                       if line and line.strip()]
        if unprocessed:
            resp.append(_('\n- Unprocessed:'))
            resp.extend(indent(unprocessed))
        if not unprocessed and not self.results:
            # The user sent an empty message; return a helpful one.
            resp.append(Utils.wrap(_("""\
No commands were found in this message.
To obtain instructions, send a message containing just the word "help".
""")))
        if self.ignored:
            resp.append(_('\n- Ignored:'))
            resp.extend(indent(self.ignored))
        resp.append(_('\n- Done.\n\n'))
        # Encode any unicode strings into the list charset, so we don't try to
        # join unicode strings and invalid ASCII.
        charset = Utils.GetCharSet(self.msgdata['lang'])
        encoded_resp = []
        for item in resp:
            if isinstance(item, unicode):
                item = item.encode(charset, 'replace')
            encoded_resp.append(item)
        results = MIMEText(NL.join(encoded_resp), _charset=charset)
        # Safety valve for mail loops with misconfigured email 'bots.  We
        # don't respond to commands sent with "Precedence: bulk|junk|list"
        # unless they explicitly "X-Ack: yes", but not all mail 'bots are
        # correctly configured, so we max out the number of responses we'll
        # give to an address in a single day.
        #
        # BAW: We wait until now to make this decision since our sender may
        # not be self.msg.get_sender(), but I'm not sure this is right.
        recip = self.returnaddr or self.msg.get_sender()
        if not autorespond_to_sender(self.mlist, recip, self.msgdata['lang']):
            return
        msg = Message.UserNotification(
            recip,
            self.mlist.GetBouncesEmail(),
            _('The results of your email commands'),
            lang=self.msgdata['lang'])
        msg.set_type('multipart/mixed')
        msg.attach(results)
        orig = MIMEMessage(self.msg)
        msg.attach(orig)
        msg.send(self.mlist)
