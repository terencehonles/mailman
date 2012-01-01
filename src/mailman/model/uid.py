# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Unique IDs."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'UID',
    ]


from storm.locals import Int
from storm.properties import UUID

from mailman.config import config
from mailman.database.model import Model



class UID(Model):
    """Enforce uniqueness of uids through a database table.

    This is used so that unique ids don't have to be tracked by each
    individual model object that uses them.  So for example, when a user is
    deleted, we don't have to keep separate track of its uid to prevent it
    from ever being used again.  This class, hooked up to the
    `UniqueIDFactory` serves that purpose.

    There is no interface for this class, because it's purely an internal
    implementation detail.
    """
    id = Int(primary=True)
    uid = UUID()

    def __init__(self, uid):
        super(UID, self).__init__()
        self.uid = uid
        config.db.store.add(self)

    def __repr__(self):
        return '<UID {0} at {1}>'.format(self.uid, id(self))

    @staticmethod
    def record(uid):
        """Record the uid in the database.

        :param uid: The unique id.
        :type uid: unicode
        :raises ValueError: if the id is not unique.
        """
        existing = config.db.store.find(UID, uid=uid)
        if existing.count() != 0:
            raise ValueError(uid)
        return UID(uid)
