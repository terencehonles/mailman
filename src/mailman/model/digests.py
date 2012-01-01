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

"""One last digest."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'OneLastDigest',
    ]


from storm.locals import Int, Reference
from zope.interface import implements

from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.interfaces.digests import IOneLastDigest
from mailman.interfaces.member import DeliveryMode



class OneLastDigest(Model):
    implements(IOneLastDigest)

    id = Int(primary=True)

    mailing_list_id = Int()
    mailing_list = Reference(mailing_list_id, 'MailingList.id')

    address_id = Int()
    address = Reference(address_id, 'Address.id')

    delivery_mode = Enum(DeliveryMode)

    def __init__(self, mailing_list, address, delivery_mode):
        self.mailing_list = mailing_list
        self.address = address
        self.delivery_mode = delivery_mode
