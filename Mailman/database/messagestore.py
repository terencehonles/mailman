# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

from __future__ import with_statement

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

from Mailman import Utils
from Mailman.configuration import config
from Mailman.database.model import Message
from Mailman.interfaces import IMessageStore

# It could be very bad if you have already stored files and you change this
# value.  We'd need a script to reshuffle and resplit.
MAX_SPLITS = 2
EMPTYSTRING = ''



class MessageStore:
    implements(IMessageStore)

    def add(self, message):
        # Ensure that the message has the requisite headers.
        message_ids = message.get_all('message-id', [])
        dates = message.get_all('date', [])
        if not (len(message_ids) == 1 and len(dates) == 1):
            raise ValueError(
                'Exactly one Message-ID and one Date header required')
        # Calculate and insert the X-List-ID-Hash.
        message_id = message_ids[0]
        date = dates[0]
        shaobj = hashlib.sha1(message_id)
        shaobj.update(date)
        hash32 = base64.b32encode(shaobj.digest())
        del message['X-List-ID-Hash']
        message['X-List-ID-Hash'] = hash32
        # Calculate the path on disk where we're going to store this message
        # object, in pickled format.
        parts = []
        split = list(hash32)
        while split and len(parts) < MAX_SPLITS:
            parts.append(split.pop(0) + split.pop(0))
        parts.append(EMPTYSTRING.join(split))
        relpath = os.path.join(*parts)
        # Store the message in the database.  This relies on the database
        # providing a unique serial number, but to get this information, we
        # have to use a straight insert instead of relying on Elixir to create
        # the object.
        result = Message.table.insert().execute(
            hash=hash32, path=relpath, message_id=message_id)
        # Add the additional header.
        seqno = result.last_inserted_ids()[0]
        del message['X-List-Sequence-Number']
        message['X-List-Sequence-Number'] = str(seqno)
        # Now calculate the full file system path.
        path = os.path.join(config.MESSAGES_DIR, relpath, str(seqno))
        # Write the file to the path, but catch the appropriate exception in
        # case the parent directories don't yet exist.  In that case, create
        # them and try again.
        while True:
            try:
                with open(path, 'w') as fp:
                    # -1 says to use the highest protocol available.
                    pickle.dump(message, fp, -1)
                    break
            except IOError, e:
                if e.errno <> errno.ENOENT:
                    raise
            os.makedirs(os.path.dirname(path))
        return seqno

    def _msgobj(self, msgrow):
        path = os.path.join(config.MESSAGES_DIR, msgrow.path, str(msgrow.id))
        with open(path) as fp:
            return pickle.load(fp)

    def get_messages_by_message_id(self, message_id):
        for msgrow in Message.select_by(message_id=message_id):
            yield self._msgobj(msgrow)

    def get_messages_by_hash(self, hash):
        for msgrow in Message.select_by(hash=hash):
            yield self._msgobj(msgrow)

    def _getmsg(self, global_id):
        try:
            hash, seqno = global_id.split('/', 1)
            seqno = int(seqno)
        except ValueError:
            return None
        msgrows = Message.select_by(id=seqno)
        if not msgrows:
            return None
        assert len(msgrows) == 1, 'Multiple id matches'
        if msgrows[0].hash <> hash:
            # The client lied about which message they wanted.  They gave a
            # valid sequence number, but the hash did not match.
            return None
        return msgrows[0]

    def get_message(self, global_id):
        msgrow = self._getmsg(global_id)
        return (self._msgobj(msgrow) if msgrow is not None else None)

    @property
    def messages(self):
        for msgrow in Message.select():
            yield self._msgobj(msgrow)

    def delete_message(self, global_id):
        msgrow = self._getmsg(global_id)
        if msgrow is None:
            raise KeyError(global_id)
        msgrow.delete()
