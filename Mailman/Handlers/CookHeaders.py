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

"""Cook a message's Subject header.
"""

import re

from email.Charset import Charset
from email.Header import Header, decode_header
import email.Utils

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman.i18n import _

CONTINUATION = ',\n\t'
COMMASPACE = ', '
MAXLINELEN = 78



def process(mlist, msg, msgdata):
    # Set the "X-Ack: no" header if noack flag is set.
    if msgdata.get('noack'):
        del msg['x-ack']
        msg['X-Ack'] = 'no'
    # Because we're going to modify various important headers in the email
    # message, we want to save some of the information in the msgdata
    # dictionary for later.  Specifically, the sender header will get waxed,
    # but we need it for the Acknowledge module later.
    msgdata['original_sender'] = msg.get_sender()
    # VirginRunner sets _fasttrack for internally crafted messages.
    fasttrack = msgdata.get('_fasttrack')
    if not msgdata.get('isdigest') and not fasttrack:
        prefix_subject(mlist, msg, msgdata)
    # Mark message so we know we've been here, but leave any existing
    # X-BeenThere's intact.
    msg['X-BeenThere'] = mlist.GetListEmail()
    # Add Precedence: and other useful headers.  None of these are standard
    # and finding information on some of them are fairly difficult.  Some are
    # just common practice, and we'll add more here as they become necessary.
    # Good places to look are:
    #
    # http://www.dsv.su.se/~jpalme/ietf/jp-ietf-home.html
    # http://www.faqs.org/rfcs/rfc2076.html
    #
    # None of these headers are added if they already exist.  BAW: some
    # consider the advertising of this a security breach.  I.e. if there are
    # known exploits in a particular version of Mailman and we know a site is
    # using such an old version, they may be vulnerable.  It's too easy to
    # edit the code to add a configuration variable to handle this.
    if not msg.get('x-mailman-version'):
        msg['X-Mailman-Version'] = mm_cfg.VERSION
    # Semi-controversial: some don't want this included at all, others
    # want the value to be `list'.
    if not msg.get('precedence'):
        msg['Precedence'] = 'bulk'
    # Reply-To: munging.  Do not do this if the message is "fast tracked",
    # meaning it is internally crafted and delivered to a specific user.  BAW:
    # Yuck, I really hate this feature but I've caved under the sheer pressure
    # of the (very vocal) folks want it.  OTOH, RFC 2822 allows Reply-To: to
    # be a list of addresses, so instead of replacing the original, simply
    # augment it.  RFC 2822 allows max one Reply-To: header so collapse them
    # if we're adding a value, otherwise don't touch it.  (Should we collapse
    # in all cases?)
    if not fasttrack:
        # Set Reply-To: header to point back to this list
        replyto = []
        if mlist.reply_goes_to_list == 1:
            replyto.append(('', mlist.GetListEmail()))
        # Set Reply-To: an explicit address, but only if reply_to_address is a
        # valid email address.  BAW: this really should be validated on input.
        elif mlist.reply_goes_to_list == 2:
            replyto.append(('', mlist.reply_to_address))
        # If we're not first stripping existing Reply-To: then we need to add
        # the original Reply-To:'s to the list we're building up.  In both
        # cases we'll zap the existing field because RFC 2822 says max one is
        # allowed.
        if not mlist.first_strip_reply_to:
            orig = msg.get_all('reply-to', [])
            replyto.extend(email.Utils.getaddresses(orig))
        del msg['reply-to']
        # Get rid of duplicates.  BAW: does order matter?  It might, because
        # not all MUAs respect Reply-To: as a list of addresses.  Also, note
        # duplicates are based on case folded email address, which means in
        # the case of dupes, the last one wins (will mostly affect the real
        # name clobbering).
        d = {}
        for name, addr in replyto:
            d[addr.lower()] = (name, addr)
        if d:
            # Don't add one back if there's nothing to add!
            msg['Reply-To'] = COMMASPACE.join(
                [email.Utils.formataddr(pair) for pair in d.values()])
    # Add list-specific headers as defined in RFC 2369 and RFC 2919, but only
    # if the message is being crafted for a specific list (e.g. not for the
    # password reminders).
    #
    # BAW: Some people really hate the List-* headers.  It seems that the free
    # version of Eudora (possibly on for some platforms) does not hide these
    # headers by default, pissing off their users.  Too bad.  Fix the MUAs.
    if msgdata.get('_nolist') or not mlist.include_rfc2369_headers:
        return
    # Pre-calculate
    listid = '<%s.%s>' % (mlist.internal_name(), mlist.host_name)
    if mlist.description:
        listid = mlist.description + ' ' + listid
    requestaddr = mlist.GetRequestEmail()
    subfieldfmt = '<%s>, <mailto:%s?subject=%ssubscribe>'
    listinfo = mlist.GetScriptURL('listinfo', absolute=1)
    # We always add a List-ID: header.  For internally crafted messages, we
    # also add a (nonstandard), "X-List-Administrivia: yes" header.  For all
    # others (i.e. those coming from list posts), we adda a bunch of other RFC
    # 2369 headers.
    headers = {
        'List-Id'         : listid,
        }
    if msgdata.get('reduced_list_headers'):
        headers['X-List-Administrivia'] = 'yes'
    else:
        headers.update({
            'List-Help'       : '<mailto:%s?subject=help>' % requestaddr,
            'List-Unsubscribe': subfieldfmt % (listinfo, requestaddr, 'un'),
            'List-Subscribe'  : subfieldfmt % (listinfo, requestaddr, ''),
            'List-Post'       : '<mailto:%s>' % mlist.GetListEmail(),
            })
        # Add this header if we're archiving
        if mlist.archive:
            archiveurl = mlist.GetBaseArchiveURL()
            if archiveurl.endswith('/'):
                archiveurl = archiveurl[:-1]
            headers['List-Archive'] = '<%s>' % archiveurl
    # First we delete any pre-existing headers because the RFC permits only
    # one copy of each, and we want to be sure it's ours.
    for h, v in headers.items():
        del msg[h]
        # Wrap these lines if they are too long.  78 character width probably
        # shouldn't be hardcoded, but is at least text-MUA friendly.  The
        # adding of 2 is for the colon-space separator.
        if len(h) + 2 + len(v) > 78:
            v = CONTINUATION.join(v.split(', '))
        msg[h] = v



def prefix_subject(mlist, msg, msgdata):
    # Add the subject prefix unless the message is a digest or is being fast
    # tracked (e.g. internally crafted, delivered to a single user such as the
    # list admin).
    prefix = mlist.subject_prefix
    subject = msg['subject']
    # The header may be multilingual; decode it from base64/quopri and search
    # each chunk for the prefix.
    has_prefix = 0
    if prefix and subject:
        pattern = re.escape(prefix.strip())
        for decodedsubj, charset in decode_header(subject):
            if re.search(pattern, decodedsubj, re.IGNORECASE):
                has_prefix = 1
    charset = Charset(Utils.GetCharSet(mlist.preferred_language))
    # We purposefully leave no space b/w prefix and subject!
    if not subject:
        del msg['subject']
        msg['Subject'] = Header(prefix + _('(no subject)'),
                                charset,
                                header_name='Subject')
    elif prefix and not has_prefix:
        del msg['subject']
        # We'll encode the new prefix (just in case) but leave the old subject
        # alone, in case it was already encoded.
        new_subject = Header(prefix, charset, header_name='Subject').encode()
        # If we go over 76 characters with the prefix, just put the old
        # subject on its own line.
        first = subject.split('\n')[0]
        if len(new_subject) + len(first) + 1 >= MAXLINELEN - len('Subject: '):
            new_subject += '\n '
        # We might have to add a space because the prefix and old subject may
        # both be MIME-encoded, losing the space at the end of the prefix.
        elif new_subject[-1] <> ' ':
            new_subject += ' '
        new_subject += subject
        msg['Subject'] = new_subject
