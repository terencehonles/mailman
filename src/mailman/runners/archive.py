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


import os
import logging

from datetime import datetime
from email.utils import parsedate_tz, mktime_tz, formatdate
from flufl.lock import Lock
from lazr.config import as_timedelta

from mailman.config import config
from mailman.core.runner import Runner

log = logging.getLogger('mailman.error')



class ArchiveRunner(Runner):
    """The archive runner."""

    def _dispose(self, mlist, msg, msgdata):
        # Support clobber_date, i.e. setting the date in the archive to the
        # received date, not the (potentially bogus) Date: header of the
        # original message.
        clobber = False
        original_date = msg.get('date')
        received_time = formatdate(msgdata['received_time'])
        # FIXME 2012-03-23 BAW: LP: #963612
        ## if not original_date:
        ##     clobber = True
        ## elif int(config.archiver.pipermail.clobber_date_policy) == 1:
        ##     clobber = True
        ## elif int(config.archiver.pipermail.clobber_date_policy) == 2:
        ##     # What's the timestamp on the original message?
        ##     timetup = parsedate_tz(original_date)
        ##     now = datetime.now()
        ##     try:
        ##         if not timetup:
        ##             clobber = True
        ##         else:
        ##             utc_timestamp = datetime.fromtimestamp(mktime_tz(timetup))
        ##             date_skew = as_timedelta(
        ##                 config.archiver.pipermail.allowable_sane_date_skew)
        ##             clobber = (abs(now - utc_timestamp) > date_skew)
        ##     except (ValueError, OverflowError):
        ##         # The likely cause of this is that the year in the Date: field
        ##         # is horribly incorrect, e.g. (from SF bug # 571634):
        ##         # Date: Tue, 18 Jun 0102 05:12:09 +0500
        ##         # Obviously clobber such dates.
        ##         clobber = True
        ## if clobber:
        ##     del msg['date']
        ##     del msg['x-original-date']
        ##     msg['Date'] = received_time
        ##     if original_date:
        ##         msg['X-Original-Date'] = original_date
        # Always put an indication of when we received the message.
        msg['X-List-Received-Date'] = received_time
        # While a list archiving lock is acquired, archive the message.
        with Lock(os.path.join(mlist.data_path, 'archive.lck')):
            for archiver in config.archivers:
                # A problem in one archiver should not prevent other archivers
                # from running.
                try:
                    archiver.archive_message(mlist, msg)
                except Exception:
                    log.exception('Broken archiver: %s' % archiver.name)
