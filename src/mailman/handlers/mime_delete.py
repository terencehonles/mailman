# Copyright (C) 2002-2012 by the Free Software Foundation, Inc.
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

"""MIME-stripping filter for Mailman.

This module scans a message for MIME content, removing those sections whose
MIME types match one of a list of matches.  multipart/alternative sections are
replaced by the first non-empty component, and multipart/mixed sections
wrapping only single sections after other processing are replaced by their
contents.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MIMEDelete',
    ]


import os
import errno
import logging
import tempfile

from email.iterators import typed_subpart_iterator
from email.mime.message import MIMEMessage
from email.mime.text import MIMEText
from lazr.config import as_boolean
from os.path import splitext
from zope.interface import implements

from mailman.config import config
from mailman.core import errors
from mailman.core.i18n import _
from mailman.email.message import OwnerNotification
from mailman.interfaces.action import FilterAction
from mailman.interfaces.handler import IHandler
from mailman.utilities.string import oneline
from mailman.version import VERSION


log = logging.getLogger('mailman.error')



def dispose(mlist, msg, msgdata, why):
    if mlist.filter_action is FilterAction.reject:
        # Bounce the message to the original author.
        raise errors.RejectMessage(why)
    elif mlist.filter_action is FilterAction.forward:
        # Forward it on to the list moderators.
        text=_("""\
The attached message matched the $mlist.display_name mailing list's content
filtering rules and was prevented from being forwarded on to the list
membership.  You are receiving the only remaining copy of the discarded
message.

""")
        subject=_('Content filter message notification')
        notice = OwnerNotification(mlist, subject, roster=mlist.moderators)
        notice.set_type('multipart/mixed')
        notice.attach(MIMEText(text))
        notice.attach(MIMEMessage(msg))
        notice.send(mlist)
        # Let this fall through so the original message gets discarded.
    elif mlist.filter_action is FilterAction.preserve:
        if as_boolean(config.mailman.filtered_messages_are_preservable):
            # This is just like discarding the message except that a copy is
            # placed in the 'bad' queue should the site administrator want to
            # inspect the message.
            filebase = config.switchboards['bad'].enqueue(msg, msgdata)
            log.info('{0} preserved in file base {1}'.format(
                msg.get('message-id', 'n/a'), filebase))
    else:
        log.error(
            '{1} invalid FilterAction: {0}.  Treating as discard'.format(
                mlist.fqdn_listname, mlist.filter_action.name))
    # Most cases also discard the message
    raise errors.DiscardMessage(why)



def process(mlist, msg, msgdata):
    # We also don't care about our own digests or plaintext
    ctype = msg.get_content_type()
    mtype = msg.get_content_maintype()
    # Check to see if the outer type matches one of the filter types
    filtertypes = set(mlist.filter_types)
    passtypes = set(mlist.pass_types)
    if ctype in filtertypes or mtype in filtertypes:
        dispose(mlist, msg, msgdata,
                _("The message's content type was explicitly disallowed"))
    # Check to see if there is a pass types and the outer type doesn't match
    # one of these types
    if passtypes and not (ctype in passtypes or mtype in passtypes):
        dispose(mlist, msg, msgdata,
                _("The message's content type was not explicitly allowed"))
    # Filter by file extensions
    filterexts = set(mlist.filter_extensions)
    passexts = set(mlist.pass_extensions)
    fext = get_file_ext(msg)
    if fext:
        if fext in filterexts:
            dispose(mlist, msg, msgdata,
                 _("The message's file extension was explicitly disallowed"))
        if passexts and not (fext in passexts):
            dispose(mlist, msg, msgdata,
                 _("The message's file extension was not explicitly allowed"))
    numparts = len([subpart for subpart in msg.walk()])
    # If the message is a multipart, filter out matching subparts
    if msg.is_multipart():
        # Recursively filter out any subparts that match the filter list
        prelen = len(msg.get_payload())
        filter_parts(msg, filtertypes, passtypes, filterexts, passexts)
        # If the outer message is now an empty multipart (and it wasn't
        # before!) then, again it gets discarded.
        postlen = len(msg.get_payload())
        if postlen == 0 and prelen > 0:
            dispose(mlist, msg, msgdata,
                    _("After content filtering, the message was empty"))
    # Now replace all multipart/alternatives with just the first non-empty
    # alternative.  BAW: We have to special case when the outer part is a
    # multipart/alternative because we need to retain most of the outer part's
    # headers.  For now we'll move the subpart's payload into the outer part,
    # and then copy over its Content-Type: and Content-Transfer-Encoding:
    # headers (any others?).
    if mlist.collapse_alternatives:
        collapse_multipart_alternatives(msg)
        if ctype == 'multipart/alternative':
            firstalt = msg.get_payload(0)
            reset_payload(msg, firstalt)
    # If we removed some parts, make note of this
    changedp = 0
    if numparts <> len([subpart for subpart in msg.walk()]):
        changedp = 1
    # Now perhaps convert all text/html to text/plain
    if mlist.convert_html_to_plaintext and config.HTML_TO_PLAIN_TEXT_COMMAND:
        changedp += to_plaintext(msg)
    # If we're left with only two parts, an empty body and one attachment,
    # recast the message to one of just that part
    if msg.is_multipart() and len(msg.get_payload()) == 2:
        if msg.get_payload(0).get_payload() == '':
            useful = msg.get_payload(1)
            reset_payload(msg, useful)
            changedp = 1
    if changedp:
        msg['X-Content-Filtered-By'] = 'Mailman/MimeDel {0}'.format(VERSION)



def reset_payload(msg, subpart):
    # Reset payload of msg to contents of subpart, and fix up content headers
    payload = subpart.get_payload()
    msg.set_payload(payload)
    del msg['content-type']
    del msg['content-transfer-encoding']
    del msg['content-disposition']
    del msg['content-description']
    msg['Content-Type'] = subpart.get('content-type', 'text/plain')
    cte = subpart.get('content-transfer-encoding')
    if cte:
        msg['Content-Transfer-Encoding'] = cte
    cdisp = subpart.get('content-disposition')
    if cdisp:
        msg['Content-Disposition'] = cdisp
    cdesc = subpart.get('content-description')
    if cdesc:
        msg['Content-Description'] = cdesc



def filter_parts(msg, filtertypes, passtypes, filterexts, passexts):
    # Look at all the message's subparts, and recursively filter
    if not msg.is_multipart():
        return True
    payload = msg.get_payload()
    prelen = len(payload)
    newpayload = []
    for subpart in payload:
        keep = filter_parts(subpart, filtertypes, passtypes,
                            filterexts, passexts)
        if not keep:
            continue
        ctype = subpart.get_content_type()
        mtype = subpart.get_content_maintype()
        if ctype in filtertypes or mtype in filtertypes:
            # Throw this subpart away
            continue
        if passtypes and not (ctype in passtypes or mtype in passtypes):
            # Throw this subpart away
            continue
        # check file extension
        fext = get_file_ext(subpart)
        if fext:
            if fext in filterexts:
                continue
            if passexts and not (fext in passexts):
                continue
        newpayload.append(subpart)
    # Check to see if we discarded all the subparts
    postlen = len(newpayload)
    msg.set_payload(newpayload)
    if postlen == 0 and prelen > 0:
        # We threw away everything
        return False
    return True



def collapse_multipart_alternatives(msg):
    if not msg.is_multipart():
        return
    newpayload = []
    for subpart in msg.get_payload():
        if subpart.get_content_type() == 'multipart/alternative':
            try:
                firstalt = subpart.get_payload(0)
                newpayload.append(firstalt)
            except IndexError:
                pass
        else:
            newpayload.append(subpart)
    msg.set_payload(newpayload)



def to_plaintext(msg):
    changedp = False
    for subpart in typed_subpart_iterator(msg, 'text', 'html'):
        filename = tempfile.mktemp('.html')
        fp = open(filename, 'w')
        try:
            fp.write(subpart.get_payload(decode=True))
            fp.close()
            cmd = os.popen(config.HTML_TO_PLAIN_TEXT_COMMAND %
                           {'filename': filename})
            plaintext = cmd.read()
            rtn = cmd.close()
            if rtn:
                log.error('HTML->text/plain error: %s', rtn)
        finally:
            try:
                os.unlink(filename)
            except OSError, e:
                if e.errno <> errno.ENOENT:
                    raise
        # Now replace the payload of the subpart and twiddle the Content-Type:
        del subpart['content-transfer-encoding']
        subpart.set_payload(plaintext)
        subpart.set_type('text/plain')
        changedp = True
    return changedp



def get_file_ext(m):
    """
    Get filename extension. Caution: some virus don't put filename
    in 'Content-Disposition' header.
"""
    fext = ''
    filename = m.get_filename('') or m.get_param('name', '')
    if filename:
        fext = splitext(oneline(filename,'utf-8'))[1]
        if len(fext) > 1:
            fext = fext[1:]
        else:
            fext = ''
    return fext



class MIMEDelete:
    """Filter the MIME content of messages."""

    implements(IHandler)

    name = 'mime-delete'
    description = _('Filter the MIME content of messages.')

    def process(self, mlist, msg, msgdata):
        # Short-circuits
        if not mlist.filter_content:
            return
        if msgdata.get('isdigest'):
            return
        process(mlist, msg, msgdata)
