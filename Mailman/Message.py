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

"""Standard Mailman message object.

This is a subclass of rfc822.Message but provides an extended interface which
is more convenient for use inside Mailman.  One of the important things it
provides is a writable mapping interface so that new headers can be added, or
existing headers modified.

"""

import sys
import os
import string
import time
import sha
import marshal
from types import StringType, ListType

from Mailman import mm_cfg
from Mailman import Utils

# Python 1.5's version of rfc822.py is buggy and lacks features we
# depend on -- so we always use the up-to-date version distributed
# with Mailman.
from Mailman.pythonlib import rfc822



class Message(rfc822.Message):
    """This class extends the standard rfc822.Message object.

    It provides some convenience functions for getting certain interesting
    information out of the message.

    """
    def __init__(self, fp):
        rfc822.Message.__init__(self, fp)
        if self.seekable:
            self.rewindbody()
        self.body = self.fp.read()

    def __repr__(self):
        """Return the entire reproducible message.
        This includes the headers, body, and `unixfrom' line.
        """
        return self.unixfrom + string.join(self.headers, '') + '\n' + self.body

    def __str__(self):
        """Return the string representation of the message.
        This includes just the standard RFC822 headers and body text.
        """
        return string.join(self.headers, '') + '\n' + self.body

    def GetSender(self, use_envelope=None):
        """Return the address considered to be the author of the email.

        This can return either the From: header, the Sender: header or the
        envelope header (a.k.a. the unixfrom header).  The first non-empty
        header value found is returned.  However the search order is
        determined by the following:

        - If mm_cfg.USE_ENVELOPE_SENDER is true, then the search order is
          Sender:, From:, unixfrom

        - Otherwise, the search order is From:, Sender:, unixfrom

        The optional argument use_envelope, if given overrides the
        mm_cfg.USE_ENVELOPE_SENDER setting.  It should be set to either 0 or 1
        (don't use None since that indicates no-override).

        unixfrom should never be empty.

        """
        senderfirst = mm_cfg.USE_ENVELOPE_SENDER
        if use_envelope is not None:
            senderfirst = use_envelope
        if senderfirst:
            headers = ('sender', 'from')
        else:
            headers = ('from', 'sender')
        for h in headers:
            realname, address = self.getaddr(h)
            # TBD: previous code said: "We can't trust that any of the headers
            # really contained an address".  I don't know if that's still true
            # or not, but we still test this
            if address and type(address) == StringType:
                return string.lower(address)
        # Didn't find a non-empty header, so let's fall back to the unixfrom
        # address.  This should never be empty, but if it ever is, it's
        # probably a Really Bad Thing.
        #
        # We also don't do all the elaboration that the old
        # GetEnvelopeSender() did.  We just assume that if the unixfrom
        # exists, the second field is the address.  This is what GetSender()
        # always did.
        if self.unixfrom:
            return string.lower(string.split(self.unixfrom)[1])
        else:
            # TBD: now what?!
            return ''

    def Enqueue(self, mlist, newdata={}, **kws):
        """Enqueue a message for redelivery by the qrunner cronjob.

        For each enqueued message, a .msg and a .db file is written.  The .msg
        contains the plain text of the message (TBD: should this be called
        .txt?).  The .db contains a marshaled dictionary of message metadata.
        The base name of the file is the SHA hexdigest of the message text.

        The message metadata is a dictionary calculated as follows:

        - If the message was previously queued, it is now being requeued and
          the metadata dictionary is initialized from the existing .db file.
          Otherwise the metadata is initialized to a dictionary containing the
          listname and a scheme version number.

        - If the argument `newdata' was given, the metadata dictionary
          initialized above is .update()'d with newdata (which must conform to
          the mapping interface).

        - If additional keyword arguments are given, they are .update()'d into
          the metadata dictionary.

        mlist is the mailing list that delivery is to be attempted for.

        """
        # Calculate a unique name for the queue file
        text = repr(self)
        filebase = sha.new(text).hexdigest()
        msgfile = os.path.join(mm_cfg.QUEUE_DIR, filebase + '.msg')
        dbfile = os.path.join(mm_cfg.QUEUE_DIR, filebase + '.db')
        # Initialize the information about this message delivery.  It's
        # possible a delivery attempt has been previously tried on this
        # message, in which case, we'll just update the data.
        try:
            dbfp = open(dbfile)
            msgdata = marshal.load(dbfp)
            dbfp.close()
            existsp = 1
        except (EOFError, ValueError, TypeError, IOError):
            msgdata = {'listname' : mlist.internal_name(),
                       'version'  : mm_cfg.QFILE_SCHEMA_VERSION,
                       }
            existsp = 0
        # Merge in the additional msgdata
        msgdata.update(newdata)
        msgdata.update(kws)
        # Get rid of volatile entries, which have the convention of starting
        # with an underscore (TBD: should we use v_ as a naming convention?)
        for k in msgdata.keys():
            if k[0] == '_':
                del msgdata[k]
        # Write the data file
        dbfp = Utils.open_ex(dbfile, 'w')
        marshal.dump(msgdata, dbfp)
        dbfp.close()
        # if it doesn't already exist, write the message file
        if not existsp:
            msgfp = Utils.open_ex(msgfile, 'w')
            msgfp.write(text)
            msgfp.close()



class OutgoingMessage(Message):
    def __init__(self, text=''):
        from Mailman.pythonlib.StringIO import StringIO
        # NOTE: text if supplied must begin with valid rfc822 headers.  It can
        # also begin with the body of the message but in that case you better
        # make sure that the first line does NOT contain a colon!
        Message.__init__(self, StringIO(text))



class UserNotification(OutgoingMessage):
    def __init__(self, recip, sender, subject=None, text=''):
        OutgoingMessage.__init__(self, text)
        if subject is None:
            subject = '(no subject)'
        self['Subject'] = subject
        self['From'] = sender
        if type(recip) == ListType:
            self['To'] = string.join(recip, ', ')
            self.recips = recip[:]
        else:
            self['To'] = recip
            self.recips = [recip]
