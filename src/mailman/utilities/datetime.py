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
    'RFC822_DATE_FMT',
    'UTC',
    'factory',
    'now',
    'today',
    'utc',
    ]


import datetime

from mailman.testing import layers


# Python always sets the locale to 'C' locale unless the user explicitly calls
# locale.setlocale(locale.LC_ALL, '').  Since we never do this in Mailman (and
# no library better do it either!) this will safely give us expected RFC 5322
# Date headers.
RFC822_DATE_FMT = '%a, %d %b %Y %H:%M:%S %z'



# Definition of UTC timezone, taken from
# http://docs.python.org/library/datetime.html
ZERO = datetime.timedelta(0)

class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return ZERO
    def tzname(self, dt):
        return 'UTC'
    def dst(self, dt):
        return ZERO

utc = UTC()
_missing = object()



class DateFactory:
    """A factory for today() and now() that works with testing."""

    # The predictable time.
    predictable_now = None
    predictable_today = None

    def now(self, tz=_missing, strip_tzinfo=True):
        # We can't automatically fast-forward because some tests require us to
        # stay on the same day for a while, e.g. autorespond.txt.
        if tz is _missing:
            tz = utc
        # Storm cannot yet handle datetimes with tz suffixes.  Assume we're
        # using UTC datetimes everywhere, so set the tzinfo to None.  This
        # does *not* change the actual time values.  LP: #280708
        tz_now = (self.predictable_now
                  if layers.is_testing()
                  else datetime.datetime.now(tz))
        return (tz_now.replace(tzinfo=None)
                if strip_tzinfo
                else tz_now)
        

    def today(self):
        return (self.predictable_today
                if layers.is_testing()
                else datetime.date.today())

    @classmethod
    def reset(cls):
        cls.predictable_now = datetime.datetime(2005, 8, 1, 7, 49, 23,
                                                tzinfo=utc)
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
