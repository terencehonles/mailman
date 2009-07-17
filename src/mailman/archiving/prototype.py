# Copyright (C) 2008-2009 by the Free Software Foundation, Inc.
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


import hashlib

from base64 import b32encode
from urlparse import urljoin
from zope.interface import implements

from mailman.config import config
from mailman.interfaces.archiver import IArchiver
from mailman.interfaces.domain import IDomainManager



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
        return IDomainManager(config)[mlist.host_name].base_url

    @staticmethod
    def permalink(mlist, msg):
        """See `IArchiver`."""
        message_id = msg.get('message-id')
        # It is not the archiver's job to ensure the message has a Message-ID.
        # If this header is missing, there is no permalink.
        if message_id is None:
            return None
        # The angle brackets are not part of the Message-ID.  See RFC 2822.
        if message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]
        else:
            message_id = message_id.strip()
        digest = hashlib.sha1(message_id).digest()
        message_id_hash = b32encode(digest)
        del msg['x-message-id-hash']
        msg['X-Message-ID-Hash'] = message_id_hash
        return urljoin(Prototype.list_url(mlist), message_id_hash)

    @staticmethod
    def archive_message(mlist, message):
        """See `IArchiver`."""
        raise NotImplementedError
