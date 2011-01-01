# Copyright (C) 2008-2011 by the Free Software Foundation, Inc.
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

"""The Mail-Archive.com archiver."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MailArchive',
    ]


import hashlib

from base64 import urlsafe_b64encode
from urllib import quote
from urlparse import urljoin
from zope.interface import implements

from mailman.config import config
from mailman.interfaces.archiver import IArchiver



class MailArchive:
    """Public archiver at the Mail-Archive.com.

    Messages get archived at http://go.mail-archive.com.
    """

    implements(IArchiver)

    name = 'mail-archive'

    @staticmethod
    def list_url(mlist):
        """See `IArchiver`."""
        if mlist.archive_private:
            return None
        return urljoin(config.archiver.mail_archive.base_url,
                       quote(mlist.posting_address))

    @staticmethod
    def permalink(mlist, msg):
        """See `IArchiver`."""
        if mlist.archive_private:
            return None
        message_id = msg.get('message-id')
        # It is not the archiver's job to ensure the message has a Message-ID.
        # If no Message-ID is available, there is no permalink.
        if message_id is None:
            return None
        # The angle brackets are not part of the Message-ID.  See RFC 2822.
        if message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]
        else:
            message_id = message_id.strip()
        sha = hashlib.sha1(message_id)
        sha.update(str(mlist.posting_address))
        message_id_hash = urlsafe_b64encode(sha.digest())
        del msg['x-message-id-hash']
        msg['X-Message-ID-Hash'] = message_id_hash
        return urljoin(config.archiver.mail_archive.base_url, message_id_hash)

    @staticmethod
    def archive_message(mlist, msg):
        """See `IArchiver`."""
        if not mlist.archive_private:
            config.switchboards['out'].enqueue(
                msg,
                listname=mlist.fqdn_listname,
                recipients=[config.archiver.mail_archive.recipient])
