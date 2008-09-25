# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

"""Process VERP'd bounces.

Called by the wrapper, stdin is the mail message, and argv[1] is the name
of the target mailing list.

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
    # Setup logging to stderr stream and error log.
    loginit.initialize(propagate=True)
    log = logging.getLogger('mailman.error')
    try:
        listname = sys.argv[1]
    except IndexError:
        log.error(_('bounces script got no listname.'))
        sys.exit(1)
    # Make sure the list exists
    if not Utils.list_exists(listname):
        log.error(_('bounces script, list not found: $listname'))
        sys.exit(1)
    # Immediately queue the message for the bounces qrunner to process.  The
    # advantage to this approach is that messages should never get lost --
    # some MTAs have a hard limit to the time a filter prog can run.  Postfix
    # is a good example; if the limit is hit, the proc is SIGKILL'd giving us
    # no chance to save the message.
    bounceq = Switchboard(config.BOUNCEQUEUE_DIR)
    bounceq.enqueue(sys.stdin.read(), listname=listname, _plaintext=True)



if __name__ == '__main__':
    main()
