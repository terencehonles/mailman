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

"""Cook a message's Subject header.
"""

import string
import re
import urlparse
from Mailman import mm_cfg



def process(mlist, msg, msgdata):
    # Mark the message as dirty so that its text will be forced to disk next
    # time it's queued.
    msgdata['_dirty'] = 1
    # Set the "X-Ack: no" header if noack flag is set.
    if msgdata.get('noack'):
        msg['X-Ack'] = 'no'
    # Because we're going to modify various important headers in the email
    # message, we want to save some of the information in the msgdata
    # dictionary for later.  Specifically, the sender header will get waxed,
    # but we need it for the Acknowledge module later.
    msgdata['original_sender'] = msg.GetSender()
    subject = msg.getheader('subject')
    adminaddr = mlist.GetAdminEmail()
    fasttrack = msgdata.get('fasttrack')
    if not msgdata.get('isdigest') and not fasttrack:
        # Add the subject prefix unless the message is a digest or is being
        # fast tracked (e.g. internally crafted, delivered to a single user
        # such as the list admin).  We assume all digests have an appropriate
        # subject header added by the ToDigest module.
        prefix = mlist.subject_prefix
        # we purposefully leave no space b/w prefix and subject!
        if not subject:
            msg['Subject'] = prefix + '(no subject)'
        elif prefix and not re.search(re.escape(prefix), subject, re.I):
            msg['Subject'] = prefix + subject
    #
    # get rid of duplicate headers
    del msg['sender']
    del msg['errors-to']
    msg['Sender'] = msgdata.get('errorsto', adminaddr)
    msg['Errors-To'] = msgdata.get('errorsto', adminaddr)
    #
    # Mark message so we know we've been here
    msg.headers.append('X-BeenThere: %s\n' % mlist.GetListEmail())
    #
    # Add Precedence: and other useful headers.  None of these are standard
    # and finding information on some of them are fairly difficult.  Some are
    # just common practice, and we'll add more here as they become necessary.
    # A good place to look is
    #
    # http://www.dsv.su.se/~jpalme/ietf/jp-ietf-home.html
    #
    # None of these headers are added if they already exist
    if not msg.get('x-mailman-version'):
        msg['X-Mailman-Version'] = mm_cfg.VERSION
    # Semi-controversial: some don't want this included at all, others
    # want the value to be `list'.
    if not msg.get('precedence'):
        msg['Precedence'] = 'bulk'
    #
    # Reply-To: munging.  Do not do this if the message is "fast tracked",
    # meaning it is internally crafted and delivered to a specific user,
    # or if there is already a reply-to set.  If the user has set
    # one we assume they have a good reason for it, and we don't
    # second guess them.
    if not fasttrack and not msg.get('reply-to'):
        # Set Reply-To: header to point back to this list
        if mlist.reply_goes_to_list == 1:
            msg['Reply-To'] = mlist.GetListEmail()
        # Set Reply-To: an explicit address
        elif mlist.reply_goes_to_list == 2:
            msg['Reply-To'] = mlist.reply_to_address
    #
    # Add list-specific headers as defined in RFC 2369, but only if the
    # message is being crafted for a specific list (e.g. not for the password
    # reminders).
    if msgdata.get('_nolist'):
        return
    #
    # Pre-calculate
    listid = '<%s.%s>' % (mlist._internal_name, mlist.host_name)
    if mlist.description:
        listid = mlist.description + ' ' + listid
    requestaddr = mlist.GetRequestEmail()
    subfieldfmt = '<%s>, <mailto:%s?subject=%ssubscribe>'
    listinfo = mlist.GetScriptURL('listinfo')
    #
    # TBD: List-Id is not in the RFC, but it was in an earlier draft so we
    # leave it in for historical reasons.
    headers = {
        'List-Id'         : listid,
        'List-Help'       : '<mailto:%s?subject=help>' % requestaddr,
        'List-Unsubscribe': subfieldfmt % (listinfo, requestaddr, 'un'),
        'List-Subscribe'  : subfieldfmt % (listinfo, requestaddr, ''),
        'List-Post'       : '<mailto:%s>' % mlist.GetListEmail(),
        }
    #
    # First we delete any pre-existing headers because the RFC permist only
    # one copy of each, and we want to be sure it's ours.
    for h, v in headers.items():
        del msg[h]
        # Wrap these lines if they are too long.  78 character width probably
        # shouldn't be hardcoded.  The adding of 2 is for the colon-space
        # separator.
        if len(h) + 2 + len(v) > 78:
            v = string.join(string.split(v, ', '), ',\n\t')
        msg[h] = v
    #
    # Always delete List-Archive header, but only add it back if the list is
    # actually archiving
    del msg['List-Archive']
    if mlist.archive:
        value = '<%s>' % urlparse.urljoin(mlist.web_page_url,
                                          mlist.GetBaseArchiveURL())
        msg['List-Archive'] = value
