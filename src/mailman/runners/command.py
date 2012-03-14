# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

"""-request robot command runner."""

from __future__ import absolute_import, print_function, unicode_literals

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
import logging

from StringIO import StringIO
from email.errors import HeaderParseError
from email.header import decode_header, make_header
from email.iterators import typed_subpart_iterator
from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.core.runner import Runner
from mailman.email.message import UserNotification
from mailman.interfaces.command import ContinueProcessing, IEmailResults
from mailman.interfaces.languages import ILanguageManager


NL = '\n'
log = logging.getLogger('mailman.vette')



class CommandFinder:
    """Generate commands from the content of a message."""

    def __init__(self, msg, msgdata, results):
        self.command_lines = []
        self.ignored_lines = []
        self.processed_lines = []
        # Depending on where the message was destined to, add some implicit
        # commands.  For example, if this was sent to the -join or -leave
        # addresses, it's the same as if 'join' or 'leave' commands were sent
        # to the -request address.
        subaddress = msgdata.get('subaddress')
        if subaddress == 'join':
            self.command_lines.append('join')
        elif subaddress == 'leave':
            self.command_lines.append('leave')
        elif subaddress == 'confirm':
            mo = re.match(config.mta.verp_confirm_regexp, msg.get('to', ''))
            if mo:
                self.command_lines.append('confirm ' + mo.group('cookie'))
        # Extract the subject header and do RFC 2047 decoding.
        raw_subject = msg.get('subject', '')
        try:
            subject = unicode(make_header(decode_header(raw_subject)))
            # Mail commands must be ASCII.
            self.command_lines.append(subject.encode('us-ascii'))
        except (HeaderParseError, UnicodeError, LookupError):
            # The Subject header was unparseable or not ASCII.  If the raw
            # subject is a unicode object, convert it to ASCII ignoring all
            # bogus characters.  Otherwise, there's nothing in the subject
            # that we can use.
            if isinstance(raw_subject, unicode):
                safe_subject = raw_subject.encode('us-ascii', 'ignore')
                self.command_lines.append(safe_subject)
        # Find the first text/plain part of the message.
        part = None
        for part in typed_subpart_iterator(msg, 'text', 'plain'):
            break
        if part is None or part is not msg:
            # Either there was no text/plain part or we ignored some
            # non-text/plain parts.
            print(_('Ignoring non-text/plain MIME parts'), file=results)
        if part is None:
            # There was no text/plain part to be found.
            return
        body = part.get_payload(decode=True)
        # text/plain parts better have string payloads.
        assert isinstance(body, basestring), 'Non-string decoded payload'
        lines = body.splitlines()
        # Use no more lines than specified
        max_lines = int(config.mailman.email_commands_max_lines)
        self.command_lines.extend(lines[:max_lines])
        self.ignored_lines.extend(lines[max_lines:])

    def __iter__(self):
        """Return each command line, split into space separated arguments."""
        while self.command_lines:
            line = self.command_lines.pop(0)
            self.processed_lines.append(line)
            parts = line.strip().split()
            if len(parts) == 0:
                continue
            # Ensure that all the parts are unicodes.  Since we only accept
            # ASCII commands and arguments, ignore anything else.
            parts = [(part 
                      if isinstance(part, unicode)
                      else part.decode('ascii', 'ignore'))
                     for part in parts]
            yield parts



class Results:
    """The email command results."""

    implements(IEmailResults)

    def __init__(self, charset='us-ascii'):
        self._output = StringIO()
        self.charset = charset
        print(_("""\
The results of your email command are provided below.
"""), file=self._output)

    def write(self, text):
        if not isinstance(text, unicode):
            text = text.decode(self.charset, 'ignore')
        self._output.write(text)

    def __unicode__(self):
        value = self._output.getvalue()
        assert isinstance(value, unicode), 'Not a unicode: %r' % value
        return value



class CommandRunner(Runner):
    """The email command runner."""

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
        charset = msg.get_param('charset')
        if charset is None:
            charset = 'us-ascii'
        results = Results(charset)
        # Include just a few key pieces of information from the original: the
        # sender, date, and message id.
        print(_('- Original message details:'), file=results)
        subject = msg.get('subject', 'n/a')
        date = msg.get('date', 'n/a')
        from_ = msg.get('from', 'n/a')
        print(_('    From: $from_'), file=results)
        print(_('    Subject: $subject'), file=results)
        print(_('    Date: $date'), file=results)
        print(_('    Message-ID: $message_id'), file=results)
        print(_('\n- Results:'), file=results)
        finder = CommandFinder(msg, msgdata, results)
        for parts in finder:
            command = None
            # Try to find a command on this line.  There may be a Re: prefix
            # (possibly internationalized) so try with the first and second
            # words on the line.
            if len(parts) > 0:
                command_name = parts.pop(0)
                command = config.commands.get(command_name)
            if command is None and len(parts) > 0:
                command_name = parts.pop(0)
                command = config.commands.get(command_name)
            if command is None:
                print(_('No such command: $command_name'), file=results)
            else:
                status = command.process(
                    mlist, msg, msgdata, parts, results)
                assert status in ContinueProcessing, (
                    'Invalid status: %s' % status)
                if status == ContinueProcessing.no:
                    break
        # All done.  Strip blank lines and send the response.
        lines = filter(None, (line.strip() for line in finder.command_lines))
        if len(lines) > 0:
            print(_('\n- Unprocessed:'), file=results)
            for line in lines:
                print(line, file=results)
        lines = filter(None, (line.strip() for line in finder.ignored_lines))
        if len(lines) > 0:
            print(_('\n- Ignored:'), file=results)
            for line in lines:
                print(line, file=results)
        print(_('\n- Done.'), file=results)
        # Send a reply, but do not attach the original message.  This is a
        # compromise because the original message is often helpful in tracking
        # down problems, but it's also a vector for backscatter spam.
        language = getUtility(ILanguageManager)[msgdata['lang']]
        reply = UserNotification(msg.sender, mlist.bounces_address,
                                 _('The results of your email commands'),
                                 lang=language)
        cte = msg.get('content-transfer-encoding')
        if cte is not None:
            reply['Content-Transfer-Encoding'] = cte
        # Find a charset for the response body.  Try the original message's
        # charset first, then ascii, then latin-1 and finally falling back to
        # utf-8.
        reply_body = unicode(results)
        for charset in (results.charset, 'us-ascii', 'latin-1'):
            try:
                reply_body.encode(charset)
                break
            except UnicodeError:
                pass
        else:
            charset = 'utf-8'
        reply.set_payload(reply_body, charset=charset)
        reply.send(mlist)
