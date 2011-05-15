# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""Bounce support."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'BounceEvent',
    'BounceProcessor',
    ]


from storm.locals import Bool, Int, DateTime, Unicode
from zope.interface import implements

from mailman.interfaces.bounce import (
    BounceContext, IBounceEvent, IBounceProcessor)
from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.utilities.datetime import now



class BounceEvent(Model):
    implements(IBounceEvent)

    id = Int(primary=True)
    list_name = Unicode()
    email = Unicode()
    timestamp = DateTime()
    message_id = Unicode()
    context = Enum()
    processed = Bool()

    def __init__(self, list_name, email, msg, context=None):
        self.list_name = list_name
        self.email = email
        self.timestamp = now()
        self.message_id = msg['message-id']
        self.context = (BounceContext.normal if context is None else context)
        self.processed = False



class BounceProcessor:
    implements(IBounceProcessor)

    def register(self, mlist, email, msg, where=None):
        """See `IBounceProcessor`."""
        return BounceEvent(mlist.fqdn_listname, email, msg, where)
