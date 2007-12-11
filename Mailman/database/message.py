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

from storm.locals import *
from zope.interface import implements

from Mailman.configuration import config
from Mailman.database.model import Model
from Mailman.interfaces import IMessage



class Message(Model):
    """A message in the message store."""

    implements(IMessage)

    id = Int(primary=True, default=AutoReload)
    message_id = Unicode()
    message_id_hash = RawStr()
    path = RawStr()
    # This is a Messge-ID field representation, not a database row id.

    def __init__(self, message_id, message_id_hash, path):
        self.message_id = message_id
        self.message_id_hash = message_id_hash
        self.path = path
        config.db.store.add(self)
