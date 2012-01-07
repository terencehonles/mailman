# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

"""Virgin runner.

This runner handles messages that the Mailman system gives virgin birth to.
E.g. acknowledgment responses to user posts or replybot messages.  They need
to go through some minimal processing before they can be sent out to the
recipient.
"""

from mailman.core.pipelines import process
from mailman.core.runner import Runner



class VirginRunner(Runner):
    def _dispose(self, mlist, msg, msgdata):
        # We need to fast track this message through any pipeline handlers
        # that touch it, e.g. especially cook-headers.
        msgdata['_fasttrack'] = True
        # Use the 'virgin' pipeline.
        process(mlist, msg, msgdata, 'virgin')
        # Do not keep this message queued.
        return False
