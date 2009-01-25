# Copyright (C) 2006-2009 by the Free Software Foundation, Inc.
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

"""Base class for all database classes."""

from __future__ import absolute_import, unicode_literals

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
            store.find(model_class).remove()



class Model:
    """Like Storm's `Storm` subclass, but with a bit extra."""
    __metaclass__ = ModelMeta
