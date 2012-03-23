# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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

"""The pipeline runner.

This runner's purpose is to take messages that have been approved for posting
through the 'preparation pipeline'.  This pipeline adds, deletes and modifies
headers, calculates message recipients, and more.
"""

from mailman.core.pipelines import process
from mailman.core.runner import Runner



class PipelineRunner(Runner):
    def _dispose(self, mlist, msg, msgdata):
        # Process the message through the mailing list's pipeline.
        pipeline = (mlist.owner_pipeline
                    if msgdata.get('to_owner', False)
                    else mlist.posting_pipeline)
        process(mlist, msg, msgdata, pipeline)
        # Do not keep this message queued.
        return False
