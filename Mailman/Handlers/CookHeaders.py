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

"""Cook a message's Subject header.
"""

import re
import urlparse

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman.i18n import _

CONTINUATION = ',\n\t'



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
    subject = msg['subject']
    adminaddr = mlist.GetAdminEmail()
    # VirginRunner sets _fasttrack for internally crafted messages.
    fasttrack = msgdata.get('_fasttrack')
    if not msgdata.get('isdigest') and not fasttrack:
        # Add the subject prefix unless the message is a digest or is being
        # fast tracked (e.g. internally crafted, delivered to a single user
        # such as the list admin).  We assume all digests have an appropriate
        # subject header added by the ToDigest module.
        prefix = mlist.subject_prefix
        # We purposefully leave no space b/w prefix and subject!
        if not subject:
            del msg['subject']
            msg['Subject'] = prefix + _('(no subject)')
        elif prefix and not re.search(re.escape(prefix), subject, re.I):
            del msg['subject']
            msg['Subject'] = prefix + subject
    # get rid of duplicate headers
    del msg['sender']
    del msg['errors-to']
    msg['Sender'] = msgdata.get('errorsto', adminaddr)
    msg['Errors-To'] = msgdata.get('errorsto', adminaddr)
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
    # of the (very vocal) folks want it.
    if not fasttrack:
        xreplyto = None
        # Set Reply-To: header to point back to this list
        if mlist.reply_goes_to_list == 1:
            xreplyto = msg.get('reply-to')
            del msg['reply-to']
            msg['Reply-To'] = mlist.GetListEmail()
        # Set Reply-To: an explicit address, but only if reply_to_address is a
        # valid email address.  BAW: this really should be validated on input.
        elif mlist.reply_goes_to_list == 2:
            try:
                Utils.ValidateEmail(mlist.reply_to_address)
            except Errors.EmailAddressError:
                pass
            else:
                xreplyto = msg.get('reply-to')
                del msg['reply-to']
                msg['Reply-To'] = mlist.reply_to_address
        # Give the recipient some ability to un-munge things.
        if xreplyto:
            del msg['x-reply-to']
            msg['X-Reply-To'] = xreplyto
    # Add list-specific headers as defined in RFC 2369 and RFC 2919, but only
    # if the message is being crafted for a specific list (e.g. not for the
    # password reminders).
    #
    # BAW: Some people really hate the List-* headers.  It seems that the free
    # version of Eudora (possibly on for some platforms) does not hide these
    # headers by default, pissing off their users.  Too bad.  Fix the MUAs.
    if msgdata.get('_nolist'):
        return
    # Pre-calculate
    listid = '<%s.%s>' % (mlist.internal_name(), mlist.host_name)
    if mlist.description:
        listid = mlist.description + ' ' + listid
    requestaddr = mlist.GetRequestEmail()
    subfieldfmt = '<%s>, <mailto:%s?subject=%ssubscribe>'
    listinfo = mlist.GetScriptURL('listinfo', absolute=1)
    headers = {
        'List-Id'         : listid,
        'List-Help'       : '<mailto:%s?subject=help>' % requestaddr,
        'List-Unsubscribe': subfieldfmt % (listinfo, requestaddr, 'un'),
        'List-Subscribe'  : subfieldfmt % (listinfo, requestaddr, ''),
        'List-Post'       : '<mailto:%s>' % mlist.GetListEmail(),
        }
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
    # Always delete List-Archive header, but only add it back if the list is
    # actually archiving
    del msg['list-archive']
    if mlist.archive:
        value = '<%s>' % urlparse.urljoin(mlist.web_page_url,
                                          mlist.GetBaseArchiveURL())
        msg['List-Archive'] = value
