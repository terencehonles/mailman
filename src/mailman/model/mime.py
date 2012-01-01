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

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ContentFilter'
    ]


from storm.locals import Int, Reference, Unicode
from zope.interface import implements

from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.interfaces.mime import IContentFilter, FilterType



class ContentFilter(Model):
    """A single filter criteria."""
    implements(IContentFilter)

    id = Int(primary=True)

    mailing_list_id = Int()
    mailing_list = Reference(mailing_list_id, 'MailingList.id')

    filter_type = Enum(FilterType)
    filter_pattern = Unicode()

    def __init__(self, mailing_list, filter_pattern, filter_type):
        self.mailing_list = mailing_list
        self.filter_pattern = filter_pattern
        self.filter_type = filter_type
