# Copyright (C) 2002 by the Free Software Foundation, Inc.
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

"""MIME-stripping filter for Mailman.

This module scans a message for MIME content, removing those sections whose
MIME types match one of a list of matches.  multipart/alternative sections are
replaced by the first non-empty component, and multipart/mixed sections
wrapping only single sections after other processing are replaced by their
contents.
"""

import os
import errno
import tempfile

from email.Iterators import typed_subpart_iterator

from Mailman import mm_cfg
from Mailman import Errors
from Mailman.Logging.Syslog import syslog
from Mailman.Version import VERSION



def process(mlist, msg, msgdata):
    # Short-circuits
    if not mlist.filter_content or not mlist.filter_mime_types:
        return
    # We also don't care about our own digests or plaintext
    ctype = msg.get_type('text/plain')
    mtype = msg.get_main_type('text')
    if msgdata.get('isdigest') or ctype == 'text/plain':
        return
    # Check to see if the outer type matches one of the filter types
    filtertypes = mlist.filter_mime_types
    if ctype in filtertypes or mtype in filtertypes:
        raise Errors.DiscardMessage
    numparts = len([subpart for subpart in msg.walk()])
    # If the message is a multipart, filter out matching subparts
    if msg.is_multipart():
        # Recursively filter out any subparts that match the filter list
        prelen = len(msg.get_payload())
        filter_parts(msg, filtertypes)
        # If the outer message is now an emtpy multipart (and it wasn't
        # before!) then, again it gets discarded.
        postlen = len(msg.get_payload())
        if postlen == 0 and prelen > 0:
            raise Errors.DiscardMessage
    # Now replace all multipart/alternatives with just the first non-empty
    # alternative.  BAW: We have to special case when the outer part is a
    # multipart/alternative because we need to retain most of the outer part's
    # headers.  For now we'll move the subpart's payload into the outer part,
    # and then copy over its Content-Type: and Content-Transfer-Encoding:
    # headers (any others?).
    collapse_multipart_alternatives(msg)
    if msg.get_type() == 'multipart/alternative':
        firstalt = msg.get_payload(0)
        msg.set_payload(firstalt.get_payload())
        del msg['content-type']
        del msg['content-transfer-encoding']
        del msg['content-disposition']
        del msg['content-description']
        msg['Content-Type'] = firstalt.get('content-type', 'text/plain')
        cte = firstalt.get('content-transfer-encoding')
        if cte:
            msg['Content-Transfer-Encoding'] = cte
        cdisp = firstalt.get('content-disposition')
        if cdisp:
            msg['Content-Disposition'] = cdisp
        cdesc = firstalt.get('content-description')
        if cdesc:
            msg['Content-Description'] = cdesc
    # We we removed some parts, make note of this
    changedp = 0
    if numparts <> len([subpart for subpart in msg.walk()]):
        changedp = 1
    # Now perhaps convert all text/html to text/plain
    if mlist.convert_html_to_plaintext and mm_cfg.HTML_TO_PLAIN_TEXT_COMMAND:
        changedp += to_plaintext(msg)
    if changedp:
        msg['X-Content-Filtered-By'] = 'Mailman/MimeDel %s' % VERSION



def filter_parts(msg, filtertypes):
    # Look at all the message's subparts, and recursively filter
    if not msg.is_multipart():
        return 1
    payload = msg.get_payload()
    prelen = len(payload)
    newpayload = []
    for subpart in payload:
        keep = filter_parts(subpart, filtertypes)
        if not keep:
            continue
        ctype = subpart.get_type('text/plain')
        mtype = subpart.get_main_type('text')
        if ctype in filtertypes or mtype in filtertypes:
            # Throw this subpart away
            continue
        newpayload.append(subpart)
    # Check to see if we discarded all the subparts
    postlen = len(newpayload)
    msg.set_payload(newpayload)
    if postlen == 0 and prelen > 0:
        # We threw away everything
        return 0
    return 1



def collapse_multipart_alternatives(msg):
    if not msg.is_multipart():
        return
    newpayload = []
    for subpart in msg.get_payload():
        if subpart.get_type() == 'multipart/alternative':
            try:
                firstalt = subpart.get_payload(0)
                newpayload.append(firstalt)
            except IndexError:
                pass
        else:
            newpayload.append(subpart)
    msg.set_payload(newpayload)



def to_plaintext(msg):
    changedp = 0
    for subpart in typed_subpart_iterator(msg, 'text', 'html'):
        filename = tempfile.mktemp('.html')
        fp = open(filename, 'w')
        try:
            fp.write(subpart.get_payload())
            fp.close()
            cmd = os.popen(mm_cfg.HTML_TO_PLAIN_TEXT_COMMAND %
                           {'filename': filename})
            plaintext = cmd.read()
            rtn = cmd.close()
            if rtn:
                syslog('error', 'HTML->text/plain error: %s', rtn)
        finally:
            try:
                os.unlink(filename)
            except OSError, e:
                if e.errno <> errno.ENOENT: raise
        # Now replace the payload of the subpart and twiddle the Content-Type:
        subpart.set_payload(plaintext)
        subpart.set_type('text/plain')
        changedp = 1
    return changedp
