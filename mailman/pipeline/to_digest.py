# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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

"""Add the message to the list's current digest and possibly send it."""

# Messages are accumulated to a Unix mailbox compatible file containing all
# the messages destined for the digest.  This file must be parsable by the
# mailbox.UnixMailbox class (i.e. it must be ^From_ quoted).
#
# When the file reaches the size threshold, it is moved to the qfiles/digest
# directory and the DigestRunner will craft the MIME, rfc1153, and
# (eventually) URL-subject linked digests from the mbox.

from __future__ import with_statement

__metaclass__ = type
__all__ = ['ToDigest']


import os
import re
import copy
import time
import logging

from StringIO import StringIO          # cStringIO can't handle unicode.
from email.charset import Charset
from email.generator import Generator
from email.header import decode_header, make_header, Header
from email.mime.base import MIMEBase
from email.mime.message import MIMEMessage
from email.mime.text import MIMEText
from email.parser import Parser
from email.utils import formatdate, getaddresses, make_msgid
from zope.interface import implements

from mailman import Errors
from mailman import Message
from mailman import Utils
from mailman import i18n
from mailman.Mailbox import Mailbox
from mailman.Mailbox import Mailbox
from mailman.configuration import config
from mailman.pipeline.decorate import decorate
from mailman.pipeline.scrubber import process as scrubber
from mailman.interfaces import DeliveryMode, DeliveryStatus, IHandler
from mailman.queue import Switchboard


_ = i18n._

UEMPTYSTRING = u''
EMPTYSTRING = ''

log = logging.getLogger('mailman.error')



def process(mlist, msg, msgdata):
    # Short circuit non-digestable lists.
    if not mlist.digestable or msgdata.get('isdigest'):
        return
    mboxfile = os.path.join(mlist.data_path, 'digest.mbox')
    mboxfp = open(mboxfile, 'a+')
    mbox = Mailbox(mboxfp)
    mbox.AppendMessage(msg)
    # Calculate the current size of the accumulation file.  This will not tell
    # us exactly how big the MIME, rfc1153, or any other generated digest
    # message will be, but it's the most easily available metric to decide
    # whether the size threshold has been reached.
    mboxfp.flush()
    size = os.path.getsize(mboxfile)
    if size / 1024.0 >= mlist.digest_size_threshold:
        # This is a bit of a kludge to get the mbox file moved to the digest
        # queue directory.
        try:
            # Enclose in try/except here because a error in send_digest() can
            # silently stop regular delivery.  Unsuccessful digest delivery
            # should be tried again by cron and the site administrator will be
            # notified of any error explicitly by the cron error message.
            mboxfp.seek(0)
            send_digests(mlist, mboxfp)
            os.unlink(mboxfile)
        except Exception, errmsg:
            # Bare except is generally prohibited in Mailman, but we can't
            # forecast what exceptions can occur here.
            log.exception('send_digests() failed: %s', errmsg)
    mboxfp.close()



def send_digests(mlist, mboxfp):
    # Set the digest volume and time
    if mlist.digest_last_sent_at:
        bump = False
        # See if we should bump the digest volume number
        timetup = time.localtime(mlist.digest_last_sent_at)
        now = time.localtime(time.time())
        freq = mlist.digest_volume_frequency
        if freq == 0 and timetup[0] < now[0]:
            # Yearly
            bump = True
        elif freq == 1 and timetup[1] <> now[1]:
            # Monthly, but we take a cheap way to calculate this.  We assume
            # that the clock isn't going to be reset backwards.
            bump = True
        elif freq == 2 and (timetup[1] % 4 <> now[1] % 4):
            # Quarterly, same caveat
            bump = True
        elif freq == 3:
            # Once again, take a cheap way of calculating this
            weeknum_last = int(time.strftime('%W', timetup))
            weeknum_now = int(time.strftime('%W', now))
            if weeknum_now > weeknum_last or timetup[0] > now[0]:
                bump = True
        elif freq == 4 and timetup[7] <> now[7]:
            # Daily
            bump = True
        if bump:
            mlist.bump_digest_volume()
    mlist.digest_last_sent_at = time.time()
    # Wrapper around actually digest crafter to set up the language context
    # properly.  All digests are translated to the list's preferred language.
    with i18n.using_language(mlist.preferred_language):
        send_i18n_digests(mlist, mboxfp)



def send_i18n_digests(mlist, mboxfp):
    mbox = Mailbox(mboxfp)
    # Prepare common information (first lang/charset)
    lang = mlist.preferred_language
    lcset = Utils.GetCharSet(lang)
    lcset_out = Charset(lcset).output_charset or lcset
    # Common Information (contd)
    realname = mlist.real_name
    volume = mlist.volume
    issue = mlist.next_digest_number
    digestid = _('$realname Digest, Vol $volume, Issue $issue')
    digestsubj = Header(digestid, lcset, header_name='Subject')
    # Set things up for the MIME digest.  Only headers not added by
    # CookHeaders need be added here.
    # Date/Message-ID should be added here also.
    mimemsg = Message.Message()
    mimemsg['Content-Type'] = 'multipart/mixed'
    mimemsg['MIME-Version'] = '1.0'
    mimemsg['From'] = mlist.request_address
    mimemsg['Subject'] = digestsubj
    mimemsg['To'] = mlist.posting_address
    mimemsg['Reply-To'] = mlist.posting_address
    mimemsg['Date'] = formatdate(localtime=1)
    mimemsg['Message-ID'] = make_msgid()
    # Set things up for the rfc1153 digest
    plainmsg = StringIO()
    rfc1153msg = Message.Message()
    rfc1153msg['From'] = mlist.request_address
    rfc1153msg['Subject'] = digestsubj
    rfc1153msg['To'] = mlist.posting_address
    rfc1153msg['Reply-To'] = mlist.posting_address
    rfc1153msg['Date'] = formatdate(localtime=1)
    rfc1153msg['Message-ID'] = make_msgid()
    separator70 = '-' * 70
    separator30 = '-' * 30
    # In the rfc1153 digest, the masthead contains the digest boilerplate plus
    # any digest header.  In the MIME digests, the masthead and digest header
    # are separate MIME subobjects.  In either case, it's the first thing in
    # the digest, and we can calculate it now, so go ahead and add it now.
    mastheadtxt = Utils.maketext(
        'masthead.txt',
        {'real_name' :        mlist.real_name,
         'got_list_email':    mlist.posting_address,
         'got_listinfo_url':  mlist.script_url('listinfo'),
         'got_request_email': mlist.request_address,
         'got_owner_email':   mlist.owner_address,
         }, mlist=mlist)
    # MIME
    masthead = MIMEText(mastheadtxt.encode(lcset), _charset=lcset)
    masthead['Content-Description'] = digestid
    mimemsg.attach(masthead)
    # RFC 1153
    print >> plainmsg, mastheadtxt
    print >> plainmsg
    # Now add the optional digest header
    if mlist.digest_header:
        headertxt = decorate(mlist, mlist.digest_header, _('digest header'))
        # MIME
        header = MIMEText(headertxt.encode(lcset), _charset=lcset)
        header['Content-Description'] = _('Digest Header')
        mimemsg.attach(header)
        # RFC 1153
        print >> plainmsg, headertxt
        print >> plainmsg
    # Now we have to cruise through all the messages accumulated in the
    # mailbox file.  We can't add these messages to the plainmsg and mimemsg
    # yet, because we first have to calculate the table of contents
    # (i.e. grok out all the Subjects).  Store the messages in a list until
    # we're ready for them.
    #
    # Meanwhile prepare things for the table of contents
    toc = StringIO()
    print >> toc, _("Today's Topics:\n")
    # Now cruise through all the messages in the mailbox of digest messages,
    # building the MIME payload and core of the RFC 1153 digest.  We'll also
    # accumulate Subject: headers and authors for the table-of-contents.
    messages = []
    msgcount = 0
    msg = mbox.next()
    while msg is not None:
        if msg == '':
            # It was an unparseable message
            msg = mbox.next()
            continue
        msgcount += 1
        messages.append(msg)
        # Get the Subject header
        msgsubj = msg.get('subject', _('(no subject)'))
        subject = Utils.oneline(msgsubj, in_unicode=True)
        # Don't include the redundant subject prefix in the toc
        mo = re.match('(re:? *)?(%s)' % re.escape(mlist.subject_prefix),
                      subject, re.IGNORECASE)
        if mo:
            subject = subject[:mo.start(2)] + subject[mo.end(2):]
        username = ''
        addresses = getaddresses([Utils.oneline(msg.get('from', ''),
                                                in_unicode=True)])
        # Take only the first author we find
        if isinstance(addresses, list) and addresses:
            username = addresses[0][0]
            if not username:
                username = addresses[0][1]
        if username:
            username = ' (%s)' % username
        # Put count and Wrap the toc subject line
        wrapped = Utils.wrap('%2d. %s' % (msgcount, subject), 65)
        slines = wrapped.split('\n')
        # See if the user's name can fit on the last line
        if len(slines[-1]) + len(username) > 70:
            slines.append(username)
        else:
            slines[-1] += username
        # Add this subject to the accumulating topics
        first = True
        for line in slines:
            if first:
                print >> toc, ' ', line
                first = False
            else:
                print >> toc, '     ', line.lstrip()
        # We do not want all the headers of the original message to leak
        # through in the digest messages.  For this phase, we'll leave the
        # same set of headers in both digests, i.e. those required in RFC 1153
        # plus a couple of other useful ones.  We also need to reorder the
        # headers according to RFC 1153.  Later, we'll strip out headers for
        # for the specific MIME or plain digests.
        keeper = {}
        all_keepers = {}
        for header in (config.MIME_DIGEST_KEEP_HEADERS +
                       config.PLAIN_DIGEST_KEEP_HEADERS):
            all_keepers[header] = True
        all_keepers = all_keepers.keys()
        for keep in all_keepers:
            keeper[keep] = msg.get_all(keep, [])
        # Now remove all unkempt headers :)
        for header in msg.keys():
            del msg[header]
        # And add back the kept header in the RFC 1153 designated order
        for keep in all_keepers:
            for field in keeper[keep]:
                msg[keep] = field
        # And a bit of extra stuff
        msg['Message'] = `msgcount`
        # Get the next message in the digest mailbox
        msg = mbox.next()
    # Now we're finished with all the messages in the digest.  First do some
    # sanity checking and then on to adding the toc.
    if msgcount == 0:
        # Why did we even get here?
        return
    toctext = toc.getvalue()
    # MIME
    try:
        tocpart = MIMEText(toctext.encode(lcset), _charset=lcset)
    except UnicodeError:
        tocpart = MIMEText(toctext.encode('utf-8'), _charset='utf-8')
    tocpart['Content-Description']= _("Today's Topics ($msgcount messages)")
    mimemsg.attach(tocpart)
    # RFC 1153
    print >> plainmsg, toctext
    print >> plainmsg
    # For RFC 1153 digests, we now need the standard separator
    print >> plainmsg, separator70
    print >> plainmsg
    # Now go through and add each message
    mimedigest = MIMEBase('multipart', 'digest')
    mimemsg.attach(mimedigest)
    first = True
    for msg in messages:
        # MIME.  Make a copy of the message object since the rfc1153
        # processing scrubs out attachments.
        mimedigest.attach(MIMEMessage(copy.deepcopy(msg)))
        # rfc1153
        if first:
            first = False
        else:
            print >> plainmsg, separator30
            print >> plainmsg
        # Use Mailman.pipeline.scrubber.process() to get plain text
        try:
            msg = scrubber(mlist, msg)
        except Errors.DiscardMessage:
            print >> plainmsg, _('[Message discarded by content filter]')
            continue
        # Honor the default setting
        for h in config.PLAIN_DIGEST_KEEP_HEADERS:
            if msg[h]:
                uh = Utils.wrap('%s: %s' % (h, Utils.oneline(msg[h],
                                                             in_unicode=True)))
                uh = '\n\t'.join(uh.split('\n'))
                print >> plainmsg, uh
        print >> plainmsg
        # If decoded payload is empty, this may be multipart message.
        # -- just stringfy it.
        payload = msg.get_payload(decode=True) \
                  or msg.as_string().split('\n\n',1)[1]
        mcset = msg.get_content_charset('us-ascii')
        try:
            payload = unicode(payload, mcset, 'replace')
        except (LookupError, TypeError):
            # unknown or empty charset
            payload = unicode(payload, 'us-ascii', 'replace')
        print >> plainmsg, payload
        if not payload.endswith('\n'):
            print >> plainmsg
    # Now add the footer
    if mlist.digest_footer:
        footertxt = decorate(mlist, mlist.digest_footer)
        # MIME
        footer = MIMEText(footertxt.encode(lcset), _charset=lcset)
        footer['Content-Description'] = _('Digest Footer')
        mimemsg.attach(footer)
        # RFC 1153
        # BAW: This is not strictly conformant RFC 1153.  The trailer is only
        # supposed to contain two lines, i.e. the "End of ... Digest" line and
        # the row of asterisks.  If this screws up MUAs, the solution is to
        # add the footer as the last message in the RFC 1153 digest.  I just
        # hate the way that VM does that and I think it's confusing to users,
        # so don't do it unless there's a clamor.
        print >> plainmsg, separator30
        print >> plainmsg
        print >> plainmsg, footertxt
        print >> plainmsg
    # Do the last bit of stuff for each digest type
    signoff = _('End of ') + digestid
    # MIME
    # BAW: This stuff is outside the normal MIME goo, and it's what the old
    # MIME digester did.  No one seemed to complain, probably because you
    # won't see it in an MUA that can't display the raw message.  We've never
    # got complaints before, but if we do, just wax this.  It's primarily
    # included for (marginally useful) backwards compatibility.
    mimemsg.postamble = signoff
    # rfc1153
    print >> plainmsg, signoff
    print >> plainmsg, '*' * len(signoff)
    # Do our final bit of housekeeping, and then send each message to the
    # outgoing queue for delivery.
    mlist.next_digest_number += 1
    virginq = Switchboard(config.VIRGINQUEUE_DIR)
    # Calculate the recipients lists
    plainrecips = set()
    mimerecips = set()
    # When someone turns off digest delivery, they will get one last digest to
    # ensure that there will be no gaps in the messages they receive.
    # Currently, this dictionary contains the email addresses of those folks
    # who should get one last digest.  We need to find the corresponding
    # IMember records.
    digest_members = set(mlist.digest_members.members)
    for address in mlist.one_last_digest:
        member = mlist.digest_members.get_member(address)
        if member:
            digest_members.add(member)
    for member in digest_members:
        if member.delivery_status <> DeliveryStatus.enabled:
            continue
        # Send the digest to the case-preserved address of the digest members.
        email_address = member.address.original_address
        if member.delivery_mode == DeliveryMode.plaintext_digests:
            plainrecips.add(email_address)
        elif member.delivery_mode == DeliveryMode.mime_digests:
            mimerecips.add(email_address)
        else:
            raise AssertionError(
                'Digest member "%s" unexpected delivery mode: %s' %
                (email_address, member.delivery_mode))
    # Zap this since we're now delivering the last digest to these folks.
    mlist.one_last_digest.clear()
    # MIME
    virginq.enqueue(mimemsg,
                    recips=mimerecips,
                    listname=mlist.fqdn_listname,
                    isdigest=True)
    # RFC 1153
    # If the entire digest message can't be encoded by list charset, fall
    # back to 'utf-8'.
    try:
        rfc1153msg.set_payload(plainmsg.getvalue().encode(lcset), lcset)
    except UnicodeError:
        rfc1153msg.set_payload(plainmsg.getvalue().encode('utf-8'), 'utf-8')
    virginq.enqueue(rfc1153msg,
                    recips=plainrecips,
                    listname=mlist.fqdn_listname,
                    isdigest=True)



class ToDigest:
    """Add the message to the digest, possibly sending it."""

    implements(IHandler)

    name = 'to-digest'
    description = _('Add the message to the digest, possibly sending it.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        process(mlist, msg, msgdata)
