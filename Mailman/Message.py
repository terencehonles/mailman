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

"""Standard Mailman message object.

This is a subclass of rfc822.Message but provides an extended interface which
is more convenient for use inside Mailman.  One of the important things it
provides is a writable mapping interface so that new headers can be added, or
existing headers modified.

"""

import sys
import string
import time
from types import StringType

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
        self.body = self.fp.read()
        if self.seekable:
            self.rewindbody()

    def GetSender(self):
	# Look for a Sender field.
	sender = self.getheader('sender')
	if sender:
	    realname, mail_address = self.getaddr('sender')
	else:
            realname, mail_address = self.getaddr('from')
        # We can't trust that any of the headers really contained an address
        if mail_address and type(mail_address) == StringType:
            return string.lower(mail_address)
        else:
            # The unix from line is all we have left...
            if self.unixfrom:
                return string.lower(string.split(self.unixfrom)[1])

    def GetEnvelopeSender(self):
        # look for unix from line and attain address from it.  return None if
        # there is no unix from line.  this function is used to get the
        # envelope sender when mail is sent to a <listname>-admin address
        if not self.unixfrom:
            return None
        # XXX assumes no whitespace in address
        parts = string.split(self.unixfrom)
        for part in parts:
            # perform minimal check for the address
            if string.find(part, '@') > -1:
                user, host = string.split(part, '@', 1)
                if not user: 
                    continue
                if string.count(host, ".") < 1:
                    # doesn't look qualified
                    continue
                return part
        return None

    def GetSenderName(self):
	real_name, mail_addr = self.getaddr('from')
	if not real_name:
	    return self.GetSender()
	return real_name

    def __str__(self):
        # TBD: should this include the unixfrom?
        return string.join(self.headers, '') + '\n' + self.body



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
        self['To'] = recip
        self.recips = [recip]
