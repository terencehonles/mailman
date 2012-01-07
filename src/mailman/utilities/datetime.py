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

"""Datetime utilities.

Use these functions to produce variable times rather than the built-in
datetime.datetime.now() and datetime.date.today().  These are better
instrumented for testing purposes.
"""


from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DateFactory',
    'factory',
    'now',
    'today',
    ]


import datetime

from mailman.testing import layers



class DateFactory:
    """A factory for today() and now() that works with testing."""

    # The predictable time.
    predictable_now = None
    predictable_today = None

    def now(self, tz=None):
        # We can't automatically fast-forward because some tests require us to
        # stay on the same day for a while, e.g. autorespond.txt.
        return (self.predictable_now
                if layers.is_testing()
                else datetime.datetime.now(tz))

    def today(self):
        return (self.predictable_today
                if layers.is_testing()
                else datetime.date.today())

    @classmethod
    def reset(cls):
        cls.predictable_now = datetime.datetime(2005, 8, 1, 7, 49, 23)
        cls.predictable_today = cls.predictable_now.date()

    @classmethod
    def fast_forward(cls, days=1):
        cls.predictable_now += datetime.timedelta(days=days)
        cls.predictable_today = cls.predictable_now.date()


factory = DateFactory()
factory.reset()
today = factory.today
now = factory.now
layers.MockAndMonkeyLayer.register_reset(factory.reset)
