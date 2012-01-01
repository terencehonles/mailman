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

"""Cook a message's headers."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'CookHeaders',
    ]


import re

from email.errors import HeaderParseError
from email.header import Header, decode_header, make_header
from email.utils import parseaddr, formataddr, getaddresses
from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler
from mailman.interfaces.mailinglist import Personalization, ReplyToMunging
from mailman.version import VERSION


COMMASPACE = ', '
MAXLINELEN = 78

nonascii = re.compile('[^\s!-~]')



def uheader(mlist, s, header_name=None, continuation_ws='\t', maxlinelen=None):
    """Get the charset to encode the string in.

    Then search if there is any non-ascii character is in the string.  If
    there is and the charset is us-ascii then we use iso-8859-1 instead.  If
    the string is ascii only we use 'us-ascii' if another charset is
    specified.
    """
    charset = mlist.preferred_language.charset
    if nonascii.search(s):
        # use list charset but ...
        if charset == 'us-ascii':
            charset = 'iso-8859-1'
    else:
        # there is no nonascii so ...
        charset = 'us-ascii'
    return Header(s, charset, maxlinelen, header_name, continuation_ws)



def process(mlist, msg, msgdata):
    """Process the headers of the message."""
    # Set the "X-Ack: no" header if noack flag is set.
    if msgdata.get('noack'):
        del msg['x-ack']
        msg['X-Ack'] = 'no'
    # Because we're going to modify various important headers in the email
    # message, we want to save some of the information in the msgdata
    # dictionary for later.  Specifically, the sender header will get waxed,
    # but we need it for the Acknowledge module later.
    msgdata['original_sender'] = msg.sender
    # VirginRunner sets _fasttrack for internally crafted messages.
    fasttrack = msgdata.get('_fasttrack')
    if not msgdata.get('isdigest') and not fasttrack:
        try:
            prefix_subject(mlist, msg, msgdata)
        except (UnicodeError, ValueError):
            # TK: Sometimes subject header is not MIME encoded for 8bit
            # simply abort prefixing.
            pass
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
    if 'x-mailman-version' not in msg:
        msg['X-Mailman-Version'] = VERSION
    # We set "Precedence: list" because this is the recommendation from the
    # sendmail docs, the most authoritative source of this header's semantics.
    if 'precedence' not in msg:
        msg['Precedence'] = 'list'
    # Reply-To: munging.  Do not do this if the message is "fast tracked",
    # meaning it is internally crafted and delivered to a specific user.  BAW:
    # Yuck, I really hate this feature but I've caved under the sheer pressure
    # of the (very vocal) folks want it.  OTOH, RFC 2822 allows Reply-To: to
    # be a list of addresses, so instead of replacing the original, simply
    # augment it.  RFC 2822 allows max one Reply-To: header so collapse them
    # if we're adding a value, otherwise don't touch it.  (Should we collapse
    # in all cases?)
    if not fasttrack:
        # A convenience function, requires nested scopes.  pair is (name, addr)
        new = []
        d = {}
        def add(pair):
            lcaddr = pair[1].lower()
            if lcaddr in d:
                return
            d[lcaddr] = pair
            new.append(pair)
        # List admin wants an explicit Reply-To: added
        if mlist.reply_goes_to_list == ReplyToMunging.explicit_header:
            add(parseaddr(mlist.reply_to_address))
        # If we're not first stripping existing Reply-To: then we need to add
        # the original Reply-To:'s to the list we're building up.  In both
        # cases we'll zap the existing field because RFC 2822 says max one is
        # allowed.
        if not mlist.first_strip_reply_to:
            orig = msg.get_all('reply-to', [])
            for pair in getaddresses(orig):
                add(pair)
        # Set Reply-To: header to point back to this list.  Add this last
        # because some folks think that some MUAs make it easier to delete
        # addresses from the right than from the left.
        if mlist.reply_goes_to_list == ReplyToMunging.point_to_list:
            i18ndesc = uheader(mlist, mlist.description, 'Reply-To')
            add((str(i18ndesc), mlist.posting_address))
        del msg['reply-to']
        # Don't put Reply-To: back if there's nothing to add!
        if new:
            # Preserve order
            msg['Reply-To'] = COMMASPACE.join(
                [formataddr(pair) for pair in new])
        # The To field normally contains the list posting address.  However
        # when messages are fully personalized, that header will get
        # overwritten with the address of the recipient.  We need to get the
        # posting address in one of the recipient headers or they won't be
        # able to reply back to the list.  It's possible the posting address
        # was munged into the Reply-To header, but if not, we'll add it to a
        # Cc header.  BAW: should we force it into a Reply-To header in the
        # above code?
        # Also skip Cc if this is an anonymous list as list posting address
        # is already in From and Reply-To in this case.
        if (mlist.personalize == Personalization.full and
            mlist.reply_goes_to_list != ReplyToMunging.point_to_list and
            not mlist.anonymous_list):
            # Watch out for existing Cc headers, merge, and remove dups.  Note
            # that RFC 2822 says only zero or one Cc header is allowed.
            new = []
            d = {}
            for pair in getaddresses(msg.get_all('cc', [])):
                add(pair)
            i18ndesc = uheader(mlist, mlist.description, 'Cc')
            add((str(i18ndesc), mlist.posting_address))
            del msg['Cc']
            msg['Cc'] = COMMASPACE.join([formataddr(pair) for pair in new])



def prefix_subject(mlist, msg, msgdata):
    """Maybe add a subject prefix.

    Add the subject prefix unless the message is a digest or is being fast
    tracked (e.g. internally crafted, delivered to a single user such as the
    list admin).
    """
    if not mlist.subject_prefix.strip():
        return
    prefix = mlist.subject_prefix
    subject = msg.get('subject', '')
    # Try to figure out what the continuation_ws is for the header
    if isinstance(subject, Header):
        lines = str(subject).splitlines()
    else:
        lines = subject.splitlines()
    ws = '\t'
    if len(lines) > 1 and lines[1] and lines[1][0] in ' \t':
        ws = lines[1][0]
    msgdata['origsubj'] = subject
    # The subject may be multilingual but we take the first charset as major
    # one and try to decode.  If it is decodable, returned subject is in one
    # line and cset is properly set.  If fail, subject is mime-encoded and
    # cset is set as us-ascii.  See detail for ch_oneline() (CookHeaders one
    # line function).
    subject, cset = ch_oneline(subject)
    # TK: Python interpreter has evolved to be strict on ascii charset code
    # range.  It is safe to use unicode string when manupilating header
    # contents with re module.  It would be best to return unicode in
    # ch_oneline() but here is temporary solution.
    subject = unicode(subject, cset)
    # If the subject_prefix contains '%d', it is replaced with the
    # mailing list sequential number.  Sequential number format allows
    # '%d' or '%05d' like pattern.
    prefix_pattern = re.escape(prefix)
    # unescape '%' :-<
    prefix_pattern = '%'.join(prefix_pattern.split(r'\%'))
    p = re.compile('%\d*d')
    if p.search(prefix, 1):
        # prefix have number, so we should search prefix w/number in subject.
        # Also, force new style.
        prefix_pattern = p.sub(r'\s*\d+\s*', prefix_pattern)
    subject = re.sub(prefix_pattern, '', subject)
    rematch = re.match('((RE|AW|SV|VS)(\[\d+\])?:\s*)+', subject, re.I)
    if rematch:
        subject = subject[rematch.end():]
        recolon = 'Re:'
    else:
        recolon = ''
    # At this point, subject may become null if someone post mail with
    # subject: [subject prefix]
    if subject.strip() == '':
        subject = _('(no subject)')
        cset = mlist.preferred_language.charset
    # and substitute %d in prefix with post_id
    try:
        prefix = prefix % mlist.post_id
    except TypeError:
        pass
    # Get the header as a Header instance, with proper unicode conversion
    if not recolon:
        h = uheader(mlist, prefix, 'Subject', continuation_ws=ws)
    else:
        h = uheader(mlist, prefix, 'Subject', continuation_ws=ws)
        h.append(recolon)
    # TK: Subject is concatenated and unicode string.
    subject = subject.encode(cset, 'replace')
    h.append(subject, cset)
    del msg['subject']
    msg['Subject'] = h
    ss = uheader(mlist, recolon, 'Subject', continuation_ws=ws)
    ss.append(subject, cset)
    msgdata['stripped_subject'] = ss



def ch_oneline(headerstr):
    # Decode header string in one line and convert into single charset.
    # Return (string, cset) tuple as check for failure.
    try:
        d = decode_header(headerstr)
        # At this point, we should rstrip() every string because some
        # MUA deliberately add trailing spaces when composing return
        # message.
        d = [(s.rstrip(), c) for (s, c) in d]
        # Find all charsets in the original header.  We use 'utf-8' rather
        # than using the first charset (in mailman 2.1.x) if multiple
        # charsets are used.
        csets = []
        for (s, c) in d:
            if c and c not in csets:
                csets.append(c)
        if len(csets) == 0:
            cset = 'us-ascii'
        elif len(csets) == 1:
            cset = csets[0]
        else:
            cset = 'utf-8'
        h = make_header(d)
        ustr = unicode(h)
        oneline = ''.join(ustr.splitlines())
        return oneline.encode(cset, 'replace'), cset
    except (LookupError, UnicodeError, ValueError, HeaderParseError):
        # possibly charset problem. return with undecoded string in one line.
        return ''.join(headerstr.splitlines()), 'us-ascii'



class CookHeaders:
    """Modify message headers."""

    implements(IHandler)

    name = 'cook-headers'
    description = _('Modify message headers.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        process(mlist, msg, msgdata)
