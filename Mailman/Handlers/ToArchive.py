# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Add the message to the archives."""

import string
import time



def process(mlist, msg, msgdata):
    # short circuits
    if msgdata.get('isdigest') or not mlist.archive:
        return
    # Common practice seems to favor "X-No-Archive: yes".  I'm keeping
    # "X-Archive: no" for backwards compatibility.
    if string.lower(msg.getheader('x-no-archive', '')) == 'yes' or \
       string.lower(msg.getheader('x-archive', '')) == 'no':
        return
    #
    # TBD: This is a kludge around the archiver to properly support
    # clobber_date, which sets the date in the archive to the resent date
    # (i.e. now) instead of the potentially bogus date in the original
    # message.  We still want the outgoing message to contain the Date: header
    # as originally sent.
    #
    # Note that there should be a third option here: to clobber the date only
    # if it's bogus, i.e. way in the future or way in the past.
    date = archivedate = msg.getheader('date')
    try:
        if mlist.clobber_date:
            archivedate = time.ctime(time.time())
            msg['Date'] = archivedate
            msg['X-Original-Date'] = date
        # TBD: this needs to be converted to the new pipeline machinery
        mlist.ArchiveMail(msg, msgdata)
    finally:
        # Restore the original date
        msg['Date'] = date
