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

Use Cleanse.py module to actually remove various headers.
"""

import re
from Mailman import mm_cfg



def process(mlist, msg, msgdata):
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
    msg['Sender'] = adminaddr
    msg['Errors-To'] = adminaddr
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
    # meaning it is internally crafted and delivered to a specific user.
    if not fasttrack:
        # Set Reply-To: header to point back to this list
        if mlist.reply_goes_to_list == 1:
            msg['Reply-To'] = mlist.GetListEmail()
        # Set Reply-To: an explicit address
        elif mlist.reply_goes_to_list == 2:
            msg['Reply-To'] = mlist.reply_to_address
    #
    # Other list related non-standard headers.  Defined in:
    #
    # Grant Neufeld and Joshua D. Baer: The Use of URLs as Meta-Syntax for
    # Core Mail List Commands and their Transport through Message Header
    # fields, draft-baer-listspec-01.txt, September 1997.
    #
    # Referenced in
    #
    # http://www.dsv.su.se/~jpalme/ietf/mail-attributes.html
    #
    if not msg.get('list-id'):
        msg['List-Id'] = mlist.GetListIdentifier()
    #
    # These currently seem like overkill.  Maybe add them in later when
    # the draft gets closer to a standard
    #
    # List-Subscribe
    # List-Unsubscribe
    # List-Owner
    # List-Help
    # List-Post
    # List-Archive
    # List-Software
    # X-Listserver
