# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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

"""Move the message to the mail->news queue."""

import logging

from Mailman.configuration import config
from Mailman.queue import Switchboard

COMMASPACE = ', '

log = logging.getLogger('mailman.error')



def process(mlist, msg, msgdata):
    # short circuits
    if not mlist.gateway_to_news or \
           msgdata.get('isdigest') or \
           msgdata.get('fromusenet'):
        return
    # sanity checks
    error = []
    if not mlist.linked_newsgroup:
        error.append('no newsgroup')
    if not mlist.nntp_host:
        error.append('no NNTP host')
    if error:
        log.error('NNTP gateway improperly configured: %s',
                  COMMASPACE.join(error))
        return
    # Put the message in the news runner's queue
    newsq = Switchboard(config.NEWSQUEUE_DIR)
    newsq.enqueue(msg, msgdata, listname=mlist.fqdn_listname)
