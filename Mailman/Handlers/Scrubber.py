# Copyright (C) 2001,2002 by the Free Software Foundation, Inc.
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
import re
import sha
import cgi
import errno
import mimetypes
import tempfile
from cStringIO import StringIO
from types import IntType

from email.Parser import HeaderParser
from email.Generator import Generator

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import LockFile
from Mailman import Message
from Mailman.Errors import DiscardMessage
from Mailman.i18n import _
from Mailman.Logging.Syslog import syslog

# Path characters for common platforms
pre = re.compile(r'[/\\:]')
# All other characters to strip out of Content-Disposition: filenames
# (essentially anything that isn't an alphanum, dot, slash, or underscore.
sre = re.compile(r'[^-\w.]')

BR = '<br>\n'



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
    sanitize = mm_cfg.ARCHIVE_HTML_SANITIZER
    outer = 1
    for part in msg.walk():
        # If the part is text/plain, we leave it alone
        if part.get_type('text/plain') == 'text/plain':
            pass
        elif part.get_type() == 'text/html' and isinstance(sanitize, IntType):
            if sanitize == 0:
                if outer:
                    raise DiscardMessage
                part.set_payload(_('HTML attachment scrubbed and removed'))
            elif sanitize == 2:
                # By leaving it alone, Pipermail will automatically escape it
                pass
            elif sanitize == 3:
                # Pull it out as an attachment but leave it unescaped.  This
                # is dangerous, but perhaps useful for heavily moderated
                # lists.
                omask = os.umask(002)
                try:
                    url = save_attachment(mlist, part, filter_html=0)
                finally:
                    os.umask(omask)
                part.set_payload(_("""\
An HTML attachment was scrubbed...
URL: %(url)s
"""))
            else:
                # HTML-escape it and store it as an attachment, but make it
                # look a /little/ bit prettier. :(
                payload = cgi.escape(part.get_payload())
                # For whitespace in the margin, change spaces into
                # non-breaking spaces, and tabs into 8 of those.  Then use a
                # mono-space font.  Still looks hideous to me, but then I'd
                # just as soon discard them.
                def doreplace(s):
                    return s.replace(' ', '&nbsp;').replace('\t', '&nbsp'*8)
                lines = [doreplace(s) for s in payload.split('\n')]
                payload = '<tt>\n' + BR.join(lines) + '\n</tt>\n'
                part.set_payload(payload)
                omask = os.umask(002)
                try:
                    url = save_attachment(mlist, part, filter_html=0)
                finally:
                    os.umask(omask)
                part.set_payload(_("""\
An HTML attachment was scrubbed...
URL: %(url)s
"""))
        elif part.get_type() == 'message/rfc822':
            # This part contains a submessage, so it too needs scrubbing
            submsg = part.get_payload()
            omask = os.umask(002)
            try:
                url = save_attachment(mlist, part)
            finally:
                os.umask(omask)
            subject = submsg.get('subject', _('no subject'))
            date = submsg.get('date', _('no date'))
            who = submsg.get('from', _('unknown sender'))
            size = len(str(submsg))
            part.set_payload(_("""\
An embedded message was scrubbed...
From: %(who)s
Subject: %(subject)s
Date: %(date)s
Size: %(size)s
Url: %(url)s
"""))
            # If we were to leave the message/rfc822 Content-Type: header, it
            # would confuse the generator.  So just delete it.  The generator
            # will treat this as a text/plain message.
            del part['content-type']
        # If the message isn't a multipart, then we'll strip it out as an
        # attachment that would have to be separately downloaded.  Pipermail
        # will transform the url into a hyperlink.
        elif not part.is_multipart():
            payload = part.get_payload()
            ctype = part.get_type()
            size = len(payload)
            omask = os.umask(002)
            try:
                url = save_attachment(mlist, part)
            finally:
                os.umask(omask)
            desc = part.get('content-description', _('not available'))
            filename = part.get_filename(_('not available'))
            part.set_payload(_("""\
A non-text attachment was scrubbed...
Name: %(filename)s
Type: %(ctype)s
Size: %(size)d bytes
Desc: %(desc)s
Url : %(url)s
"""))
        outer = 0
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



def save_attachment(mlist, msg, filter_html=1):
    # The directory to store the attachment in
    dir = os.path.join(mlist.archive_dir(), 'attachments')
    try:
        os.mkdir(dir, 02775)
    except OSError, e:
        if e.errno <> errno.EEXIST: raise
    # We need a directory to contain this message's attachments.  Base it
    # on the Message-ID: so that all attachments for the same message end
    # up in the same directory (we'll uniquify the filenames in that
    # directory as needed).  We use the first 2 and last 2 bytes of the
    # SHA1 has of the message id as the basis of the directory name.
    # Clashes here don't really matter too much, and that still gives us a
    # 32-bit space to work with.
    msgid = msg['message-id']
    if msgid is None:
        msgid = msg['Message-ID'] = Utils.unique_message_id(mlist)
    # We assume that the message id actually /is/ unique!
    digest = sha.new(msgid).hexdigest()
    msgdir = digest[:4] + digest[-4:]
    try:
        os.mkdir(os.path.join(dir, msgdir), 02775)
    except OSError, e:
        if e.errno <> errno.EEXIST: raise
    # Figure out the attachment type and get the decoded data
    decodedpayload = msg.get_payload(decode=1)
    # BAW: mimetypes ought to handle non-standard, but commonly found types,
    # e.g. image/jpg (should be image/jpeg).  For now we just store such
    # things as application/octet-streams since that seems the safest.
    ext = mimetypes.guess_extension(msg.get_type())
    if not ext:
        # We don't know what it is, so assume it's just a shapeless
        # application/octet-stream, unless the Content-Type: is
        # message/rfc822, in which case we know we'll coerce the type to
        # text/plain below.
        if msg.get_type() == 'message/rfc822':
            ext = '.txt'
        else:
            ext = '.bin'
    path = None
    # We need a lock to calculate the next attachment number
    lockfile = os.path.join(dir, msgdir, 'attachments.lock')
    lock = LockFile.LockFile(lockfile)
    lock.lock()
    try:
        # Now base the filename on what's in the attachment, uniquifying it if
        # necessary.
        filename = msg.get_filename()
        if not filename:
            filename = 'attachment' + ext
        else:
            # Sanitize the filename given in the message headers
            parts = pre.split(filename)
            filename = parts[-1]
            # Allow only alphanumerics, dash, underscore, and dot
            filename = sre.sub('', filename)
            # If the filename's extension doesn't match the type we guessed,
            # which one should we go with?  Not sure.  Let's do this at least:
            # if the filename /has/ no extension, then tack on the one we
            # guessed.
            if not os.path.splitext(filename)[1]:
                filename += ext
            # BAW: Anything else we need to be worried about?
        counter = 0
        extra = ''
        while 1:
            path = os.path.join(dir, msgdir, filename + extra)
            # Generally it is not a good idea to test for file existance
            # before just trying to create it, but the alternatives aren't
            # wonderful (i.e. os.open(..., O_CREAT | O_EXCL) isn't
            # NFS-safe).  Besides, we have an exclusive lock now, so we're
            # guaranteed that no other process will be racing with us.
            if os.path.exists(path):
                counter += 1
                extra = '-%04d%s' % (counter, ext)
            else:
                break
    finally:
        lock.unlock()
    # `path' now contains the unique filename for the attachment.  There's
    # just one more step we need to do.  If the part is text/html and
    # ARCHIVE_HTML_SANITIZER is a string (which it must be or we wouldn't be
    # here), then send the attachment through the filter program for
    # sanitization
    if filter_html and msg.get_type() == 'text/html':
        base, ext = os.path.splitext(path)
        tmppath = base + '-tmp' + ext
        fp = open(tmppath, 'w')
        try:
            fp.write(decodedpayload)
            fp.close()
            cmd = mm_cfg.ARCHIVE_HTML_SANITIZER % {'filename' : tmppath}
            progfp = os.popen(cmd, 'r')
            decodedpayload = progfp.read()
            status = progfp.close()
            if status:
                syslog('error',
                       'HTML sanitizer exited with non-zero status: %s',
                       status)
        finally:
            os.unlink(tmppath)
        # BAW: Since we've now sanitized the document, it should be plain
        # text.  Blarg, we really want the sanitizer to tell us what the type
        # if the return data is. :(
        path = base + '.txt'
        filename = os.path.splitext(filename)[0] + '.txt'
    # Is it a message/rfc822 attachment?
    elif msg.get_type() == 'message/rfc822':
        submsg = msg.get_payload()
        # BAW: I'm sure we can eventually do better than this. :(
        decodedpayload = cgi.escape(str(submsg))
    fp = open(path, 'w')
    fp.write(decodedpayload)
    fp.close()
    # Now calculate the url
    baseurl = mlist.GetBaseArchiveURL()
    # Private archives will likely have a trailing slash.  Normalize.
    if baseurl[-1] <> '/':
        baseurl += '/'
    url = baseurl + 'attachments/%s/%s' % (msgdir, filename)
    return url
