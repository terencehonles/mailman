# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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

"""Prototypical permalinking archiver."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Prototype',
    ]


import os
import errno
import hashlib
import logging

from base64 import b32encode
from datetime import timedelta
from mailbox import Maildir
from urlparse import urljoin

from flufl.lock import Lock, TimeOutError
from zope.interface import implements

from mailman.config import config
from mailman.interfaces.archiver import IArchiver

elog = logging.getLogger('mailman.error')


class Prototype:
    """A prototype of a third party archiver.

    Mailman proposes a draft specification for interoperability between list
    servers and archivers: <http://wiki.list.org/display/DEV/Stable+URLs>.
    """

    implements(IArchiver)

    name = 'prototype'

    @staticmethod
    def list_url(mlist):
        """See `IArchiver`."""
        return mlist.domain.base_url

    @staticmethod
    def permalink(mlist, msg):
        """See `IArchiver`."""
        # It is the LMTP server's responsibility to ensure that the message
        # has a X-Message-ID-Hash header.  If it doesn't then there's no
        # permalink.
        message_id_hash = msg.get('x-message-id-hash')
        if message_id_hash is None:
            return None
        return urljoin(Prototype.list_url(mlist), message_id_hash)

    @staticmethod
    def archive_message(mlist, message):
        """See `IArchiver`.
        
        This sample archiver saves nmessages into a maildir
        """
        archive_dir = os.path.join(config.ARCHIVE_DIR, 'prototype')
        try:
            os.makedirs(archive_dir, 0775)
        except OSError as e:
            # If this already exists, then we're fine
            if e.errno != errno.EEXIST:
                raise

        # Maildir will throw an error if the directories are partially created
        # (for instance the toplevel exists but cur, new, or tmp do not)
        # therefore we don't create the toplevel as we did above
        list_dir = os.path.join(archive_dir, mlist.fqdn_listname)
        mail_box = Maildir(list_dir, create=True, factory=None)

        # Lock the maildir as Maildir.add() is not threadsafe
        lock = Lock(os.path.join(config.LOCK_DIR, '%s-maildir.lock'
            % mlist.fqdn_listname))
        try:
            lock.lock(timeout=timedelta(seconds=1))
            # Add the message to the Maildir
            # Message_key could be used to construct the file path if
            # necessary::
            #   os.path.join(archive_dir, mlist.fqdn_listname, 'new',
            #           message_key)
            message_key = mail_box.add(message)
        except TimeOutError:
            # log the error and go on
            elog.error('Unable to lock archive for %s, discarded'
                    ' message: %s' % (mlist.fqdn_listname, 
                        message.get('message-id', '<unknown>')))
        finally:
            lock.unlock(unconditionally=True)
