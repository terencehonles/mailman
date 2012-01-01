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

"""Internationalization."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    '_',
    'ctime',
    'initialize',
    ]


import time
from flufl.i18n import PackageStrategy, registry

import mailman.messages


_ = None



def initialize(application=None):
    """Initialize the i18n subsystem.

    :param application: An optional `flufl.i18n.Application` instance to use
        as the translation context.  This primarily exists to support the
        testing environment.
    :type application: `flufl.i18n.Application`
    """
    global _
    if application is None:
        strategy = PackageStrategy('mailman', mailman.messages)
        application = registry.register(strategy)
    _ = application._



def ctime(date):
    """Translate a ctime.

    :param date: The date to translate.
    :type date: str or time float
    :return: The translated date.
    :rtype: string
    """
    # Don't make these module globals since we have to do runtime translation
    # of the strings anyway.
    daysofweek = [
        _('Mon'), _('Tue'), _('Wed'), _('Thu'),
        _('Fri'), _('Sat'), _('Sun')
        ]
    months = [
        '',
        _('Jan'), _('Feb'), _('Mar'), _('Apr'), _('May'), _('Jun'),
        _('Jul'), _('Aug'), _('Sep'), _('Oct'), _('Nov'), _('Dec')
        ]

    tzname = _('Server Local Time')
    if isinstance(date, str):
        try:
            year, mon, day, hh, mm, ss, wday, ydat, dst = time.strptime(date)
            if dst in (0, 1):
                tzname = time.tzname[dst]
            else:
                # MAS: No exception but dst = -1 so try
                return ctime(time.mktime((year, mon, day, hh, mm, ss, wday,
                                          ydat, dst)))
        except (ValueError, AttributeError):
            try:
                wday, mon, day, hms, year = date.split()
                hh, mm, ss = hms.split(':')
                year = int(year)
                day = int(day)
                hh = int(hh)
                mm = int(mm)
                ss = int(ss)
            except ValueError:
                return date
            else:
                for i in range(0, 7):
                    wconst = (1999, 1, 1, 0, 0, 0, i, 1, 0)
                    if wday.lower() == time.strftime('%a', wconst).lower():
                        wday = i
                        break
                for i in range(1, 13):
                    mconst = (1999, i, 1, 0, 0, 0, 0, 1, 0)
                    if mon.lower() == time.strftime('%b', mconst).lower():
                        mon = i
                        break
    else:
        year, mon, day, hh, mm, ss, wday, yday, dst = time.localtime(date)
        if dst in (0, 1):
            tzname = time.tzname[dst]

    wday = daysofweek[wday]
    mon = months[mon]
    return _('$wday $mon $day $hh:$mm:$ss $tzname $year')
