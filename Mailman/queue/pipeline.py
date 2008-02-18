# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""The pipeline queue runner.

This runner's purpose is to take messages that have been approved for posting
through the 'preparation pipeline'.  This pipeline adds, deletes and modifies
headers, calculates message recipients, and more.
"""

from Mailman.app.pipeline import process
from Mailman.configuration import config
from Mailman.queue import runner



class PipelineRunner(Runner):
    QDIR = config.PIPELINEQUEUE_DIR

    def _dispose(self, mlist, msg, msgdata):
        # Process the message through the mailing list's pipeline.
        process(mlist, msg, msgdata, mlist.pipeline)
        # Do not keep this message queued.
        return False
