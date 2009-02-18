# Copyright (C) 2009 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AutoResponseRecord',
    'AutoResponseSet',
    'adapt_mailing_list_to_response_set',
    ]


from storm.locals import And, Date, Int, Reference
from zope.interface import implements

from mailman.config import config
from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.interfaces.autorespond import (
    IAutoResponseRecord, IAutoResponseSet, Response)
from mailman.interfaces.mailinglist import IMailingList
from mailman.utilities.datetime import today



class AutoResponseRecord(Model):
    implements(IAutoResponseRecord)

    id = Int(primary=True)

    address_id = Int()
    address = Reference(address_id, 'Address.id')

    mailing_list_id = Int()
    mailing_list = Reference(mailing_list_id, 'MailingList.id')

    response_type = Enum()
    date_sent = Date()

    def __init__(self, mailing_list, address, response_type):
        self.mailing_list = mailing_list
        self.address = address
        self.response_type = response_type
        self.date_sent = today()



class AutoResponseSet:
    implements(IAutoResponseSet)

    def __init__(self, mailing_list):
        self._mailing_list = mailing_list

    def todays_count(self, address, response_type):
        """See `IAutoResponseSet`."""
        return config.db.store.find(
            AutoResponseRecord,
            And(AutoResponseRecord.address == address,
                AutoResponseRecord.mailing_list == self._mailing_list,
                AutoResponseRecord.response_type == response_type,
                AutoResponseRecord.date_sent == today())).count()

    def response_sent(self, address, response_type):
        """See `IAutoResponseSet`."""
        response = AutoResponseRecord(
            self._mailing_list, address, response_type)
        config.db.store.add(response)



def adapt_mailing_list_to_response_set(iface, obj):
    """Adapt an `IMailingList` to an `IAutoResponseSet`.

    :param iface: The interface to adapt to.
    :type iface: `zope.interface.Interface`
    :param obj: The object being adapted.
    :type obj: `IMailingList`
    :return: An `IAutoResponseSet` instance if adaptation succeeded or None if
        it didn't.
    """
    return (AutoResponseSet(obj)
            if IMailingList.providedBy(obj) and iface is IAutoResponseSet
            else None)
