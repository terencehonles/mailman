# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Module stuff."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'AutoResponseRecord',
    'AutoResponseSet',
    ]


from storm.locals import And, Date, Desc, Int, Reference
from zope.interface import implementer

from mailman.database.model import Model
from mailman.database.transaction import dbconnection
from mailman.database.types import Enum
from mailman.interfaces.autorespond import (
    IAutoResponseRecord, IAutoResponseSet, Response)
from mailman.utilities.datetime import today



@implementer(IAutoResponseRecord)
class AutoResponseRecord(Model):
    """See `IAutoResponseRecord`."""

    id = Int(primary=True)

    address_id = Int()
    address = Reference(address_id, 'Address.id')

    mailing_list_id = Int()
    mailing_list = Reference(mailing_list_id, 'MailingList.id')

    response_type = Enum(Response)
    date_sent = Date()

    def __init__(self, mailing_list, address, response_type):
        self.mailing_list = mailing_list
        self.address = address
        self.response_type = response_type
        self.date_sent = today()



@implementer(IAutoResponseSet)
class AutoResponseSet:
    """See `IAutoResponseSet`."""

    def __init__(self, mailing_list):
        self._mailing_list = mailing_list

    @dbconnection
    def todays_count(self, store, address, response_type):
        """See `IAutoResponseSet`."""
        return store.find(
            AutoResponseRecord,
            And(AutoResponseRecord.address == address,
                AutoResponseRecord.mailing_list == self._mailing_list,
                AutoResponseRecord.response_type == response_type,
                AutoResponseRecord.date_sent == today())).count()

    @dbconnection
    def response_sent(self, store, address, response_type):
        """See `IAutoResponseSet`."""
        response = AutoResponseRecord(
            self._mailing_list, address, response_type)
        store.add(response)

    @dbconnection
    def last_response(self, store, address, response_type):
        """See `IAutoResponseSet`."""
        results = store.find(
            AutoResponseRecord,
            And(AutoResponseRecord.address == address,
                AutoResponseRecord.mailing_list == self._mailing_list,
                AutoResponseRecord.response_type == response_type)
            ).order_by(Desc(AutoResponseRecord.date_sent))
        return (None if results.count() == 0 else results.first())
