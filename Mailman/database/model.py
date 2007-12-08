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

"""Base class for all database classes."""

__metaclass__ = type
__all__ = [
    'Model',
    ]

from storm.properties import PropertyPublisherMeta



class ModelMeta(PropertyPublisherMeta):
    """Do more magic on table classes."""

    _class_registry = set()

    def __init__(self, name, bases, dict):
        # Before we let the base class do it's thing, force an __storm_table__
        # property to enforce our table naming convention.
        self.__storm_table__ = name.lower()
        super(ModelMeta, self).__init__(name, bases, dict)
        # Register the model class so that it can be more easily cleared.
        # This is required by the test framework.
        if name == 'Model':
            return
        ModelMeta._class_registry.add(self)

    @staticmethod
    def _reset(store):
        for model_class in ModelMeta._class_registry:
            for row in store.find(model_class):
                store.remove(row)



class Model(object):
    """Like Storm's `Storm` subclass, but with a bit extra."""
    __metaclass__ = ModelMeta
