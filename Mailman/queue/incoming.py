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

"""Incoming queue runner.

This runner's sole purpose in life is to decide the disposition of the
message.  It can either be accepted for delivery, rejected (i.e. bounced),
held for moderator approval, or discarded.

When accepted, the message is forwarded on to the `prep queue` where it is
prepared for delivery.  Rejections, discards, and holds are processed
immediately.
"""



from Mailman.app.chains import process
from Mailman.configuration import config
from Mailman.queue import Runner



class IncomingRunner(Runner):
    QDIR = config.INQUEUE_DIR

    def _dispose(self, mlist, msg, msgdata):
        if msgdata.get('envsender') is None:
            msgdata['envsender'] = mlist.no_reply_address
        # Process the message through the mailing list's start chain.
        process(mlist, msg, msgdata, mlist.start_chain)
        # Do not keep this message queued.
        return False
