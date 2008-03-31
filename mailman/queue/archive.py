# Copyright (C) 2000-2008 by the Free Software Foundation, Inc.
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

"""Archive queue runner."""

from __future__ import with_statement

__metaclass__ = type
__all__ = [
    'ArchiveRunner',
    ]


import os
import time

from datetime import datetime
from email.Utils import parsedate_tz, mktime_tz, formatdate
from locknix.lockfile import Lock

from mailman.app.plugins import get_plugins
from mailman.configuration import config
from mailman.queue import Runner



class ArchiveRunner(Runner):
    QDIR = config.ARCHQUEUE_DIR

    def _dispose(self, mlist, msg, msgdata):
        # Support clobber_date, i.e. setting the date in the archive to the
        # received date, not the (potentially bogus) Date: header of the
        # original message.
        clobber = False
        original_date = msg.get('date')
        received_time = formatdate(msgdata['received_time'])
        if not original_date:
            clobber = True
        elif config.ARCHIVER_CLOBBER_DATE_POLICY == 1:
            clobber = True
        elif config.ARCHIVER_CLOBBER_DATE_POLICY == 2:
            # What's the timestamp on the original message?
            timetup = parsedate_tz(original_date)
            now = datetime.now()
            try:
                if not timetup:
                    clobber = True
                else:
                    utc_timestamp = datetime.fromtimestamp(mktime_tz(timetup))
                    clobber = (abs(now - utc_timestamp) > 
                               config.ARCHIVER_ALLOWABLE_SANE_DATE_SKEW)
            except (ValueError, OverflowError):
                # The likely cause of this is that the year in the Date: field
                # is horribly incorrect, e.g. (from SF bug # 571634):
                # Date: Tue, 18 Jun 0102 05:12:09 +0500
                # Obviously clobber such dates.
                clobber = True
        if clobber:
            del msg['date']
            del msg['x-original-date']
            msg['Date'] = received_time
            if original_date:
                msg['X-Original-Date'] = original_date
        # Always put an indication of when we received the message.
        msg['X-List-Received-Date'] = received_time
        # While a list archiving lock is acquired, archive the message.
        with Lock(os.path.join(mlist.data_path, 'archive.lck')):
            for archive_factory in get_plugins('mailman.archiver'):
                archiver = archive_factory(mlist)
                archiver.archive_message(msg)

