# Copyright (C) 2001 by the Free Software Foundation, Inc.
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

"""Cleanse a message for archiving.
"""

import os
import cgi
import errno
import cPickle
import mimetypes
from cStringIO import StringIO

import email
import email.Errors
from email.Parser import HeaderParser

from Mailman import LockFile
from Mailman import Message
from Mailman.Errors import DiscardMessage
from Mailman.i18n import _
from Mailman.Logging.Syslog import syslog

ARCHIVE_FILE_VERSION = 1



def process(mlist, msg, msgdata=None):
    for part in msg.walk():
        # if the part is text/plain, we leave it alone
        if part.get_type('text/plain') == 'text/plain':
            continue
        if part.get_type() == 'text/html':
            part.set_payload(cgi.escape(part.get_payload()))
        elif not part.is_multipart():
            payload = part.get_payload()
            ctype = part.get_type()
            size = len(payload)
            url = save_attachment(mlist, part)
            desc = part.get('content-description', _('not available'))
            part.set_payload(_("""
A non-text attachment was scrubbed...
Type: %(ctype)s
Size: %(size)d bytes
Desc: %(desc)s
Url : %(url)s
"""))
    # We still have to sanitize the message to flat text because Pipermail
    # can't handle messages with list payloads.  Having to do it this way
    # seems most unfortunate. ;/
    if msg.is_multipart():
        sfp = StringIO(str(msg))
        msg = HeaderParser(Message.Message).parse(sfp)
    return msg



def save_attachment(mlist, msg):
    # The directory to store the attachment in
    dir = os.path.join(mlist.archive_dir(), 'attachments')
    lock = LockFile.LockFile(os.path.join(mlist.archive_dir(),
                                          'attachments.lock'))
    lock.lock()
    try:
        try:
            os.mkdir(dir, 02775)
        except OSError, e:
            if e.errno <> errno.EEXIST: raise
        # Open the attachments database file
        dbfile = os.path.join(dir, 'attachments.pck')
        try:
            fp = open(dbfile)
            d = cPickle.load(fp)
            fp.close()
        except IOError, e:
            if e.errno <> errno.ENOENT: raise
            d = {'version': ARCHIVE_FILE_VERSION,
                 'next'   : 1,
                 }
        # Calculate the attachment file name
        file = 'attachment-%04d' % d['next']
        d['next'] += 1
        fp = open(dbfile, 'w')
        cPickle.dump(d, fp, 1)
        fp.close()
    finally:
        lock.unlock()
    # Figure out the attachment type and get the decoded data
    decodedpayload = msg.get_payload(decode=1)
    ext = mimetypes.guess_extension(msg.get_type())
    fp = open(os.path.join(dir, file + ext), 'w')
    fp.write(decodedpayload)
    fp.close()
    # Now calculate the url
    url = mlist.GetBaseArchiveURL() + '/attachments/' + file + ext
    return url
