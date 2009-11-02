# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

"""Calculate the list owner recipients (includes moderators)."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'process',
    ]



def process(mlist, msg, msgdata):
    # The recipients are the owner and the moderator
    msgdata['recipients'] = mlist.owner + mlist.moderator
    # Don't decorate these messages with the header/footers
    msgdata['nodecorate'] = True
    msgdata['personalize'] = False
