# Copyright (C) 2006-2007 by the Free Software Foundation, Inc.
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

from Mailman.database import Model
from Mailman.database.types import Enum
from Mailman.interfaces import IPreferences



class Preferences(Model):
    implements(IPreferences)

    id = Int(primary=True)
    acknowledge_posts = Bool()
    hide_address = Bool()
    preferred_language = Unicode()
    receive_list_copy = Bool()
    receive_own_postings = Bool()
    delivery_mode = Enum()
    delivery_status = Enum()

    def __repr__(self):
        return '<Preferences object at %#x>' % id(self)
