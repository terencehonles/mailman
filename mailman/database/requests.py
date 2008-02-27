# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""Implementations of the IRequests and IListRequests interfaces."""

from datetime import timedelta
from storm.locals import *
from zope.interface import implements

from mailman.configuration import config
from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.interfaces import IListRequests, IPendable, IRequests, RequestType


__metaclass__ = type
__all__ = [
    'Requests',
    ]



class DataPendable(dict):
    implements(IPendable)



class ListRequests:
    implements(IListRequests)

    def __init__(self, mailing_list):
        self.mailing_list = mailing_list

    @property
    def count(self):
        return config.db.store.find(
            _Request, mailing_list=self.mailing_list).count()

    def count_of(self, request_type):
        return config.db.store.find(
            _Request,
            mailing_list=self.mailing_list, request_type=request_type).count()

    @property
    def held_requests(self):
        results = config.db.store.find(
            _Request, mailing_list=self.mailing_list)
        for request in results:
            yield request

    def of_type(self, request_type):
        results = config.db.store.find(
            _Request,
            mailing_list=self.mailing_list, request_type=request_type)
        for request in results:
            yield request

    def hold_request(self, request_type, key, data=None):
        if request_type not in RequestType:
            raise TypeError(request_type)
        if data is None:
            data_hash = None
        else:
            # We're abusing the pending database as a way of storing arbitrary
            # key/value pairs, where both are strings.  This isn't ideal but
            # it lets us get auxiliary data almost for free.  We may need to
            # lock this down more later.
            pendable = DataPendable()
            pendable.update(data)
            token = config.db.pendings.add(pendable, timedelta(days=5000))
            data_hash = token
        request = _Request(key, request_type, self.mailing_list, data_hash)
        config.db.store.add(request)
        return request.id

    def get_request(self, request_id):
        result = config.db.store.get(_Request, request_id)
        if result is None:
            return None
        if result.data_hash is None:
            return result.key, result.data_hash
        pendable = config.db.pendings.confirm(result.data_hash, expunge=False)
        data = dict()
        data.update(pendable)
        return result.key, data

    def delete_request(self, request_id):
        request = config.db.store.get(_Request, request_id)
        if request is None:
            raise KeyError(request_id)
        # Throw away the pended data.
        config.db.pendings.confirm(request.data_hash)
        config.db.store.remove(request)



class Requests:
    implements(IRequests)

    def get_list_requests(self, mailing_list):
        return ListRequests(mailing_list)



class _Request(Model):
    """Table for mailing list hold requests."""

    id = Int(primary=True, default=AutoReload)
    key = Unicode()
    request_type = Enum()
    data_hash = RawStr()

    mailing_list_id = Int()
    mailing_list = Reference(mailing_list_id, 'MailingList.id')

    def __init__(self, key, request_type, mailing_list, data_hash):
        self.key = key
        self.request_type = request_type
        self.mailing_list = mailing_list
        self.data_hash = data_hash
