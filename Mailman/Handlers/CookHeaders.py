# Copyright (C) 1998 by the Free Software Foundation, Inc.
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



def process(mlist, msg):
    subject = msg.getheader('subject')
    adminaddr = mlist.GetAdminEmail()
    if not getattr(msg, 'isdigest', 0):
        # add the subject prefix unless the message is a digest.  we assume
        # all digests have an appropriate subject header added by the ToDigest
        # module.
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
    msg['X-BeenThere'] = mlist.GetListEmail()
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
    # semi-controversial: some don't want this included at all, others
    # want the value to be `list'
    if not msg.get('precedence'):
        msg['Precedence'] = 'bulk'
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
