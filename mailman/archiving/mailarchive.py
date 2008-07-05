# Copyright (C) 2008 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""The Mail-Archive.com archiver."""

__metaclass__ = type
__all__ = [
    'MailArchive',
    ]


import hashlib

from base64 import urlsafe_b64encode
from urllib import quote
from urlparse import urljoin
from zope.interface import implements

from mailman.configuration import config
from mailman.interfaces.archiver import IArchiver
from mailman.queue import Switchboard



class MailArchive:
    """Public archiver at the Mail-Archive.com.

    Messages get archived at http://go.mail-archive.com.
    """

    implements(IArchiver)

    name = 'mail-archive'
    is_enabled = False

    @staticmethod
    def list_url(mlist):
        """See `IArchiver`."""
        if mlist.archive_private:
            return None
        return urljoin(config.MAIL_ARCHIVE_BASEURL,
                       quote(mlist.posting_address))

    @staticmethod
    def permalink(mlist, msg):
        """See `IArchiver`."""
        if mlist.archive_private:
            return None
        message_id = msg.get('message-id')
        # It is not the archiver's job to ensure the message has a Message-ID.
        assert message_id is not None, 'No Message-ID found'
        # The angle brackets are not part of the Message-ID.  See RFC 2822.
        start = (1 if message_id.startswith('<') else 0)
        end = (-1 if message_id.endswith('>') else None)
        message_id = message_id[start:end]
        sha = hashlib.sha1(message_id)
        sha.update(str(mlist.post_id))
        message_id_hash = urlsafe_b64encode(sha.digest())
        del msg['x-message-id-hash']
        msg['X-Message-ID-Hash'] = message_id_hash
        return urljoin(config.MAIL_ARCHIVE_BASEURL, message_id_hash)

    @staticmethod
    def archive_message(mlist, msg):
        """See `IArchiver`."""
        if mlist.archive_private:
            return
        outq = Switchboard(config.OUTQUEUE_DIR)
        outq.enqueue(
            msg,
            listname=mlist.fqdn_listname,
            recips=[config.MAIL_ARCHIVE_RECIPIENT])
