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

"""Implementations of the pending requests interfaces."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


from datetime import timedelta
from storm.locals import AutoReload, Int, RawStr, Reference, Unicode
from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.interfaces.pending import IPendable, IPendings
from mailman.interfaces.requests import IListRequests, RequestType



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
            token = getUtility(IPendings).add(pendable, timedelta(days=5000))
            data_hash = token
        request = _Request(key, request_type, self.mailing_list, data_hash)
        config.db.store.add(request)
        return request.id

    def get_request(self, request_id, request_type=None):
        result = config.db.store.get(_Request, request_id)
        if result is None:
            return None
        if request_type is not None and result.request_type != request_type:
            return None
        if result.data_hash is None:
            return result.key, result.data_hash
        pendable = getUtility(IPendings).confirm(
            result.data_hash, expunge=False)
        data = dict()
        data.update(pendable)
        return result.key, data

    def delete_request(self, request_id):
        request = config.db.store.get(_Request, request_id)
        if request is None:
            raise KeyError(request_id)
        # Throw away the pended data.
        getUtility(IPendings).confirm(request.data_hash)
        config.db.store.remove(request)



class _Request(Model):
    """Table for mailing list hold requests."""

    id = Int(primary=True, default=AutoReload)
    key = Unicode()
    request_type = Enum(RequestType)
    data_hash = RawStr()

    mailing_list_id = Int()
    mailing_list = Reference(mailing_list_id, 'MailingList.id')

    def __init__(self, key, request_type, mailing_list, data_hash):
        super(_Request, self).__init__()
        self.key = key
        self.request_type = request_type
        self.mailing_list = mailing_list
        self.data_hash = data_hash
