# Copyright (C) 2000-2012 by the Free Software Foundation, Inc.
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

"""Archive runner."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ArchiveRunner',
    ]


import copy
import logging

from email.utils import parsedate_tz, mktime_tz
from datetime import datetime
from lazr.config import as_timedelta

from mailman.config import config
from mailman.core.runner import Runner
from mailman.interfaces.archiver import ClobberDate
from mailman.utilities.datetime import RFC822_DATE_FMT, now


log = logging.getLogger('mailman.error')



def _should_clobber(msg, msgdata, archiver):
    """Should the Date header in the original message get clobbered?"""
    # Calculate the Date header of the message as a datetime.  What if there
    # are multiple Date headers, even in violation of the RFC?  For now, take
    # the first one.  If there are no Date headers, then definitely clobber.
    original_date = msg.get('date')
    if original_date is None:
        return True
    section = getattr(config.archiver, archiver, None)
    if section is None:
        log.error('No archiver config section found: {0}'.format(archiver))
        return False
    try:
        clobber = ClobberDate[section.clobber_date]
    except ValueError:
        log.error('Invalid clobber_date for "{0}": {1}'.format(
            archiver, section.clobber_date))
        return False
    if clobber is ClobberDate.always:
        return True
    elif clobber is ClobberDate.never:
        return False
    # Maybe we'll clobber the date.  Let's see if it's farther off from now
    # than the skew period.
    skew = as_timedelta(section.clobber_skew)
    try:
        time_tuple = parsedate_tz(original_date)
    except (ValueError, OverflowError):
        # The likely cause of this is that the year in the Date: field is
        # horribly incorrect, e.g. (from SF bug # 571634):
        #
        # Date: Tue, 18 Jun 0102 05:12:09 +0500
        #
        # Obviously clobber such dates.
        return True
    if time_tuple is None:
        # There was some other bogosity in the Date header.
        return True
    claimed_date = datetime.fromtimestamp(mktime_tz(time_tuple))
    return (abs(now() - claimed_date) > skew)



class ArchiveRunner(Runner):
    """The archive runner."""

    def _dispose(self, mlist, msg, msgdata):
        received_time = msgdata.get('received_time', now(strip_tzinfo=False))
        for archiver in config.archivers:
            msg_copy = copy.deepcopy(msg)
            if _should_clobber(msg, msgdata, archiver.name):
                original_date = msg_copy['date']
                del msg_copy['date']
                del msg_copy['x-original-date']
                msg_copy['Date'] = received_time.strftime(RFC822_DATE_FMT)
                if original_date:
                    msg_copy['X-Original-Date'] = original_date
            # A problem in one archiver should not prevent other archivers
            # from running.
            try:
                archiver.archive_message(mlist, msg_copy)
            except Exception:
                log.exception('Broken archiver: %s' % archiver.name)
