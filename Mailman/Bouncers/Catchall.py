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

# TBD: this is cruft and should eventually just go away.  It contains the old
# implementation of Bouncer.ScanMessage().  We keep it because I don't feel
# like splitting it up and porting it.  It should at the very least be ported
# to use mimetools and re. :(

import re
import string
import regsub
import regex
from types import StringType

from Mailman import mm_cfg



# Return 0 if we couldn't make any sense of it, 1 if we handled it.
def process(msg):
    candidates = []
    # See Mailman.Message.GetSender :(
    sender = msg.get('sender')
    if sender:
        name, addr = msg.getaddr('sender')
    else:
        name, addr = msg.getaddr('from')
    if addr and type(addr) == StringType:
        who_info = string.lower(addr)
    elif msg.unixfrom:
        who_info = string.lower(string.split(msg.unixfrom)[1])
    else:
        return None
    at_index = string.find(who_info, '@')
    if at_index != -1:
        who_from = who_info[:at_index]
        remote_host = who_info[at_index+1:]
    else:
        who_from = who_info
        remote_host = mm_cfg.DEFAULT_HOST_NAME
    if not who_from in ['mailer-daemon', 'postmaster', 'orphanage',
                        'postoffice', 'ucx_smtp', 'a2']:
        return 0
    mime_info = msg.getheader('content-type')
    boundry = None
    if mime_info:
        mime_info_parts = regsub.splitx(
            mime_info, '[Bb][Oo][Uu][Nn][Dd][Aa][Rr][Yy]="[^"]+"')
        if len(mime_info_parts) > 1:
            boundry = regsub.splitx(mime_info_parts[1],
                                    '"[^"]+"')[1][1:-1]

    # snag out the message body
    msg.rewindbody()
    msgbody = msg.fp.read()
    if boundry:
        relevant_text = string.split(msgbody, '--%s' % boundry)
        # Invalid MIME messages shouldn't cause exceptions
        if len(relevant_text) >= 2:
            relevant_text = relevant_text[1]
        else:
            relevant_text = relevant_text[0]
    else:
        # This looks strange, but at least 2 are going to be no-ops.
        relevant_text = regsub.split(msgbody,
                                     '^.*Message header follows.*$')[0]
        relevant_text = regsub.split(relevant_text,
                                     '^The text you sent follows:.*$')[0]
        relevant_text = regsub.split(
            relevant_text, '^Additional Message Information:.*$')[0]
        relevant_text = regsub.split(relevant_text,
                                     '^-+Your original message-+.*$')[0]

    BOUNCE = 1
    REMOVE = 2

    # Bounce patterns where it's simple to figure out the email addr.
    email_regexp = '<?\([^ \t@|<>]+@[^ \t@<>]+\.[^ \t<>.]+\)>?'
    simple_bounce_pats = (
        (regex.compile('.*451 %s.*' % email_regexp), BOUNCE),
        (regex.compile('.*554 %s.*' % email_regexp), BOUNCE),
        (regex.compile('.*552 %s.*' % email_regexp), BOUNCE),
        (regex.compile('.*501 %s.*' % email_regexp), BOUNCE),
        (regex.compile('.*553 %s.*' % email_regexp), BOUNCE),
        (regex.compile('.*550 %s.*' % email_regexp), BOUNCE),
        (regex.compile('%s .bounced.*' % email_regexp), BOUNCE),
        (regex.compile('.*%s\.\.\. Deferred.*' % email_regexp), BOUNCE),
        (regex.compile('.*User %s not known.*' % email_regexp), REMOVE),
        (regex.compile('.*%s: User unknown.*' % email_regexp), REMOVE),
        (regex.compile('.*%s\.\.\. User unknown' % email_regexp), REMOVE))
    # patterns we can't directly extract the email (special case these)
    messy_pattern_1 = regex.compile('^Recipient .*$')
    messy_pattern_2 = regex.compile('^Addressee: .*$')
    messy_pattern_3 = regex.compile('^User .* not listed.*$')
    messy_pattern_4 = regex.compile('^550 [^ ]+\.\.\. User unknown.*$')
    messy_pattern_5 = regex.compile('^User [^ ]+ is not defined.*$')
    messy_pattern_6 = regex.compile('^[ \t]*[^ ]+: User unknown.*$')
    messy_pattern_7 = regex.compile('^[^ ]+ - User currently disabled.*$')

    # Patterns for cases where email addr is separate from error cue.
    separate_cue_1 = re.compile(
        '^554 .+\.\.\. unknown mailer error.*$', re.I)
    separate_addr_1 = regex.compile('expanded from: %s' % email_regexp)

    message_grokked = 0
    use_prospects = 0
    prospects = []                  # If bad but no candidates found.

    for line in string.split(relevant_text, '\n'):
        for pattern, action in simple_bounce_pats:
            if pattern.match(line) <> -1:
                email = extract(line)
                candidates.append((string.split(email,',')[0], action))
                message_grokked = 1

        # Now for the special case messages that are harder to parse...
        if (messy_pattern_1.match(line) <> -1
            or messy_pattern_2.match(line) <> -1):
            username = string.split(line)[1]
            candidates.append(('%s@%s' % (username, remote_host),
                               BOUNCE))
            message_grokked = 1
            continue
        if (messy_pattern_3.match(line) <> -1
            or messy_pattern_4.match(line) <> -1
            or messy_pattern_5.match(line) <> -1):
            username = string.split(line)[1]
            candidates.append(('%s@%s' % (username, remote_host),
                               REMOVE))
            message_grokked = 1
            continue
        if messy_pattern_6.match(line) <> -1:
            username = string.split(string.strip(line))[0][:-1]
            candidates.append(('%s@%s' % (username, remote_host),
                               REMOVE))
            message_grokked = 1
            continue
        if messy_pattern_7.match(line) <> -1:
            username = string.split(string.strip(line))[0]
            candidates.append(('%s@%s' % (username, remote_host),
                               REMOVE))
            message_grokked = 1
            continue

        if separate_cue_1.match(line):
            # Here's an error message that doesn't contain the addr.
            # Set a flag to use prospects found on separate lines.
            use_prospects = 1
        if separate_addr_1.search(line) != -1:
            # Found an addr that *might* be part of an error message.
            # Register it on prospects, where it will only be used if a 
            # separate check identifies this message as an error message.
            prospects.append((separate_addr_1.group(1), BOUNCE))

    if use_prospects and prospects:
        candidates = candidates + prospects

    did = []
    for who, action in candidates:
        # First clean up some cruft around the addrs.
        el = string.find(who, "...")
        if el != -1:
            who = who[:el]
        if len(who) > 1 and who[0] == '<':
            # Use stuff after open angle and before (optional) close:
            who = regsub.splitx(who[1:], ">")[0]
        if who not in did:
            did.append(who)
##    return message_grokked
    return did



def extract(line):
    email = regsub.splitx(line, '[^ \t@<>]+@[^ \t@<>]+\.[^ \t<>.]+')[1]
    if email[0] == '<':
        return regsub.splitx(email[1:], ">")[0]
    else:
        return email
