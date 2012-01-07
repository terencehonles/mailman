# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""Model for message stores."""


from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MessageStore',
    ]

import os
import errno
import base64
import hashlib
import cPickle as pickle

from zope.interface import implements

from mailman.config import config
from mailman.interfaces.messages import IMessageStore
from mailman.model.message import Message
from mailman.utilities.filesystem import makedirs


# It could be very bad if you have already stored files and you change this
# value.  We'd need a script to reshuffle and resplit.
MAX_SPLITS = 2
EMPTYSTRING = ''



class MessageStore:
    implements(IMessageStore)

    def add(self, message):
        # Ensure that the message has the requisite headers.
        message_ids = message.get_all('message-id', [])
        if len(message_ids) <> 1:
            raise ValueError('Exactly one Message-ID header required')
        # Calculate and insert the X-Message-ID-Hash.
        message_id = message_ids[0]
        # Complain if the Message-ID already exists in the storage.
        existing = config.db.store.find(Message,
                                        Message.message_id == message_id).one()
        if existing is not None:
            raise ValueError(
                'Message ID already exists in message store: {0}'.format(
                    message_id))
        shaobj = hashlib.sha1(message_id)
        hash32 = base64.b32encode(shaobj.digest())
        del message['X-Message-ID-Hash']
        message['X-Message-ID-Hash'] = hash32
        # Calculate the path on disk where we're going to store this message
        # object, in pickled format.
        parts = []
        split = list(hash32)
        while split and len(parts) < MAX_SPLITS:
            parts.append(split.pop(0) + split.pop(0))
        parts.append(hash32)
        relpath = os.path.join(*parts)
        # Store the message in the database.  This relies on the database
        # providing a unique serial number, but to get this information, we
        # have to use a straight insert instead of relying on Elixir to create
        # the object.
        row = Message(message_id=message_id,
                      message_id_hash=hash32,
                      path=relpath)
        # Now calculate the full file system path.
        path = os.path.join(config.MESSAGES_DIR, relpath)
        # Write the file to the path, but catch the appropriate exception in
        # case the parent directories don't yet exist.  In that case, create
        # them and try again.
        while True:
            try:
                with open(path, 'w') as fp:
                    # -1 says to use the highest protocol available.
                    pickle.dump(message, fp, -1)
                    break
            except IOError as error:
                if error.errno <> errno.ENOENT:
                    raise
            makedirs(os.path.dirname(path))
        return hash32

    def _get_message(self, row):
        path = os.path.join(config.MESSAGES_DIR, row.path)
        with open(path) as fp:
            return pickle.load(fp)

    def get_message_by_id(self, message_id):
        row = config.db.store.find(Message, message_id=message_id).one()
        if row is None:
            return None
        return self._get_message(row)

    def get_message_by_hash(self, message_id_hash):
        # It's possible the hash came from a message header, in which case it
        # will be a Unicode.  However when coming from source code, it may be
        # an 8-string.  Coerce to the latter if necessary; it must be
        # US-ASCII.
        if isinstance(message_id_hash, unicode):
            message_id_hash = message_id_hash.encode('ascii')
        row = config.db.store.find(Message,
                                   message_id_hash=message_id_hash).one()
        if row is None:
            return None
        return self._get_message(row)

    @property
    def messages(self):
        for row in config.db.store.find(Message):
            yield self._get_message(row)

    def delete_message(self, message_id):
        row = config.db.store.find(Message, message_id=message_id).one()
        if row is None:
            raise LookupError(message_id)
        path = os.path.join(config.MESSAGES_DIR, row.path)
        os.remove(path)
        config.db.store.remove(row)
