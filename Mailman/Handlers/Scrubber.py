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
from email.Generator import Generator

from Mailman import LockFile
from Mailman import Message
from Mailman.Errors import DiscardMessage
from Mailman.i18n import _
from Mailman.Logging.Syslog import syslog

ARCHIVE_FILE_VERSION = 1



# We're using a subclass of the standard Generator because we want to suppress
# headers in the subparts of multiparts.  We use a hack -- the ctor argument
# skipheaders to accomplish this.  It's set to true for the outer Message
# object, but false for all internal objects.  We recognize that
# sub-Generators will get created passing only mangle_from_ and maxheaderlen
# to the ctors.
#
# This isn't perfect because we still get stuff like the multipart boundaries,
# but see below for how we corrupt that to our nefarious goals.
class ScrubberGenerator(Generator):
    def __init__(self, outfp, mangle_from_=1, maxheaderlen=78, skipheaders=1):
        Generator.__init__(self, outfp, mangle_from_=0)
        self.__skipheaders = skipheaders

    def _write_headers(self, msg):
        if not self.__skipheaders:
            Generator._write_headers(self, msg)



def process(mlist, msg, msgdata=None):
    outer = 1
    for part in msg.walk():
        # If the part is text/plain, we leave it alone
        if part.get_type('text/plain') == 'text/plain':
            continue
        # I think it's generally a good idea to scrub out HTML.  You never
        # know what's in there -- web bugs, JavaScript nasties, etc.  If the
        # whole message is HTML, just discard the entire thing.  Otherwise,
        # just add an indication that the HTML part was removed.
        if part.get_type() == 'text/html':
            if outer:
                raise DiscardMessage
            part.set_payload(_("An HTML attachment was scrubbed and removed"))
        # If the message isn't a multipart, then we'll strip it out as an
        # attachment that would have to be separately downloaded.  Pipermail
        # will transform the url into a hyperlink.
        elif not part.is_multipart():
            payload = part.get_payload()
            ctype = part.get_type()
            size = len(payload)
            url = save_attachment(mlist, part)
            desc = part.get('content-description', _('not available'))
            part.set_payload(_("""\
A non-text attachment was scrubbed...
Type: %(ctype)s
Size: %(size)d bytes
Desc: %(desc)s
Url : %(url)s
"""))
    # We still have to sanitize the message to flat text because Pipermail
    # can't handle messages with list payloads.  This is a kludge (def (n)
    # clever hack ;).
    if msg.is_multipart():
        # We're corrupting the boundary to provide some more useful
        # information, because while we can suppress subpart headers, we can't
        # suppress the inter-part boundary without a redesign of the Generator
        # class or a rewrite of of the whole _handle_multipart() method.
        msg.set_boundary('%s %s attachment' %
                         ('-'*20, msg.get_type('text/plain')))
        sfp = StringIO()
        g = ScrubberGenerator(sfp, mangle_from_=0, skipheaders=0)
        g(msg)
        sfp.seek(0)
        # We don't care about parsing the body because we've already scrubbed
        # it of nasty stuff.  Just slurp it all in.
        msg = HeaderParser(Message.Message).parse(sfp)
    return msg



def save_attachment(mlist, msg):
    # The directory to store the attachment in
    dir = os.path.join(mlist.archive_dir(), 'attachments')
    # We need a lock to calculate the next attachment number
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
    # BAW: mimetypes ought to handle non-standard, but commonly found types,
    # e.g. image/jpg (should be image/jpeg).  For now we just store such
    # things as application/octet-streams since that seems the safest.
    ext = mimetypes.guess_extension(msg.get_type())
    if not ext:
        # We don't know what it is, so assume it's just a shapeless
        # application/octet-stream
        ext = '.bin'
    fp = open(os.path.join(dir, file + ext), 'w')
    fp.write(decodedpayload)
    fp.close()
    # Now calculate the url
    url = mlist.GetBaseArchiveURL() + '/attachments/' + file + ext
    return url
