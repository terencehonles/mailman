# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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

"""Send a message to the mailing list owner.

All messages to a list's -owner address should be piped through this script.
The -owner address is defined to be delivered directly to the list owners plus
the list moderators, with no intervention for bounce processing.

Stdin is the mail message, and argv[1] is the name of the target mailing list.

Errors are redirected to logs/error.
"""

import sys
import logging

from mailman import Utils
from mailman import loginit
from mailman.configuration import config
from mailman.i18n import _
from mailman.queue import Switchboard



def main():
    config.load()
    # Setup logging to stderr stream and error log.
    loginit.initialize(propagate=True)
    log = logging.getLogger('mailman.error')
    try:
        listname = sys.argv[1]
    except IndexError:
        log.error(_('owner script got no listname.'))
        sys.exit(1)
    # Make sure the list exists
    if not Utils.list_exists(listname):
        log.error(_('owner script, list not found: $listname'))
        sys.exit(1)
    # Queue the message for the owners.  We will send them through the
    # incoming queue because we need some processing done on the message.  The
    # processing is minimal though, so craft our own pipeline, expressly for
    # the purpose of delivering to the list owners.
    inq = Switchboard(config.INQUEUE_DIR)
    inq.enqueue(sys.stdin.read(),
                listname=listname,
                _plaintext=True,
                pipeline=config.OWNER_PIPELINE,
                toowner=True)



if __name__ == '__main__':
    main()
