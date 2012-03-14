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
import logging

from datetime import timedelta
from mailbox import Maildir
from urlparse import urljoin

from flufl.lock import Lock, TimeOutError
from zope.interface import implements

from mailman.config import config
from mailman.interfaces.archiver import IArchiver

log = logging.getLogger('mailman.error')



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

        This archiver saves messages into a maildir.
        """
        archive_dir = os.path.join(config.ARCHIVE_DIR, 'prototype')
        try:
            os.makedirs(archive_dir, 0775)
        except OSError as error:
            # If this already exists, then we're fine
            if error.errno != errno.EEXIST:
                raise

        # Maildir will throw an error if the directories are partially created
        # (for instance the toplevel exists but cur, new, or tmp do not)
        # therefore we don't create the toplevel as we did above.
        list_dir = os.path.join(archive_dir, mlist.fqdn_listname)
        mailbox = Maildir(list_dir, create=True, factory=None)
        lock_file = os.path.join(
            config.LOCK_DIR, '{0}-maildir.lock'.format(mlist.fqdn_listname))

        # Lock the maildir as Maildir.add() is not threadsafe.  Don't use the
        # context manager because it's not an error if we can't acquire the
        # archiver lock.  We'll just log the problem and continue.
        #
        # XXX 2012-03-14 BAW: When we extend the chain/pipeline architecture
        # to other runners, e.g. the archive runner, it would be better to let
        # any TimeOutError propagate up.  That would cause the message to be
        # re-queued and tried again later, rather than being discarded as
        # happens now below.
        lock = Lock(lock_file)
        try:
            lock.lock(timeout=timedelta(seconds=1))
            # Add the message to the maildir.  The return value could be used
            # to construct the file path if necessary.  E.g.
            #
            # os.path.join(archive_dir, mlist.fqdn_listname, 'new',
            #              message_key)
            mailbox.add(message)
        except TimeOutError:
            # Log the error and go on.
            log.error('Unable to acquire prototype archiver lock for {0}, '
                      'discarding: {1}'.format(
                          mlist.fqdn_listname,
                          message.get('message-id', 'n/a')))
        finally:
            lock.unlock(unconditionally=True)
